# Phase 4 执行与部署验收

## 路线与边界

ClassLab 保留原 C++20 Web 服务和教室数据。独立 Python 3 Judge 通过本机 Unix socket 接收源码和标准输入，使用 Docker + gVisor 在独立进程中执行 GCC 14.3.0（-std=c++20）。镜像按摘要固定，执行时禁止拉取。编译用一个容器，每项测试使用新容器、新工作区。教师预期输出留在 C++ 服务中，比较沿用 Phase 3 的换行规则。隐藏用例的运行输出不落库，学生只收到隐藏用例的编号及状态。

考察了三条路线。独立服务器执行器需要可验证的 cgroup v2、容器文件系统和运行时，当前 Codex Cloud 缺少有效控制器。独立 Judge 路线保持权限边界，可接自托管组件。Judge0 等方案还需要额外服务及其自己的隔离前提，本项目选用只依赖 Python 标准库的本机 Worker。浏览器 WASM 可用于自由练习，但需要固定并分发可在浏览器内使用的 C++20 工具链和标准库，还要验证 cin/cout、内存和浏览器兼容性。浏览器结果不能作为可信课堂成绩，本轮未实现该路线。

## 运行配置

需要独立、经批准的 Linux x86-64 环境，Docker 本机守护进程及有效 cgroup v2 CPU/内存/PID 控制器。默认使用 gVisor runsc。若目标 gVisor 无法通过探针，可以在专用且不含敏感数据的 VM 上评估 runc，使用相同验收门槛。runc 共享该 VM 的内核，不能当成 gVisor 的附加内核隔离。使用专门的 Docker 主机或 daemon，不放入其他工作负载或数据。安装可信 Docker 和 gVisor，使用 Docker 的 runsc 注册，运行时不得忽略 cgroups。Judge 用户需要访问 daemon，本身属于高权限主体，应与课堂 Web 用户分开。学生容器不挂载宿主路径、Docker Socket、凭据或课堂数据。不能假定 Codespaces 开通这些权限。

1. 浏览并信任镜像来源后，在目标主机预拉特定镜像：

   ~~~sh
   docker pull --platform linux/amd64 docker.io/library/gcc@sha256:5e927c284bf55a7dc796262e311a0703344f62f41f5621eb56843111b1d37e15
   ~~~

2. 先以实际 Judge 用户运行探针和验收。任一失败都保持执行关闭。

   ~~~sh
   python3 judge/worker.py
   python3 tests/judge_smoke.py --acceptance
   python3 tests/judge_real_flow.py build/classlab
   ~~~

3. 核对启动探针、验收脚本与实际配置。探针验证可见的宿主 cgroup 配额、根挂载、UID、capabilities、NoNewPrivs、网络、临时盘和文件大小上限。验收还需确认 CPU 节流、内存超限与进程上限、禁止访问测试标记文件和服务、编译和运行超时、强制终止后清理。检查宿主 Docker 无代理注入凭据，无业务路径挂载，确认跨用例工作区隔离。发生任一基础设施或清理故障须重启并重新验证。

4. 在同一主机使用 judge/classlab-judge.service 作为 systemd 配置示例，项目部署路径为 /opt/classlab，独立服务用户和组为 classlab-judge。先准备这些账户及组，再由管理员安装服务。Web 用户只加入 classlab-judge 组以获得 socket 权限。Judge 使用私有目录 /run/classlab-judge，服务停止后 ExecStopPost 清理由该专用 Worker 标记的容器。验收完成后才以 --operator-verified 启动。选用 runc 时，探针、验收和服务启动均须传入 --runtime runc。

5. 启动 ClassLab，设置 CLASSLAB_JUDGE_SOCKET=/run/classlab-judge/judge.sock。保持 Web 预览端口私有，不转发 Judge。网页会按 Judge 实时可用性启用 Run。Judge 独立服务不可用时，Run 返回 503，Submit 保存源码并显示未评测。

## 运行与故障语义

容器配置申请单核、256 MiB 无交换、32 进程、8 MiB 的 /tmp、16 MiB 的 /work、单文件 1 MiB，并使用 Docker 默认 seccomp 策略及无外网、禁用 IPC 共享。编译和运行的流处理各有 15 秒和 3 秒墙钟期限，Docker 管理命令和整体任务另设期限。运行标准输出、标准错误分别最多保留 16 KiB，编译产物经过固定大小的传输和 ELF 校验。超时或超量时尽力强制移除容器，清理异常会关闭 Judge，systemd 的停止钩子补充清理。执行器一次执行一个 Run 或正式评测。Phase 5 的正式提交进入持久化队列，Run 在忙碌或有排队项时提示稍后重试。评测启动失败记为系统错误，学生编译和运行的时限从受信任的容器启动确认后开始计时。正式结果按提交编号更新，等待中的提交在重启后恢复，中断的评测记为评测服务错误。评测服务错误不会算成学生答错。

## 测试证据

- CTest 包含已有课堂与输出比较测试，以及明确使用 Mock Judge 的 Unix 协议集成，涵盖状态校验、并发、故障恢复、权限和结果存储。
- tests/judge_smoke.py 默认只运行代码中固定的可信 GCC 示例。tests/judge_real_flow.py 使用临时 Unix socket，只允许固定源码与固定输入，用于验证真实执行经 C++ 后端形成课堂统计。这两个测试入口都不会开启正常的学生执行服务。
- Codex Cloud 的 Docker cgroup driver 为 none，配置的 runsc 带有 --ignore-cgroups，生产启动探针拒绝启用。当前环境的有效 CPU、内存、进程限制，资源滥用及强制终止恢复尚待在验收主机验证。可信探针已确认非特权 UID、零 capabilities、只读根目录、仅回环网络、8 MiB /tmp、16 MiB /work、文件大小 ulimit、未挂载仓库或 Docker Socket，以及通过 prctl 确认 no-new-privileges。不要在当前环境运行 --acceptance 的危险样例或开放执行。
