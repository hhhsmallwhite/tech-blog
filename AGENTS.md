# AGENTS.md —— 本仓库的 Agent 工作规则

任何 Agent（DEV/REV/QA/PM）在本仓库工作前必读本文件。人类同事可跳过，但建议看"环境注意"一节。

## 必读顺序（接到任务先读，按序）

1. `docs/development-plan.md` —— 总纲：确认任务属于哪个里程碑、当前项目状态（§9）
2. `docs/task-breakdown.md` 中**你的任务卡** —— 白名单、三场景验收、测试清单、DoD 增补
3. `docs/definition-of-done.md` —— 怎样才算"完成"（十条 DoD、验证记录模板、⚠卡加严项）
4. `docs/development-workflow.md` —— 过程规则（分支/提交/PR 清单/交接单/状态流转/红线 §9）
5. 任务卡"对应章节"指向的设计文档段落（docs/ 下的七份设计文档）

## 铁律（违反即打回）

- **白名单纪律**：只改任务卡"修改范围"列出的文件；出现白名单外文件=PR 打回
- **一任务一分支一 PR**：`feat/T-0xx-短名`；无任务号不开分支；main 不直推功能
- **PR 必填验证记录**（definition-of-done.md §3）：只勾实际执行过的项；未执行不得勾选、不得写"应通过"
- **三场景验收**：正常/边界/失败缺一不可；契约断言=状态码+响应内容+适用头
- **断言完整**：不得删/弱断言迁就实现（DoD 9）；发现契约与实现冲突→上报，不得私自改
- **红线操作**（development-workflow.md §9 十类：force-push/改写已推送历史/删备份/碰生产库/破坏性迁移/改 Secrets/生产发版等）**必须用户亲口批准**，授权原话记台账
- **禁改清单**（definition-of-done.md §7）：.env、已合并迁移、db.sqlite3、media/、其他任务白名单文件
- 迁移只经 makemigrations；已合并 main 的迁移永不修改

## 本机环境注意（Windows）

- 统一使用 **PowerShell 7**（`pwsh`）；git 2.50；Python 3.14.6（`D:\DevEnv\Workspace\py3.14.6`）
- 虚拟环境：项目内 `.venv/`，**不碰全局 Python、不改系统环境变量、不升级全局工具**
- pip 已配阿里云镜像（勿改）；依赖只进 requirements/*.txt 且精确锁定版本
- 本机有代理残留断网坑：git/GitHub 连不上时**先查代理**（Clash 残留 127.0.0.1:7897）
- 本仓库 V1 **不需要 Node.js**

## 状态与汇报

- 任务完成：按 development-workflow.md §6 交接单格式汇报（含验证记录）
- 里程碑完成：按 §6.5 汇报单呈用户，附证据链接
- 卡住/契约冲突/评审循环 5 轮未过：置 BLOCKED 上报 PM/用户，不得自行绕过
