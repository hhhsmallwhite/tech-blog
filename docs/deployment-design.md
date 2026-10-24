# 部署设计与测试设计

> 文档版本：v1.0
> 文档状态：**已批准**（2026-10-23 用户确认，作为架构基线）
> 编写日期：2026-10-23
> 上游输入：`requirements-analysis.md` v1.1、`technology-decisions.md` v1.0（ADR-06/07/08）、`architecture.md`、`security-design.md`
> 本文档含两部分：测试设计（§1～6）与生产运维设计（§7～12）。一致性审查修订：部署序列补齐 collectstatic 步骤（OPS-7）。

## 第一部分：测试设计

### 1. 分层职责

| 层 | 工具 | 职责 | V1 状态 |
|---|---|---|---|
| L1 单元 | pytest | 模型不变量、状态机、管线净化、上传校验、health 检查 | 必做 |
| L2 接口集成 | pytest + Django test client | 全部 P/S/H/U/V 契约断言（状态码/内容/noindex/sitemap）+ Admin 操作 | 必做 |
| L3 E2E | Playwright（Chromium） | 真浏览器关键旅程（登录→写作→上传→发布→前台可见；撤回→404；锁定；改密） | 必做（冒烟集） |
| L4 前端组件 | Vitest | 自定义 JS 组件 | **V1 无**（服务端渲染 + 极少 JS，行为由 L3 覆盖；出现成规模自定义 JS 时再引入，TST-1） |

### 2. 测试数据库与生产隔离

| 项 | 设计 |
|---|---|
| 隔离机制 | pytest-django 自动创建独立 `test_*` SQLite 库，与 dev/prod 物理分离；生产环境**永不运行测试** |
| E2E 环境 | CI 内以 test settings 起真实服务（随机端口）+ 种子数据，跑完即弃 |
| 生产冒烟 | 部署后仅执行**只读**检查（§11 发布序列第 4 步），不写数据 |

### 3. 测试数据与迁移测试

- 数据构造：轻量 helper/fixture 函数（实体少，不引入 factory_boy）；分类种子由数据迁移自带；E2E 专用种子脚本。
- **迁移测试（TST-2）**：每次 CI 建测试库即从零跑全部迁移（隐式回归）；另加 `makemigrations --check` 门禁——模型与迁移漂移直接失败。

### 4. 关键用例清单（业务/边界/异常/权限）

| 组 | 用例 |
|---|---|
| 状态机 | 首发时间仅写一次；撤回保留；发布校验失败保持草稿；发布/撤回幂等 |
| 可见性七处一致性 | 草稿不出现在列表/详情/搜索/归档/上下篇/项目关联/sitemap（逐一断言） |
| 边界 | 分页 page=0/负/非数字/超界 → 404；恰好 11 篇时第 2 页；2MB 图片边界；标签同名不同大小写复用 |
| 异常 | 404/500 状态码与模板；空状态；上传三类拒绝码；CSRF 缺失 403 |
| 权限 | 未登录访问全部 admin URL → 302；U1 未认证 → 403 JSON；axes 5 次锁定（正确密码也拒）；登出会话失效 |
| 安全 | XSS 语料净化组（见 security-design.md §4）；搜索注入参数化；noindex/sitemap 内容断言 |
| 时区 | 跨月发布文章归档按 Asia/Shanghai 分组（DM-8） |

### 5. CI 必须通过（门禁顺序）

1. `ruff check` + `ruff format --check`
2. `makemigrations --check`（模型漂移）
3. `pytest`（L1+L2）
4. `manage.py check --deploy`（生产 settings）
5. Playwright E2E（冒烟集）
6. Docker build（可部署性）

mypy 后置（ADR 修正 #3）；覆盖率仅报告不设硬门槛（防指标博弈，TST-3）。

### 6. AC 追溯矩阵（分组）

| AC 组 | 覆盖层 |
|---|---|
| AC-01～10 公共阅读 | L2 集成为主，AC-01/05 加 L3 |
| AC-11～21 后台管理 | L2 + L3（登录/发布/撤回/删除全旅程） |
| AC-22～26 安全与一致性 | L1（哈希/约束）+ L2（权限/净化） |
| AC-27～33 SEO/分享/异常 | L2（内容断言）+ 阶段 B 人工复核收录 |
| AC-34～36 响应式/兼容/可访问性 | L3（视口断言）+ 人工抽检 |
| AC-37 性能 | 人工 + 页重检查（构建期断言静态资源预算） |
| AC-38 工程质量 | CI 门禁本身 |

## 第二部分：生产运维设计

### 7. 三环境差异

| 维度 | dev | CI/test | prod |
|---|---|---|---|
| DEBUG | True（仅 localhost） | False | False |
| DB | 本地 SQLite | 独立 test SQLite（用后即弃） | WAL SQLite（bind mount） |
| SECRET_KEY | 本地 .env | 随机生成 | 环境变量（强随机） |
| SITE_URL / ALLOWED_HOSTS | localhost | localhost | 阶段 A：ECS-IP；阶段 B：域名 |
| Cookie Secure | false | false | 阶段 A false / 阶段 B true |
| 备份/监控 | 无 | 无 | 每夜快照 + uptime |

### 8. 配置与密钥

- 环境变量清单（fail-fast）：`SECRET_KEY`、`DEBUG`、`SITE_URL`、`ALLOWED_HOSTS`、`COOKIE_SECURE`、`BACKUP_DIR`、`HEALTHZ_DISK_THRESHOLD`、`HEALTHZ_BACKUP_MAX_AGE`。
- 阶段 B 增配：`SECURE_PROXY_SSL_HEADER`（信任 Caddy 的 `X-Forwarded-Proto`）、`SECURE_SSL_REDIRECT`；HSTS 待运行稳定后启用。
- `.env.example` 入库作文档；实际 `.env` 仅存服务器与本地。

### 9. HTTPS、反向代理、服务进程、静态资源

| 组件 | V1 设计 |
|---|---|
| Caddy | 反代 → Gunicorn（127.0.0.1:8000）；gzip/zstd；基础安全头 + `/admin/*` noindex 注入（RV-6）；`/static/`、`/media/` 直读 + 长缓存；JSON 访问日志；阶段 B 自动 HTTPS + HTTP→301 |
| Gunicorn | 2 workers × 2 threads；timeout 30s；`restart: unless-stopped` + compose healthcheck（/healthz） |
| 静态资源 | `collectstatic` + ManifestStaticFilesStorage（哈希文件名，配合长缓存）；产物写入 bind mount 供 Caddy 直读 |

### 10. 数据库备份、恢复验证、迁移

沿用 `database-design.md` §8（DM-13：双层备份、14 天保留、月度演练、RPO 24h；部署序列含 migrate）。**补充（OPS-3）**：部署流水线在 migrate 前自动执行一次 SQLite 快照——每次发布都有回滚锚点。

### 11. 结构化日志、健康检查、错误告警

| 项 | V1 | 延后 |
|---|---|---|
| 应用日志 | Django 输出 JSON 行（时间/级别/模块/事件）到 stdout；Docker json-file + max-size 轮转 | request-id 贯穿、集中式日志 |
| 访问日志 | Caddy JSON 格式，含耗时与状态码 | — |
| 审计 | django_admin_log（DB）+ axes 记录 | — |
| 健康检查 | /healthz 三项（AD-10） | 证书到期检查 |
| 告警 | 外部 uptime 探测 /healthz → 邮件告警；磁盘/备份过期经 503 触发同一通道 | Sentry（错误追踪）、webhook 通知 |

### 12. 发布、回滚、故障排查

**发布（OPS-1：打 tag 才部署，发布是显式动作）**：

1. PR → CI 六门禁全绿 → 合并 main
2. 打 tag `vX.Y.Z` → Actions：构建镜像推 GHCR
3. SSH 部署序列：**快照 DB（OPS-3）→ pull 镜像 → `migrate` → `collectstatic` → `up -d`**（OPS-7：collectstatic 产物写入 bind mount，供 Caddy 直读）
4. 部署后冒烟（只读）：/healthz 200、`/`、`/articles/`、`/sitemap.xml` 200

**回滚**：重新部署上一 tag（GHCR 保留历史镜像）。**迁移兼容策略（OPS-2）**：只部署向后兼容迁移（加列/加索引）；破坏性变更跨版本执行（对齐 DM-12 三步法）——保证旧镜像 + 新 schema 可运行，回滚不需回数据库；极端情况用部署前快照恢复。

**故障排查 runbook（入库文档，OPS-6）**：

| 症状 | 首查 | 处置 |
|---|---|---|
| 全站不可达 | uptime 告警 / 安全组 | `docker compose ps` → restart / 重启实例 |
| 502 | gunicorn 存活 | 容器日志 → 定位异常 → 回滚 |
| 页面慢 | Caddy 访问日志耗时 | 带宽/图片大小 → 压缩/CDN |
| 后台锁死 | axes | 按文档清除尝试记录 |
| 磁盘告警 | /healthz checks | 清理旧备份/日志；图片审计 |
| 证书告警（阶段 B） | Caddy 日志 | 检查 80/443、DNS、备案状态 |
| 数据误删 | 备份目录 | database-design.md §8 恢复流程 |

### 13. 设计决策 TST-1～4、OPS-1～7

| # | 决策 | 依据 | 替代（不选原因） |
|---|---|---|---|
| TST-1 | 四层测试 V1 实现三层（无前端组件层） | 服务端渲染，JS 极少 | Vitest（无对象可测） |
| TST-2 | `makemigrations --check` 入 CI 门禁 | 模型/迁移漂移是隐形炸弹 | 事后发现（部署期爆炸） |
| TST-3 | 覆盖率只报告不设门槛 | 防指标博弈；关键用例清单才是真门禁 | 80% 硬门槛（为覆盖率写废测试） |
| TST-4 | E2E 在 CI 起真实服务 + 种子数据 | 验证的是真实栈而非 mock | 纯 mock（失真） |
| OPS-1 | 打 tag 触发部署 | 发布显式化、可追溯 | push 即部署（误发风险） |
| OPS-2 | 迁移向后兼容策略（破坏性延一版） | 保证回滚不需回数据库 | 随意破坏性迁移（回滚即事故） |
| OPS-3 | 部署前自动 DB 快照 | 每次发布有恢复锚点 | 仅每夜备份（发布窗口裸奔） |
| OPS-4 | JSON 行日志 + Docker 轮转，无集中式 | 单机规模 | ELK/Loki（运维负担失控） |
| OPS-5 | 部署后只读冒烟 | 生产永不跑写测试 | 全量 E2E 打生产（危险） |
| OPS-6 | runbook 入库 | 单人维护的记忆外置 | 脑内 runbook（不可交接） |
| OPS-7 | 部署序列含 collectstatic（写入 bind mount） | 静态产物需 Caddy 可读；镜像内无法跨容器共享文件 | 镜像内 collectstatic（Caddy 读不到）；Caddy 代理 Django serve（耗 Python worker） |
