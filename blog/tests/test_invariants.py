"""T-009 模型不变量测试全集 + T-012 body_text 同步（database-design §7 + AC-26 + DM-6）。

T-009 卡片纪律：只加测试、禁改模型实现（T-012 按其白名单接管 blog/models.py
保存路径）。projects/tests/、about/tests/ 不动：用例集中本文件（设计裁定，
记录于评审请柬）。

T-009 点名用例：test_published_implies_fp_at、test_delete_category_protected、
test_delete_project_nulls_articles、test_delete_article_cascades_m2m、
test_m2m_no_duplicate、test_slug_immutable_on_resave、test_sqlite_pragmas_on。
T-012 转正（删 xfail 标记，DoD 9 说明在 PR 记录）：test_draft_also_generates_body_text、
test_body_md_change_regenerates_body_text（原 T-009 占位两名）；另补
test_body_text_empty_after_body_md_cleared（T-012 验收边界行）。
"""

import pytest
from django.db import connection
from django.db.models.deletion import ProtectedError

from blog.models import Article, Tag
from blog.tests.test_models import make_article
from core.content import markdown_to_text
from projects.tests.test_models import make_project

pytestmark = pytest.mark.django_db


class TestVisibilityInvariant:
    def test_published_implies_fp_at(self) -> None:
        # §7 不变量：status='published' ⇒ first_published_at 非空（断点式全表扫描）
        make_article().save()  # 草稿（fp 为空合法）
        published = make_article(summary="摘要", body_md="正文")
        published.save()
        published.publish()
        # 边界：刚发布
        assert not Article.objects.filter(
            status=Article.Status.PUBLISHED.value,
            first_published_at__isnull=True,
        ).exists()
        # 边界：刚撤回（draft 保留 fp）——不变量仍成立
        published.withdraw()
        assert not Article.objects.filter(
            status=Article.Status.PUBLISHED.value,
            first_published_at__isnull=True,
        ).exists()
        # 撤回后再发布（BR-04）：published 行必有 fp
        published.publish()
        published.refresh_from_db()
        assert published.first_published_at is not None


class TestDeleteMatrix:
    def test_delete_category_protected(self) -> None:
        # 删除矩阵（§6）：删有文章的分类 → PROTECT 拒绝，分类与文章俱在
        article = make_article()
        article.save()
        with pytest.raises(ProtectedError):
            article.category.delete()
        article.refresh_from_db()
        assert article.category is not None

    def test_delete_project_nulls_articles(self) -> None:
        # 删除矩阵（§6/AC-26）：删项目 → 文章 project 置空，不删文章
        project = make_project()
        project.save()
        article = make_article(project=project)
        article.save()
        project.delete()
        article.refresh_from_db()
        assert article.project is None

    def test_delete_article_cascades_m2m(self) -> None:
        # 删除矩阵（§6）：删文章 → 行 + M2M 级联清理；标签本体保留为孤儿（§5/BR-02）
        first = Tag(name="前端")
        first.save()
        second = Tag(name="后端")
        second.save()
        article = make_article()
        article.save()
        article.tags.add(first, second)
        assert Article.tags.through.objects.count() == 2
        article.delete()
        assert not Article.objects.filter(pk=article.pk).exists()
        assert Article.tags.through.objects.count() == 0
        assert Tag.objects.count() == 2


class TestM2MIntegrity:
    def test_m2m_no_duplicate(self) -> None:
        # §3.4/§7：M2M 无重复——add 幂等 + UNIQUE(article, tag) 兜底
        tag = Tag(name="Django")
        tag.save()
        article = make_article()
        article.save()
        article.tags.add(tag)
        article.tags.add(tag)
        assert Article.tags.through.objects.filter(article=article).count() == 1


class TestSlugStability:
    def test_slug_immutable_on_resave(self) -> None:
        # §6：slug 创建后不可变——改标题再保存不影响 slug
        article = make_article()
        article.save()
        original = article.slug
        article.title = "换一个标题"
        article.save()
        article.refresh_from_db()
        assert article.slug == original


class TestSqlitePragmas:
    def test_sqlite_pragmas_on(self) -> None:
        # §7：foreign_keys=ON 是删除矩阵的执行基础；journal_mode 文件库 WAL /
        # 测试内存库 memory（WAL 完整断言待配置缺陷卡——base.py 注释"数据库任务
        # 启用"无承接卡，领单时已裁定登记挂账）
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA foreign_keys")
            foreign_keys = cursor.fetchone()[0]
            cursor.execute("PRAGMA journal_mode")
            journal_mode = cursor.fetchone()[0]
        assert foreign_keys == 1
        assert journal_mode in ("wal", "memory")


class TestBodyTextSync:
    """T-012 转正（database §4 保存行/DM-6：保存即重算 body_text）。

    原为 T-009 xfail 占位两项，T-012 实现后删标记转正
    （DoD 9 说明：转正过程与断言变更记录于 PR 验证记录）。
    """

    def test_draft_also_generates_body_text(self) -> None:
        # 正常+边界：草稿保存同样生成；body_text == body_md 去标记结果（§3.1）
        article = make_article(body_md="# 标题\n\n**加粗** 正文")
        article.save()
        expected = markdown_to_text("# 标题\n\n**加粗** 正文")
        assert article.body_text == expected
        assert article.body_text != ""

    def test_body_md_change_regenerates_body_text(self) -> None:
        # 正常：published 保存（改 body_md）→ body_text 重算；slug/fp 不变（§4 行 5）
        article = make_article(summary="摘要", body_md="旧正文")
        article.save()
        article.publish()
        article.refresh_from_db()
        original_slug = article.slug
        first_fp = article.first_published_at
        article.body_md = "# 新标题\n新正文"
        article.save()
        article.refresh_from_db()
        assert article.body_text == markdown_to_text("# 新标题\n新正文")
        assert article.slug == original_slug
        assert article.first_published_at == first_fp

    def test_body_text_empty_after_body_md_cleared(self) -> None:
        # 边界：正文清空后 body_text 为空串（卡片验收边界行）
        article = make_article(body_md="有一段正文")
        article.save()
        assert article.body_text != ""
        article.body_md = ""
        article.save()
        article.refresh_from_db()
        assert article.body_text == ""
