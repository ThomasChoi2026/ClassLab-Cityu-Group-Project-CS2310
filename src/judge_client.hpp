#pragma once

#include "judging.hpp"

#include <httplib.h>
#include <chrono>
#include <mutex>
#include <string>
#include <string_view>

namespace judging {

inline std::string decode_output(std::string_view hex) {
    if (hex.size() > 32768 || hex.size() % 2 != 0) throw std::runtime_error("invalid output");
    const auto digit = [](char ch) {
        if (ch >= '0' && ch <= '9') return ch - '0';
        if (ch >= 'a' && ch <= 'f') return ch - 'a' + 10;
        throw std::runtime_error("invalid output");
    };
    std::string output;
    output.reserve(hex.size() / 2);
    for (std::size_t i = 0; i < hex.size(); i += 2) {
        output.push_back(static_cast<char>(16 * digit(hex[i]) + digit(hex[i + 1])));
    }
    return output;
}

inline std::string public_text(const std::string& bytes) {
    return Json::parse(Json(bytes).dump(-1, ' ', false, Json::error_handler_t::replace)).get<std::string>();
}

inline std::string limited_text(const Json& data, const char* key, std::size_t limit) {
    auto text = data.value(key, std::string{});
    if (text.size() > limit) {
        text.resize(limit);
        text = public_text(text);
    }
    return text;
}

class Client {
public:
    explicit Client(std::string socket, bool demo = false) : socket_(std::move(socket)), demo_(demo) {}

    bool demo() const { return demo_; }

    bool configured() const { return !socket_.empty(); }

    bool available() const {
        if (socket_.empty()) return false;
        return request("", nullptr).value("status", "") == "ready";
    }

    bool can_start() const {
        const auto health = request("", nullptr);
        return health.value("status", "") == "ready" && health.value("busy", Json(false)) == false;
    }

    std::unique_lock<std::mutex> reserve() { return std::unique_lock(slot_, std::try_to_lock); }

    Json run(const std::string& code, const std::string& input, bool probe = false) const {
        const auto reply = request(code, Json::array({probe ? std::string{} : input}),
                                   probe ? "probe" : "run");
        const auto status = reply.value("status", "");
        if (demo_ && status == "demo_no_fixture") {
            return {{"status", "demo_no_fixture"},
                    {"error", "仅支持课堂演示 Notebook 的预置代码与输入：2 3、0 0、-4 9；这里没有编译或运行任意 C++。"}};
        }
        if (probe && status == "stdin_required") {
            try {
                return {{"status", "stdin_required"},
                        {"stdout", public_text(decode_output(reply.at("stdoutHex").get<std::string>()))},
                        {"stderr", limited_text(reply, "stderr", 16384)}};
            } catch (const std::exception&) {
                return judge_error();
            }
        }
        if (status != "success") return failure(reply);
        try {
            if (!reply.at("cases").is_array() || reply.at("cases").size() != 1) return judge_error();
            const auto& outcome = reply.at("cases").at(0);
            const auto result = checked_status(outcome);
            if (result == "judge_error") return judge_error();
            Json visible = {{"status", result}, {"stdout", public_text(decode_output(outcome.at("stdoutHex").get<std::string>()))},
                            {"stderr", limited_text(outcome, "stderr", 16384)}};
            if (outcome.contains("exitCode")) visible["exitCode"] = outcome.at("exitCode").get<int>();
            return visible;
        } catch (const std::exception&) {
            return judge_error();
        }
    }

    Json grade(const std::string& code, const Json& tests) const {
        Json inputs = Json::array();
        for (const auto& test : tests) inputs.push_back(test.at("input"));
        const auto reply = request(code, inputs, "grade");
        if (demo_ && reply.value("status", "") == "demo_no_fixture") return {{"status", "demo_no_fixture"}};
        if (reply.value("status", "") != "success") return failure(reply);
        try {
            const auto& cases = reply.at("cases");
            if (!cases.is_array() || cases.size() != tests.size()) return judge_error();
            Json outcomes = Json::array();
            std::size_t passed = 0;
            std::string overall = "accepted";
            for (std::size_t i = 0; i < tests.size(); ++i) {
                const auto& test = tests.at(i);
                const auto& worker = cases.at(i);
                auto status = checked_status(worker);
                if (status == "judge_error") return judge_error();
                const auto output = decode_output(worker.at("stdoutHex").get<std::string>());
                if (status == "success") {
                    status = normalize_output(output) == normalize_output(test.at("expectedOutput").get<std::string>())
                        ? "passed" : "wrong_answer";
                }
                if (status == "passed") {
                    ++passed;
                } else if (overall == "accepted" || (overall == "wrong_answer" && status != "wrong_answer")) {
                    overall = status;
                }
                Json item = {{"testId", test.at("id")}, {"status", status}};
                if (test.at("visibility") == "public") item["actualOutput"] = public_text(output);
                outcomes.push_back(std::move(item));
            }
            return {{"status", overall}, {"passed", passed}, {"total", tests.size()}, {"cases", outcomes}};
        } catch (const std::exception&) {
            return judge_error();
        }
    }

private:
    static Json judge_error() { return {{"status", "judge_error"}}; }

    static std::string checked_status(const Json& result) {
        const auto status = result.at("status").get<std::string>();
        if (status == "success" || status == "runtime_error" || status == "time_limit" ||
            status == "resource_limit") return status;
        return "judge_error";
    }

    static Json failure(const Json& result) {
        try {
            const auto status = result.value("status", "");
            if (status == "compilation_error") {
                return {{"status", status}, {"diagnostic", limited_text(result, "diagnostic", 16384)}};
            }
            if (status == "time_limit" || status == "resource_limit") return {{"status", status}};
        } catch (const std::exception&) {
            return judge_error();
        }
        return judge_error();
    }

    Json request(const std::string& code, const Json& inputs, std::string_view mode = {}) const {
        try {
            const bool health = inputs.is_null();
            httplib::Client client(socket_, 80);
            client.set_address_family(AF_UNIX);
            client.set_follow_location(false);
            client.set_connection_timeout(0, 300000);
            client.set_read_timeout(health ? 1 : 110);
            client.set_write_timeout(3);
            const auto result = health ? client.Get("/health") :
                client.Post("/evaluate", Json{{"version", 1}, {"code", code}, {"inputs", inputs}, {"mode", mode}}.dump(), "application/json");
            if (!result || result->status != 200 || result->body.size() > 600000) return judge_error();
            const auto data = Json::parse(result->body, nullptr, false);
            if (!data.is_object() || data.value("version", 0) != 1 || data.value("demoFixture", false) != demo_ ||
                !data.contains("status") || !data.at("status").is_string()) return judge_error();
            return data;
        } catch (const std::exception&) {
            return judge_error();
        }
    }

    std::string socket_;
    bool demo_;
    std::mutex slot_;
};

} // namespace judging
