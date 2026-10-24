# 安全设计

> 文档版本：v1.0
> 文档状态：**已批准**（2026-10-23 用户确认，作为架构基线）
> 编写日期：2026-10-23
> 上游输入：`requirements-analysis.md` v1.1（NFR-SEC-01～07、AC-11/12/17/20/22～25）、`architecture.md`、`api-design.md`
> 配套：测试用例执行细则见 `deployment-design.md` 测试设计部分。

## 1. 认证与会话生命周期

| 措施 | 风险/场景 | V1 必做 | 延后增强 | 验收 | 成本 |
|---|---|---|---|---|---|
| 认证通道 | 凭据窃取、中间人 | Django Admin 登录（唯一入口）；阶段 A 仅经 SSH 隧道/安全组白名单（AD-8）；阶段 B HTTPS | 2FA（django-otp） | E2E 登录流程；阶段 A 公网直访 /admin/ 不可达 | 低 |
| 会话属性 | 会话窃取/固定 | HttpOnly + SameSite=Lax（框架默认）；登录时轮换 session key（框架）；`SESSION_COOKIE_AGE=14 天` | 短有效期 + 滑动过期 | 检查响应头；登出后 cookie 失效测试 | 低 |
| Cookie Secure 标志 | 明文传输 cookie | 由环境变量驱动：阶段 A=false（HTTP 现实）、阶段 B=true（SEC-1） | — | 阶段 B 断言 Set-Cookie 含 Secure | 低 |
| 退出登录 | 共享设备残留 | Admin 登出 = session 全量 flush | — | AC-12：退出后后台 URL 302 | 零 |
| 权限检查 | 越权 | 公开页零权限分支；`/admin/*` 统一 staff；无自定义权限体系 | 细粒度角色（多作者时） | 越权测试组 | 零 |
| 暴力登录 | 撞库/爆破 | django-axes：5 次失败锁 15 分钟（EX-03），锁定期间正确密码也拒绝 | Caddy 层限流、fail2ban | AC-11 | 低 |

## 2. 密码存储

| 项 | 内容 |
|---|---|
| 风险 | 数据库/备份泄露后凭据被还原 |
| V1 必做 | 框架默认 **PBKDF2-SHA256**（迭代次数随 Django 版本自动提升）；启用四个内置校验器（最小长度 10、用户名相似性、常见密码、纯数字）；明文不出现在界面/日志/仓库（NFR-SEC-01） |
| 延后增强 | Argon2（换 hasher + 依赖，收益边际） |
| 验收 | `check --deploy` 无密码相关警告；DB 中哈希格式断言；AC-22 |
| 成本 | 零（框架内置） |

## 3. CSRF / XSS / SQL 注入 / CORS

| 威胁 | 风险/场景 | V1 必做 | 延后增强 | 验收 | 成本 |
|---|---|---|---|---|---|
| CSRF | 伪造管理员写操作 | CsrfViewMiddleware + 全部表单 token；U1 要求 X-CSRFToken 头；SameSite=Lax 双保险 | — | 无 token POST → 403 测试 | 零 |
| XSS | 存储型（正文/项目字段） | 模板自动转义；**管线输出是全站唯一 `\|safe` 入口**，且必经 nh3 净化（§4） | **CSP 严格策略**（延后原因：Alpine 内联表达式与 Admin 需宽松 script 策略，半吊子 CSP 提供虚假安全感，SEC-3）；V1 基础头：`X-Content-Type-Options: nosniff`、`Referrer-Policy: strict-origin-when-cross-origin`、`X-Frame-Options: DENY`（Caddy 全站注入） | XSS 语料测试（§4）；响应头断言 | 基础头零成本 |
| SQL 注入 | 搜索/筛选参数注入 | ORM 唯一通道（AD-4/R3），无 raw SQL；icontains 参数化 | 代码评审持续把关 | 搜索注入 payload 测试 | 零 |
| CORS | 跨域读取 | **不配置任何 CORS 头**（同源架构、无 API，默认即最严，SEC-4） | — | 响应无 Access-Control-Allow-Origin | 零 |

## 4. Markdown 渲染与不可信 HTML（core.content 净化细则）

**处理链**：Markdown →（Python-Markdown：fenced_code / tables / toc / codehilite+Pygments）→ HTML → **nh3.clean 白名单净化** → 安全 HTML。

**nh3 白名单（V1 固定，变更需评审）**：

| 类别 | 允许内容 |
|---|---|
| 标签 | p, h1–h6, ul, ol, li, a, code, pre, blockquote, em, strong, i, b, img, table, thead, tbody, tr, th, td, hr, br, span, del, sup, sub |
| 属性 | `a[href,title]`；`img[src,alt,width,height]`；`h1–h6[id]`（TOC 锚点）；`code[class]`、`pre[class]`、`span[class]`（Pygments 输出）；`td/th[colspan,rowspan]` |
| URL scheme | http / https / mailto / 相对路径；其余（javascript:、data:）剥离 |
| img src 附加规则 | 仅允许站内相对路径（`/media/...`，与 U1 上传流闭环；外部图床被剥离，SEC-5） |
| 外链 rel | nh3 `link_rel` 默认注入 `noopener noreferrer` |

| 项 | 内容 |
|---|---|
| 风险 | 存储型 XSS（作者粘贴不可信内容）；iframe/script 注入 |
| V1 必做 | 上述白名单；净化失败不抛错、输出安全结果（宁可丢格式不丢安全） |
| 延后增强 | 视频嵌入白名单、KaTeX/MathJax |
| 验收 | XSS 语料测试集：`<script>`、`onerror=`、`javascript:`、`data:text/html`、`<iframe>`、`<style>` 全部剥离；外链含 noopener；Pygments 高亮 span 保留；TOC 锚点可用 |
| 成本 | 零运行成本；白名单评审一次性 |

## 5. 文件上传（U1 + 项目封面）

**处理链（core.uploads）**：接收 → 大小检查（≤2MB）→ Pillow 打开 + verify（魔数 + 完整性）→ 格式 ∈ {JPEG, PNG, WebP, GIF} → **重编码存储**（JPEG/PNG/WebP：天然剥离 EXIF 含 GPS；GIF 为保动画原样存储、GIF 无 EXIF，SEC-6）→ 随机文件名（base62）→ `MEDIA_ROOT/uploads/%Y/%m/`（封面走 `covers/%Y/%m/`）→ 返回 URL。

| 项 | 内容 |
|---|---|
| 风险 | 恶意文件上传（脚本伪装图片）、磁盘滥用、草稿图片被猜测访问 |
| V1 必做 | 上述链路；SVG 及改后缀伪装拒绝（魔数判定）；存储目录由 Caddy 以静态文件服务（天然不可执行、无目录列表、nosniff）；上传行为仅 staff+CSRF；随机文件名 = 不可枚举 capability URL（62^8 空间，草稿图片 URL 不可猜，接受该模型） |
| 延后增强 | 病毒扫描、WebP 转码压缩、媒体库、OSS |
| 验收 | AC-17/24 全组（四格式通过、SVG/伪装拒绝、2MB 边界、非 staff 403）；`.php` 上传后以纯文本下载而非执行；EXIF 剥离抽检 |
| 成本 | 零；磁盘由 /healthz 阈值监控兜底 |

## 6. 密钥、配置与日志敏感信息

| 措施 | 风险/场景 | V1 必做 | 延后增强 | 验收 | 成本 |
|---|---|---|---|---|---|
| 密钥管理 | SECRET_KEY/SSH 私钥入库 | SECRET_KEY 等经环境变量注入，缺失启动失败（fail-fast）；`.env` 不入库、`.env.example` 入库；CI 凭据放 GitHub Secrets；镜像不烤入密钥 | 密钥轮换流程 | `check --deploy`；仓库无 `.env`；公共仓库启用 GitHub 内置 secret scanning（免费自带） | 低 |
| 日志脱敏 | 日志含凭据 | Django 默认不记录 POST 体；密码/令牌不落日志；axes 记录 IP+用户名（可接受）；500 页无堆栈 | 日志集中脱敏审查 | 抽查日志无明文密码 | 零 |
| 备份保护 | 备份含全库 | 本地备份目录属主 root、权限 600；阿里云备份侧由平台隔离 | 备份加密 | 权限检查入月度演练清单 | 零 |

## 7. OWASP ASVS 对照与安全验收原则

| ASVS 域 | 本设计覆盖 | 有意接受/延后 |
|---|---|---|
| V2 认证 | 单用户 + 框架认证 + 锁定 | 无注册/无自助找回（范围外）；2FA 延后 |
| V3 会话管理 | 超时、Secure（阶段 B）、登出失效、固定防护 | 严格 CSP 延后 |
| V4 访问控制 | staff 统一 + URL 级拒绝 + 草稿不可达 | 细粒度角色不需要 |
| V5 验证与编码 | 模板转义 + ORM 参数化 + nh3 | — |
| V6 密码学 | 框架 PBKDF2；TLS（阶段 B） | — |
| V7 错误与日志 | 友好错误页 + 审计日志 + 告警 | request-id 延后 |
| V12 文件上传 | 白名单 + 魔数 + 大小 + 不可执行目录 | 病毒扫描延后 |

**安全验收原则（SEC-8）**：安全结论只由四件事支撑——①安全测试组通过；②`check --deploy` 通过；③阶段 B 上线前一次 OWASP ZAP baseline 人工评估（一次性、非 CI 常态）；④月度备份恢复演练。不因"用了 Django"或"跑过扫描"宣称系统安全；扫描器只是发现问题的手段之一，人工评审与不变量测试是主防线。

## 8. 设计决策 SEC-1～SEC-8

| # | 决策 | 依据 | 替代（不选原因） |
|---|---|---|---|
| SEC-1 | Cookie Secure / SSL 相关设置由环境驱动（阶段 A/B 差异） | ADR-06 双阶段现实 | 一刀切 true（阶段 A 无法登录） |
| SEC-2 | 密码 = 框架 PBKDF2 + 四校验器（长度≥10） | 框架默认且随版本强化 | Argon2（加依赖，边际收益） |
| SEC-3 | CSP 延后，V1 基础安全头 | Alpine/Admin 内联脚本使严格 CSP 需大量改造，半吊子 CSP 无意义 | 宽松 CSP（虚假安全感） |
| SEC-4 | 不配置 CORS | 同源架构，默认即最严 | 显式 allow（无消费者） |
| SEC-5 | 管线 img 仅允许站内相对路径 | 与上传流闭环；杜绝外链图床的混合内容与跟踪 | 允许 https 外链（不可控） |
| SEC-6 | 上传重编码去 EXIF（GIF 原样保动画） | 隐私（GPS）；Pillow 重存天然实现 | 原样存储（EXIF 泄漏） |
| SEC-7 | 会话 14 天 + 登录轮换 + axes 5/15 | 单管理员便利与安全平衡 | 每次登录失效（体验差） |
| SEC-8 | 安全声明 = 测试 + check --deploy + 上线前 ZAP 人工基线 + 月度演练 | 不凭框架/扫描宣称安全 | 工具通过即宣称（自欺） |
