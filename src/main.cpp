#include <httplib.h>
#include <nlohmann/json.hpp>

#include <fcntl.h>
#include <sys/file.h>
#include <sys/stat.h>
#include <unistd.h>

#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <exception>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <mutex>
#include <random>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>

namespace fs = std::filesystem;
using Json = nlohmann::json;
using httplib::Request;
using httplib::Response;

namespace {

struct ApiError {
    int status;
    const char* message;
};

std::string random_id() {
    std::random_device random;
    constexpr std::string_view hex = "0123456789abcdef";
    std::string id;
    for (int i = 0; i < 32; ++i) {
        id += hex[random() & 15];
    }
    return id;
}

long long now() {
    using namespace std::chrono;
    return duration_cast<seconds>(system_clock::now().time_since_epoch()).count();
}

void reply(Response& response, const Json& body, int status = 200) {
    response.status = status;
    response.set_content(body.dump(), "application/json; charset=utf-8");
    response.set_header("Cache-Control", "no-store");
}

Json body_of(const Request& request) {
    auto body = Json::parse(request.body, nullptr, false);
    if (!body.is_object()) {
        throw ApiError{400, "请求内容必须是 JSON 对象。"};
    }
    return body;
}

std::string field(const Json& body, const char* key, std::size_t limit, bool allow_empty = false) {
    const auto value = body.find(key);
    if (value == body.end() || !value->is_string()) {
        throw ApiError{400, "请填写所有必填字段。"};
    }
    auto text = value->get<std::string>();
    if (text.size() > limit || (!allow_empty && text.find_first_not_of(" \t\r\n") == std::string::npos)) {
        throw ApiError{400, "字段不能为空或超出长度限制。"};
    }
    return text;
}

class Store {
public:
    explicit Store(fs::path path) : path_(std::move(path)) {
        if (path_.has_parent_path()) {
            fs::create_directories(path_.parent_path());
        }
        const auto lock_path = path_.string() + ".lock";
        lock_ = ::open(lock_path.c_str(), O_CREAT | O_RDWR | O_CLOEXEC, 0600);
        if (lock_ < 0 || ::flock(lock_, LOCK_EX | LOCK_NB) != 0) {
            if (lock_ >= 0) ::close(lock_);
            throw std::runtime_error("Cannot lock data file. Check permissions and running instances.");
        }
        try {
            if (fs::exists(path_)) {
                std::ifstream input(path_);
                input >> rooms_;
                if (!rooms_.is_object()) {
                    throw std::runtime_error("Invalid classroom data file.");
                }
            }
        } catch (...) {
            ::close(lock_);
            throw;
        }
    }

    ~Store() { ::close(lock_); }

    template <typename Operation>
    Json read(Operation operation) {
        std::lock_guard guard(mutex_);
        return operation(std::as_const(rooms_));
    }

    template <typename Operation>
    Json write(Operation operation) {
        std::lock_guard guard(mutex_);
        auto next = rooms_;
        auto result = operation(next);
        const auto temporary = path_.string() + ".tmp";
        const auto serialized = next.dump();
        try {
            std::ofstream output(temporary, std::ios::binary | std::ios::trunc);
            output.exceptions(std::ios::failbit | std::ios::badbit);
            output << serialized << '\n';
            output.close();
            fs::rename(temporary, path_);
        } catch (...) {
            std::error_code ignored;
            fs::remove(temporary, ignored);
            throw;
        }
        rooms_.swap(next);
        return result;
    }

private:
    fs::path path_;
    int lock_;
    Json rooms_ = Json::object();
    std::mutex mutex_;
};

template <typename Rooms>
auto& room_for(Rooms& rooms, const Request& request) {
    const auto found = rooms.find(request.matches[1].str());
    if (found == rooms.end()) {
        throw ApiError{404, "找不到这个课堂，请检查加入链接。"};
    }
    return *found;
}

void require_teacher(const Json& room, const Request& request) {
    if (room.at("teacherKey") != request.get_header_value("X-Teacher-Key")) {
        throw ApiError{403, "缺少此课堂的教师访问权限。"};
    }
}

std::string require_student(const Json& room, const Request& request) {
    auto key = request.get_header_value("X-Student-Key");
    if (!room.at("students").contains(key)) {
        throw ApiError{403, "请先加入课堂。"};
    }
    return key;
}

Json active_task(const Json& room) {
    const auto& tasks = room.at("tasks");
    return tasks.empty() ? Json(nullptr) : tasks.back();
}

Json progress(const Json& room) {
    const auto task = active_task(room);
    Json rows = Json::array();
    std::size_t submitted = 0;
    std::size_t attempts = 0;
    for (const auto& [key, student] : room.at("students").items()) {
        std::size_t count = 0;
        Json latest;
        for (const auto& submission : student.at("submissions")) {
            if (!task.is_null() && submission.at("taskId") == task.at("id")) {
                ++count;
                latest = submission.at("receivedAt");
            }
        }
        if (count > 0) ++submitted;
        attempts += count;
        rows.push_back({{"number", student.at("number")}, {"name", student.at("name")},
                        {"count", count}, {"lastSubmittedAt", latest}});
    }
    std::sort(rows.begin(), rows.end(), [](const Json& left, const Json& right) {
        return left.at("number") < right.at("number");
    });
    return {{"name", room.at("name")}, {"task", task}, {"joined", rows.size()},
            {"submitted", submitted}, {"attempts", attempts}, {"students", rows}};
}

void routes(httplib::Server& server, Store& store) {
    server.new_task_queue = [] { return new httplib::ThreadPool(8, 64); };
    server.set_payload_max_length(512 * 1024);
    server.set_default_headers({{"X-Content-Type-Options", "nosniff"},
                                {"Referrer-Policy", "no-referrer"},
                                {"Content-Security-Policy", "default-src 'self'; frame-ancestors 'none'; base-uri 'none'"}});
    server.set_exception_handler([](const Request&, Response& response, std::exception_ptr error) {
        try {
            std::rethrow_exception(error);
        } catch (const ApiError& failure) {
            reply(response, {{"error", failure.message}}, failure.status);
        } catch (const std::exception& failure) {
            std::cerr << "ClassLab request error: " << failure.what() << '\n';
            reply(response, {{"error", "服务器未能完成请求，请稍后重试。"}}, 500);
        }
    });
    server.set_error_handler([](const Request& request, Response& response) {
        if (request.path.starts_with("/api/") && response.body.empty()) {
            reply(response, {{"error", "请求地址或大小无效。"}}, response.status);
        }
    });

    server.Get("/", [](const Request&, Response& response) {
        response.set_file_content(CLASSLAB_WEB_DIR "/teacher.html", "text/html; charset=utf-8");
    });
    server.Get(R"(/join/[a-f0-9]{32})", [](const Request&, Response& response) {
        response.set_file_content(CLASSLAB_WEB_DIR "/student.html", "text/html; charset=utf-8");
    });
    server.Get(R"(/(app\.js|style\.css|vendor/qrcode\.js))", [](const Request& request, Response& response) {
        const auto type = request.path.ends_with(".js") ? "text/javascript" : "text/css";
        response.set_file_content(std::string(CLASSLAB_WEB_DIR) + request.path, type);
    });
    server.Get("/api/health", [](const Request&, Response& response) {
        reply(response, {{"status", "ready"}});
    });

    server.Post("/api/rooms", [&](const Request& request, Response& response) {
        const auto name = field(body_of(request), "name", 120);
        reply(response, store.write([&](Json& rooms) -> Json {
            const auto id = random_id();
            const auto key = random_id();
            rooms[id] = {{"name", name}, {"teacherKey", key}, {"tasks", Json::array()},
                         {"students", Json::object()}};
            return {{"id", id}, {"teacherKey", key}};
        }), 201);
    });
    server.Post(R"(/api/rooms/([a-f0-9]{32})/tasks)", [&](const Request& request, Response& response) {
        const auto body = body_of(request);
        reply(response, store.write([&](Json& rooms) -> Json {
            auto& room = room_for(rooms, request);
            require_teacher(room, request);
            Json task = {{"id", random_id()}, {"title", field(body, "title", 160)},
                         {"description", field(body, "description", 10000)},
                         {"starterCode", field(body, "starterCode", 65536, true)}};
            room["tasks"].push_back(task);
            return task;
        }), 201);
    });
    server.Get(R"(/api/rooms/([a-f0-9]{32})/progress)", [&](const Request& request, Response& response) {
        reply(response, store.read([&](const Json& rooms) {
            const auto& room = room_for(rooms, request);
            require_teacher(room, request);
            return progress(room);
        }));
    });
    server.Post(R"(/api/rooms/([a-f0-9]{32})/students)", [&](const Request& request, Response& response) {
        const auto name = field(body_of(request), "name", 120);
        reply(response, store.write([&](Json& rooms) -> Json {
            auto& room = room_for(rooms, request);
            const auto key = random_id();
            auto& students = room.at("students");
            const auto number = students.size() + 1;
            students[key] = {{"number", number}, {"name", name}, {"submissions", Json::array()}};
            return {{"studentKey", key}};
        }), 201);
    });
    server.Get(R"(/api/rooms/([a-f0-9]{32})/task)", [&](const Request& request, Response& response) {
        reply(response, store.read([&](const Json& rooms) -> Json {
            const auto& room = room_for(rooms, request);
            const auto key = require_student(room, request);
            return {{"roomName", room.at("name")}, {"studentName", room.at("students").at(key).at("name")},
                    {"task", active_task(room)}};
        }));
    });
    server.Post(R"(/api/rooms/([a-f0-9]{32})/submissions)", [&](const Request& request, Response& response) {
        const auto body = body_of(request);
        reply(response, store.write([&](Json& rooms) -> Json {
            auto& room = room_for(rooms, request);
            const auto key = require_student(room, request);
            const auto task = active_task(room);
            const auto task_id = field(body, "taskId", 32);
            if (task.is_null() || task.at("id") != task_id) {
                throw ApiError{409, "教师已更新任务，请刷新任务后再提交。"};
            }
            const auto received_at = now();
            room["students"][key]["submissions"].push_back({
                {"taskId", task_id}, {"code", field(body, "code", 65536)}, {"receivedAt", received_at}
            });
            return {{"status", "received"}, {"receivedAt", received_at}};
        }), 201);
    });
}

std::string setting(const char* key, const char* fallback) {
    const char* value = std::getenv(key);
    return value == nullptr ? fallback : value;
}

} // namespace

int main() {
    try {
        ::umask(0077);
        Store store(setting("CLASSLAB_DATA", "data/classrooms.json"));
        const auto host = setting("CLASSLAB_HOST", "127.0.0.1");
        const auto port_text = setting("CLASSLAB_PORT", "8080");
        std::size_t parsed = 0;
        const auto port = std::stoi(port_text, &parsed);
        if (parsed != port_text.size() || port < 0 || port > 65535) {
            throw std::runtime_error("Invalid CLASSLAB_PORT.");
        }
        httplib::Server server;
        routes(server, store);
        const auto bound_port = port == 0 ? server.bind_to_any_port(host)
                                          : (server.bind_to_port(host, port) ? port : -1);
        if (bound_port < 0) throw std::runtime_error("Cannot bind HTTP server.");
        std::cout << "ClassLab listening on " << host << ':' << bound_port << std::endl;
        return server.listen_after_bind() ? 0 : 1;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
