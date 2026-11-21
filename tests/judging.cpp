#include "judging.hpp"

#include <iostream>
#include <string_view>

int main() {
    using judging::normalize_output;
    const bool output_rules =
        normalize_output("a\r\nb\r\n") == normalize_output("a\nb") &&
        normalize_output("8\n") == normalize_output("8") &&
        normalize_output("8\n\n") != normalize_output("8") &&
        normalize_output("8 ") != normalize_output("8") &&
        normalize_output("8\r") != normalize_output("8") &&
        normalize_output("8\n9") != normalize_output("8 9");

    const auto classified = [](std::string_view diagnostic, std::string_view category) {
        return judging::classify_diagnostic(diagnostic).first == category;
    };
    const bool classification =
        classified("note: next line\nfile.cpp:1: error: expected ‘;’ before ‘}’", "missing_semicolon") &&
        classified("error: use of undeclared identifier 'test'", "undeclared_identifier") &&
        classified("fatal error: header: No such file or directory", "header_or_namespace") &&
        classified("error: cannot convert 'int' to 'const char*'", "type_mismatch") &&
        classified("error: expected primary-expression", "syntax") &&
        classified("note: example mentions syntax error", "other");

    if (!output_rules || !classification) {
        std::cerr << "Judging helpers failed. Output rules: " << output_rules
                  << ", classification: " << classification << '\n';
        return 1;
    }
}
