# 执行台账（Execution Log）

> 文档版本：v1.0
> 文档状态：M0 收口落档（2026-10-25 用户批准"6 件全办"）
> 文档定位：`development-workflow.md` 三层证据之一（PR / 任务台账 / 本台账），每里程碑收口时更新
> 证据原则：只记实际执行项，未执行不得记为通过（DoD §1-8）；每条含提交号或可复查链接

---

## M0 工程地基（T-001～T-004，2026-10-23 ～ 10-25）

### 前置：设计文档与任务体系（2026-10-23）

- 7 份设计文档全部批准（requirements-analysis v1.1、technology-decisions、architecture、database-design、api-design、security-design、deployment-design）；任务清单 task-breakdown v1.0→v3.0（41 卡、三场景验收、DoD 十条）；协作规则 v1.0
- 2026-10-24 四文档整合生效：development-plan / task-breakdown v4.0 / definition-of-done / development-workflow v2.0

### T-001 建仓（2026-10-24，批次 1）

- 提交 `a034d09`（docs 整合 12 份）+ `898f17f`（基础 7 文件）
- 独立审查（10 项）：5 过 / 3 未到时点 / 1 中缺口 + 3 低 → 用户拍板 P1/P2/P3 → 收口三笔 `efa6530`（任务清单 v4.1）/ `202a320`（选型 v1.2 + python-dotenv）/ `35f948a`（.gitignore 通配 + AGENTS.local.md 外移）
- 偏离记录：无远端期两笔直落 main（被批准的例外，无 PR 流）；验收轮建 .venv 装依赖（U1/U2 消除：Django 5.2.18 与 pytest 9.1.1×pytest-django 4.14.0 在 py3.14 可装可解析）

### T-002 Django 脚手架（⚠A 认证类）

- 分支 feat/T-002-scaffold 四笔（5bbeecb 测试先行先红 → 5036584 settings 四拆 → 97688d2 骨架空壳 → 8387a91 ruff 清零）；评审会话补测 `283e1a4`（+4 用例：非法布尔/整数 fail-fast 点名变量）
- 独立评审（新会话请柬方式）：**PASS**——白名单 20/20、⚠A security §1/§2 对照 14/14、复跑 16 绿、探针验证
- squash 合并 `a2f013e`（20 文件 +358 行）；main 回归 16/16
- 偏离记录：子代理通道全程不可用（debug-iterator 拦截 ×2、general-purpose provider-not-found ×3）→ PM 直接实现 + 结构化自查补偿；评审角色越权补测经 PM 逐行核查合格（纯测试新增、白名单内）

### T-003 开发约定与工具配置

- 分支 feat/T-003-dev-conventions 三笔（17f54d2 pyproject + A1 豁免 → 59e567b README 开发章 → 39762f5 评审修复）
- 第 1 轮独立评审 **FAIL** 退回（阻塞：README `check --deploy` 裸跑必炸 + CI 超前承诺）→ 修复后第 2 轮 **PASS**（8/8 核对点，含示例逐字复跑 exit=0 与长密钥 W009 对照实验）
- squash 合并 `57b8c5a`

### 正式验收 v1.0 + 矩阵第 1 轮 + QA 审计（2026-10-24）

- `docs/acceptance-report.md`（提交 `6bac2a6`）：结论 **❌不通过（现阶段）**——MVP 3/39、关键验证缺失、M0 出口未达；已交付 3 卡质量可复现；转通过路径列明
- 测试矩阵 53 条第 1 轮执行：**2 过 / 3 部分过 / 0 败 / 48 未解锁**（未解锁=功能未实现，非缺陷）；两个非缺陷发现（管理员账号依赖 T-005 迁移；POST / 200 探针预期写错归档为测试设计问题）
- 独立 QA 审计：**P0=0、P1=0、P2×3、P3×5**；无虚假通过声明，执行报告可复现

### T-004 CI 骨架（2026-10-24～25）

- 前置：用户 GitHub 建仓 hhhsmallwhite/tech-blog（U-3 销账）+ SSH 公钥绑定 + main 首推（T-001 正式收口）
- 分支 feat/T-004-ci-skeleton 十笔；**CI 调试 9 次运行**：4 红（三重根因：裸命令不在 PATH → PIP_USER 用户站点 → 自造 .venv-ci 名不在 ruff 默认排除；外加真缺陷 EXE001=manage.py shebang 无可执行位，Windows 本地盲区）→ 修复（python -m / 隔离 venv 定名 .venv / v4.2 照准移除 shebang）→ 5 绿
- 验收探针：①故意格式违规→恰红在门禁 2→还原复绿（run 40101676339→40101861376）；②故意失败断言→恰红在门禁 3→还原复绿（40102011078→40102171105）；全绿链路 run 40101503665（EXE001 修复首绿）/ 40102171105（HEAD）
- 独立评审 **PASS**（7/7 核对点，含 Windows EXE001 盲区亲测；2 条收尾建议均已落实）
- 分支保护（T-001 遗留项收口）：规则集 main=Active、目标 main、Require PR + Require status checks(gates)；**直推探针被服务器拒绝**（GH013：Changes must be made through a pull request + Required status check "gates" is expected）——保护真实生效实证
- **PR #1**：pull_request 事件触发新 CI run 且 gates 绿（=评审建议①等效新执行）；完整验证记录以 PR 评论留档（正文被本机多工具剪贴板劫持误写为 `D:\tech-blog`，以评论为准——环境偏离记录在案，见下"环境异常"）
- squash 合并 `ace5c5a`（单父提交、提交信息干净）；main CI 绿；本地三门禁 16 passed / 双 ruff 绿；远程+本地分支已删

### 环境异常记录（2026-10-25，非项目缺陷）

- 本机多个 AI 工具（WorkBuddy AI、DeepSeek Harness）与浏览器自动化互抢剪贴板/前台/标签页：建 PR 过程中剪贴板被劫持、表单被导航丢弃一次、PR 正文被误写；无仓库数据受损（探针核实未误建 PR）
- GitHub 新版 React 组件拒绝程序化点击（Create/Comment 按钮、合并方式下拉、设置复选框）：Create 与 Squash 合并由用户手点完成；评论经无障碍 setValue + Ctrl+Enter 发表成功

### M0 出口核验（2026-10-25）

| 出口条件 | 结果 | 证据 |
|---|---|---|
| 四卡全合并（T-001～T-004） | ✅ | main 时间线 10 笔至 `ace5c5a` |
| main 恒绿（本地+CI 双通道） | ✅ | CI success@ace5c5a；本地 16 passed/双 ruff |
| 分支保护生效 | ✅ | 直推探针被拒（GH013） |
| 评审独立性（⚠卡全量） | ✅ | T-002/T-003×2轮/T-004 均新会话请柬评审 |
| 克隆级安装验证 | ⚠️ 同机全新目录实测（见下），非新机器 | M0 收口批次补测，局限已注明 |

### M0 收口批次（本批，docs/m0-closure，2026-10-25）

用户拍板"6 件全办"：①执行台账落库（本文件）②测试矩阵 v1.1 入库 ③清 db.sqlite3（0 字节、已被忽略，仅本地删除）④R1 传递依赖快照 requirements/freeze.txt ⑤.gitattributes `* text=auto`（批次 1 悬置项）⑥基线 tag `m0`（合并后打）

- 克隆级验证：同机全新目录 `git clone → venv → pip install（阿里云镜像）→ pytest` 实测耗时见 PR 记录（局限：同机非新机器，作 30 分钟上界的部分证据）

---

## 遗留与悬决（进入 M1 前清点）

| # | 事项 | 状态 |
|---|---|---|
| 1 | B2：ALLOWED_HOSTS 空表（阶段 A 部署前立卡） | 已裁决挂账 |
| 2 | 仓库设置合并方式仍三种全开 + 未开自动删分支（网页复选框拒绝程序化操作） | 低优先，用户顺手或立卡处理 |
| 3 | 矩阵补强 2 条：trailing-slash 301（并入 T-018）、登录会话轮换断言（并入 T-027） | 已登记 |
| 4 | pip 26.2.2 可升级 | 不动（单一通道原则） |
| 5 | 旧 temp_20261023_05 目录已空待删 | 用户本地操作 |
