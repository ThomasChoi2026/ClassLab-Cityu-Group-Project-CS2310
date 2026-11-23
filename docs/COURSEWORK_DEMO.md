# ClassLab — CS2310 作业现场演示指南

## 核心原则

这个 Demo 可以**在 ClassLab 页面直接点击「演示 Run（回放）」并看到结果**，也可以展示课堂/Notebook/学生真实加入与代码提交/教师实时分析。它只识别固定、已审计的合成代码和预置输入：**绝不编译或执行任意学生 C++ 代码**。Run 输出和评分均在网页中标明「预置演示回放」。正式 Judge 的隔离开关没有解除，OPT CPP 的组员原版一键外部跳转没有更改。

## 1. 一键启动

在一个干净的本地 clone 或临时 git worktree 中，运行：

```bash
bash demo/start_coursework.sh 8082
```

脚本先构建 ClassLab 并运行 CTest，然后启动临时 Demo 服务。Web 服务绑定到 `127.0.0.1:8082`，不使用平时的课堂数据文件。关闭 Ctrl+C 后自动删除临时数据。**不需要 Docker/gVisor、不需要正式网站或域名。**

使用 GitHub Codespaces 时，打开 **Ports** 面板，手动转发 `8082`，设置为 **Private**，使用 **Open in Browser**。只有有权访问该私有端口的浏览器用户才能打开；不要把它设置为 Public。若浏览器端口代理不可用，先在终端检查：

```bash
curl -fsS http://127.0.0.1:8082/api/health
```

若没有返回 JSON `{"status":"ready","demo":true}`，优先检查启动终端日志；若返回正常但浏览器仍打不开，属于 Codespaces 私有端口转发问题，而不是 Demo 的 C++ 后端故障。

如果现有工作区已有未提交修改，不要强制切换分支。使用：

```bash
git fetch origin main
DEMO_DIR=$(mktemp -d /tmp/classlab-coursework.XXXXXX)
git worktree add --detach "$DEMO_DIR" origin/main
cd "$DEMO_DIR"
bash demo/start_coursework.sh 8082
```

以上 worktree 不会覆盖原工作区未提交的代码。

## 2. Demo Lecture

教师页演示横幅提供两个文件：原有简版 Notebook，及新增的 **CS2310 教学版 Notebook**（完整文件路径：`examples/CS2310_ClassLab_Demo_Lecture.ipynb`）。

教学版内容依据上传的教授课程主题设计：Elements of Computations（表达式、值和数据类型）、Imperative Programming（输入与控制流）、Procedural Abstraction（把运算提取为函数）。这是重新编写的合成练习，不冒充教授原题。

只使用教学版的 **Cell 2** 作为 ClassLab 演示题目，不要把正确答案 Cell 5 或语法错误 Cell 7 合并进题目，否则预置回放不会匹配。

1. 教师「课前备课」选择下载的教学版 `.ipynb`；选择 **Cell 2** 并点击「填入起始代码」。
2. 填写标题 **Fix the addition**，任务说明 **The program should output the sum of two integers. Find and fix the bug.**
3. 点击 **填入三个演示用例**，发布任务。
4. 打开 QR/加入链接，用三个不同的浏览器会话进入课堂。

## 3. 演示 Run 和学生提交

**Run 预置回放**：

- 初始代码为 `std::cout << a - b << '\\n';`。
- 点击「演示 Run（回放）」→ 显示 `stdin` 输入框；输入 `2 3` → 再点击「输入并查看预置结果」→ 显示 **-1**，并且明确标注没有执行实际 C++。
- 把 `a - b` 改成 `a + b`，同样回放 `2 3` → 显示 **5**。
- 只支持输入 `2 3`、`0 0`、`-4 9` 及精确匹配的两种预置代码。其他输入或改写为不匹配源码时，显示「无匹配的演示夹具」，不会编造结果。
- 另外可以用合成 Notebook 的语法错误 Cell 7 演示**预置的编译诊断**，但它并不是真正调用编译器。

**课堂过程和教师分析**：

- Student 1 提交未修改的 `a - b`。
- Student 2、3 提交修改后的 `a + b`。
- 教师管理端显示 **3 人提交、2 人通过、1 人失败**，打开共同改动查看一行 `a - b` → `a + b` 的 diff。
- 学生提交和班级人数**是真实实时操作**；测试 verdict 依然是明确标注的预置回放。

## 4. 60-second English demonstration script

| 时间 | 页面动作 | 讲稿 |
|---|---|---|
| 0–10 秒 | 导入 Notebook，指向 Bug | “ClassLab turns a C++ notebook example into a classroom debugging task.” |
| 10–22 秒 | 发布任务并显示 QR | “I select this buggy cell, publish test cases and share a QR link.” |
| 22–36 秒 | 学生点击 Demo Run、输入和修改代码 | “The Run-first interaction can be demonstrated with labeled prerecorded fixtures. Students can also edit and submit their code.” |
| 36–52 秒 | 教师仪表板，展示 2/3，通过/失败及 diff | “Two students corrected subtraction to addition. The live dashboard groups their common edit.” |
| 52–60 秒 | 展示学生加入人数和投影 | “Teachers can identify misunderstandings while the class is still working.” |

**Q&A 应答：** “This is a safe fixture-replay demonstration, not unrestricted C++ execution. The production Judge is implemented separately but needs a validated isolated runtime.”

## 5. 验收命令与界限

```bash
ctest --test-dir build --output-on-failure
# 在终端一启动 Demo 后，另一个终端：
python3 tests/browser_demo.py http://127.0.0.1:8082
```

第二条需要已安装的 Playwright/Chromium、Pillow 和 zxing-cpp；GitHub Actions 的 `coursework-demo.yml` 会安装依赖并自动执行真浏览器演示验收。测试同时验证二维码、Notebook、Run-first 预置输出、三名学生、教师汇总及代码差异。

**此项目演示不承诺真实在线执行任意 C++。** 若教授把真实执行任意程序列为强制要求，仍需要经完整验收的 gVisor 独立 Judge，Demo 模式不能代替正式功能。
