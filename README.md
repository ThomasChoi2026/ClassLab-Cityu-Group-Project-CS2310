# ClassLab

ClassLab 是 CityUHK CS2310 的 C++ Agentic Coding Project。教师可以在课堂上发布 C++ 练习，学生通过链接获取题目、编辑并提交代码，教师可以看到班级的参与和提交进度。

ClassLab is an interactive C++ teaching tool for CityUHK CS2310. Teachers prepare exercises from Notebook cells, add public or hidden tests and anticipated pitfalls, and publish to a classroom. Students join by QR code, edit and submit code, and review their own attempts. Teachers can inspect per-student diffs and class-wide submission and test evidence.

[English delivery guide, architecture, and 60-second demo script](docs/COURSE_DELIVERY.md)

## 当前开发与快速验收

ClassLab 持续开发。`main` 保留最近经过验证的版本，是复现和后续开发的起点。新任务从最新 `main` 创建独立功能分支，经测试和审核后合并。各阶段分支保留供查阅和协作。

在 Linux 或 WSL 中运行下列命令。需要 Git、CMake 3.24+、C++20 编译器和 Python 3；首次构建需联网。

~~~sh
git clone --branch main https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310.git
cd ClassLab-Cityu-Group-Project-CS2310
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
ctest --test-dir build --output-on-failure
python3 demo/run.py
~~~

打开 <http://127.0.0.1:8080>。从仓库下载 [完整成绩分析教学 Notebook](examples/CS2310_Score_Analysis.ipynb) 到教师设备，创建课堂，进入「课前备课」并直接上传文件。默认显示 5 道互动练习（共 74 Cell），选择 **Fix the grade boundary（Cell 22）** 自动载入题目与用例，检查后发布。学生输入 `60` 回放时，错误版本显示 `FAIL`；将 `score > 60` 修正为 `score >= 60` 后显示 `PASS`。一人提交错误版本、两人提交修正版，教师端显示 3 人提交、2 人通过、1 人失败及共同修改。教师页面与学生设备须访问同一地址。

演示中的加入、源代码和人数都是实时数据，评测使用标明的固定回放。任意新代码不会在演示中执行。普通课堂服务使用下方的启动命令，真实评测仍须通过独立 Judge 的隔离验收。

### 演示每周课表与时间冲突

1. 创建课堂，在教师工作台展开 **每周课表**。加入课堂的学生也可展开课表查看已保存的时段。
2. 添加 **CS2310 Lecture**，选择星期一 **10:00–12:00**。再添加 **CS2310 Lab**，选择星期一 **11:00–13:00**。提示会列出与 Lecture 重叠的 **11:00–12:00**，并保留 Lab 的输入供修改。
3. 将 Lab 的开始时间改为 **12:00** 再提交即可保存。课表按星期和开始时间排列。教师可移除时段，学生页面会自动更新。每个课堂独立保存一份每周重复的课表，每个时段须在同一天内结束。

### 教师如何解读反馈

- 提交详情逐行对齐，保留空格、空行和末尾换行的差异，统一 CRLF/LF。大范围重写超出对齐预算时直接展示完整源码。
- 共同修改按每人本题最后一次提交计数。仅收录去除相同首尾后，原文和新文各不超过三行、每行不超过 240 字节的修改。相同位置和内容至少出现两次才显示，按人数取前六组。
- 每组直接列出这些学生的评测状态。教师可结合各用例的失败类型、编译器诊断原文和示例提交判断是否重讲。相同修改或共同失败本身不能确定学生的思路。

## 开发记录

| 阶段 | 主要变化 | 代表提交 |
| --- | --- | --- |
| Initial / MVP | 项目初始化、课堂发布、学生提交和教师统计 | `19b0c3d`、`4fb68b0` |
| Phase 2 | 二维码加入和跨设备体验 | `0c76b02` |
| Phase 3 | 公开与隐藏测试、评测反馈和课堂统计 | `92a93ef` |
| Phase 4 | 独立 C++ Judge 与判题接入 | `1b27053` |
| Phase 5 | 持久化评测队列与限额检查 | `4bcae25` |
| Phase 6 | Notebook 导入、投影和受限演示 | `f9ae94f`、`4bfc3e8` |
| Classroom Analysis | 代码逐行对比、全班共性和诊断分组 | `959e256` |
| Teaching Workflow | 多单元备课、练习库和预期易错点反馈 | `a7dda84` |

完整提交、作者及分支关系可在 [main 提交历史](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/commits/main/) 或通过 `git log --graph --oneline --all` 查看。

## Team Contributions

The table records CS2310 team accounts and the work traceable to their original commits and pull requests.

| Team Member | GitHub | Actual Contribution |
| --- | --- | --- |
| Thomas | [ThomasChoi2026](https://github.com/ThomasChoi2026) | Developed the classroom MVP and the Notebook lesson preparation workflow. Defined the requirements and prompts for classroom analysis and student code comparison. |
| aries36white | [aries36white](https://github.com/aries36white) | Linked the student editor to the external OPT CPP tab. [PR #3](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pull/3) |
| superlulu77 | [superlulu77](https://github.com/superlulu77) | Added starter-code reset, C++ download, and timestamped submission receipts. [PR #1](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pull/1) |
| godferywong098kirito-blip | [godferywong098kirito-blip](https://github.com/godferywong098kirito-blip) | Added student submission history. [PR #2](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pull/2) |
| Mizunonamae | [Mizunonamae](https://github.com/Mizunonamae) | Added teacher classroom controls, student removal and praise, and a macOS build fix. [PR #4](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pull/4) |
| isferr | [isferr](https://github.com/isferr) | Added the weekly timetable and overlap detection. [PR #5](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/pull/5) |

See the [classroom MVP commit](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/commit/4fb68b0921305a08e3cad88a62193acf9f17237e) and [Notebook lesson preparation commit](https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310/commit/a7dda8450da2b95796ecc2d80550e4aaa537a7d5) for development records.

## 开发阶段验收与演示

GitHub 保存完整代码、构建与测试命令，供组员协作和教授复现。课堂分析阶段在 WSL 完成构建和测试。课堂演示可直接使用本机浏览器，也可使用已有的临时私有预览。

验收重点是从干净目录构建、运行测试，并演示创建课堂、发布任务、学生提交和教师看到状态的完整流程。公开部署、长期运营和商业级账户系统不在本课程交付范围内。未经验证的隔离环境不得执行学生提交的 C++ 代码。

## 构建与运行

需要 Linux、支持 C++20 的编译器、CMake 3.24 或更新版本，以及用于运行测试的 Python 3。首次构建从 GitHub 下载固定版本的 cpp-httplib 和 nlohmann/json，并校验 SHA-256。前端无需单独构建。

~~~sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
ctest --test-dir build --output-on-failure
./build/classlab
~~~

从仓库根目录启动后，在同一台机器的浏览器打开 http://127.0.0.1:8080 。教师创建课堂后可以复制加入链接，也可以点击二维码放大投影。发布标题、说明和 C++ 起始代码后，学生可扫码或打开链接填写昵称、编辑并提交。可以在同一浏览器的另一个标签页扮演学生。

课堂进度每两秒刷新，显示全班加入人数、当前任务已提交人数、提交总次数，以及每位学生的提交状态和次数。发布新任务后统计切换为新任务，历史任务和提交仍保存在数据文件中。学生页面会自动接收新任务。身份及各题草稿保存在此浏览器和站点地址下，刷新页面可恢复当前任务的未提交草稿。

## Native Run-first practice (Judge required)

The student editor initially hides stdin. When the isolated ClassLab Judge is available, the first **运行代码** click runs a disposable probe with a one-byte stdin file. The trusted wrapper checks whether the program **actually consumed stdin**, supporting ordinary C++ `cin`, `getline`, C `scanf` and POSIX `read(0,...)` without inspecting source text. If stdin was consumed, ClassLab shows the input box and the student clicks Run again; this performs a **fresh execution from the start** with the supplied input, not a live resumable session. If no stdin was read, the first run's output appears immediately. Compilation errors and execution-limit errors appear normally. Input is reset when the task changes.

This feature does **not** enable or weaken the native Judge: without a separately configured and security-accepted Docker/gVisor worker, the native Run button stays disabled and official grading remains unavailable. OPT CPP remains a separate external link, not an embedded runtime. The teammate's original **抄送至OPT_CPP** button sits beside Copy Code for a single-click external tab. An optional collapsed OPT CPP input field is independent from native Judge stdin.

The new trusted-fixture test `tests/stdin_probe.py` runs only hard-coded C++20 programs on the host. It does not certify untrusted-code isolation, which still requires the checks in `docs/PHASE_4.md`.

## Student editor and external practice

Students can restore the teacher's starter code, download their current editor contents as a .cpp file, and review the newest 50 formal submissions for the current task. The original **抄送至OPT_CPP** control opens the external visualizer in one click with the current code and optional external-practice stdin. It is available even when the ClassLab Judge is disabled.

See the [student workflow and privacy notes](docs/COURSE_DELIVERY.md#student-workflow) for the exact controls, history scope, long-link fallback and browser testing.

## Notebook Classroom Integration

在普通 C++ Code Cell 的第一条非空行（或裸 `%%cpp` 后第一条非空行）添加：

```cpp
// @classlab exercise: Fix the grade boundary
#include <iostream>
int main() {
    int score;
    std::cin >> score;
    std::cout << (score > 60 ? "PASS" : "FAIL") << '\n';
}
```

- 省略冒号和标题即可使用原始 Cell 编号自动命名。进入 **课前备课 → 直接上传 Notebook → 选择互动练习**，自动载入预设内容。无标记 Notebook 仍显示全部 Cell，普通搜索、筛选、预览、组合继续可用。
- 普通 Cell 点击后只预览。选择「用此 Cell 作为起始代码」，或选好多个 Cell 后点击「将组合填入起始代码」。可单独将 Markdown 追加到任务说明。发布以起始代码编辑框为准。开放题需要勾选「让学生从空白开始」。
- 在可选 Cell Metadata 中填写公开说明、公开/隐藏测试、预期输出及易错点。检查后手动发布；上传不会覆盖草稿或自动发布。已编辑的草稿需确认才会被互动练习替换，发布成功后会清空本题编辑内容与组合选择，保留当前 Notebook、预览、搜索和筛选。刷新或关闭页面后需重新导入。
- 教师答案请单独保存，或使用 `// @classlab answer` / Metadata role=answer/reference，使其仅可预览。隐藏测试和易错点不进入学生端任务数据。不要把私密材料写进公开说明或起始代码。
- [标记及 Metadata 完整规范](docs/NOTEBOOK_CLASSROOM.md) · [完整教学 Notebook（74 Cells / 5 题）](examples/CS2310_Score_Analysis.ipynb) · [课堂 Demo 指南](docs/COURSEWORK_DEMO.md)。

教师可以通过原有练习库保存、更新草稿，或在全班分析中查看用例失败与源码片段命中情况；这些是复核线索，不应直接认定学生的思路。

原创示例 [polymorphism-slicing.ipynb](examples/polymorphism-slicing.ipynb) 包含继承层次、接收参数的函数及 main，分三个代码单元。组合后，输入 0 预期输出 animal，输入 1 预期输出 meow。起始版本把 Cat 按 Animal 值传递，实际输出 animal。学生将参数改为 const Animal& animal 后可保留动态派发。教师可用 const Animal animal 作为复核片段，并关联第二个用例。CTest 编译并运行这两个固定示例，还验证错误的 override 签名产生编译诊断。

当前 Codex Cloud 的 Docker cgroup driver 为 none，runsc 忽略 cgroups，另一个用户命名空间探针也因 UID 映射只读被拒绝。网页依旧遵守安全门槛。课程范围内优先复用学校已有的专用 Linux VM，配置已有的独立 Judge，验证 CPU、内存、PID、文件和网络限制后再启用。浏览器 WebAssembly 若要接受学生输入的 C++，还需在浏览器提供经过验证的 C++20 编译工具链及执行限制，现有网站没有该能力。课堂文件和学生代码无需发送给外部评测服务。参见 [执行环境验收](docs/PHASE_4.md)。

## Phase 6 教学演示

教师可直接粘贴 C++，也可选择本地的 Notebook v4 文件并将一个代码单元填入任务编辑器。Notebook 只在浏览器解析。教师切换到课堂投影后，屏幕只保留课堂名称、加入二维码、任务标题与汇总进度。

构建完成后，可运行 `bash demo/start_coursework.sh 8082` 进行完整作业演示；它先执行 CTest，再启动临时课堂。演示模式可在学生页面点击「演示 Run（回放）」、输入预置 stdin 并查看明确标注的结果，但**不会编译或执行任意学生 C++**，也不开放正式 Judge。五道完整教学练习支持预置源码/输入回放（自由 Run 仅支持其公开输入），旧版合成题仍可用。用 Ctrl+C 停止并清理演示数据；完整 60 秒流程见 [作业 Demo 指南](docs/COURSEWORK_DEMO.md)。

~~~sh
python3 demo/run.py
~~~

[演示用例、完整操作和课程交付检查表](docs/COURSE_DELIVERY.md)

## Phase 5 独立评测与提交队列

配置独立 Judge 后，正式提交先保存到数据文件并立即返回，随后显示等待评测、评测中及最终结果。全站同时保留最多 64 项待评测与评测中任务，按保存顺序逐项处理。队列满时仍保存源码并标记未评测，学生可以稍后重交。学生的最新状态按提交顺序计算，评测完成顺序不会改变它。自由运行继续使用自定义输入，不计入提交次数。

Judge 断线时保留等待项，恢复连接后继续。Web 服务重启时继续处理已保存的等待项，中断的评测记为评测服务错误，避免重复执行。教师可查看等待人数及最新结果。关闭或未配置 Judge 的普通预览仍可保存代码，显示未评测。实际启用步骤和隔离门槛见 [执行与部署验收](docs/PHASE_4.md)。

## 用 GitHub Codespaces 私有预览

在 GitHub 选择要验收的分支，在该分支的 Codespace 网页终端执行同一组构建和启动命令。进入 **Ports** 面板，转发 8080 并保持 **Private**，点 **Open in Browser** 打开教师页。二维码及复制链接都使用此 HTTPS 地址。另一台设备也需要登录有权访问该私有端口的 GitHub 账号。用 Ctrl+C 停止网站，完成后在 GitHub 停止 Codespace。Judge 的 Unix socket 只留在服务端。

判断已有 Codespace 能否作为 Judge 宿主，请在其网页终端运行下列只读命令：

~~~sh
docker --host unix:///var/run/docker.sock info --format 'cgroup={{.CgroupVersion}} driver={{.CgroupDriver}} security={{json .SecurityOptions}} runsc={{json (index .Runtimes "runsc")}}'
cat /sys/fs/cgroup/cgroup.controllers
~~~

Docker 不可达、驱动为 none 或所选运行时忽略 cgroups 时，继续使用仅收件预览。即使输出符合预期，仍需在实际主机通过 [执行验收](docs/PHASE_4.md) 后才能启用学生执行。当前 Codex Cloud 检查结果不能用来判定你的 Codespace。

二维码由浏览器使用随项目提供的 [qrcode-generator 1.4.4](https://www.npmjs.com/package/qrcode-generator/v/1.4.4) 生成，课堂链接不会发送给外部二维码服务。开源许可见 [web/vendor/qrcode.LICENSE](web/vendor/qrcode.LICENSE)。

## 环境变量

| 变量 | 默认值 | 用途 |
| --- | --- | --- |
| CLASSLAB_HOST | 127.0.0.1 | 监听地址。本机演示使用默认值，转发服务端口时可设置为 0.0.0.0 |
| CLASSLAB_PORT | 8080 | 监听端口 |
| CLASSLAB_JUDGE_SOCKET | 空 | 可选的独立 Judge 本机 Unix socket 路径 |
| CLASSLAB_DATA | data/classrooms.json | 以进程工作目录为基准的数据文件，可设为绝对路径 |

跨设备演示时，教师应从学生设备可访问的同一站点地址打开教师页，生成的加入链接会沿用该站点地址。在云端运行时需要另行配置支持该端口的访问入口。

## 保存、权限和限制

- C++ 服务保存课堂、任务、学生身份和提交源代码。一个数据文件仅供一个进程使用，进程内通过互斥锁保护读写。每次写入先完成同目录临时文件，再原子替换数据文件。写入失败会向客户端报错，内存状态保留上一次成功保存的版本。
- 教师在创建课堂时获得独立访问密钥，发布任务和读取进度都需要该密钥。知道加入链接的人可以用昵称加入，学生使用独立随机会话密钥访问题目和提交。教师密钥、学生会话和草稿保存在浏览器本地。清除浏览器数据会丢失相应访问权限和草稿。每个浏览器来源的教师页面目前保留一个课堂，没有课堂列表、教师账号或密钥恢复功能。
- MVP 用于小规模、受信任的课堂演示。昵称未验证，加入链接可转发。数据文件需由运行者妥善保护。每次写入会重写数据快照，尚无跨进程扩容、断电持久性保证、数据清理策略或公网运营所需的登录、限流和 HTTPS。跨设备演示所用的 HTTPS 应由外部代理提供。
- 提交成功表示服务器已收件。默认配置只保存提交。自动评测需要独立且验收合格的 Judge。学生能查看本题最近 50 次提交。跨任务归档、学生账号及 Jupyter 扩展尚未实现。

## Acknowledgements and third-party tools

We thank our CS2310 instructor, **Professor Chung Chan**, for developing **OPT CPP** [1], the external C++ visualizer that ClassLab links to for student practice. OPT CPP runs C++ programs and shows execution steps, stack frames, variables and heap state. It is published under the DIVE4DEC GitHub account.

OPT CPP builds on the visualization work of **Philip J. Guo**, who created **Python Tutor**, originally **Online Python Tutor** [2–5]. The ClassLab team develops the classroom workflow, editor handoff, submission history, teacher analytics and Judge integration. ClassLab is an independent project. This attribution does not imply participation, sponsorship or endorsement.

| Component | Use in ClassLab | Source and licensing scope |
| --- | --- | --- |
| OPT CPP and Python Tutor | External reference and browser link to OPT CPP | ClassLab ships no visualizer source or WASM assets. The link does not establish the external site's privacy or usage terms. |
| qrcode-generator 1.4.4 | Bundled JavaScript for join QR codes | MIT. The notice is included in [web/vendor/qrcode.LICENSE](web/vendor/qrcode.LICENSE). |
| cpp-httplib v0.28.0 and nlohmann/json v3.12.0 | Build-time dependencies fetched by CMake at pinned versions | MIT. See the source notices for [cpp-httplib](https://github.com/yhirose/cpp-httplib/tree/v0.28.0) and [nlohmann/json](https://github.com/nlohmann/json/tree/v3.12.0). |

### References

1. Chan, C. [OPT_CPP source, runtime documentation and references](https://github.com/dive4dec/OPT_CPP). See the [initial OPT_CPP commit](https://github.com/dive4dec/OPT_CPP/commit/f8b60a93e15139831546a4e4d7c37a39fe217354) for the author credit.
2. Python Tutor. [Official website](https://pythontutor.com/).
3. Python Tutor. [Official C++ Visualizer](https://pythontutor.com/cpp.html).
4. Python Tutor. [Official link integration guide](https://pythontutor.com/for-ai-assistants.html).
5. Guo, P. J. (2013). Online Python Tutor: Embeddable Web-Based Program Visualization for CS Education. *Proceedings of the 44th ACM Technical Symposium on Computer Science Education (SIGCSE '13)*, 579–584. [https://doi.org/10.1145/2445196.2445368](https://doi.org/10.1145/2445196.2445368).

项目交接背景见 [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md)。交接文档包含规划，当前功能以本页为准。
