"""公共配置：三套环境（dev/test/prod）共享的一切。

8 个必需环境变量 fail-fast（deployment-design §8）：
缺任一，进程启动即失败，报错点名缺失变量名。
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parents[2]


def _required_env(name: str) -> str:
    """读取必需环境变量；缺失即启动失败（报错必须含变量名，供测试断言）。"""
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        msg = f"缺少必需环境变量：{name}（复制 .env.example 为 .env 并填值）"
        raise ImproperlyConfigured(msg)
    return value.strip()


def _required_bool(name: str) -> bool:
    """布尔环境变量：只认 True/False（大小写不敏感），其余值同样 fail-fast。"""
    raw = _required_env(name)
    if raw.lower() == "true":
        return True
    if raw.lower() == "false":
        return False
    msg = f"环境变量 {name} 必须是 True 或 False，当前值：{raw!r}"
    raise ImproperlyConfigured(msg)


def _required_int(name: str) -> int:
    """整数环境变量：解析失败同样 fail-fast。"""
    raw = _required_env(name)
    try:
        return int(raw)
    except ValueError as exc:
        msg = f"环境变量 {name} 必须是整数，当前值：{raw!r}"
        raise ImproperlyConfigured(msg) from exc


# ===== 8 个必需环境变量（deployment-design §8）=====
SECRET_KEY = _required_env("SECRET_KEY")
DEBUG = _required_bool("DEBUG")
SITE_URL = _required_env("SITE_URL")
ALLOWED_HOSTS = [
    h.strip() for h in _required_env("ALLOWED_HOSTS").split(",") if h.strip()
]
COOKIE_SECURE = _required_bool("COOKIE_SECURE")
BACKUP_DIR = _required_env("BACKUP_DIR")  # /healthz 备份新鲜度检查用（T-015 消费）
HEALTHZ_DISK_THRESHOLD = _required_int(
    "HEALTHZ_DISK_THRESHOLD"
)  # 磁盘余量告警阈值（%）
HEALTHZ_BACKUP_MAX_AGE = _required_int(
    "HEALTHZ_BACKUP_MAX_AGE"
)  # 备份新鲜度上限（小时）

# ===== 会话与密码（security-design §1/§2 逐行对照）=====
SESSION_COOKIE_AGE = 14 * 24 * 60 * 60  # 14 天（SEC-7）
SESSION_COOKIE_SECURE = COOKIE_SECURE  # SEC-1：阶段 A False / 阶段 B True，由环境驱动
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ===== 应用与中间件 =====
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "blog",
    "projects",
    "about",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ===== 数据库（SQLite；WAL 于数据库任务启用）=====
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    },
}

# ===== 国际化（任务卡 ④）=====
USE_TZ = True
TIME_ZONE = "Asia/Shanghai"

# ===== 静态资源 =====
STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
