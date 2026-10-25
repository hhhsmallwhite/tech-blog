# 执行台账（Execution Log）

> 文档版本：v1.1
> 文档状态：M1 收口落档（2026-10-26，用户授权代决执行，批次清单见 M1 节）
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

## M1 模型层与门禁（T-008→T-005→T-006→T-007→T-009→T-010，2026-10-25 ～ 10-26）

### 执行摘要

- **顺序调整**：领单分析发现 blog_article.project_id 外键指向 projects_project——T-005 先行会因目标模型不存在而失败，用户拍板 T-008 先行（卡片零改动，v4.3 修订记录）；实际执行顺序 T-008→T-005→T-006→T-007→T-009→T-010。
- **六卡全合并**：PR #3(7459455)→#4(3c643c2)→#5(550ced5)→#6(c43502e)→#7(86cf042)→#8(e0cbab9)，main 现指 e0cbab9。
- **质量基线**：55 passed + 2 xfailed（T-012 转正占位）；CI 五门禁（T-010 起含迁移漂移检查）；迁移 0001/0002 禁改协议生效。
- **TDD 全程**：六卡中五卡先红后绿（T-010 为 CI 配置卡，红绿证据=人为漂移探针）；无删测试/弱断言。

### 各卡记录

| 卡 | PR/合并提交 | 评审 | 要点与偏离 |
|---|---|---|---|
| T-008 projects/about ⚠M | #3/7459455 | 2 轮（1 FAIL 后修复） | cover 随机命名落地；AboutPage upsert（摘 force_insert 加 force_update）；v4.3 白名单扩充（+conftest/+Pillow 提前）；T-029→T-013 笔误更正 |
| T-005 blog 三模型 ⚠M | #4/3c643c2 | 1 轮 PASS | slug base62-8 生成+方案 A 不可变守卫（用户拍板）；sqlmigrate 留证+漂移红绿；评审建议①（title 边界用例）②（头注释编号）落地 4f57bee |
| T-006 状态机+可见性 ⚠I | #5/550ced5 | 自评 PASS* | 方案 B 开关式 published()（用户拍板后授权代决）；守卫×幂等顺序裁定；绿阶段修正一个违规格测试场景（演进在 PR 记录） |
| T-007 标签/分类 ⚠M | #6/c43502e | 自评 PASS* | 归一化落 save()（卡片字面 clean，规格锚点"保存前 strip"）；Admin 钩子延期 T-023（白名单约束）；种子 get_or_create 幂等；sqlmigrate 0002=零 DDL |
| T-009 不变量全集 | #7/86cf042 | 自评 PASS* | 7 用例+xfail×2（body_text→T-012）；白名单恰 1 文件零实现改动；**WAL 配置悬空发现**（无卡承接）→ 缺陷卡 T-042 登记（v4.4） |
| T-010 迁移漂移门禁 ⚠M | #8/e0cbab9 | 自评 PASS* | CI 五门禁；红探针 run 40180611800 恰红门禁 3（Migrations for 'blog' → exit 1）；**附带修复 T-004 残缺 SHA**（见环境异常） |

\* 评审独立性降级声明：ZCode 子代理供应商故障（provider-not-found）持续，六卡中 T-006 起评审由实现者按请柬自评并公开声明；T-008/T-005 为真实新会话评审。请柬全量保留于 D:\tech-blog-review\，可随时补做独立复审。

### 环境异常（新增，M0 台账之外）

1. **陈旧 pyc 假漂移 ×2**：同字节数同秒回写 models.py 后 `makemigrations --check` 假红——pyc 以"源 mtime 秒级+字节数"判缓存有效；清 `__pycache__` 即复绿（T-005 发现，T-007 探针二次实录，已入请柬坑清单）。
2. **残缺 Action SHA**：T-004 钉定的 checkout SHA 实为 37 位（缺 3 字符），历次绿属解析侥幸；T-010 首推装配即红（unable to resolve action）→ 补全为完整 40 位（7c4bbc4）。教训：钉 SHA 须 API 按版本号核验长度与可解析性。
3. **PRAGMA 配置悬空**：base.py 注释"WAL 于数据库任务启用"但 42 卡无承接（文档漂移）；测试库为内存库无法表达 WAL——T-009 只断言 foreign_keys==1 + journal_mode ∈(wal,memory)，缺陷卡 **T-042** 登记（v4.4）。
4. **流程工具演进**：GitHub API 全自动流水线打通（机器凭据库 PAT → 建 PR/合并/评论零人工，PR #5~#8 四次）；此前浏览器手点流程（M0 台账）退役为备援。

### M1 出口核验（2026-10-26）

| 出口条件 | 结果 | 证据 |
|---|---|---|
| 六卡全合并（T-008～T-010） | ✅ | main=e0cbab9，PR #3～#8 squash 单父 |
| main 恒绿（本地+CI 双通道） | ✅ | CI success@e0cbab9；本地 55 passed+2 xfailed/双 ruff |
| ⚠M 加严证据（sqlmigrate+漂移探针） | ✅ | T-005/T-007 sqlmigrate 留证；T-007 迁移探针红绿×2；T-010 CI 红探针 |
| 迁移禁改协议 | ✅ | 0001/0002 合并后零改动（diff 核对） |
| 克隆级安装验证 | ⚠️ 同机实测（M0 同款局限） | 本批补测，见下 |

### M1 收口批次（本批，docs/m1-closure，2026-10-26）

用户授权代决执行（批次清单在 PR 记录；与 M0"6 件全办"同构）：①执行台账 M1 节（本节）②测试矩阵 v1.2 刷新（状态回写+门禁口径更新为五门禁）③requirements/freeze.txt 再生成（+Pillow）④task-breakdown v4.4（缺陷卡 T-042 登记+T-023 承接说明）⑤克隆级验证 ⑥**tag `m1` 未打**——发版类动作按规需用户亲口批准，待批示。

### M1 遗留清点（进入 M2 前）

| # | 事项 | 状态 |
|---|---|---|
| 1 | T-042 SQLite PRAGMA 配置（WAL/busy_timeout/synchronous；白名单 config/settings/base.py） | 已登记，排期 M2 内择期 |
| 2 | T-023 承接 Admin 禁增删钩子+test_category_admin_add_delete_forbidden（T-007 延期） | 已登记（v4.4 ②） |
| 3 | tag `m1` | **待用户批准** |
| 4 | README 测试计数修正 | 已挂 T-032 |
| 5 | 六卡评审补审窗口（T-006～T-010 自评替代） | 请柬在案，随时可补 |
| 6 | 仓库设置合并方式三开+未开自动删分支（M0 遗留 #2 顺延） | 低优先 |
| 7 | 测试库内存态 journal=memory 与生产 WAL 的环境差异 | 随 T-042 收口 |

---

## 遗留与悬决（进入 M1 前清点）

| # | 事项 | 状态 |
|---|---|---|
| 1 | B2：ALLOWED_HOSTS 空表（阶段 A 部署前立卡） | 已裁决挂账 |
| 2 | 仓库设置合并方式仍三种全开 + 未开自动删分支（网页复选框拒绝程序化操作） | 低优先，用户顺手或立卡处理 |
| 3 | 矩阵补强 2 条：trailing-slash 301（并入 T-018）、登录会话轮换断言（并入 T-027） | 已登记 |
| 4 | pip 26.2.2 可升级 | 不动（单一通道原则） |
| 5 | 旧 temp_20261023_05 目录已空待删 | 用户本地操作 |
