# ClassLab

ClassLab 是 CityUHK CS2310 的 C++ Agentic Coding Project。教师可以在课堂上发布 C++ 练习，学生通过链接获取题目、编辑并提交代码，教师可以看到班级的参与和提交进度。

ClassLab is an interactive C++ teaching tool for CityUHK CS2310. Teachers can publish exercises from Notebook code cells, students join through a QR code, and teachers can follow class-wide submission and test results.

[English delivery guide, architecture, and 60-second demo script](docs/COURSE_DELIVERY.md)

## 教授快速验收

在 Linux 或 WSL 中，从课程交付分支开始。需要 Git、CMake 3.24+、C++20 编译器和 Python 3；首次构建需联网。

~~~sh
git clone --branch feature/classlab-course-final https://github.com/ThomasChoi2026/ClassLab-Cityu-Group-Project-CS2310.git
cd ClassLab-Cityu-Group-Project-CS2310
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
ctest --test-dir build --output-on-failure
python3 demo/run.py
~~~

打开 <http://127.0.0.1:8080>。下载横幅上的示例 Notebook、创建课堂、选择第一个代码单元并点击「填入起始代码」。填写标题和说明，点击「填入三个演示用例」后发布。用独立浏览器会话打开加入链接。一位学生提交原代码，另两位将 `a - b` 改为 `a + b` 后提交，教师端应显示 **3 人提交、2 人通过、1 人未通过**。打开「全班共同修改」的示例可核对原代码与提交的行号和增删。教师页面使用本机地址时，二维码也指向本机；手机演示需要双方都能访问的课堂地址。

演示中的加入、源代码和人数都是实时数据，评测使用标明的固定回放。任意新代码不会在演示中执行。普通课堂服务使用下方的启动命令，真实评测仍须通过独立 Judge 的隔离验收。

### 教师如何解读反馈

- 提交详情逐行对齐，保留空格、空行和末尾换行的差异，统一 CRLF/LF。大范围重写超出对齐预算时直接展示完整源码。
- 共同修改按每人本题最后一次提交计数。仅收录去除相同首尾后，原文和新文各不超过三行、每行不超过 240 字节的修改。相同位置和内容至少出现两次才显示，按人数取前六组。
- 每组直接列出这些学生的评测状态。教师可结合各用例的失败类型、编译器诊断原文和示例提交判断是否重讲。相同修改或共同失败本身不能确定学生的思路。

## 课程交付与演示

GitHub 保存完整代码、构建与测试命令，供组员协作和教授复现。课程交付分支在本地 WSL 构建和测试。课堂演示可直接使用本机浏览器，也可使用已有的临时私有预览。

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

## Phase 6 教学演示

教师可直接粘贴 C++，也可选择本地的 Notebook v4 文件并将一个代码单元填入任务编辑器。Notebook 只在浏览器解析。教师切换到课堂投影后，屏幕只保留课堂名称、加入二维码、任务标题与汇总进度。

构建完成后，运行临时演示。此命令使用独立的临时存储、固定评测回放，并关闭自由运行。页面会明确标识回放结果。用 Ctrl+C 停止并清理演示数据。

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
- 提交成功表示服务器已收件。默认配置只保存提交。自动评测需要独立且验收合格的 Judge。学生账号、完整历史提交网页及 Jupyter 扩展尚未实现。

项目交接背景见 [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md)。交接文档包含规划，当前功能以本页为准。
