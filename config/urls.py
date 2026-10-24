"""根路由：纯 include 结构，当前仅 admin 占位（architecture §13）。"""

from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]
