"""core.content——Markdown 渲染管线：全站唯一安全 HTML 来源（T-011，⚠I）。

处理链（security §4）：Markdown →（Python-Markdown：fenced_code / tables /
toc / codehilite+Pygments）→ HTML → nh3 白名单净化 → 安全 HTML。

nh3 白名为 security §4 表的 V1 固定值——放宽=单独评审（卡片 DoD）。净化失败
不抛错、输出空串（宁可丢格式不丢安全）。img src 仅站内 /media/（SEC-5，
attribute_filter 收口）。markdown_to_text 供 body_text 检索生成（DM-6，
消费方 T-012）。
"""

from __future__ import annotations

from html.parser import HTMLParser

import markdown
import nh3
from markdown.extensions.toc import slugify_unicode

# 标签白名单（security §4 表：V1 固定，变更需评审）
_TAGS = {
    "p",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "ul",
    "ol",
    "li",
    "a",
    "code",
    "pre",
    "blockquote",
    "em",
    "strong",
    "i",
    "b",
    "img",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "hr",
    "br",
    "span",
    "del",
    "sup",
    "sub",
}

# 属性白名单：a[href,title]；img[src,alt,width,height]；h1–h6[id]（TOC 锚点）；
# code/pre/span[class]（Pygments 输出）；td/th[colspan,rowspan]
_ATTRIBUTES: dict[str, set[str]] = {
    "a": {"href", "title"},
    "img": {"src", "alt", "width", "height"},
    "h1": {"id"},
    "h2": {"id"},
    "h3": {"id"},
    "h4": {"id"},
    "h5": {"id"},
    "h6": {"id"},
    "code": {"class"},
    "pre": {"class"},
    "span": {"class"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan"},
}

# URL scheme：http/https/mailto/相对路径；其余（javascript:、data:）剥离
_URL_SCHEMES = {"http", "https", "mailto"}

_LINK_REL = "noopener noreferrer"  # 外链 rel 注入（security §4）

_MD_EXTENSIONS = ["fenced_code", "tables", "toc", "codehilite"]
_MD_EXTENSION_CONFIGS = {
    # 中文标题的 TOC 锚点：默认 slugify 剔除非 ASCII 会退化成下划线，换 unicode 版
    "toc": {"slugify": slugify_unicode},
}


def _img_src_media_only(tag: str, attribute: str, value: str) -> str | None:
    """img src 附加规则：仅站内相对路径 /media/...（SEC-5，外链图床剥离）。"""
    if tag == "img" and attribute == "src" and not value.startswith("/media/"):
        return None
    return value


def _clean(html: str) -> str:
    """按 security §4 白名单净化 HTML（render/toc 共用同一配置）。"""
    return nh3.clean(
        html,
        tags=_TAGS,
        attributes=_ATTRIBUTES,
        url_schemes=_URL_SCHEMES,
        link_rel=_LINK_REL,
        attribute_filter=_img_src_media_only,
    )


def render_markdown(md: str) -> tuple[str, str]:
    """Markdown →（渲染 → nh3 净化）；返回（安全 HTML, 净化后 TOC HTML）。

    净化链任一步失败不抛错，返回 ("", "")（宁可丢格式不丢安全，security §4）。
    """
    if not md:
        return "", ""
    try:
        doc = markdown.Markdown(
            extensions=_MD_EXTENSIONS, extension_configs=_MD_EXTENSION_CONFIGS
        )
        raw_html = doc.convert(md)
        raw_toc = doc.toc
    except Exception:  # noqa: BLE001 —— 失败不抛错（security §4"输出安全结果"）
        return "", ""
    try:
        return _clean(raw_html), _clean(raw_toc)
    except Exception:  # noqa: BLE001 —— 同上
        return "", ""


class _TextExtractor(HTMLParser):
    """收集 HTML 纯文本（convert_charrefs=True，实体已解码）。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        self._chunks.append(data)

    def text(self) -> str:
        return " ".join("".join(self._chunks).split())


def markdown_to_text(md: str) -> str:
    """Markdown → 检索用纯文本：先走同一净化链，再剥标签（database §3.1）。"""
    if not md:
        return ""
    html, _toc = render_markdown(md)
    if not html:
        return ""
    try:
        extractor = _TextExtractor()
        extractor.feed(html)
        extractor.close()
    except Exception:  # noqa: BLE001 —— 同上
        return ""
    return extractor.text()
