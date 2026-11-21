#include <iostream>
#include <string_view>

int main() {
    constexpr std::string_view project = "ClassLab C++20";
    static_assert(project.starts_with("ClassLab"));
    std::cout << project << '\n';
}
