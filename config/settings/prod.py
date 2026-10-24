"""生产环境：DEBUG 结构强制为 False——即使环境变量 DEBUG=True 也压为 False（任务卡验收项）。"""

from .base import *

DEBUG = False  # 结构强制：不信任环境变量（deployment §7 prod 行）
