# ClassLab

ClassLab 是 CityUHK CS2310 的 C++ Agentic Coding Project，旨在帮助教师在课堂上发布 C++ 练习、收集学生提交并查看课堂进度。

## 当前进度

项目已建立 C++20 和 CMake 构建入口。下一步会通过 C++ 后端连接教师与学生网页，并实现课堂、任务和提交数据的保存。自动评测、账号和 Jupyter 集成留待后续开发。

## 基础构建

需要 CMake 3.24 或更高版本以及支持 C++20 的编译器。

```sh
cmake -S . -B build
cmake --build build
./build/classlab
```

项目交接背景见 [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md)。当前实现状态以本 README 为准。
