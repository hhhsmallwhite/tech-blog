# tech-blog —— 个人技术博客

单作者个人技术博客：访客公开只读 + 单管理员后台写作。两个用途——**技术沉淀**（Python / Django / 智能体开发学习与实践）与**求职作品集**（完整展示需求分析 → 架构设计 → 实现 → 测试 → 部署 → 维护的工程过程）。

> 状态：**工程初始化中（M0）**。设计文档已全部批准，任务清单已冻结；本仓库将按里程碑 M0→M6 交付第一版（阶段 A：ECS + IP + HTTP），域名/备案/HTTPS 属阶段 B（条件触发）。

## 技术栈（已批准，详见 docs/）

Django 5.2 LTS 模块化单体 · Django 模板 + HTMX/Alpine · SQLite（WAL）· Django Admin · pytest + Playwright · GitHub Actions 六道门禁 · Docker + Caddy + Gunicorn 两容器

## 快速上手

> 前置：Python 3.14（3.13 亦可）、Git。本项目**无 Node 依赖**（无前端构建链）。

```bash
git clone <仓库地址> && cd tech-blog
python -m venv .venv
# Windows (PowerShell 7)：.venv\Scripts\Activate.ps1
# Linux/macOS：source .venv/bin/activate
pip install -r requirements/dev.txt
copy .env.example .env   # Linux: cp；SECRET_KEY 换成自己生成的值
pytest                   # 应全绿（当前 16 例）
python manage.py runserver   # http://127.0.0.1:8000
```

## 开发指南

### 检查命令（每任务必过，DoD §4 基线）

```bash
ruff format --check .    # 格式检查
ruff check .             # 静态检查
pytest                   # 全部测试（规则配置见 pyproject.toml）
```

- 类型检查（mypy）按已批准决策后置到上线稳定后（`definition-of-done.md` §4 不适用声明）
- Playwright 端到端测试 M5 起启用（当前在 dev.txt 中注释）

### 日常命令

```bash
python manage.py check                  # 配置自检（dev，自动读 .env）
python manage.py runserver              # 开发服务器（自动读 .env，默认 dev 配置）
```

### 生产配置检查（用得少）

`python manage.py check --deploy --settings=config.settings.prod`——注意 **prod 只认 shell 环境变量、不读 .env**，缺任何一个变量都会启动失败并点名缺失变量（fail-fast 是设计行为，不是故障）。先导出 8 个变量（清单与含义见 `.env.example`）再执行：

```powershell
$env:SECRET_KEY="<随机长串>"; $env:DEBUG="False"; $env:SITE_URL="http://127.0.0.1:8000"; $env:ALLOWED_HOSTS="localhost,127.0.0.1"; $env:COOKIE_SECURE="False"; $env:BACKUP_DIR="./backups"; $env:HEALTHZ_DISK_THRESHOLD="10"; $env:HEALTHZ_BACKUP_MAX_AGE="48"
python manage.py check --deploy --settings=config.settings.prod
```

> CI 自 T-031 起自动执行本检查；当前（M0）无 CI，需要时手动跑。

### 迁移与测试数据

当前**没有数据库迁移**（框架迁移按 T-005 任务卡首次产出）。`makemigrations`/`migrate`/`createsuperuser` 将在 T-005 完成后可用，届时本节更新操作指南；测试用数据库由 pytest-django 自动创建与销毁（配置随 T-005 落地）。

### 环境变量

8 个必需变量（缺失即启动失败并点名）说明见 `.env.example`，每变量一行注释；dev 模式由 python-dotenv 自动读取 `.env`（选型 v1.2），test/prod 只认真实环境变量。


## 目录结构

```
docs/        全部设计文档与开发计划（阅读顺序见下）
config/      Django 组合根（settings 四拆/根路由/wsgi）   —— T-002 起
core/        共享服务（Markdown 管线/上传/健康检查/SEO）   —— M2 起
blog/ projects/ about/   三个业务域                      —— M1 起
templates/ static/       模板与静态资源（无构建链）        —— M3 起
e2e/         Playwright 真实浏览器测试                    —— M5 起
deploy/      Dockerfile / compose / Caddyfile            —— M6 起
requirements/  base.txt（生产）/ dev.txt（开发）
```

## 文档索引（阅读顺序）

1. [development-plan.md](docs/development-plan.md) —— 总纲：阶段、顺序、范围、风险、阶段门
2. [task-breakdown.md](docs/task-breakdown.md) —— 41 张任务卡（白名单/三场景验收/测试清单）
3. [definition-of-done.md](docs/definition-of-done.md) —— 完成定义（DoD 十条/验证记录/加严模板）
4. [development-workflow.md](docs/development-workflow.md) —— 协作规范（分支/评审/交接/红线）
5. 设计文档（均已批准）：需求分析 → 技术选型 → 技术决策（ADR）→ 架构 → 数据库 → 接口 → 安全 → 部署

## 质量与协作

- main 恒绿，一任务一分支一 PR（`feat/T-0xx-短名`），squash 合并；PR 必填验证记录
- CI 六道门禁渐进启用（ruff → 迁移漂移 → pytest → check --deploy → Playwright → docker build）
- 类型检查（mypy）按已批准决策后置到上线稳定后；详见 definition-of-done.md §4
- Agent 执行规则见 [AGENTS.md](AGENTS.md)
