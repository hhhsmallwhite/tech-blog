from django.db import migrations

SEED_CATEGORIES = [
    {"name": "技术文章", "slug": "tech", "sort_order": 1},
    {"name": "项目实践", "slug": "practice", "sort_order": 2},
    {"name": "学习复盘", "slug": "notes", "sort_order": 3},
]


def seed_categories(apps, schema_editor):
    """三行分类种子，get_or_create 按 slug 幂等——重放任意遍库中恰好 3 行（§3.2/DM-7）。"""
    Category = apps.get_model("blog", "Category")
    for row in SEED_CATEGORIES:
        Category.objects.get_or_create(slug=row["slug"], defaults=row)


class Migration(migrations.Migration):
    dependencies = [  # noqa: RUF012
        ("blog", "0001_initial"),
    ]

    operations = [  # noqa: RUF012
        migrations.RunPython(seed_categories, migrations.RunPython.noop),
    ]
