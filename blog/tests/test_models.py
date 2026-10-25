"""T-005 blog 模型验收测试（database-design §3.1～3.4 逐项对照）。

任务卡点名用例：test_slug_unique_with_retry、test_slug_charset_length_base62_8、
test_title_required、test_summary_max_200、test_status_default_draft、
test_category_tag_unique_constraints；另加 slug 不可变守卫用例
（领单方案 A，2026-10-26 用户拍板）。
"""

import itertools
import re
import secrets

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from blog.models import Article, Category, Tag

pytestmark = pytest.mark.django_db

_SLUG_RE = re.compile(r"[0-9A-Za-z]{8}")


_CATEGORY_SEQ = itertools.count(1)


def make_category(**overrides: object) -> Category:
    """最小合法 Category——每次调用产出不重样的 name/slug（种子三行属 T-007）。"""
    seq = next(_CATEGORY_SEQ)
    base: dict[str, object] = {
        "name": f"分类{seq}",
        "slug": f"cat{seq}",
        "sort_order": seq,
    }
    base.update(overrides)
    return Category(**base)


def make_article(**overrides: object) -> Article:
    """最小合法 Article——缺省字段满足字典必填约束。"""
    category = overrides.pop("category", None) or make_category()
    if category.pk is None:
        category.save()
    base: dict[str, object] = {"title": "测试文章", "category": category}
    base.update(overrides)
    return Article(**base)


class TestSlug:
    def test_slug_unique_with_retry(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # 边界：首生成命中已有 slug → 重试得到新值（choice 注入两轮固定输出）
        make_article(slug="aaaaaaaa").save()
        seq = ["a"] * 8 + ["b"] * 8
        monkeypatch.setattr(secrets, "choice", lambda _alphabet: seq.pop(0))
        article = make_article()
        article.save()
        assert article.slug == "bbbbbbbb"

    def test_slug_charset_length_base62_8(self) -> None:
        # 正常：8 位 base62
        for _ in range(5):
            article = make_article()
            article.save()
            assert _SLUG_RE.fullmatch(article.slug)


class TestSlugImmutable:
    def test_slug_immutable_after_save(self) -> None:
        # 失败：已入库后改 slug → save 拒绝且库中保持原值（database §3.1 不可变）
        article = make_article()
        article.save()
        original = article.slug
        article.slug = "zzzzzzzz"
        with pytest.raises(ValidationError) as exc_info:
            article.save()
        assert "slug" in exc_info.value.message_dict
        article.refresh_from_db()
        assert article.slug == original


class TestTitleSummaryStatus:
    def test_title_required(self) -> None:
        # 失败：title 空被拒
        with pytest.raises(ValidationError) as exc_info:
            make_article(title="").full_clean()
        assert "title" in exc_info.value.message_dict

    def test_summary_max_200(self) -> None:
        # 边界：201 字被拒；200 字通过
        with pytest.raises(ValidationError) as exc_info:
            make_article(summary="字" * 201).full_clean()
        assert "summary" in exc_info.value.message_dict
        make_article(summary="字" * 200).full_clean()

    def test_status_default_draft(self) -> None:
        # 正常：默认 draft；失败：非法 status 被 choices 拒
        article = make_article()
        assert article.status == Article.Status.DRAFT.value
        with pytest.raises(ValidationError):
            make_article(status="archived").full_clean()


class TestUniqueConstraints:
    def test_category_tag_unique_constraints(self) -> None:
        # 失败：重复一律被拒——Category 名/slug、Tag 名/slug（full_clean 唯一校验）
        saved = make_category()
        saved.save()
        with pytest.raises(ValidationError):
            Category(name=saved.name, slug=saved.slug, sort_order=9).full_clean()

        tag = Tag(name="Python", slug="python")
        tag.save()
        with pytest.raises(ValidationError):
            Tag(name="Python", slug="python2").full_clean()
        with pytest.raises(ValidationError):
            Tag(name="Python2", slug="python").full_clean()

        # 失败：M2M 重复行被 UNIQUE(article, tag) 拒（database §3.4；置末位防事务中断）
        article = make_article()
        article.save()
        article.tags.add(tag)
        with pytest.raises(IntegrityError):
            Article.tags.through.objects.create(article=article, tag=tag)
