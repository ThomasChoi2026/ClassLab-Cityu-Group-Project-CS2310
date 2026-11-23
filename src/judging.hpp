#pragma once

#include <nlohmann/json.hpp>

#include <algorithm>
#include <cctype>
#include <string>
#include <string_view>

namespace judging {
using Json = nlohmann::json;

// CRLF and one final newline are equivalent. Other bytes remain significant.
inline std::string normalize_output(std::string_view output) {
    std::string normalized;
    for (std::size_t i = 0; i < output.size(); ++i) {
        if (output[i] == '\r' && i + 1 < output.size() && output[i + 1] == '\n') continue;
        normalized += output[i];
    }
    if (!normalized.empty() && normalized.back() == '\n') normalized.pop_back();
    return normalized;
}

inline Json cases_for(const Json& task) {
    return task.value("testCases", Json::array());
}

inline Json student_task(const Json& task) {
    if (task.is_null()) return nullptr;
    Json visible = {{"id", task.at("id")}, {"title", task.at("title")},
                    {"description", task.at("description")}, {"starterCode", task.at("starterCode")}};
    if (task.contains("testCases")) {
        visible["testCases"] = Json::array();
        for (const auto& test : cases_for(task)) {
            if (test.at("visibility") == "public") {
                visible["testCases"].push_back({{"name", test.at("name")},
                    {"input", test.at("input")}, {"expectedOutput", test.at("expectedOutput")}});
            }
        }
    }
    return visible;
}

inline const Json* latest_for(const Json& student, const Json& task_id) {
    const auto& submissions = student.at("submissions");
    const auto found = std::find_if(submissions.rbegin(), submissions.rend(), [&](const Json& submission) {
        return submission.at("taskId") == task_id;
    });
    return found == submissions.rend() ? nullptr : &*found;
}

inline Json result_for(const Json& submission) {
    return submission.value("judgement", Json{{"status", "received"}});
}

inline Json student_result(const Json& submission, const Json& task) {
    const auto result = result_for(submission);
    Json visible = {{"status", result.at("status")}, {"receivedAt", submission.at("receivedAt")}};
    if (result.value("demoFixture", false)) visible["demoFixture"] = true;
    if (result.contains("passed")) visible["passed"] = result.at("passed");
    if (result.contains("total")) visible["total"] = result.at("total");
    if (result.at("status") == "compilation_error" && result.contains("diagnostic")) {
        visible["diagnostic"] = result.at("diagnostic");
    }
    visible["cases"] = Json::array();
    std::size_t hidden_number = 0;
    const auto results = result.value("cases", Json::array());
    for (const auto& test : cases_for(task)) {
        const bool public_case = test.at("visibility") == "public";
        if (!public_case) ++hidden_number;
        const auto outcome = std::find_if(results.begin(), results.end(), [&](const Json& item) {
            return item.at("testId") == test.at("id");
        });
        if (outcome == results.end()) continue;
        const auto& status = outcome->at("status");
        const bool recognized = status == "passed" || status == "wrong_answer" ||
            status == "runtime_error" || status == "time_limit" || status == "resource_limit" ||
            status == "judge_error";
        Json row = {{"status", recognized ? status : Json("judge_error")}};
        if (public_case) {
            row["name"] = test.at("name");
            row["input"] = test.at("input");
            row["expectedOutput"] = test.at("expectedOutput");
            if (outcome->contains("actualOutput")) row["actualOutput"] = outcome->at("actualOutput");
        } else {
            row["name"] = "隐藏测试 " + std::to_string(hidden_number);
        }
        visible["cases"].push_back(std::move(row));
    }
    return visible;
}

inline std::pair<std::string_view, std::string> classify_diagnostic(std::string_view log) {
    while (!log.empty()) {
        const auto end = log.find('\n');
        const auto line = log.substr(0, end);
        log = end == std::string_view::npos ? std::string_view{} : log.substr(end + 1);
        const auto marker = line.find("error: ");
        if (marker == std::string_view::npos) continue;
        const auto message = line.substr(marker + 7);
        std::string lower(message);
        std::transform(lower.begin(), lower.end(), lower.begin(), [](unsigned char ch) {
            return static_cast<char>(std::tolower(ch));
        });
        const auto has = [&](std::string_view text) { return lower.find(text) != std::string::npos; };
        std::string_view category = "other";
        if (has("expected") && (has("';'") || has("‘;’") ||
            has("semicolon"))) {
            category = "missing_semicolon";
        } else if (has("no such file or directory") || has("file not found") ||
                   has("is not a member of") || has("using namespace")) {
            category = "header_or_namespace";
        } else if (has("undeclared identifier") || has("not declared in this scope")) {
            category = "undeclared_identifier";
        } else if (has("cannot convert") || has("invalid conversion") ||
                   has("incompatible types") || has("invalid operands")) {
            category = "type_mismatch";
        } else if (has("expected") || has("syntax error")) {
            category = "syntax";
        }
        return {category, std::string(message.substr(0, 240))};
    }
    return {"other", ""};
}

inline bool case_failed(const Json& status) {
    return status == "wrong_answer" || status == "runtime_error" ||
           status == "time_limit" || status == "resource_limit";
}
inline Json history_for(const Json& student, const Json& task_id) {
    Json history = Json::array();
    constexpr std::size_t limit = 50;
    const auto& submissions = student.at("submissions");
    for (auto it = submissions.rbegin(); it != submissions.rend() && history.size() < limit; ++it) {
        if (it->at("taskId") != task_id) continue;
        const auto result = result_for(*it);
        Json item = {{"receivedAt", it->at("receivedAt")}, {"status", result.at("status")}};
        if (result.contains("passed") && result.contains("total")) {
            item["passed"] = result.at("passed");
            item["total"] = result.at("total");
        }
        history.push_back(std::move(item));
    }
    return history;
}
} // namespace judging
