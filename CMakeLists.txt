cmake_minimum_required(VERSION 3.24)
project(ClassLab LANGUAGES CXX)

add_executable(classlab src/main.cpp)
target_compile_features(classlab PRIVATE cxx_std_20)
set_target_properties(classlab PROPERTIES CXX_EXTENSIONS OFF)

include(FetchContent)
set(HTTPLIB_USE_OPENSSL_IF_AVAILABLE OFF CACHE BOOL "")
set(HTTPLIB_USE_ZLIB_IF_AVAILABLE OFF CACHE BOOL "")
set(HTTPLIB_USE_BROTLI_IF_AVAILABLE OFF CACHE BOOL "")
set(HTTPLIB_USE_ZSTD_IF_AVAILABLE OFF CACHE BOOL "")
set(JSON_BuildTests OFF CACHE INTERNAL "")
FetchContent_Declare(httplib
    URL https://codeload.github.com/yhirose/cpp-httplib/tar.gz/refs/tags/v0.28.0
    URL_HASH SHA256=ccb32f9832c906d571f61794f453223dbb724ba738265551e3cd28ca325b529d)
FetchContent_Declare(json
    URL https://codeload.github.com/nlohmann/json/tar.gz/refs/tags/v3.12.0
    URL_HASH SHA256=4b92eb0c06d10683f7447ce9406cb97cd4b453be18d7279320f7b2f025c10187)
FetchContent_MakeAvailable(httplib json)
target_link_libraries(classlab PRIVATE httplib::httplib nlohmann_json::nlohmann_json)
target_compile_definitions(classlab PRIVATE CLASSLAB_WEB_DIR="${CMAKE_CURRENT_SOURCE_DIR}/web")

include(CTest)
if(BUILD_TESTING)
    find_package(Python3 REQUIRED COMPONENTS Interpreter)
    find_program(NODE_EXECUTABLE node)
    if(NODE_EXECUTABLE)
        add_test(NAME line_diff COMMAND "${NODE_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tests/diff.cjs")
    endif()
    add_executable(classlab_judging_tests tests/judging.cpp)
    target_compile_features(classlab_judging_tests PRIVATE cxx_std_20)
    set_target_properties(classlab_judging_tests PROPERTIES CXX_EXTENSIONS OFF)
    target_include_directories(classlab_judging_tests PRIVATE src)
    target_link_libraries(classlab_judging_tests PRIVATE nlohmann_json::nlohmann_json)
    add_test(NAME judging_helpers COMMAND classlab_judging_tests)
    add_test(NAME classroom_workflow
        COMMAND Python3::Interpreter "${CMAKE_CURRENT_SOURCE_DIR}/tests/workflow.py" $<TARGET_FILE:classlab>)
    add_test(NAME judge_supervisor
        COMMAND Python3::Interpreter "${CMAKE_CURRENT_SOURCE_DIR}/tests/judge_supervisor.py")
    add_test(NAME demo_workflow
        COMMAND Python3::Interpreter "${CMAKE_CURRENT_SOURCE_DIR}/tests/demo_workflow.py" $<TARGET_FILE:classlab>)
    add_test(NAME teaching_workflow
        COMMAND Python3::Interpreter "${CMAKE_CURRENT_SOURCE_DIR}/tests/teaching_workflow.py"
            $<TARGET_FILE:classlab> "${CMAKE_CXX_COMPILER}")
    add_test(NAME student_history
        COMMAND Python3::Interpreter "${CMAKE_CURRENT_SOURCE_DIR}/tests/student_history.py" $<TARGET_FILE:classlab>)
    add_test(NAME judge_protocol
        COMMAND Python3::Interpreter "${CMAKE_CURRENT_SOURCE_DIR}/tests/judge_protocol.py" $<TARGET_FILE:classlab>)
endif()
