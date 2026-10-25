"""about 域模型——database-design §3.6 单例 id=1（T-008，⚠M）。"""

from django.core.exceptions import ValidationError
from django.db import models


class AboutPage(models.Model):
    """关于页：全库恒为 id=1 一行（get_or_create 保证；save 强制 pk=1 兜底）。"""

    home_summary = models.CharField("首页简介", max_length=200)
    bio = models.TextField("个人简介")
    direction = models.TextField("方向", blank=True, default="")
    tech_stack = models.JSONField("技术栈", default=list, blank=True)
    contacts = models.JSONField(
        "联系方式", default=list, blank=True, help_text='[{"label": ..., "value": ...}]'
    )
    links = models.JSONField(
        "外链", default=list, blank=True, help_text='[{"label": ..., "url": ...}]'
    )
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "关于页"
        verbose_name_plural = "关于页"

    def __str__(self) -> str:
        return "关于页（单例）"

    @classmethod
    def get_solo(cls) -> AboutPage:
        """唯一读取入口：get_or_create(id=1)，首次访问自动建行（database §3.6）。"""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args: object, **kwargs: object) -> None:
        """强制单例：恒写 id=1 行；行已存在时直插转为更新（upsert 语义）。"""
        self.pk = 1
        if type(self).objects.filter(pk=1).exists():
            kwargs.pop("force_insert", None)
            kwargs["force_update"] = True
        super().save(*args, **kwargs)

    def clean(self) -> None:
        """contacts 与 links 至少一项（database §3.6）。"""
        if not self.contacts and not self.links:
            msg = "contacts 与 links 至少填写一项"
            raise ValidationError({"contacts": msg, "links": msg})
