"""T-002 settings 验收测试：8 变量 fail-fast、prod DEBUG 结构强制、时区、check --deploy。

策略：全部经子进程运行 manage.py——"缺变量进程启动即失败并点名变量"本质是
进程级行为，隔进程断言退出码与 stderr 才是对启动行为的真实测试；同时不依赖
pytest-django 配置（pytest 配置属 T-003）。
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_DIR = Path(__file__).resolve().parents[2]
MANAGE_PY = REPO_DIR / "manage.py"

REQUIRED_VARS = [
    "SECRET_KEY",
    "DEBUG",
    "SITE_URL",
    "ALLOWED_HOSTS",
    "COOKIE_SECURE",
    "BACKUP_DIR",
    "HEALTHZ_DISK_THRESHOLD",
    "HEALTHZ_BACKUP_MAX_AGE",
]

BASE_ENV = {
    "SECRET_KEY": "test-only-key-not-a-real-secret",
    "DEBUG": "False",
    "SITE_URL": "http://127.0.0.1:8000",
    "ALLOWED_HOSTS": "localhost,127.0.0.1",
    "COOKIE_SECURE": "False",
    "BACKUP_DIR": "./backups",
    "HEALTHZ_DISK_THRESHOLD": "10",
    "HEALTHZ_BACKUP_MAX_AGE": "48",
    "PYTHONUTF8": "1",
    "PYTHONIOENCODING": "utf-8",
}


def run_manage(
    args: list[str],
    settings: str,
    drop: str | None = None,
    **overrides: str,
) -> subprocess.CompletedProcess[str]:
    """子进程运行 manage.py；drop 从环境删除某变量，overrides 覆盖某变量。"""
    env = {**os.environ, **BASE_ENV, **overrides}
    env["DJANGO_SETTINGS_MODULE"] = settings
    if drop is not None:
        env.pop(drop, None)
    return subprocess.run(
        [sys.executable, str(MANAGE_PY), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=REPO_DIR,
        env=env,
        timeout=120,
    )


@pytest.mark.parametrize("missing", REQUIRED_VARS)
def test_missing_env_fails_with_var_name(missing: str) -> None:
    result = run_manage(["check"], settings="config.settings.test", drop=missing)
    assert result.returncode != 0, (
        f"缺少 {missing} 应启动失败\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    assert missing in result.stderr, f"报错应点名 {missing}\nstderr={result.stderr}"


@pytest.mark.parametrize(
    ("var", "bad_value"), [("DEBUG", "maybe"), ("COOKIE_SECURE", "yes")]
)
def test_invalid_bool_env_fails_with_var_name(var: str, bad_value: str) -> None:
    result = run_manage(["check"], settings="config.settings.test", **{var: bad_value})
    assert result.returncode != 0, (
        f"{var}={bad_value} 应启动失败\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    assert var in result.stderr, f"报错应点名 {var}\nstderr={result.stderr}"


@pytest.mark.parametrize(
    ("var", "bad_value"),
    [("HEALTHZ_DISK_THRESHOLD", "abc"), ("HEALTHZ_BACKUP_MAX_AGE", "1.5")],
)
def test_invalid_int_env_fails_with_var_name(var: str, bad_value: str) -> None:
    result = run_manage(["check"], settings="config.settings.test", **{var: bad_value})
    assert result.returncode != 0, (
        f"{var}={bad_value} 应启动失败\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    assert var in result.stderr, f"报错应点名 {var}\nstderr={result.stderr}"


def test_prod_debug_false() -> None:
    # 失败场景（防错）：环境变量故意 DEBUG=True，prod 结构强制压为 False
    code = "import sys; from django.conf import settings; sys.exit(0 if settings.DEBUG is False else 1)"
    result = run_manage(
        ["shell", "-c", code], settings="config.settings.prod", DEBUG="True"
    )
    assert result.returncode == 0, (
        f"prod 必须恒 DEBUG=False\nstdout={result.stdout}\nstderr={result.stderr}"
    )


def test_tz_use_tz_true_shanghai() -> None:
    code = (
        "import sys; from django.conf import settings; "
        "ok = settings.USE_TZ is True and settings.TIME_ZONE == 'Asia/Shanghai'; "
        "sys.exit(0 if ok else 1)"
    )
    result = run_manage(["shell", "-c", code], settings="config.settings.dev")
    assert result.returncode == 0, (
        f"USE_TZ/TIME_ZONE 应为 True/Asia/Shanghai\nstderr={result.stderr}"
    )


def test_check_deploy_no_critical() -> None:
    result = run_manage(["check", "--deploy"], settings="config.settings.prod")
    combined = result.stdout + result.stderr
    assert result.returncode == 0, f"check --deploy 存在致命项\n{combined}"
    assert "ERROR" not in combined, combined


def test_dev_check_ok() -> None:
    result = run_manage(["check"], settings="config.settings.dev")
    assert result.returncode == 0, f"dev check 应通过\nstderr={result.stderr}"
