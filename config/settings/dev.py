"""开发环境：先从仓库根 .env 加载环境变量（python-dotenv，选型 v1.2），再继承 base。"""

from pathlib import Path

from dotenv import load_dotenv

# 必须在导入 base 之前加载 .env：base 在导入时就读取全部环境变量（fail-fast）
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from .base import *
