"""projects 域模型——database-design §3.5 逐字段对照（T-008，⚠M）。

字段/约束/索引以数据字典为准；封面随机文件名在本模块实现（§3.5"随机命名"），
上传的格式校验与重编码剥 EXIF 属 core.uploads（T-013）。
"""

import os
import secrets
import string

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

TECH_STACK_ITEM_MAX_LENGTH = 30  # 技术栈单项字数上限（database §3.5）
COVER_NAME_LENGTH = 8  # 封面随机名 base62-8（api §4 媒体路径示例同长 xK92mQa1）
_COVER_ALPHABET = string.ascii_letters + string.digits


def cover_upload_to(_instance: "Project", filename: str) -> str:
    """封面存储路径：covers/年/月/base62-8 随机名 + 原扩展名（小写）。

    随机名使 URL 与内容编辑解耦、不可猜测（database §3.5"随机命名"；
    语义与文章 slug 一致——§6）。年月按 TIME_ZONE 本地时间分桶。
    """
    ext = os.path.splitext(filename)[1].lower()
    rand = "".join(secrets.choice(_COVER_ALPHABET) for _ in range(COVER_NAME_LENGTH))
    return f"covers/{timezone.localtime():%Y/%m}/{rand}{ext}"


class Project(models.Model):
    """项目展示条目。"""

    class Status(models.TextChoices):
        """三档状态（database §3.5：in_progress/done/archived）。"""

        IN_PROGRESS = "in_progress", "进行中"
        DONE = "done", "已完成"
        ARCHIVED = "archived", "已归档"

    name = models.CharField("项目名", max_length=80)
    summary = models.CharField("一句话简介", max_length=200)
    responsibilities = models.TextField("职责", help_text="多行纯文本")
    cover = models.ImageField(
        "封面图",
        upload_to=cover_upload_to,
        blank=True,
        default="",
        help_text="封面缺失时模板以占位图兜底（api §4 P6）",
    )
    tech_stack = models.JSONField("技术栈", default=list, blank=True)
    status = models.CharField(
        "状态", max_length=20, choices=Status.choices, default=Status.IN_PROGRESS
    )
    background = models.TextField("项目背景", blank=True, default="")
    goals = models.TextField("目标", blank=True, default="")
    features = models.TextField("功能亮点", blank=True, default="")
    architecture = models.TextField("架构设计", blank=True, default="")
    challenges = models.TextField("挑战", blank=True, default="")
    solutions = models.TextField("解决方案", blank=True, default="")
    demo_url = models.URLField("演示地址", blank=True, default="")
    repo_url = models.URLField("仓库地址", blank=True, default="")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "项目"
        verbose_name_plural = "项目"
        # 列表排序 BR-11（database §3.5）
        ordering = ["-updated_at"]  # noqa: RUF012

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        """tech_stack 归一化：strip、去空、去重保序；单项超 30 字拒绝。"""
        stripped = [str(item).strip() for item in self.tech_stack if str(item).strip()]
        deduped: list[str] = []
        for item in stripped:
            if item not in deduped:
                deduped.append(item)
        if any(len(item) > TECH_STACK_ITEM_MAX_LENGTH for item in deduped):
            msg = f"技术栈单项不得超过 {TECH_STACK_ITEM_MAX_LENGTH} 字"
            raise ValidationError({"tech_stack": msg})
        self.tech_stack = deduped
