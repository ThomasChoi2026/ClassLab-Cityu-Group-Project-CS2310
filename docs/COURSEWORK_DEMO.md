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

## 2. 完整教学 Notebook

从仓库下载 [CS2310 — From Control Flow to Procedural Abstraction](../examples/CS2310_Score_Analysis.ipynb) 到教师设备。该原创教材由 74 个 Cell 组成，包含五道互动练习。参考实现与预置回放数据在单独的 instructor reference JSON 中，不通过课堂 HTTP 服务分发。

| 原始 Cell | 互动练习 |
| --- | --- |
| 22 | Fix the grade boundary |
| 35 | Debug the accumulation loop |
| 48 | Find the maximum correctly |
| 63 | Fix the average function |
| 72 | Complete the score analyser |

进入教师工作台的 **课前备课**，直接选择文件。上传后默认显示五道互动练习，点击第一题自动填入标题、说明、起始代码、5 个测试（3 个公开、2 个隐藏）与易错点。确认后点「发布为当前任务」。不需要逐格查找，也不要额外点「填入三个演示用例」（该按钮是旧版合成加法题专用）。

## 3. 演示 Run 和学生提交

1. 用 QR 或加入链接在三个独立浏览器会话中加入课堂。
2. Student 1 点击「演示 Run（回放）」，输入公开边界用例 `60`，再次点击，得到 `FAIL`（有缺陷的 `score > 60`）。正式提交仍是预置判定。
3. Student 2 和 3 把比较运算符改为 `score >= 60`。用同一公开输入 `60` 回放，显示 `PASS`，再正式提交。
4. 教师端显示 3 人提交、2 人通过、1 人失败。打开共同修改查看比较运算符的变化，并结合边界测试及预设易错点解释为什么需要等号。
5. Notebook 在发布后保留；选择下一道互动题即可继续教学，无需重新上传。

五道练习均有精确匹配 starter/reference 源码的回放，实际 C++20 离线验证由 CTest 完成。Demo Run 仅接受该题公开预置输入；隐藏测试只在正式提交回放使用，学生只看到隐藏测试状态。任意改写为其他源码、改变用例集合或输入不匹配都会提示无演示数据。正确但不同的实现也可能不匹配；生产 Judge 才能执行任意学生源码。

## 4. 60-second English demonstration script

| 时间 | 页面动作 | 讲稿 |
|---|---|---|
| 0–12 秒 | 上传 Notebook，展示 74 Cells / 5 Exercises | “A full teaching notebook may contain dozens of cells. ClassLab recognizes just the five interactive exercises.” |
| 12–24 秒 | 点击 Cell 22，检查自动填入的题目与用例，发布 | “I select the boundary exercise. The specification, starter and tests are loaded automatically; I decide when to publish.” |
| 24–39 秒 | 学生扫码加入；Run 输入 60，修改 > 为 >= | “The boundary fails before the fix and passes afterward. The demo results are clearly labeled prerecorded fixtures.” |
| 39–54 秒 | 教师统计 3/2/1，打开共同修改 | “The class submits live. The dashboard identifies the shared correction and the test failure.” |
| 54–60 秒 | 选择下一道练习 | “The notebook stays open, so the teacher can move to the next activity without re-importing it.” |

**Q&A:** “All five fixture variants were checked by real C++20 tests offline. The live demonstration does not execute arbitrary student code; unrestricted execution requires a validated isolated Judge.”

## 5. 验收命令与界限

```bash
ctest --test-dir build --output-on-failure
# 在终端一启动 Demo 后，另一个终端：
python3 tests/browser_notebook_classroom.py http://127.0.0.1:8082 --evidence-dir notebook-evidence
```

第二条需要已安装的 Playwright/Chromium、Pillow 和 zxing-cpp；GitHub Actions 的 `notebook-classroom.yml` 会安装依赖并自动执行真浏览器演示验收。测试验证直接上传、74/5 筛选、覆盖保护、隐私、Run-first、提交和教师汇总；另运行原有二维码及浏览器回归。

**此项目演示不承诺真实在线执行任意 C++。** 若教授把真实执行任意程序列为强制要求，仍需要经完整验收的 gVisor 独立 Judge，Demo 模式不能代替正式功能。
