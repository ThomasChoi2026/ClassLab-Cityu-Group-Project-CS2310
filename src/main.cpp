#include "judge_client.hpp"

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
#include <map>
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
    response.set_content(body.dump(-1, ' ', false, Json::error_handler_t::replace), "application/json; charset=utf-8");
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

Json test_cases(const Json& body) {
    const auto& tests = body.at("testCases");
    if (!tests.is_array() || tests.empty() || tests.size() > 12) {
        throw ApiError{400, "每项评测任务需要 1 到 12 个测试用例。"};
    }
    Json normalized = Json::array();
    for (const auto& test : tests) {
        if (!test.is_object()) throw ApiError{400, "测试用例格式无效。"};
        const auto visibility = field(test, "visibility", 6);
        if (visibility != "public" && visibility != "hidden") {
            throw ApiError{400, "测试用例只能设为公开或隐藏。"};
        }
        normalized.push_back({{"id", std::to_string(normalized.size() + 1)},
            {"name", field(test, "name", 120)}, {"visibility", visibility},
            {"input", field(test, "input", 8192, true)},
            {"expectedOutput", field(test, "expectedOutput", 8192, true)}});
    }
    return normalized;
}

Json progress(const Json& room) {
    const auto task = active_task(room);
    const auto task_id = task.is_null() ? Json(nullptr) : task.at("id");
    Json rows = Json::array();
    Json cases = Json::array();
    std::map<std::string, Json> errors;
    std::size_t submitted = 0, attempts = 0, accepted = 0, failed = 0, pending = 0, unjudged = 0;
    if (!task.is_null()) {
        for (const auto& test : judging::cases_for(task)) {
            cases.push_back({{"id", test.at("id")}, {"name", test.at("name")},
                {"visibility", test.at("visibility")}, {"passed", 0}, {"failed", 0}});
        }
    }
    for (const auto& [key, student] : room.at("students").items()) {
        const auto& submissions = student.at("submissions");
        const auto count = std::count_if(submissions.begin(), submissions.end(),
            [&](const Json& item) { return item.at("taskId") == task_id; });
        attempts += count;
        Json row = {{"number", student.at("number")}, {"name", student.at("name")}, {"count", count},
                    {"lastSubmittedAt", nullptr}, {"latestStatus", "not_submitted"}};
        if (const auto* latest = judging::latest_for(student, task_id)) {
            ++submitted;
            const auto result = judging::result_for(*latest);
            const auto status = result.at("status").get<std::string>();
            row["lastSubmittedAt"] = latest->at("receivedAt");
            row["latestStatus"] = status;
            if (result.contains("passed")) row["passed"] = result.at("passed");
            if (result.contains("total")) row["total"] = result.at("total");
            if (status == "accepted") ++accepted;
            else if (status == "pending") ++pending;
            else if (status == "compilation_error" || judging::case_failed(status)) ++failed;
            else ++unjudged;

            if (status == "compilation_error") {
                const auto [category, message] = judging::classify_diagnostic(result.value("diagnostic", ""));
                auto [entry, inserted] = errors.try_emplace(std::string(category), Json{
                    {"category", category}, {"count", 0}, {"example", message},
                    {"studentNumber", student.at("number")}});
                auto& group = entry->second;
                group["count"] = group.at("count").get<unsigned>() + 1;
                if (!inserted && student.at("number") < group.at("studentNumber")) {
                    group["studentNumber"] = student.at("number");
                    group["example"] = message;
                }
            }

            const auto outcomes = result.value("cases", Json::array());
            for (auto& test : cases) {
                const auto outcome = std::find_if(outcomes.begin(), outcomes.end(), [&](const Json& item) {
                    return item.at("testId") == test.at("id");
                });
                if (outcome == outcomes.end()) continue;
                const auto& status = outcome->at("status");
                const char* field = status == "passed" ? "passed" :
                    (judging::case_failed(status) ? "failed" : nullptr);
                if (field) test[field] = test.at(field).get<unsigned>() + 1;
            }
        }
        rows.push_back(std::move(row));
    }
    std::sort(rows.begin(), rows.end(), [](const Json& left, const Json& right) {
        return left.at("number") < right.at("number");
    });
    Json groups = Json::array();
    for (const auto& [category, group] : errors) groups.push_back(group);
    std::sort(groups.begin(), groups.end(), [](const Json& left, const Json& right) {
        if (left.at("count") != right.at("count")) return left.at("count") > right.at("count");
        return left.at("category") < right.at("category");
    });
    return {{"name", room.at("name")}, {"task", task}, {"joined", rows.size()}, {"unsubmitted", rows.size() - submitted},
            {"submitted", submitted}, {"attempts", attempts}, {"students", rows},
            {"accepted", accepted}, {"failed", failed}, {"pending", pending}, {"unjudged", unjudged},
            {"caseStats", cases}, {"errorGroups", groups}};
}

Json receipt_for(const Json& submission) {
    Json receipt = {{"status", "received"}, {"receivedAt", submission.at("receivedAt")}};
    if (submission.contains("judgement")) receipt["judgement"] = submission.at("judgement").at("status");
    return receipt;
}

void routes(httplib::Server& server, Store& store, judging::Client& judge) {
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
            if (body.contains("testCases")) task["testCases"] = test_cases(body);
            room["tasks"].push_back(task);
            return task;
        }), 201);
    });
    server.Get(R"(/api/rooms/([a-f0-9]{32})/progress)", [&](const Request& request, Response& response) {
        auto result = store.read([&](const Json& rooms) {
            const auto& room = room_for(rooms, request);
            require_teacher(room, request);
            return progress(room);
        });
        result["executionAvailable"] = judge.available();
        reply(response, result);
    });
    server.Get(R"(/api/rooms/([a-f0-9]{32})/latest/([1-9][0-9]{0,15}))",
        [&](const Request& request, Response& response) {
            reply(response, store.read([&](const Json& rooms) -> Json {
                const auto& room = room_for(rooms, request);
                require_teacher(room, request);
                const auto task = active_task(room);
                if (task.is_null() || task.at("id") != request.get_param_value("taskId")) {
                    throw ApiError{409, "当前任务已切换，请重新打开提交记录。"};
                }
                const auto number = std::stoull(request.matches[2].str());
                for (const auto& student : room.at("students")) {
                    if (student.at("number") != number) continue;
                    if (const auto* latest = judging::latest_for(student, task.at("id"))) {
                        return {{"name", student.at("name")}, {"code", latest->at("code")},
                                {"result", judging::result_for(*latest)}};
                    }
                    break;
                }
                throw ApiError{404, "没有找到这位学生的提交。"};
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
        auto result = store.read([&](const Json& rooms) -> Json {
            const auto& room = room_for(rooms, request);
            const auto key = require_student(room, request);
            const auto& student = room.at("students").at(key);
            const auto task = active_task(room);
            Json latest_result;
            if (!task.is_null()) {
                if (const auto* latest = judging::latest_for(student, task.at("id"))) {
                    latest_result = judging::student_result(*latest, task);
                }
            }
            return {{"roomName", room.at("name")}, {"studentName", student.at("name")},
                    {"task", judging::student_task(task)}, {"latestResult", latest_result}};
        });
        result["executionAvailable"] = judge.available();
        reply(response, result);
    });
    server.Post(R"(/api/rooms/([a-f0-9]{32})/run)", [&](const Request& request, Response& response) {
        const auto body = body_of(request);
        store.read([&](const Json& rooms) -> Json {
            const auto& room = room_for(rooms, request);
            require_student(room, request);
            const auto task = active_task(room);
            if (task.is_null() || task.at("id") != field(body, "taskId", 32)) {
                throw ApiError{409, "教师已更新任务，请刷新后再运行。"};
            }
            field(body, "code", 65536);
            field(body, "input", 8192, true);
            return nullptr;
        });
        auto slot = judge.reserve();
        if (!slot && judge.configured()) throw ApiError{429, "评测器正在处理另一请求，请稍后重试。"};
        if (!judge.available()) {
            reply(response, {{"status", "judge_unavailable"},
                             {"error", "隔离执行器不可用，程序未运行。"}}, 503);
            return;
        }
        reply(response, judge.run(body.at("code").get<std::string>(), body.at("input").get<std::string>()));
    });
    server.Post(R"(/api/rooms/([a-f0-9]{32})/submissions)", [&](const Request& request, Response& response) {
        const auto body = body_of(request);
        const auto task_id = field(body, "taskId", 32);
        const auto code = field(body, "code", 65536);
        store.read([&](const Json& rooms) -> Json {
            require_student(room_for(rooms, request), request);
            return nullptr;
        });
        auto slot = judge.reserve();
        Json tests;
        std::string student_key;
        std::string submission_id;
        const auto available = slot && judge.available();
        auto receipt = store.write([&](Json& rooms) -> Json {
            auto& room = room_for(rooms, request);
            student_key = require_student(room, request);
            const auto task = active_task(room);
            if (task.is_null() || task.at("id") != task_id) {
                throw ApiError{409, "教师已更新任务，请刷新任务后再提交。"};
            }
            auto& submissions = room["students"][student_key]["submissions"];
            Json submission = {{"taskId", task_id}, {"code", code}, {"receivedAt", now()}};
            if (body.contains("requestId")) {
                const auto request_id = field(body, "requestId", 64);
                for (const auto& saved : submissions) {
                    if (saved.at("taskId") != task_id || saved.value("requestId", "") != request_id) continue;
                    if (saved.at("code") != code) throw ApiError{409, "提交编号与已保存的代码不一致。"};
                    return receipt_for(saved);
                }
                submission["requestId"] = request_id;
            }
            if (task.contains("testCases")) {
                if (!slot && judge.configured()) throw ApiError{429, "评测器正在处理另一请求，请稍后重试。"};
                submission["judgement"] = {{"status", available ? "pending" : "judge_unavailable"}};
                if (available) {
                    submission_id = random_id();
                    submission["id"] = submission_id;
                    tests = judging::cases_for(task);
                }
            }
            submissions.push_back(submission);
            return receipt_for(submission);
        });
        if (!submission_id.empty()) {
            const auto result = judge.grade(code, tests);
            receipt = store.write([&](Json& rooms) -> Json {
                auto& submissions = room_for(rooms, request).at("students").at(student_key).at("submissions");
                for (auto& saved : submissions) {
                    if (saved.value("id", "") != submission_id) continue;
                    saved["judgement"] = result;
                    return receipt_for(saved);
                }
                throw std::runtime_error("Pending submission disappeared");
            });
        }
        reply(response, receipt, 201);
    });

}

void recover_pending(Store& store) {
    const auto contains_pending = [](const Json& submission) {
        return submission.contains("judgement") && submission.at("judgement").at("status") == "pending";
    };
    const auto pending = store.read([&](const Json& rooms) -> Json {
        for (const auto& room : rooms) {
            for (const auto& student : room.at("students")) {
                const auto& submissions = student.at("submissions");
                if (std::any_of(submissions.begin(), submissions.end(), contains_pending)) return true;
            }
        }
        return false;
    });
    if (pending == true) {
        store.write([&](Json& rooms) -> Json {
            for (auto& room : rooms) {
                for (auto& student : room.at("students")) {
                    for (auto& submission : student.at("submissions")) {
                        if (contains_pending(submission)) submission["judgement"] = {{"status", "judge_error"}};
                    }
                }
            }
            return nullptr;
        });
    }
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
        recover_pending(store);
        judging::Client judge(setting("CLASSLAB_JUDGE_SOCKET", ""));
        routes(server, store, judge);
        server.set_write_timeout(120);
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
