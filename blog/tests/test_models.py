"""T-005/T-006 blog 模型验收测试（database-design §3.1～3.4 逐项对照 + §4 状态机）。

T-005 任务卡点名用例：test_slug_unique_with_retry、test_slug_charset_length_base62_8、
test_title_required、test_summary_max_200、test_status_default_draft、
test_category_tag_unique_constraints；另加 slug 不可变守卫用例
（领单方案 A，2026-10-26 用户拍板）与 test_title_max_120
（T-005 评审建议①补录，2026-10-26）。

T-006 任务卡点名用例：test_publish_writes_first_published_at_once、
test_publish_guard_each_missing_field（参数化×4）、test_publish_atomic_no_partial_write、
test_withdraw_keeps_first_published_at、test_publish_withdraw_republish_same_fp_at、
test_publish_idempotent、test_withdraw_idempotent。
"""

import itertools
import re
import secrets

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone

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

    def test_title_max_120(self) -> None:
        # 边界：121 字被拒；120 字通过（评审探针证实后补录，建议①）
        with pytest.raises(ValidationError) as exc_info:
            make_article(title="字" * 121).full_clean()
        assert "title" in exc_info.value.message_dict
        make_article(title="字" * 120).full_clean()

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


def make_publishable(**overrides: object) -> Article:
    """四项守卫字段齐全的最小 Article（可发布底座，缺省走 make_article）。"""
    base: dict[str, object] = {"summary": "摘要", "body_md": "正文"}
    base.update(overrides)
    return make_article(**base)


class TestStateMachine:
    """T-006 状态机与可见性守卫（database §4 逐行 + BR-04；⚠I 失败路径逐项断言）。"""

    def test_publish_writes_first_published_at_once(self) -> None:
        # 正常：draft→发布→published 且首发时间写入（database §4 行 2）
        t0 = timezone.now()
        article = make_publishable()
        article.save()
        article.publish()
        article.refresh_from_db()
        assert article.status == Article.Status.PUBLISHED.value
        assert t0 <= article.first_published_at <= timezone.now()

    @pytest.mark.parametrize("missing", ["title", "summary", "body_md", "category"])
    def test_publish_guard_each_missing_field(self, missing: str) -> None:
        # 失败：缺任一守卫字段 → 字段级报错且库中保持 draft（database §4 行 3；⚠I ×4）
        article = make_publishable()
        article.save()
        if missing == "category":
            article.category = None
        else:
            setattr(article, missing, "")
        with pytest.raises(ValidationError) as exc_info:
            article.publish()
        assert missing in exc_info.value.message_dict
        article.refresh_from_db()
        assert article.status == Article.Status.DRAFT.value

    def test_publish_atomic_no_partial_write(self) -> None:
        # 失败：守卫失败不产生任何部分写入——内存预埋的首发时间也不得泄漏入库；
        # 且库中不存在"published 且无首发时间"的半成品行（database §4 行 3 不变量）
        article = make_publishable(body_md="")
        article.save()
        article.first_published_at = timezone.now()
        with pytest.raises(ValidationError):
            article.publish()
        article.refresh_from_db()
        assert article.status == Article.Status.DRAFT.value
        assert article.first_published_at is None
        assert not Article.objects.published().exists()
        assert not Article.objects.filter(
            status=Article.Status.PUBLISHED.value, first_published_at__isnull=True
        ).exists()

    def test_withdraw_keeps_first_published_at(self) -> None:
        # 正常：撤回→draft 且首发时间保留（database §4 行 6）
        article = make_publishable()
        article.save()
        article.publish()
        article.refresh_from_db()
        fp = article.first_published_at
        assert fp is not None
        article.withdraw()
        article.refresh_from_db()
        assert article.status == Article.Status.DRAFT.value
        assert article.first_published_at == fp

    def test_publish_withdraw_republish_same_fp_at(self) -> None:
        # 边界：撤回后再发布，首发时间不变（BR-04）
        article = make_publishable()
        article.save()
        article.publish()
        article.refresh_from_db()
        first_fp = article.first_published_at
        article.withdraw()
        article.publish()
        article.refresh_from_db()
        assert article.status == Article.Status.PUBLISHED.value
        assert article.first_published_at == first_fp

    def test_publish_idempotent(self) -> None:
        # 边界：对已发布重复发布 = no-op 成功，首发时间不被刷新
        article = make_publishable()
        article.save()
        article.publish()
        article.refresh_from_db()
        fp = article.first_published_at
        article.publish()
        article.refresh_from_db()
        assert article.status == Article.Status.PUBLISHED.value
        assert article.first_published_at == fp

    def test_withdraw_idempotent(self) -> None:
        # 边界：从未发布的草稿撤回 = no-op；已撤回文章再撤回首发时间仍保留
        draft = make_publishable()
        draft.save()
        draft.withdraw()
        draft.refresh_from_db()
        assert draft.status == Article.Status.DRAFT.value
        assert draft.first_published_at is None

        article = make_publishable()
        article.save()
        article.publish()
        article.refresh_from_db()
        fp = article.first_published_at
        article.withdraw()
        article.withdraw()
        article.refresh_from_db()
        assert article.status == Article.Status.DRAFT.value
        assert article.first_published_at == fp
