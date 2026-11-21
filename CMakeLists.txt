cmake_minimum_required(VERSION 3.24)
project(ClassLab LANGUAGES CXX)

add_executable(classlab src/main.cpp)
target_compile_features(classlab PRIVATE cxx_std_20)
set_target_properties(classlab PROPERTIES CXX_EXTENSIONS OFF)
