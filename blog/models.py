"""blog 域模型——database-design §3.1～3.4 逐字段对照（T-005，⚠M）。

边界声明：body_md→body_text 的生成管线属 core.content（T-011/T-012 前只落
字段）；标签归一化（strip/casefold）与分类三行种子、Admin 禁增删属 T-007；
发布/撤回状态机与 published() 属 T-006。
"""

import secrets
import string

from django.core.exceptions import ValidationError
from django.db import models

SLUG_LENGTH = 8  # 随机 base62-8（database §3.1/§6）
_SLUG_ALPHABET = string.ascii_letters + string.digits


def generate_unique_slug() -> str:
    """随机 base62-8；命中已有值则重试，DB UNIQUE 约束兜底并发（database §3.1）。"""
    while True:
        slug = "".join(secrets.choice(_SLUG_ALPHABET) for _ in range(SLUG_LENGTH))
        if not Article.objects.filter(slug=slug).exists():
            return slug


class Category(models.Model):
    """文章分类：固定 3 行 taxonomy（种子与 Admin 禁增删属 T-007）。"""

    name = models.CharField("名称", max_length=20, unique=True)
    slug = models.CharField("路径代号", max_length=20, unique=True)
    sort_order = models.SmallIntegerField("排序", default=1)

    class Meta:
        verbose_name = "分类"
        verbose_name_plural = "分类"

    def __str__(self) -> str:
        return self.name


class Tag(models.Model):
    """自由标签（strip/casefold 归一化属 T-007）。"""

    name = models.CharField("名称", max_length=20, unique=True)
    slug = models.CharField("路径代号", max_length=16, unique=True)

    class Meta:
        verbose_name = "标签"
        verbose_name_plural = "标签"

    def __str__(self) -> str:
        return self.name


class Article(models.Model):
    """文章：slug 创建时生成、此后不可变；状态转换集中 T-006 服务方法。"""

    class Status(models.TextChoices):
        DRAFT = "draft", "草稿"
        PUBLISHED = "published", "已发布"

    slug = models.CharField(
        "网址代号", max_length=16, unique=True, blank=True, default=""
    )
    title = models.CharField("标题", max_length=120)
    summary = models.CharField("摘要", max_length=200, blank=True, default="")
    body_md = models.TextField("正文（Markdown 源）", blank=True, default="")
    body_text = models.TextField(
        "正文（检索用纯文本）", blank=True, default="", editable=False
    )
    status = models.CharField(
        "状态", max_length=10, choices=Status.choices, default=Status.DRAFT
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, verbose_name="分类"
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="关联项目",
    )
    first_published_at = models.DateTimeField("首发时间", null=True, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)
    tags = models.ManyToManyField(Tag, blank=True, verbose_name="标签")

    class Meta:
        verbose_name = "文章"
        verbose_name_plural = "文章"
        indexes = [  # noqa: RUF012
            models.Index(
                fields=["status", "-first_published_at"], name="article_pub_idx"
            ),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args: object, **kwargs: object) -> None:
        """slug 首存生成、入库后不可变（database §3.1；领单方案 A 守卫）。"""
        if not self.slug:
            self.slug = generate_unique_slug()
        elif self.pk is not None:
            original = (
                type(self)
                .objects.filter(pk=self.pk)
                .values_list("slug", flat=True)
                .first()
            )
            if original is not None and original != self.slug:
                msg = "slug 创建后不可变（database §3.1）"
                raise ValidationError({"slug": msg})
        super().save(*args, **kwargs)
