#pragma once

#include <nlohmann/json.hpp>
#include <algorithm>
#include <map>
#include <string>
#include <string_view>
#include <tuple>
#include <vector>

namespace review {
using Json = nlohmann::json;
using Lines = std::vector<std::string_view>;

// Keep a final empty line so adding/removing the final newline is observable.
inline Lines lines(std::string_view code) {
    Lines result;
    while (!code.empty()) {
        const auto end = code.find('\n');
        if (end == code.npos) {
            result.push_back(code);
            break;
        }
        auto line = code.substr(0, end);
        if (line.ends_with('\r')) line.remove_suffix(1);
        result.push_back(line);
        code.remove_prefix(end + 1);
        if (code.empty()) result.emplace_back();
    }
    return result;
}

// A short contiguous edit, anchored in the starter. Ignore large rewrites.
// All views refer to strings owned by the current classroom snapshot.
class Patterns {
    using Key = std::tuple<std::size_t, Lines, Lines>;
    struct Group {
        unsigned count = 0;
        unsigned example = 0;
        std::map<std::string, unsigned> outcomes;
    };
    Lines starter_;
    std::map<Key, Group> groups_;
public:
    explicit Patterns(std::string_view starter) : starter_(lines(starter)) {}

    void observe(std::string_view code, unsigned student, const std::string& status) {
        const auto edited = lines(code);
        std::size_t first = 0, oldEnd = starter_.size(), newEnd = edited.size();
        while (first < oldEnd && first < newEnd && starter_[first] == edited[first]) ++first;
        while (oldEnd > first && newEnd > first && starter_[oldEnd-1] == edited[newEnd-1]) {
            --oldEnd;
            --newEnd;
        }
        if (oldEnd == first && newEnd == first) return;
        if (oldEnd - first > 3 || newEnd - first > 3) return;
        Lines before(starter_.begin() + first, starter_.begin() + oldEnd);
        Lines after(edited.begin() + first, edited.begin() + newEnd);
        for (const auto& block : {before, after})
            for (auto line : block) if (line.size() > 240) return;
        auto& group = groups_[{first, before, after}];
        ++group.count;
        ++group.outcomes[status];
        if (!group.example || student < group.example) group.example = student;
    }

    Json summary() const {
        Json rows = Json::array();
        for (const auto& [key, group] : groups_) {
            if (group.count < 2) continue;
            const auto& [first, before, after] = key;
            rows.push_back({{"line", first + 1}, {"before", before}, {"after", after},
                {"count", group.count}, {"outcomes", group.outcomes}, {"studentNumber", group.example}});
        }
        std::stable_sort(rows.begin(), rows.end(), [](const Json& a, const Json& b) {
            return a.at("count") > b.at("count");
        });
        if (rows.size() > 6) rows.erase(rows.begin() + 6, rows.end());
        return rows;
    }
};
} // namespace review
