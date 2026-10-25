"""pytest 根夹具：绑定 Django test settings 并注入 8 个必需环境变量。

T-003 有意不在 pyproject 绑 DJANGO_SETTINGS_MODULE（裸 pytest 会在收集期即红，
违反"新环境 30 分钟可开发"）；随首个 Django 模型测试（T-008）以根 conftest 落地
（任务清单 v4.3，2026-10-25 用户照准）。

机制说明：环境变量必须在 pytest-django 启动判定前就位——根 conftest 恰在
其判定点之前加载，故在此设值即可让插件正常接管（django.setup 与测试库
创建均由 pytest-django 负责）；需要数据库的测试模块照常声明
`pytestmark = pytest.mark.django_db`（SQLite 测试库默认内存态，退出即散）。

环境变量以 setdefault 注入测试值——不覆盖真实导出；test settings 只认真实
环境变量、不读 .env（deployment §7），故本地与 CI（无 .env）行为一致。
"""

import os

_TEST_ENV = {
    "SECRET_KEY": "test-only-key-not-a-real-secret",
    "DEBUG": "False",
    "SITE_URL": "http://127.0.0.1:8000",
    "ALLOWED_HOSTS": "localhost,127.0.0.1",
    "COOKIE_SECURE": "False",
    "BACKUP_DIR": "./backups",
    "HEALTHZ_DISK_THRESHOLD": "10",
    "HEALTHZ_BACKUP_MAX_AGE": "48",
}

for _key, _value in _TEST_ENV.items():
    os.environ.setdefault(_key, _value)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")

# 必须待环境变量就绪后导入；pytest-django 只认启动期配置，
# 此处自行为模型导入完成注册表初始化，测试库由 django_db 标记接管。
import django

django.setup()
