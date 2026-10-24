# 个人技术博客技术选型分析

> 文档版本：v1.2
> 文档状态：已确认（决策结论见 `docs/technology-decisions.md`；v1.2 增补经用户 2026-10-24 批准）
> 编写日期：2026-10-23
> 修订日期：2026-10-24（v1.2：0.1 主方案表新增 python-dotenv 1.2.4——dev/本地从 `.env` 加载 8 个环境变量，来源 deployment-design §8；v1.1：修正 CD 构建位置、SQLite 持久化方式、mypy 门禁时机、Python 版本兜底）
> 资料核查日期：2026-10-23
> 需求基线：`docs/requirements-analysis.md` v1.1（2026-10-23 已批准，Q-01～Q-08 全部落定；原待确认项记录见 11.3）
> 文档边界：只做技术选型分析与推荐，不创建项目、不安装依赖、不编写业务代码，也不替代后续架构设计。

## 0. 结论摘要

### 0.1 推荐主方案

**以“上线成功率、可维护性、基本生产安全”为第一优先级，推荐 Django 单体方案。**

| 层次 | 推荐选择 | 核查时版本 | 核心理由 |
|---|---|---|---|
| 运行时 | Python 3.13 / 3.14 | 3.14.7 | Django 5.2 LTS 官方支持 3.13–3.14；**3.13 为兜底**，见 10.1 |
| 后端/全栈 | Django | 5.2.17 LTS | 内置认证、会话、CSRF、Admin、ORM、迁移、模板；服务端渲染，发布即生效 |
| 数据库 | SQLite | 3.54.1 | 单机、单作者、读多写少；WAL 支持并发读；文件级备份简单 |
| 数据访问 | Django ORM + 内置迁移 | 随 Django | 与 Admin、认证、测试集成最紧密；后续可迁移 PostgreSQL |
| 配置加载 | python-dotenv | 1.2.4 | dev/本地从 `.env` 读取 8 个环境变量（deployment §8）；2026-10-24 用户批准新增（方案 B，替代自写解析器） |
| 前端 | Django 模板 + HTMX + Alpine.js | 随项目 | HTML-first、SEO 友好、首屏轻、无需独立前端构建 |
| 后台 | Django Admin + ModelAdmin | 随 Django | 文章/项目/关于页 CRUD、草稿/发布、删除确认、密码修改均可复用 |
| Markdown/高亮 | Python-Markdown + Pygments + nh3 | 以实施时锁定版本为准 | 服务端渲染，SEO 与安全边界清晰；nh3 替换已弃用的 bleach |
| 搜索 | Django `icontains`（标题/摘要/正文文本） | 随 Django | 数据量小，无需额外搜索服务；后续可升级 SQLite FTS5 |
| 部署 | 阿里云 99 元/年 ECS + Docker Compose + Caddy | ECS 2C2G/3M/40G；Caddy 2.10.0 | 单机、低成本、可重复部署；Caddy 自动 HTTPS |
| CI/CD | GitHub Actions + SSH 部署 | 免费公有仓库；私有仓库 2,000 分钟/月 | 生态成熟；避免在 2C2G 服务器上跑复杂构建 |
| 测试 | pytest + pytest-django + Playwright + Ruff（mypy 后置） | pytest 9.1.1；Playwright 1.64 | 覆盖业务规则、真实浏览器流程、静态检查；类型检查上线后引入 |
| 备份 | 阿里云文件备份 + SQLite 在线备份 + 媒体归档 | 99 套餐含 100GiB 文件备份权益 | 与单机 SQLite 匹配；恢复路径简单、可演练 |

**一句话结论**：本项目的内容量、访问量、写并发和运维预算都不需要分布式架构；Django + SQLite + 服务端模板能让“发布立即生效、SEO 可控、后台可用、备份简单”同时成立，且把最容易出错的身份认证、CSRF、后台 CRUD 交给成熟框架，而不是自研。

### 0.2 条件性替代方案

| 方案 | 适合前提 | 主要代价 | 结论 |
|---|---|---|---|
| FastAPI + Jinja2/HTMX + SQLAlchemy + Alembic + SQLite | 你把“学习 FastAPI、API-first、异步生态”放在首位，并接受自建认证、CSRF、后台 CRUD | 多一套认证/会话/后台代码；安全与测试成本显著增加 | 合理备选，不作为默认推荐 |
| Next.js 16 LTS + Prisma 7 + SQLite/PostgreSQL | 你把“React/TypeScript 全栈”作为核心学习目标，并接受 Node 运行时 | 构建内存、运行时、缓存与安全补丁面更大；2C2G 上更吃紧 | 备选，不作为默认推荐 |
| Astro 7 + FastAPI | 你愿意接受“发布后触发静态重建”的延迟，或改用 Astro SSR | 与“保存后立即生效/无需重新部署”的验收标准直接冲突；多一条构建/部署链路 | 条件备选，首版不推荐 |
| Django + PostgreSQL | 你明确要学习 PostgreSQL，或预期未来多实例/高写并发 | 多一个数据库服务、内存占用、备份与升级步骤 | 可作为迁移目标；首版不必 |

### 0.3 不推荐方案

- **NestJS**：对本项目是明显的过度设计；没有内置后台、认证、ORM 迁移和模板，样板代码多，Node 运行时还会增加部署面；与 Python/AI 学习方向也不一致。
- **Headless CMS（Strapi/Directus 等）**：会引入额外的 Node 服务、数据库、补丁和资源占用；本项目的固定分类、项目-文章关联、关于页结构化字段仍需要定制，未必比 Django Admin 省事。
- **微服务、消息队列、Redis、Elasticsearch、Kubernetes**：需求中没有对应的并发、异步任务、全文检索或弹性伸缩要求；引入它们只会增加故障面和维护成本。
- **公开站使用纯 React SPA（Vite）**：SEO 需要额外预渲染/SSR；对本项目是额外复杂度，不是收益。

## 1. 需求与约束核对

### 1.1 需求文档状态

- 需求文档内容完整，覆盖页面、角色、功能边界、数据实体关系、异常场景和验收标准。
- 编写本文档时需求文档为“待审核”状态；2026-10-23 需求文档已获用户批准，Q-01～Q-08 全部落定（原待确认项 Q-01～Q-05、Q-07 确认沿用默认值，见 11.3）。
- 本轮技术选型以该文档 v1.1 为基线，涉及未确认项的选型标注为“条件性推荐”，不把未确认项当作既定事实，例如项目状态枚举、项目隐藏状态、标签管理、文章封面、图片限制、站点文案。

### 1.2 硬性约束

1. 单作者、公开只读、无评论、无多用户、无多角色。
2. 部署在阿里云 99 元/年大陆 ECS：2 核 2G、3M 固定带宽（不限流量）、40G ESSD Entry 云盘。
3. 预算以服务器约 99 元/年为主，域名等费用另计；不引入额外常驻付费服务。
4. 公开页面需要基础 SEO、稳定 URL、404 状态、sitemap、robots、canonical 与分享卡片信息。
5. 后台发布/撤回/关于页保存后需要前台立即生效，不依赖改代码或手动重新部署。
6. 基本生产安全：HTTPS、密码不可逆存储、会话、CSRF、XSS 净化、上传校验、登录失败锁定、备份可恢复。
7. 核心流程需要自动化测试与 CI 质量门禁，主分支可部署。
8. 单人维护，优先减少需要长期照看的组件。

### 1.3 对技术选型有决定性影响的需求

| 需求 | 对选型的影响 |
|---|---|
| 发布后立即生效（AC-16/AC-19） | 纯静态生成（Astro static）需要重建/重新部署才能生效，和验收标准冲突；服务端渲染或 SSR 更合适 |
| SEO + 3M 带宽 | 优先 HTML-first、少量 JS、图片懒加载；避免首屏加载大型前端 bundle |
| 单管理员后台 | 内置认证/Admin/CSRF 的框架能显著减少自研安全代码 |
| 单机、低写入 | SQLite 的单写者模型可接受；不需要 PostgreSQL 常驻服务 |
| 2C2G/40G | 不适合同时跑应用、数据库、搜索服务、Node 构建和多个前端服务 |
| 无评论/无多用户 | 不需要 Redis 会话集群、消息队列、复杂权限系统 |
| 图片上传 2MB、无媒体库 | 本地媒体目录 + 备份即可；OSS 可后置 |
| 单人维护 | LTS、少组件、单代码库、简单备份优先于“技术先进性” |

### 1.4 学习诉求与项目合理性的边界

- **已确认的工程目标**：架构与可维护性、CI/CD 与自动化测试、AI Agent 协作研发流程。
- **可能的学习偏好（未确认）**：FastAPI、React/TypeScript、Astro、PostgreSQL。
- **原则**：学习价值只在满足硬约束、风险可接受之后作为加分项；不能用“想学某框架”来掩盖自研认证/后台、额外运行时或静态发布延迟带来的实际成本。
- 如果目标是学习 FastAPI，更合理的做法是：主站用 Django 保证交付，把 FastAPI 放到后续独立的 AI/检索小服务或第二个作品里，而不是让博客主站承担两套认证与后台。

## 2. 评价标准

所有候选按同一组标准评分，1～5 分，5 分最好。对“开发复杂度、维护成本、部署成本”三个维度，5 分表示更简单/更低成本，避免分数方向混淆。

| 维度 | 权重 | 说明 |
|---|---:|---|
| 需求适配度 | 25% | 是否直接满足已确认需求，尤其是立即发布、SEO、单管理员后台 |
| 开发复杂度 | 15% | 需要自研的模块数量、集成面、调试成本 |
| 维护成本 | 15% | 版本升级、补丁、备份、故障排查、长期照看成本 |
| 部署成本 | 10% | 服务器资源、费用、部署步骤、可重复性 |
| 安全性 | 10% | 认证、会话、CSRF、XSS、上传、默认安全配置 |
| 性能 | 10% | 3M 带宽下的首屏、HTML/JS 体积、数据库读写 |
| 生态成熟度与扩展 | 10% | 文档、社区、插件、未来迁移路径 |
| 学习价值 | 5% | 对架构、CI/CD、Agent 协作或目标技术栈的学习收益 |

**硬门槛**：不满足“单机 99 ECS 可运行、SEO、立即发布、单管理员、低维护、无额外常驻服务”的方案，不进入推荐位，评分只用于解释差距，不用加权总分掩盖硬伤。

## 3. 前端技术

### 3.1 候选与评分

> 说明：Django 模板 + HTMX 与 FastAPI + Jinja2/HTMX 同属服务端渲染路线；下表以 Django 为例。Astro/Next/React 的评分以其独立前端形态为准。

| 方案 | 需求适配 | 开发复杂度 | 维护成本 | 部署成本 | 安全 | 性能 | 生态/扩展 | 学习价值 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Django 模板 + HTMX + Alpine | 5 | 4 | 5 | 5 | 4 | 5 | 4 | 4 | **推荐** |
| Astro 7 | 3 | 3 | 4 | 3 | 4 | 5 | 4 | 4 | 条件备选 |
| Next.js 16 LTS | 4 | 2 | 3 | 3 | 3 | 4 | 5 | 5 | 备选 |
| React + Vite SPA | 2 | 4 | 4 | 4 | 4 | 3 | 5 | 4 | 公开站不推荐 |

### 3.2 逐项分析

#### 3.2.1 Django 模板 + HTMX + Alpine

**适合**
- 内容阅读为主、交互集中在后台表单和少量前端行为（复制链接、系统分享、TOC、代码高亮）。
- 需要发布后立即生效、SEO 友好、首屏轻量。
- 希望一个代码库、一次部署完成公开站与后台。

**不适合**
- 需要复杂富交互、大量客户端状态、离线能力或原生 App 式体验。
- 团队前端希望以 React 组件库为主进行长期开发。

**主要风险**
- 模板层容易写出重复的 HTML；需要用 include/模板标签保持结构清晰。
- HTMX/Alpine 的交互测试要依赖 Playwright，而不是纯单元测试。
- 如果未来公开站需要复杂交互，可能需要迁移到 Astro/Next；迁移成本中等。
- CSS 方案在架构/UI 阶段确定；为保持“零 Node 构建”，优先原生 CSS/自定义属性；若采用 Tailwind，可用独立 CLI，不引入 SPA 构建链。

**评价**：在本项目里，它是“最少活动部件”的方案。Django 模板负责 SEO 和首屏，HTMX 负责局部刷新，Alpine 负责少量状态；没有独立 Node 构建，也没有 hydration。

#### 3.2.2 Astro 7

**适合**
- 内容驱动站点、静态生成、极致首屏与 SEO。
- 前端团队熟悉组件化，但不需要常驻 Node 服务。
- 可以接受“发布后触发构建”的内容工作流。

**不适合 / 关键冲突**
- 需求明确要求“已发布文章保存后立即生效”“关于页保存后前台刷新可见”“无需改代码或重新部署”。Astro 的默认静态输出需要在发布后重新构建并部署；即使由 webhook 自动触发，也存在构建/部署延迟，并且多了一条构建链路。
- 若要真正即时，需要 Astro SSR（Node adapter），这会把部署变成“Python API + Node SSR + 静态资源”的多运行时结构，和“减少常驻服务”的约束冲突。

**迁移成本**
- 从 Astro static 迁到 Django/Next：公开页面模板需要重写；如果保留 FastAPI，内容 API 可复用；发布流程要从“重建”改为“服务端渲染”。
- 从 Django 模板迁到 Astro：需要引入内容 API、构建/发布流水线和前端组件体系；中等偏高。

**评价**：Astro 是优秀的博客框架，但它的静态发布模型与当前验收标准冲突。除非你愿意修改“立即生效/无需重新部署”的验收标准，或接受 Astro SSR 的 Node 运行时，否则不应作为首版主方案。

#### 3.2.3 Next.js 16 LTS

**适合**
- 明确要以 React/TypeScript 全栈作为学习目标。
- 需要 SSR/ISR、复杂路由、服务端组件、同一代码库内的前后端。
- 可以接受 Node 运行时、构建内存和更频繁的框架升级。

**不适合**
- 以最低运维成本、最低资源占用为优先的内容站。
- 2C2G 服务器上同时跑应用、数据库、构建和 Node 运行时。
- 不希望处理缓存、图片优化、SSR/ISR 的安全与失效问题。

**主要风险**
- Next.js 16 是 Active LTS，安全更新节奏快；2026 年 9 月的安全公告涉及自托管 SSG/ISR 缓存污染、图片优化 SSRF 等问题，需要及时打补丁。
- 构建和运行都比 Django 模板重；在 2C2G 上需要更谨慎的构建策略（CI 构建、standalone 输出）。
- 如果只用它做公开站，Django/FastAPI 仍需另做后台，反而增加集成面。

**评价**：Next.js 能满足 SEO 与立即更新，但它是“为 React 全栈学习付费”的方案，不是本项目的最优解。

#### 3.2.4 React + Vite SPA

**适合**
- 后台管理界面、内部工具、需要大量客户端交互的应用。
- 作为 Django/FastAPI 后台的独立 SPA，而不是公开内容站。

**不适合**
- 公开博客：SPA 的 HTML 初始内容少，SEO 需要预渲染/SSR；首屏依赖 JS，3M 带宽下更吃亏。
- 需要“复制链接/系统分享/TOC/代码高亮”等轻交互的阅读页，用 SPA 是杀鸡用牛刀。

**评价**：不推荐作为公开站。若确实想要 React 后台，可以后续把 Django Admin 替换为独立 SPA，但首版没有必要。

### 3.3 前端迁移成本

| 迁移 | 成本 | 说明 |
|---|---|---|
| Django 模板 → Astro/Next | 中高 | 模板重写、内容 API/构建流水线、前端组件体系 |
| Astro static → Django/Next | 中高 | 发布模型从“重建”改为“服务端渲染”；路由/模板重写 |
| Next.js → Django/Astro | 高 | 前后端边界、数据获取、认证与部署全部重做 |
| React SPA → Django 模板 | 中 | 公开页重写；如果只用于后台，可保留 SPA |

### 3.4 前端推荐

- **主方案**：Django 模板 + HTMX + Alpine。
- **条件备选**：Next.js 16 LTS（React/TS 学习优先）；Astro 7（接受重建延迟或 SSR，需先修改验收标准）。
- **不推荐**：公开站使用 React + Vite SPA。

## 4. 后端技术

### 4.1 候选与评分

| 方案 | 需求适配 | 开发复杂度 | 维护成本 | 部署成本 | 安全 | 性能 | 生态/扩展 | 学习价值 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Django 5.2 LTS | 5 | 4 | 5 | 5 | 5 | 4 | 4 | 4 | **推荐** |
| FastAPI 0.143 | 3 | 2 | 3 | 4 | 3 | 5 | 5 | 5 | 条件备选 |
| NestJS 11.2 | 2 | 2 | 3 | 3 | 3 | 4 | 5 | 4 | 不推荐 |

### 4.2 逐项分析

#### 4.2.1 Django 5.2 LTS

**适合**
- 内容管理 + 公开站点 + 单管理员后台。
- 希望认证、会话、CSRF、Admin、ORM、迁移、模板、安全默认值开箱可用。
- 希望服务端渲染、发布即生效、SEO 稳定。
- 希望长期维护成本低、版本支持周期明确。

**不适合**
- 只想要纯 JSON API、由独立前端消费。
- 需要大量异步 I/O、WebSocket 或事件驱动架构。
- 团队已经重度使用 TypeScript 全栈。

**优势**
- Django Admin 直接覆盖文章/项目/关于页的 CRUD、筛选、删除确认、密码修改；自定义 ModelAdmin 可加 Markdown 编辑器和图片上传。
- 内置 auth/session/CSRF/密码哈希/安全中间件；`manage.py check --deploy` 提供部署安全检查清单。
- Django 5.2 是 LTS，支持到 2028 年 4 月；Python 3.14 受支持；升级到 6.2 LTS 的路径明确。
- 单代码库、单应用进程，和 SQLite、Caddy、Docker Compose 的部署模型匹配。

**风险**
- Django Admin 的默认 UI 是内部管理工具，不是面向公众的产品界面；公开站必须用自定义模板，不能把 Admin 当公开前端。
- 模板层的前端体验不如 React 生态；复杂交互需要 HTMX/Alpine 或后续迁移。
- Django 官方在生产环境推荐 PostgreSQL；SQLite 需要额外说明适用边界（见第 5 节）。

#### 4.2.2 FastAPI 0.143

**适合**
- API-first、前后端分离、AI/Agent 服务、需要 OpenAPI/Pydantic 的强类型接口。
- 团队希望 Python 异步栈、独立前端（Astro/Next/React）。
- 想把博客作为 API 设计的练习。

**不适合**
- 需要开箱即用的后台、认证、会话、CSRF、模板。
- 单人、低维护、希望减少自研安全代码的项目。

**优势**
- Pydantic 校验、OpenAPI 文档、依赖注入、异步性能好。
- 与 AI/Agent 生态自然衔接；后续做 RAG/Agent 服务时更顺手。
- SQLAlchemy 2.1 + Alembic 是成熟的 Python 数据访问组合。

**风险**
- FastAPI 官方安全文档明确指出，认证/授权在很多系统里可能占代码量的一半以上；本项目还需要后台 CRUD、Markdown 编辑器、图片上传、登录锁定、CSRF、会话管理，全部要自研或集成。
- 需要额外决定：Jinja2/HTMX 还是独立 SPA；会话还是 JWT；CSRF 如何保护表单；后台如何做草稿/发布/预览。这些都是容易出错的地方。
- 两套运行时/构建链（FastAPI + 前端）增加部署与测试面。

**评价**：FastAPI 不是“不能做”，而是“用更多工程量换 API/异步学习”。如果这是你的核心目标，它是合理备选；如果目标是上线和维护，它不是最优。

#### 4.2.3 NestJS 11.2

**适合**
- 大型 TypeScript 服务、团队协作、需要模块化/DI/守卫/拦截器的企业应用。
- 前端团队以 TypeScript 为主，希望共享类型与工程规范。

**不适合**
- 单作者内容博客；功能规模和团队规模都不匹配。
- 希望低维护、少样板、少运行时。

**风险**
- 需要自建后台、认证、模板/前端；对本项目没有内置能力优势。
- Node 运行时 + 构建 + 依赖升级 + 2C2G 资源，均比 Django 单体更重。
- 与 Python/AI 学习方向不一致。

**评价**：不推荐。它是“为大型团队/复杂后端付费”的框架，本项目没有对应规模。

### 4.3 后端迁移成本

| 迁移 | 成本 | 说明 |
|---|---|---|
| Django → FastAPI | 高 | 认证、会话、CSRF、Admin、模板全部重做；ORM 换 SQLAlchemy；DB 可迁移 |
| FastAPI → Django | 高 | API 层重写；SQLAlchemy → Django ORM；自建后台 → Django Admin |
| Django/FastAPI → NestJS | 很高 | 语言、运行时、ORM、认证、部署全部重做 |
| Django 5.2 LTS → 6.2 LTS | 低中 | 按发布说明升级；LTS 路径明确 |

### 4.4 后端推荐

- **主方案**：Django 5.2 LTS。
- **条件备选**：FastAPI 0.143 + Jinja2/HTMX + SQLAlchemy 2.1 + Alembic 1.19；仅当你明确优先 API-first/FastAPI 学习，并接受自建认证与后台。
- **不推荐**：NestJS。

## 5. 数据库与数据访问

### 5.1 数据库：SQLite vs PostgreSQL

| 维度 | SQLite 3.54 | PostgreSQL 18.6 |
|---|---|---|
| 部署 | 单文件、无独立服务 | 独立服务/容器，需要端口、用户、连接池 |
| 并发 | 多读 + 单写；WAL 下读写可并行 | MVCC，多写并发强 |
| 本项目适配 | 单作者、写操作少、单机；非常合适 | 能力过剩；除非未来多实例/高写并发 |
| 备份 | 文件复制/在线备份 API；最简单 | pg_dump/PITR；更成熟但步骤更多 |
| 迁移 | 文件级；换机简单 | dump/restore、版本升级更规范 |
| 资源 | 几乎无额外内存 | 常驻内存与维护成本更高 |
| 扩展 | 单机；多实例/网络文件系统不适合 | 多实例、只读副本、托管数据库 |
| 结论 | **首版推荐** | 条件备选/迁移目标 |

**关键判断**
- SQLite 官方明确说明：网站读多写少、单机应用服务器、写入可排队时，SQLite 是合适的；只有高写入量、多服务器或大量并发写时才需要客户端/服务器数据库。
- Django 官方在生产环境推荐 PostgreSQL，但 SQLite 也是官方支持的数据库；这是通用建议，不是对本项目写并发的硬性要求。
- 本项目写操作只来自一个管理员：发布/撤回/编辑文章、项目、关于页；读操作是访客浏览。写事务很短，SQLite 的单写者队列完全够用。
- 需要配置：WAL 模式、`busy_timeout`、外键约束、合理的 `synchronous`；不要放在 NFS/网络文件系统上；只运行一个应用容器（多 worker 可共享同一文件，但写会串行）。
- 备份：使用 SQLite 在线备份 API 或 `VACUUM INTO`，不要在高写入时直接 `cp` 数据库文件；配合阿里云文件备份。
- 迁移到 PostgreSQL：Django ORM 让 schema 迁移相对平滑；需要停机/双写窗口、数据导出导入、连接配置切换；不是零成本，但可控。

**什么时候应该直接选 PostgreSQL**
- 你明确想学习 PostgreSQL 运维；
- 预期多实例/多容器同时写；
- 需要行级锁、复杂并发事务、物化视图、PostGIS 等；
- 未来要做多用户/评论/协作。
如果没有这些前提，首版 PostgreSQL 是“用运维成本换用不到的能力”。

### 5.2 ORM/数据访问

| 方案 | 适配后端 | 优势 | 代价 | 结论 |
|---|---|---|---|---|
| Django ORM + 内置迁移 | Django | 与 Admin/auth/测试集成最好；迁移开箱即用；查询 API 足够 | 复杂 SQL/异步能力不如 SQLAlchemy | **Django 路线推荐** |
| SQLAlchemy 2.1 + Alembic 1.19 | FastAPI/任意 Python | 显式、灵活、类型友好；SQL 控制力强 | 需要单独配置 session、迁移、模型组织 | **FastAPI 路线推荐** |
| Prisma 7.10 | Node/Next/Nest | 类型安全、DX 好、迁移工具体验好 | 引入 Node 运行时与生成步骤；Prisma 8 仍是 RC | 仅 Node 路线；首版不推荐 |

**注意**
- 不要把 ORM 和数据库当成同一层选择：SQLite 可以配 Django ORM、SQLAlchemy 或 Prisma；PostgreSQL 也一样。先定后端，再定 ORM。
- Prisma 8.0 在核查时为 RC，不应在生产使用；若走 Node 路线，锁 Prisma 7.10.x 稳定版。
- Alembic 1.19.2 与 SQLAlchemy 2.1.6 是当前稳定组合；SQLAlchemy 2.0.55 仍在维护，但新项目优先 2.1。

### 5.3 搜索方案

| 方案 | 适合 | 代价 | 结论 |
|---|---|---|---|
| Django `icontains` / SQLite LIKE | 文章量小、只需子串匹配、无排名 | 无法利用索引，数据量大时慢；无相关性排序 | **首版推荐** |
| SQLite FTS5 + 中文分词 | 文章增多、需要排名/性能 | 需要额外 FTS 表、分词（如 jieba）、同步逻辑 | 后续升级 |
| PostgreSQL 全文检索 | 已使用 PostgreSQL、需要排名 | 中文分词仍需扩展；运维面更大 | 迁移后再考虑 |
| Meilisearch/Elasticsearch | 大规模搜索、独立搜索体验 | 额外常驻服务、内存、备份、监控 | 首版不引入 |

**建议**：首版用标题、摘要、正文纯文本的 `icontains`；在保存文章时生成/更新 `body_text`（去除 Markdown 标记），避免每次查询都做 Markdown 解析。数据量超过数千篇或搜索体验成为关键时，再评估 FTS5。

### 5.4 数据库推荐

- **首版**：SQLite 3.54.1 + Django ORM + 内置迁移 + WAL。
- **条件备选**：PostgreSQL 18.6（Django 5.2 官方支持 PostgreSQL 14+；上线前在 CI 验证 18.x 兼容性）。
- **迁移路径**：Django ORM → PostgreSQL 是中等成本；先保持模型层干净，避免 SQLite 特有 SQL。
- **搜索**：首版 LIKE/`icontains`；不引入独立搜索服务。

## 6. 认证、后台与内容渲染

### 6.1 认证与后台方案

| 方案 | 需求适配 | 开发复杂度 | 维护成本 | 安全 | 结论 |
|---|---:|---:|---:|---:|---|
| Django auth + Django Admin | 5 | 5 | 5 | 5 | **推荐** |
| FastAPI 自建 session + Jinja2/HTMX Admin | 3 | 2 | 3 | 3 | 条件备选 |
| Next.js Auth.js + 自建 Admin | 3 | 3 | 3 | 3 | 备选（TS 优先） |
| Headless CMS（Strapi/Directus） | 3 | 3 | 2 | 3 | 不推荐 |

**Django 路线**
- 内置 User/Group/Permission、session、CSRF、密码哈希、登录/退出、密码修改。
- Django Admin 提供模型级 CRUD、列表筛选、搜索、批量操作、删除确认；用 ModelAdmin 定制文章状态、项目关联、关于页单例。
- 需要额外做：Markdown 编辑器控件（EasyMDE/CodeMirror 二选一，后台专用）、图片上传字段与校验、发布/撤回动作、预览视图、登录失败锁定（django-axes 8.3.1）。
- Django Admin 文档明确说它是内部管理工具，不建议作为整个前台；公开站用自定义 Django 模板，这是正确分工。
- Q-06 的“修改密码”在 Django Admin 中几乎零成本，已确认提供；需求文档 Q-06 已同步从“不提供”改为“提供”。

**FastAPI 路线**
- 必须自建：登录页、密码哈希、会话存储、CSRF、锁定、后台列表/编辑/删除、预览、图片上传、Markdown 编辑器集成。
- 建议用服务端 session cookie + CSRF，不要用 JWT 放在 localStorage；浏览器后台场景下 JWT 带来的收益很小，风险更高。
- 适合学习，但安全代码量和测试量明显增加。

**Next.js 路线**
- Auth.js 可提供会话/OAuth，但单管理员仍要自建后台 CRUD、草稿/发布、图片上传、Markdown 编辑。
- 引入 Node 运行时、数据库适配、构建与缓存配置；对本项目是额外层。

**Headless CMS**
- 后台开箱即用，但需要额外的 Node 服务、数据库、补丁、备份；固定分类/项目关联/关于页单例/SEO 字段仍需定制。
- 对 2C2G 单机是明显的资源与维护负担；不推荐。

### 6.2 Markdown、代码高亮与安全

| 方案 | SEO | 安全 | 性能 | 复杂度 | 结论 |
|---|---:|---:|---:|---:|---|
| 服务端 Python-Markdown + Pygments + nh3 | 5 | 4 | 5 | 4 | **推荐** |
| 客户端 markdown-it + Shiki/Prism | 3 | 3 | 3 | 4 | 仅后台预览 |

- 公开页在服务端渲染 Markdown，HTML 直接进入页面，SEO 和无 JS 阅读都成立。
- 代码高亮用 Pygments 在服务端生成 HTML/CSS，避免给访客加载语法高亮 JS。
- Markdown 允许原始 HTML 时必须净化：`bleach` 已于 2026-06-05 停止维护，使用 `nh3`（Rust ammonia 绑定）做白名单净化。
- 目录用 Python-Markdown 的 TOC 扩展；代码块用 fenced code + CodeHilite/Pygments（CodeHilite 处于维护模式，但功能稳定）。
- 后台预览可以用同一套服务端渲染，或用一个只存在于后台的 JS 预览器；公开页不要依赖客户端 Markdown 解析。

### 6.3 认证/后台推荐

- **主方案**：Django auth + Django Admin + ModelAdmin + EasyMDE/CodeMirror + django-axes。
- **密码修改**：启用 Django Admin 自带的密码修改，成本接近零，补齐基本账户安全（已确认，见 `technology-decisions.md` ADR-05）。
- **FastAPI 条件方案**：服务端 session + CSRF + Jinja2/HTMX 后台；不要为了“现代”上 JWT + SPA。
- **不推荐**：Headless CMS、JWT 存 localStorage、把 Django Admin 当公开前台。

## 7. 部署与运维

### 7.1 部署方案对比

| 方案 | 需求适配 | 开发复杂度 | 维护成本 | 部署成本 | 安全 | 性能 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---|
| 阿里云 ECS + Docker Compose + Caddy | 5 | 4 | 4 | 5 | 4 | 4 | **推荐** |
| Vercel/同类静态托管 + Serverless | 2 | 5 | 4 | 5 | 4 | 5 | 不适合本项目约束 |
| 阿里云 ECS + systemd + Nginx（无 Docker） | 4 | 3 | 3 | 5 | 4 | 4 | 备选 |

**阿里云 ECS + Docker Compose + Caddy**
- 99 元/年 ECS：2C2G、3M 固定带宽（不限流量）、40G ESSD；官方页面标注续费同价、价格锁至 2029-03-31，并含 100GiB 文件备份权益（活动资格以页面为准）。
- 拓扑：Internet → Caddy（443/80，自动 HTTPS、压缩、静态媒体）→ Gunicorn/Django → SQLite + 本地媒体目录。
- 两个容器即可：`web` + `caddy`；不需要数据库容器、Redis、Nginx、Node。
- **持久化使用 bind mount**：`/srv/blog/data`（SQLite）与 `/srv/blog/media`（图片）挂载到容器内固定路径，不使用 named volume。备份脚本（cron 中的 `sqlite3 .backup` / `VACUUM INTO`）可直接在原地执行，无需 `docker exec` 绕行；阿里云文件备份也能直接覆盖该目录。
- Docker Compose 提供可重复部署；Caddy 自动申请/续期证书；Docker restart policy + healthcheck 提供基本恢复。
- 3M 带宽约 384KB/s 下载；必须控制首屏资源，建议首屏 HTML/CSS/JS 总计控制在 500KB 以内，图片懒加载。
- 大陆服务器绑定域名需要 ICP 备案；没有备案域名时只能先用 IP 做测试，不应把后台长期暴露在公网 HTTP 上。

**Vercel/同类静态托管 + Serverless**
- Hobby 免费、全球 CDN、部署体验好；但本项目要求大陆访问稳定、单机 SQLite、后台与图片上传，Serverless + 静态托管需要额外的托管数据库/对象存储，SQLite 不适合。
- 大陆访问与备案/合规存在不确定性；不适合作为主部署。
- 仅适合作为纯静态展示镜像或未来的前端预览，不是主站方案。

**ECS + systemd + Nginx（无 Docker）**
- 资源开销更低、依赖更少；但部署步骤手工、环境不可重复、CI/CD 集成更麻烦。
- 如果不想学 Docker，可作为退路；但本项目明确要练 CI/CD 和可重复部署，Docker Compose 更合适。

### 7.2 CI/CD 方案对比

| 方案 | 需求适配 | 开发复杂度 | 维护成本 | 成本 | 安全 | 网络 | 结论 |
|---|---:|---:|---:|---:|---:|---:|---|
| GitHub Actions + SSH 部署 | 5 | 4 | 4 | 5 | 3 | 3 | **推荐** |
| 阿里云自托管 Runner | 4 | 3 | 2 | 5 | 2 | 5 | 不推荐（生产同机风险） |
| 阿里云云效/Codeup | 4 | 3 | 4 | 4 | 4 | 5 | 备选（待核实价格/功能） |

**GitHub Actions + SSH**
- 公有仓库的 standard runner 免费；私有仓库 GitHub Free 含 2,000 分钟/月、500MB 存储；超出按量计费。
- CI：Ruff、pytest、Django `check --deploy`、Playwright 冒烟、Docker build（mypy 后置，见 8.2/8.3）。
- CD：仅在 main 分支通过 CI 后，由 Actions 构建镜像并推送 GHCR，再通过 SSH 到阿里云执行：备份数据库 → `docker compose pull` → 迁移 → `up -d` → 健康检查；失败则回滚到上一镜像 tag。
  - **不在 2C2G 服务器上构建镜像**：`pip install` 与镜像构建在该内存下易 OOM 且极慢，与 0.1 “避免在服务器上跑复杂构建”保持一致。
  - 镜像按 commit SHA / 语义化版本打 tag，回滚即切换 tag，无需重新构建。
- 中国网络访问 GitHub 可能抖动；用 pip/阿里云镜像、Docker 镜像加速；不把自托管 Runner 放在生产同机。
- Secrets：SSH 私钥、服务器指纹、环境变量放 GitHub Secrets；部署用户非 root、仅授权必要目录与 Docker 命令。

**自托管 Runner**
- 网络最好、免费；但 Runner 跑在生产服务器上，一旦仓库/工作流被攻破，攻击者可能拿到生产权限；需要额外隔离与补丁，单人维护不划算。

**阿里云云效/Codeup**
- 大陆网络与阿里云集成更好；具体免费额度、流水线能力和价格需在选型后到控制台核实，本文不假设其免费。
- 如果 GitHub Actions 持续不可用，再作为迁移备选。

### 7.3 备份、监控与恢复

**备份**
- 阿里云 99 套餐含 100GiB 文件备份权益：备份 `/srv/blog/data`（SQLite）与 `/srv/blog/media`（图片）。
- 每日定时 `sqlite3 .backup` 或 `VACUUM INTO` 生成一致性快照，保留 7～30 天；媒体目录打包/增量备份。
- 每月至少做一次恢复演练：在临时目录恢复数据库与媒体，启动应用，验证文章/图片/关于页。
- 备份文件与生产盘分离；可选阿里云 OSS 作为异地副本，按量计费，首版非必需。

**监控**
- `/healthz`：检查应用进程、数据库可读、磁盘剩余空间；Caddy/Uptime 机器人定时探测。
- Docker `restart: unless-stopped`；Caddy 访问日志 + Django 日志输出到 stdout，Docker 日志轮转。
- 外部 uptime 监控（如 UptimeRobot 免费档）或阿里云云监控；告警到邮箱。
- 首版不引入 Prometheus/Grafana/Sentry；需要时再加 Sentry 免费档。

**故障恢复**
- 应用崩溃：Docker 自动重启；查看日志与健康检查。
- 数据库损坏/误删：停止写入 → 用最近备份恢复 → 校验文章/项目/关于页 → 重启。
- 证书问题：Caddy 自动续期；检查 80/443、DNS、ICP 状态。
- 磁盘满：清理日志/旧备份；图片上传限制 2MB；必要时迁移媒体到 OSS。

### 7.4 部署推荐与硬前提

- **推荐**：阿里云 ECS 99 + Docker Compose（web + Caddy）+ SQLite/媒体卷（bind mount）+ GitHub Actions 构建推 GHCR + SSH 拉取部署。
- **域名策略（已确认：延期，双阶段上线）**：大陆服务器绑定域名必须完成 ICP 备案，但备案不作为首版交付的阻塞项。
  - **阶段 A（无域名）**：ECS 以 IP + HTTP 部署，用于功能验收与 CI/CD 打通；后台经 SSH 隧道或安全组白名单访问，不长期暴露在公网 HTTP；`SITE_URL` 用环境变量占位，canonical/sitemap/分享卡片统一从该变量生成。此阶段只验证 SEO 结构正确性，不验证收录。
  - **阶段 B（决定公开时）**：购买域名 → ICP 备案 → 解析 → Caddy 自动签发 HTTPS → 切换 `SITE_URL` → 复核 canonical/sitemap 并提交搜索引擎。
  - 详见 `docs/technology-decisions.md` ADR-06。
- **不建议**：Kubernetes、Nginx+PostgreSQL+Redis 三件套、Vercel 主站 + 托管数据库、生产同机自托管 Runner。

## 8. 测试与质量

### 8.1 测试矩阵

| 测试类型 | 候选 | 推荐 | 理由 |
|---|---|---|---|
| 后端单元/集成（Django） | pytest + pytest-django vs Django TestCase | pytest + pytest-django | fixture/参数化/插件生态；与 Django 测试数据库集成 |
| API 集成（FastAPI 路线） | pytest + HTTPX vs requests | pytest + HTTPX | 支持 async、现代 HTTP 客户端 |
| 端到端 | Playwright vs Cypress | Playwright | 多浏览器、并行、Python/TS 都可写；适合真实业务流程 |
| 前端单元（仅 React/Astro 路线） | Vitest vs Jest | Vitest | Vite 原生、ESM、启动快 |
| Lint/格式化 | Ruff vs Flake8 + Black | Ruff | 一个工具覆盖 lint/format，速度快 |
| 类型检查 | mypy + django-stubs vs pyright | Django 用 mypy + django-stubs；TS 用 tsc/pyright | 与 Django 生态匹配；TS 用官方类型检查 |
| 类型检查时机 | — | **后置**：上线稳定后以独立 PR 引入 | django-stubs 与 Django 版本强耦合，配置成本高；首版不阻塞交付 |
| 依赖/安全检查 | pip-audit / npm audit + Dependabot | 两者结合 | 供应链漏洞与自动升级 |
| CI 编排 | GitHub Actions | GitHub Actions | 公有仓库免费、生态成熟 |

### 8.2 工具取舍

- **pytest vs Django TestCase**：Django TestCase 可用，但 pytest 的 fixture、参数化、插件和失败输出更适合长期维护；pytest-django 负责数据库与 settings 集成。
- **Playwright vs Cypress**：Playwright 支持 Chromium/Firefox/WebKit、并行、Python/TypeScript；Cypress 的 JS 单栈体验好，但跨浏览器与多语言不如 Playwright。本项目后台是 Django 模板/HTMX，Playwright 更合适。
- **Vitest vs Jest**：只有在 React/Astro 路线才需要；Vite 原生选 Vitest，否则不引入前端单测框架。
- **Ruff vs Flake8+Black**：Ruff 一个工具完成 lint/format/isort，CI 更快；类型检查交由 mypy 后置引入，不混用。
- **mypy + django-stubs 后置**：django-stubs 与 Django 版本强耦合，配置与类型 stub 调校能吃掉半天到一天工期，对首版交付无实质收益。首版 CI 门禁先上 Ruff + pytest + `check --deploy` + Playwright + Docker build，已经足够展示工程能力；上线稳定后再以独立 PR 引入类型检查，避免它与业务开发抢时间。
- **覆盖率**：不追求 100%；覆盖核心业务规则（发布/撤回、项目关联、关于页保存、权限、图片校验、404）与关键 E2E（登录→发布→前台可见→撤回→404）。

### 8.3 CI 质量门禁

1. `ruff check` + `ruff format --check`
2. `pytest`（单元 + 集成）
3. `python manage.py check --deploy`（生产 settings）
4. `playwright test`（核心冒烟，可在 CI 启动测试栈）
5. Docker build（确保可部署）
6. 依赖审计（pip-audit；Dependabot 周更）

> 首版门禁不含 `mypy`：django-stubs 与 Django 版本强耦合，配置成本高、对交付无实质收益，上线稳定后以独立 PR 引入（见 8.2）。

### 8.4 测试推荐

- **Django 主方案**：pytest 9.1.1 + pytest-django + Playwright 1.64 + Ruff；mypy + django-stubs 后置引入；不引入 Vitest（除非后续加自定义 JS 组件）。
- **FastAPI 备选**：pytest + HTTPX + Playwright；若有 React 后台，加 Vitest 5.0。
- **Next.js 备选**：Vitest 5.0 + Playwright + ESLint + TypeScript。

## 9. 推荐方案与迁移成本

### 9.1 主方案清单

| 层次 | 选择 | 版本/说明 |
|---|---|---|
| 运行时 | Python 3.14.x（兜底 3.13） | Django 5.2 官方支持 3.13–3.14；3.14.7 为核查时最新 3.14 补丁；依赖轮子不顺时降级 3.13 |
| Web 框架 | Django 5.2 LTS | 5.2.17；支持到 2028-04；计划 2027-04 升级 6.2 LTS |
| 数据库 | SQLite 3.54.1 | WAL、busy_timeout、外键；单应用容器 |
| ORM | Django ORM | 内置迁移；避免 SQLite 特有 SQL |
| 公开前端 | Django 模板 + HTMX + Alpine | 服务端渲染；少量 JS；无独立构建 |
| 后台 | Django Admin + ModelAdmin | Markdown 编辑器、图片上传、发布/撤回、预览、django-axes |
| 内容渲染 | Python-Markdown + Pygments + nh3 | TOC、代码高亮、HTML 白名单净化 |
| 搜索 | `icontains` | 标题/摘要/正文纯文本；后续 FTS5 |
| 图片 | 本地媒体卷 + Pillow 校验 | 2MB、JPG/PNG/WebP/GIF、禁 SVG；Caddy 提供媒体 |
| 部署 | 阿里云 ECS 99 + Docker Compose + Caddy | 2C2G/3M/40G；Caddy 2.10.0；无 DB 容器 |
| CI/CD | GitHub Actions + SSH | 公有仓库免费；私有 2,000 分钟/月 |
| 测试 | pytest + pytest-django + Playwright + Ruff（mypy 后置） | 核心业务与 E2E |
| 备份 | 阿里云文件备份 + SQLite 在线备份 + 媒体归档 | 100GiB 权益；每月恢复演练 |

**部署拓扑**

```text
Internet
  │  HTTPS (443) / HTTP (80 redirect)
  ▼
Caddy (TLS, compression, /media, reverse proxy)
  ▼
Gunicorn → Django (templates, Admin, ORM)
  ├── SQLite (data/blog.sqlite3, WAL)
  └── media/ (uploaded images)
```

### 9.2 为什么这是合理选择

1. **直接满足“立即发布”**：Django 请求时读数据库渲染，发布/撤回/关于页保存后无需构建或重新部署。
2. **把最贵的安全能力变成内置能力**：认证、会话、CSRF、密码哈希、Admin、ORM 迁移、模板转义、部署检查都由 Django 提供，减少自研认证/后台的风险。
3. **资源匹配 2C2G/3M**：一个 Python 进程 + Caddy + SQLite；没有 Node 运行时、数据库服务、搜索服务、Redis。首屏 HTML/CSS/JS 可控在 500KB 内。
4. **SEO 天然成立**：服务端 HTML、稳定 URL、sitemap/robots/canonical/404 都可在模板与 Django 站点地图框架中完成。
5. **备份/恢复简单**：SQLite 单文件 + 媒体目录 + 阿里云文件备份；恢复路径可演练。
6. **维护成本低**：Django 5.2 LTS、单一代码库、单一部署单元；升级路径明确。
7. **适合 Agent 协作**：模块边界清晰（models/views/templates/tests），测试与 CI 提供护栏；比多服务/多运行时更容易让 Agent 理解和验证。
8. **学习价值仍然充足**：Django 架构、ORM/迁移、认证/安全、模板、HTMX、Docker、CI/CD、备份恢复、生产检查，都是完整工程实践。

**代价**
- 前端体验不如 React/Astro 现代；复杂交互需要 HTMX/Alpine 或后续迁移。
- Django Admin 不是漂亮的产品界面；后台只追求可用，公开站需要自定义模板。
- 不能直接展示 FastAPI/React/TS 技能；如果这是求职作品集的核心，需要另做项目或后续替换。

### 9.3 替代方案与迁移成本

| 方案 | 迁移/替换成本 | 适合场景 |
|---|---|---|
| FastAPI + Jinja2/HTMX + SQLAlchemy + SQLite | 中高：重写后端、认证、后台；DB 可迁移 | 明确优先 FastAPI/API-first 学习 |
| Next.js 16 LTS + Prisma 7 + SQLite/PostgreSQL | 高：前后端/数据层/认证全部重做；Node 运行时 | 明确优先 React/TS 全栈 |
| Astro 7 + FastAPI | 中高：公开页静态化 + 发布重建/SSR；两条构建链 | 内容站优先、接受发布延迟 |
| Django + PostgreSQL | 中：Django ORM 迁移 + 数据导入 + 连接配置 | 学习 PostgreSQL、未来多实例/高写并发 |
| Django Admin → 自建后台 | 中高：UI/交互/权限重做 | 后台视觉/交互是作品集重点 |
| Caddy → Nginx | 低：配置重写 | 需要更细粒度反向代理/生态 |
| GitHub Actions → 阿里云云效 | 中：流水线重写 | GitHub 网络不可用/阿里云一体化 |

### 9.4 明确不引入

- 微服务、API Gateway、消息队列、Redis、Celery、Elasticsearch/Meilisearch、Kubernetes。
- 多用户/评论/点赞/收藏、多角色权限、OAuth 登录。
- AI 写作/AI 摘要/AI 标签建议（首版）。
- 媒体库、图片删除/孤儿清理、对象存储（可后置）。
- 文章版本历史、定时发布、协同编辑、自动保存。
- 公开站 SPA、JWT 存 localStorage、把 Django Admin 当前台。

## 10. 版本与支持状态

> 以下为 2026-10-23 核查快照；实施时以 lockfile 固定，并在编码前重新核对。不要在生产使用 RC/Canary/Preview。

| 组件 | 核查时版本/状态 | 支持/备注 | 来源 |
|---|---|---|---|
| Python | 3.14.7（3.14 bugfix） | 3.14 安全支持到 2030-10；3.15.1 为最新，但 Django 5.2 只支持到 3.14 | S08、S03 |
| Django | 5.2.17 LTS | 扩展支持到 2028-04；6.2 LTS 计划 2027-04，支持到 2030-04 | S02、S03 |
| SQLite | 3.54.1 | 文件格式承诺支持到 2050；WAL 并发模型见来源 | S09、S10、S11、S13 |
| PostgreSQL | 18.6 | 支持到 2030-11；Django 5.2 要求 PostgreSQL 14+ | S14、S05 |
| SQLAlchemy | 2.1.6 | 2.0.55 仍在维护；新项目优先 2.1 | S16 |
| Alembic | 1.19.2 | 与 SQLAlchemy 2.x 配套 | S17 |
| FastAPI | 0.143.2 | 0.x 无 LTS 承诺；锁版本、按发布说明升级 | S18 |
| Next.js | 16.x Active LTS；16.3.8 安全补丁；16.4 最新 | 16.x 为 Active LTS，15.x 为 Maintenance LTS；自托管需及时打补丁 | S20、S21 |
| Astro | 7.3.5（npm 最新稳定）；7.4 已公布 | Node >=22.12.0；核查资料中未见与 Django/Next 同等级的 LTS 承诺，按稳定版与升级指南维护 | S24、S25 |
| Vite | 8.1 | 需要 Node 20.19+ 或 22.12+ | S26、S27 |
| React | 19.3 | 2026-09-09 发布 | S28 |
| Node.js | 24.22.1 LTS（Krypton）；26.12.1 Current | 生产用 Active/Maintenance LTS；Node 26 尚为 Current | S29 |
| NestJS | 11.2.8 | 需要 Node 22.22.3+/24.15+/26+ | S30、S31 |
| Prisma | 7.10.1 稳定；8.0.0-rc 为 RC | 生产不要用 8.0 RC | S32 |
| pytest | 9.1.1 | 2026-06-19 | S33 |
| Playwright | 1.64 | 当前版本 | S34 |
| Vitest | 5.0 | 2026-09-03 | S35 |
| Caddy | 2.10.0 | 自动 HTTPS、HTTP→HTTPS 重定向 | S36、S37 |
| GitHub Actions | 公有仓库免费；私有 Free 2,000 分钟/月、500MB | 超出按量；Linux 2-core $0.008/分钟 | S38 |
| 阿里云 ECS 99 | 2C2G/3M/40G，99 元/年 | 续费同价、价格锁至 2029-03-31；含 100GiB 文件备份权益（以活动规则为准） | S39 |
| 阿里云备案 | 大陆服务器绑定域名需 ICP 备案 | 备案免费但需时间；未备案只能先用 IP 测试 | S40 |
| Vercel | Hobby $0；Pro $20/月 | Hobby 仅限非商业个人用途；有用量限制 | S41、S42 |

### 10.1 版本策略

- **LTS 优先**：Django 5.2 LTS、Node 24 LTS（若走 Node 路线）；不使用 6.1（非 LTS）作为长期主版本，除非需要其新特性。
- **Python 版本兜底**：优先 3.14.x；**若 django-axes、Pillow、nh3 等关键依赖在 3.14 上无预编译轮子或实测不顺，直接使用 3.13**——Django 5.2 同样支持，生产站不为一个小版本号消耗工期。Python 版本在依赖安装阶段一次性验证，验证结论写入 README。
- **锁定精确版本**：Python 3.14.x、Django 5.2.x、SQLite 3.54.x、pytest 9.x、Playwright 1.64.x；用 lockfile/容器镜像固定。
- **不使用预发布**：Python 3.16 pre-release、Node 26 Current、Next.js canary、Prisma 8 RC、Astro 7.4（若 npm 尚未稳定）。
- **升级节奏**：每月看安全补丁；每季度评估 minor；Django 5.2 → 6.2 LTS 在 2027-04 后按发布说明执行。
- **第三方 GitHub Actions 按 commit SHA 固定**；依赖升级用 Dependabot/Renovate，升级前跑完整 CI + 恢复演练。

### 10.2 成本估算

| 项目 | 估算 | 说明 |
|---|---|---|
| 阿里云 ECS | 99 元/年 | 2C2G/3M/40G；活动价/续费规则以页面为准 |
| 域名 | 以注册商为准 | 未在本文假设具体价格；需 ICP 备案后才能绑定大陆服务器 |
| ICP 备案 | 0 元 | 阿里云提供免费备案服务，时间成本另计 |
| TLS 证书 | 0 元 | Caddy + Let's Encrypt/ZeroSSL 自动签发与续期 |
| GitHub Actions | 0 元（公有仓库） | 私有仓库 Free 2,000 分钟/月；超出按量 |
| 备份 | 0 元（套餐权益内） | 100GiB 文件备份；OSS 异地副本可选、按量计费 |
| 总计 | 约 99 元/年 + 域名 | 远低于引入 RDS/Redis/搜索服务的方案 |

## 11. 决策结果

> 本节原为“仍需你决定的问题”，已于 2026-10-23 全部确认。逐项理由、后果与复审条件见 `docs/technology-decisions.md`。

### 11.1 已确认决策

| 编号 | 问题 | 结论 | 影响 |
|---|---|---|---|
| D-01 | 后端路线：Django / FastAPI / Next.js | **Django 5.2 LTS** | 决定认证、后台、ORM、模板、部署方式 |
| D-02 | 公开站渲染：Django 模板+HTMX / Next.js SSR / Astro 静态+重建 / React SPA | **Django 模板 + HTMX + Alpine** | 决定是否接受立即发布、首屏性能、构建链 |
| D-03 | 数据库：SQLite / PostgreSQL | **SQLite 3.54（WAL）** | 决定是否多一个常驻服务、备份方式、内存占用 |
| D-04 | 后台：Django Admin / 自建后台 | **Django Admin + ModelAdmin** | 决定后台开发量、UI 定制程度、安全代码量 |
| D-05 | Q-06 密码修改：启用 / 不启用 | **启用** Django Admin 自带密码修改 | 需求文档 Q-06 已同步改为“提供” |
| D-06 | 域名与 ICP | **延期**，采用双阶段上线（IP 阶段 + 域名阶段） | 见 `technology-decisions.md` ADR-06 |

**决策上下文**：本项目求职方向为 Python 后端 / AI Agent 应用开发，该上下文支持 D-01 选择 Django。

### 11.2 已确认的工程/运维决策

| 编号 | 问题 | 结论 | 影响 |
|---|---|---|---|
| D-07 | 代码仓库与 CI | **公开 GitHub + Actions** | CI 成本为零、作品集加分；必要时可转私有（2,000 分钟/月够用） |
| D-08 | 备份/监控 | **最小化**：文件备份 + 每夜 SQLite 备份 + 外部 uptime + 每月恢复演练 | 数据安全、故障恢复、成本 |
| D-09 | 搜索 | **`icontains`**（预生成 `body_text`） | 不引入独立搜索服务 |

### 11.3 需求层待确认项（历史记录；2026-10-23 用户已确认全部沿用默认值）

| 编号 | 问题 | 当前默认 | 影响 |
|---|---|---|---|
| D-10 | Q-01 项目状态枚举 | 进行中/已完成/已归档 | 项目列表/详情/校验 |
| D-11 | Q-02 项目是否隐藏/草稿 | 不需要，创建即公开 | 项目管理与访客可见性 |
| D-12 | Q-03 标签是否独立管理 | 不需要，文章编辑中创建/选择 | 后台范围与标签纠错 |
| D-13 | Q-04 文章是否需要封面 | 不需要，列表仅文字信息 | 数据模型、图片上传范围、列表视觉 |
| D-14 | Q-05 图片限制 | JPG/PNG/WebP/GIF，≤2MB | 上传校验、磁盘与带宽 |
| D-15 | Q-07 站点名称与文案 | 待提供，先用占位文案开发 | 首页与 SEO 元信息 |

## 12. 下一步

1. 决策已全部确认（D-01～D-09），不再阻塞设计。
2. 下一步输出**架构设计文档**：模块边界、数据模型、路由/视图、认证流程、内容渲染管线、部署拓扑、CI 流水线、备份/恢复手册、测试策略。
3. 架构确认后再输出实施计划（里程碑/任务拆分/验收映射），最后才进入编码。
4. 本阶段不创建项目、不安装依赖、不写业务代码。

## 13. 资料来源

> 核查日期均为 2026-10-23。版本与价格可能变化，实施前需复核。

| 编号 | 来源 | URL |
|---|---|---|
| S01 | 本项目需求分析文档 v1.0 | `docs/requirements-analysis.md` |
| S02 | Django download / supported versions | https://www.djangoproject.com/download/ |
| S03 | Django 5.2 release notes（Python 3.10–3.14） | https://docs.djangoproject.com/en/5.2/releases/5.2/ |
| S04 | Django FAQ: Installation | https://docs.djangoproject.com/en/5.2/faq/install/ |
| S05 | Django 5.2 databases（PostgreSQL 14+、SQLite 支持） | https://docs.djangoproject.com/en/5.2/ref/databases/ |
| S06 | Django Admin documentation | https://docs.djangoproject.com/en/5.2/ref/contrib/admin/ |
| S07 | Django deployment checklist | https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/ |
| S08 | Python downloads（3.15.1 / 3.14.7 / 支持周期） | https://www.python.org/downloads/ |
| S09 | SQLite download（3.54.1） | https://sqlite.org/download.html |
| S10 | SQLite WAL / concurrency | https://sqlite.org/wal.html |
| S11 | SQLite Appropriate Uses | https://sqlite.org/whentouse.html |
| S12 | SQLite Online Backup API | https://sqlite.org/backup.html |
| S13 | SQLite version numbers / support | https://sqlite.org/versionnumbers.html |
| S14 | PostgreSQL versioning policy（18.6） | https://www.postgresql.org/support/versioning/ |
| S15 | PostgreSQL backup and restore | https://www.postgresql.org/docs/current/backup.html |
| S16 | SQLAlchemy（2.1.6 / 2.0.55） | https://www.sqlalchemy.org/ |
| S17 | Alembic（1.19.2） | https://pypi.org/project/alembic/ |
| S18 | FastAPI（0.143.2） | https://pypi.org/project/fastapi/ |
| S19 | FastAPI Security docs | https://fastapi.tiangolo.com/tutorial/security/ |
| S20 | Next.js Support Policy（16.x Active LTS） | https://nextjs.org/support-policy |
| S21 | Next.js September 2026 Security Release | https://nextjs.org/blog/september-2026-security-release |
| S22 | Next.js installation（Node 20.9+） | https://nextjs.org/docs/app/getting-started/installation |
| S23 | Astro: Why Astro | https://docs.astro.build/en/concepts/why-astro/ |
| S24 | Astro npm registry（7.3.5，Node >=22.12.0） | https://registry.npmjs.org/astro/latest |
| S25 | Astro 7.4 blog | https://astro.build/blog/astro-740/ |
| S26 | Vite Getting Started（Node 20.19+/22.12+） | https://vite.dev/guide/ |
| S27 | Vite 8.1 release | https://vite.dev/blog/announcing-vite8-1 |
| S28 | React 19.3 | https://react.dev/blog/2026/09/09/react-19-3 |
| S29 | Node.js releases（24 LTS / 26 Current） | https://nodejs.org/en/about/previous-releases |
| S30 | NestJS first steps（Node 版本要求） | https://docs.nestjs.com/first-steps |
| S31 | NestJS v11.2.8 release | https://github.com/nestjs/nest/releases/tag/v11.2.8 |
| S32 | Prisma dist-tags（7.10.1 / 8.0 RC） | https://registry.npmjs.org/-/package/prisma/dist-tags |
| S33 | pytest 9.1.1 release | https://github.com/pytest-dev/pytest/releases/tag/9.1.1 |
| S34 | Playwright release notes（1.64） | https://playwright.dev/docs/release-notes |
| S35 | Vitest blog（5.0） | https://vitest.dev/blog/ |
| S36 | Caddy Automatic HTTPS | https://caddyserver.com/docs/automatic-https |
| S37 | Caddy v2.10.0 release | https://github.com/caddyserver/caddy/releases/tag/v2.10.0 |
| S38 | GitHub Actions billing（免费额度） | https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions |
| S39 | 阿里云 99 元/年 ECS 活动页 | https://www.aliyun.com/activity/ecs/99program |
| S40 | 阿里云 ICP 备案 | https://beian.aliyun.com/ |
| S41 | Vercel Hobby Plan | https://vercel.com/docs/plans/hobby |
| S42 | Vercel Pricing（Pro $20/月） | https://vercel.com/pricing |
| S43 | Python-Markdown Sanitization（bleach 已弃用，nh3） | https://python-markdown.github.io/sanitization/ |
| S44 | Python-Markdown CodeHilite | https://python-markdown.github.io/extensions/code_hilite/ |
| S45 | Django sitemap framework 5.2 | https://docs.djangoproject.com/en/5.2/ref/contrib/sitemaps/ |
| S46 | django-axes 8.3.1 文档 | https://django-axes.readthedocs.io/en/stable/3_usage.html |
