"""T-008 projects 模型验收测试（database-design §3.5 逐项对照）。

任务卡点名用例：test_project_required_fields、test_tech_stack_dedupe_and_limit、
test_status_choices_default、test_project_ordering_updated_desc。
"""

import datetime

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from projects.models import Project


def make_project(**overrides: object) -> Project:
    """最小合法 Project——缺省字段全部满足字典必填约束。"""
    base: dict[str, object] = {
        "name": "测试项目",
        "summary": "一句话简介",
        "responsibilities": "需求分析\n开发实现",
    }
    base.update(overrides)
    return Project(**base)


class TestProjectRequiredFields:
    def test_project_required_fields(self) -> None:
        # 失败：name/summary/responsibilities 逐个置空 → full_clean 字段级报错
        for missing in ("name", "summary", "responsibilities"):
            project = make_project(**{missing: ""})
            with pytest.raises(ValidationError) as exc_info:
                project.full_clean()
            assert missing in exc_info.value.message_dict
        # 正常：三必填齐全即通过
        make_project().full_clean()


class TestTechStack:
    def test_tech_stack_dedupe_and_limit(self) -> None:
        # 边界：strip + 去重（保序）归一化
        project = make_project(tech_stack=["Django", " Django ", "React", "  "])
        project.clean()
        assert project.tech_stack == ["Django", "React"]
        # 失败：单项超 30 字拒绝
        project.tech_stack = ["a" * 31]
        with pytest.raises(ValidationError) as exc_info:
            project.clean()
        assert "tech_stack" in exc_info.value.message_dict


class TestStatus:
    def test_status_choices_default(self) -> None:
        # 正常：默认 in_progress；失败：非法值被 choices 拒
        assert make_project().status == Project.Status.IN_PROGRESS.value
        with pytest.raises(ValidationError):
            make_project(status="cancelled").full_clean()


class TestOrdering:
    def test_project_ordering_updated_desc(self) -> None:
        # 正常：列表按 -updated_at（auto_now 秒级同值不可控 → update() 显式设两档时间）
        older = make_project(name="旧项目")
        older.save()
        newer = make_project(name="新项目")
        newer.save()
        Project.objects.filter(pk=older.pk).update(
            updated_at=datetime.datetime(2026, 1, 1, tzinfo=timezone.utc)
        )
        Project.objects.filter(pk=newer.pk).update(
            updated_at=datetime.datetime(2026, 10, 1, tzinfo=timezone.utc)
        )
        names = list(Project.objects.values_list("name", flat=True))
        assert names == ["新项目", "旧项目"]
