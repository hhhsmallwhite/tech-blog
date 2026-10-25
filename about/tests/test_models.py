"""T-008 about 模型验收测试（database-design §3.6 单例）。

任务卡点名用例：test_get_solo_singleton、test_clean_requires_at_least_one_contact、
test_about_updated_at_auto。
"""

import pytest
from about.models import AboutPage
from django.core.exceptions import ValidationError


class TestSolo:
    def test_get_solo_singleton(self) -> None:
        # 正常：get_solo 两次返回同一行（id=1）
        first = AboutPage.get_solo()
        second = AboutPage.get_solo()
        assert first.pk == second.pk == 1
        # 失败场景：绕过 get_solo 直接 create 也只产生一行（save 强制 pk=1）
        AboutPage.objects.create(home_summary="x", bio="y")
        assert AboutPage.objects.count() == 1


class TestClean:
    def test_clean_requires_at_least_one_contact(self) -> None:
        # 失败：contacts 与 links 全空 → clean 拒绝
        page = AboutPage(home_summary="s", bio="b", contacts=[], links=[])
        with pytest.raises(ValidationError) as exc_info:
            page.full_clean()
        assert "contacts" in exc_info.value.message_dict
        # 正常：有任一联系方式即通过
        ok = AboutPage(
            home_summary="s",
            bio="b",
            contacts=[{"label": "邮箱", "value": "me@example.com"}],
        )
        ok.full_clean()


class TestTimestamp:
    def test_about_updated_at_auto(self) -> None:
        # 正常：保存时 updated_at 自动刷新（auto_now）
        page = AboutPage.get_solo()
        before = page.updated_at
        page.home_summary = "改一句话"
        page.save()
        page.refresh_from_db()
        assert page.updated_at >= before
