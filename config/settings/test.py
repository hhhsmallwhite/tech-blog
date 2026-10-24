"""测试环境（deployment §7：DEBUG 恒 False；只认真实环境变量，不加载 .env）。"""

from .base import *

DEBUG = False
