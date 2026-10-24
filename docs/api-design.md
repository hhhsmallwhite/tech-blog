# HTTP 接口契约（API 设计）

> 文档版本：v1.0
> 文档状态：**已批准**（2026-10-23 用户确认，作为架构基线）
> 编写日期：2026-10-23
> 上游输入：`requirements-analysis.md` v1.1、`architecture.md`、`database-design.md`
> 本文档由原 `architecture-design.md` 第四部分迁移而来，并补充一致性审查修订（EX-16 降级约定）。

## 1. 范围说明

已确认架构无 REST/JSON API（D-02/ADR-02：Django 模板 + HTMX，服务端渲染）。本文档为已确认架构的 **HTTP 接口契约**：8 个公开页面 + robots/sitemap + 2 个自定义端点（图片上传、健康检查）+ 草稿预览 + Admin 操作契约。不新增面向第三方的 JSON API。

## 2. 接口总表

| # | 方法 | 路径 | 模块 | 认证 | 用途 | 成功 |
|---|---|---|---|---|---|---|
| P1 | GET | `/` | blog | 无 | 首页 | 200 HTML |
| P2 | GET | `/articles/` | blog | 无 | 文章列表（q/tag/page） | 200 HTML |
| P3 | GET | `/articles/category/{cat_slug}/` | blog | 无 | 分类筛选列表 | 200 HTML |
| P4 | GET | `/articles/{slug}/` | blog | 无 | 文章详情 | 200 HTML |
| P5 | GET | `/archive/` | blog | 无 | 归档 | 200 HTML |
| P6 | GET | `/projects/` | projects | 无 | 项目列表 | 200 HTML |
| P7 | GET | `/projects/{id}/` | projects | 无 | 项目详情 | 200 HTML |
| P8 | GET | `/about/` | about | 无 | 关于页 | 200 HTML |
| S1 | GET | `/robots.txt` | config | 无 | 爬虫规则 | 200 text/plain |
| S2 | GET | `/sitemap.xml` | 各域 | 无 | 站点地图 | 200 XML |
| H1 | GET | `/healthz` | core.health | 无 | 健康检查 | 200/503 JSON |
| U1 | POST | `/admin/upload-image/` | core.uploads | staff + CSRF | 编辑器图片上传 | 200 JSON |
| V1 | GET | `/admin/blog/article/{id}/preview/` | blog | staff | 草稿预览 | 200 HTML |
| A1～A8 | GET/POST | `/admin/...`（框架路由） | config + 各域 | staff | 认证/CRUD/发布/撤回/删除/改密 | 见 §6 |

## 3. 共享契约

- **基础**：路径以 SITE_URL 为根；trailing slash 必带（缺失 301）；公开页仅 GET/HEAD（他法 405）；UTF-8；Caddy 压缩。
- **认证**：公开资源无认证；`/admin/*` 需 staff 会话（未登录 302 → `/admin/login/?next=`，U1 例外 403 JSON）；全部 POST 需 CSRF（失败 403）；axes 5 次失败锁 15 分钟。
- **错误**：HTML 页 404（不存在/草稿/撤回/页码越界/参数非法）、405、302、500（友好页无堆栈）；JSON 端点错误带真实状态码（400/403/503）+ `{"error": "CODE", "message"}`，绝不 200 包错误；Admin 表单校验失败 200 重渲染 + 字段级错误（平台惯例）。
- **分页**：`page`（int ≥1，默认 1），每页 10（BR-10）；非数字/越界 → 404；翻页保留其余参数。
- **搜索/筛选**：`q`（strip 空→不过滤，截断 100 字符，icontains 三字段，仅已发布）；`tag`（不存在→404，存在无文章→空状态）；`category` 路径固定 3 slug；组合交集（BR-14）；带 q/tag 响应 noindex；标签候选集仅含被已发布文章引用者。
- **SEO/缓存**：canonical 规则（P2 指向无参版，其余指向自身）；OG 卡片；`/admin/*` 由 Caddy 注入 X-Robots-Tag: noindex；HTML `Cache-Control: no-cache`，/static/ /media/ 长缓存（随机/哈希文件名）。

## 4. 公开页面与自定义端点

| 接口 | 关键契约 | 测试 |
|---|---|---|
| P1 首页 | 最新 5 篇 published() 卡片 + home_summary + 3 分类入口；空状态 | AC-01 |
| P2/P3 列表 | 卡片 10/页 + 筛选区 + 分页；P3 可索引入 sitemap，P2 带参 noindex；空状态+清除筛选 | AC-02/03/04；P3 非法 slug 404 |
| P4 详情 | 草稿/撤回/不存在 404（无论登录）；TOC/上下篇（相邻 published，边界隐藏）/关联项目入口；排序键 (first_published_at, id)；**正文 img 必带 alt，引用图片丢失时浏览器自然降级为 alt 文本（EX-16，模板约定）** | AC-05/06；草稿 404；上下篇不跨草稿；EX-16 降级 |
| P5 归档 | 年-月分组（Asia/Shanghai，Python 侧）；不分页；空状态 | AC-07 |
| P6 项目列表 | 卡片按 -updated_at；封面缺失占位；空状态 | AC-08 |
| P7 项目详情 | 空字段区块隐藏；关联文章经 `project.article_set.published()`；id 路径 | AC-09；关联不含草稿 |
| P8 关于 | 全字段；空区块隐藏；外链合法 | AC-10 |
| S1 robots | Disallow /admin/、/healthz；Sitemap 行 | AC-29 |
| S2 sitemap | P1、P2、P3×3、P4×已发布、P5、P6、P7×全部、P8；lastmod=updated_at；排除草稿/搜索/标签页/后台 | AC-28/15 |
| H1 healthz | 200 `{"status":"ok"}` / 503 `{"status":"error","checks":{失败项名}}`（无路径细节） | 三项注入失败 |
| U1 上传 | staff+CSRF（未认证统一 403 JSON）；multipart `file`；魔数∈{JPEG,PNG,WebP,GIF}、≤2MB、拒 SVG；成功 `{"url":"/media/...随机名"}`；失败 400 + code（UNSUPPORTED_TYPE/TOO_LARGE/CORRUPT_FILE）；无 DB 事务 | AC-17/24 |
| V1 预览 | staff；公开详情模板+预览横幅；noindex；id 无效 404 | 未登录 302；草稿可预览且公开 slug 404 |

**典型请求/响应示例**：

```text
GET /articles/?q=fastapi&tag=python&page=2      → 200（含 noindex meta）
GET /articles/aB3xK9mP/                        → 200 文章详情
GET /articles/notexist1/                       → 404
GET /healthz                                   → 200 {"status": "ok"}
GET /healthz（备份过期）                        → 503 {"status": "error", "checks": {"backup": "stale"}}

POST /admin/upload-image/  (staff + X-CSRFToken, multipart: file=cat.png)
  → 200 {"url": "/media/uploads/2026/10/xK92mQa1.png"}
  → 400 {"error": "UNSUPPORTED_TYPE", "message": "仅支持 JPG/PNG/WebP/GIF"}
```

## 5. Admin 操作契约（框架路由 + 定制行为）

均 staff + CSRF；成功 POST → 302；校验失败 → 200 表单重渲染。

| # | 操作 | 契约要点 | 事务 | 测试 |
|---|---|---|---|---|
| A1 | 登录 | 通用错误（EX-02）；axes 5 次锁 15 分钟（EX-03） | axes 写入 | AC-11 |
| A2 | 登出 | 会话立即失效 | — | 后台 URL 302 |
| A3 | 文章列表 | 状态筛选；-updated_at | 无 | 列表字段 |
| A4 | 新建/编辑 | 草稿仅标题必填；slug 创建后只读；保存重生成 body_text；未保存离开提示（JS） | Admin 原子 | AC-13/21 |
| A5 | 发布/撤回 action | 发布守卫四字段（失败→error message 保持草稿）；撤回保留首发时间；幂等（重复执行 no-op 成功） | atomic | AC-14/15；幂等 |
| A6 | 删除 | 两步确认（BR-18）；项目删除提示关联文章将解除（EX-12） | atomic | AC-26 |
| A7 | 修改密码 | 框架 PasswordChangeForm 验证当前密码 | atomic | 旧密码失效 |
| A8 | 项目/关于 Admin | 项目必填四字段；关于单例禁增删 + clean 至少一联系方式 | Admin 原子 | AC-18/19 |

## 6. 安全检查结论

- **越权**：公开页零权限分支；admin 全 staff+CSRF；P4 对草稿无条件 404；U1 未认证统一 403。
- **泄漏**：七处消费点全经 published()；404/500 无堆栈；healthz 仅检查项名；axes 通用错误；admin 双重 noindex（Caddy 头 + robots）。
- **重复提交**：发布/撤回幂等；删除两步确认；上传重复=孤儿文件（接受）+ 前端防抖；登录暴力破解由 axes 锁定。
- **方法/参数**：公开页仅 GET（405 兜底）；query 全 ORM 参数化；上传魔数校验。

安全实施细则（净化白名单、上传链路、会话策略）见 `security-design.md`。

## 7. 兼容性规则

公开 URL 上线后冻结（变更须 301）；query 参数只增不改不删；JSON 字段只增、error code 词表稳定；sitemap/robots 遵循标准；模板字段变更属内部事务；本文档为接口基线，变更需评审并升版。

## 8. 设计决策 RV-1～RV-8

| # | 决策 | 依据 | 替代（不选原因） |
|---|---|---|---|
| RV-1 | 分类走路径、标签/搜索走 query | 需求 3.2.2 索引语义 | 全 query（分类失去规范 URL） |
| RV-2 | 项目 URL 用 id | id 稳定；项目名可变；数量少 | 加 slug（需重开 DB 设计） |
| RV-3 | 预览走 /admin/ staff 页 | 公开路由无草稿可达路径 | 公开 URL+token（扩大攻击面） |
| RV-4 | HTML no-cache + 静态/媒体长缓存 | 发布即生效闭环；随机文件名安全 | 全不缓存（浪费带宽） |
| RV-5 | 标签不存在 404；存在无文章空状态 | 资源语义区分 | 一律空状态（掩盖 404） |
| RV-6 | /admin/* noindex 由 Caddy 注入 | 基础设施层一行（AD-8 精神） | 应用中间件（阶段 B 残留） |
| RV-7 | U1 未认证统一 403 JSON | 不泄漏登录态差异 | 302（语义含糊） |
| RV-8 | Admin action 幂等 | 双击/重放无害化 | 严格报错（噪音） |

## 9. 需求追溯

FR-01→P1；FR-02→P2/P3；FR-03→P2/P3 筛选；FR-04→search_articles+P2；FR-05→P5；FR-06→P4+core.content；FR-07→P4；FR-08→P6；FR-09→P7；FR-10→FK+article_set；FR-11→P8；FR-12→A1/A2；FR-13→A7；FR-14→A3/A4/V1；FR-15→A5/A6；FR-16→U1+封面；FR-17→A8；FR-18→A8；FR-19→S1/S2+seo；FR-20→P4（纯前端）；FR-21→404/500+空状态；FR-22→模板；FR-23→表单/模型 clean+uploads。EX-01～20 逐项映射见各卡片。
