"""T-011 Markdown 渲染管线验收测试（security §4 逐行 + AC-23，⚠I 攻击语料）。

任务卡点名用例 13 个：test_render_basic_markdown、test_code_highlight_span_kept、
test_toc_anchors、test_xss_script_stripped、test_xss_onerror_stripped、
test_xss_javascript_href_stripped、test_xss_data_uri_stripped、
test_iframe_style_stripped、test_img_external_src_stripped_only_media、
test_link_noopener_injected、test_malformed_md_tolerated、test_to_text_strips_markup、
test_empty_input。纯函数测试（无数据库），白名单=security §4 表 V1 固定值。
"""

import re

from core.content import markdown_to_text, render_markdown


class TestRenderNormal:
    def test_render_basic_markdown(self) -> None:
        # 正常：标题/列表/强调渲染正确（security §4 验收行"合法内容完整保留"）
        html, _toc = render_markdown("# 标题\n\n- 项一\n- 项二\n\n**粗** 和 *斜*")
        assert "<h1" in html and "标题" in html
        assert "<ul>" in html and "<li>项一</li>" in html
        assert "<strong>粗</strong>" in html
        assert "<em>斜</em>" in html

    def test_code_highlight_span_kept(self) -> None:
        # 正常：Pygments 高亮 span 保留（codehilite + 白名单 span[class]/pre[class]）
        html, _toc = render_markdown("```python\nprint('hi')\n```")
        assert "<pre" in html
        assert "<span" in html
        assert "class=" in html

    def test_toc_anchors(self) -> None:
        # 正常：TOC 锚点可用——标题 id 与目录 href 一一对应（toc 扩展 + h2[id]）
        html, toc = render_markdown("## 一节\n\n正文\n\n## 二节")
        ids = set(re.findall(r'id="([^"]+)"', html))
        hrefs = set(re.findall(r'href="#([^"]+)"', toc))
        assert len(ids) >= 2
        assert hrefs
        assert hrefs <= ids


class TestXssCorpus:
    def test_xss_script_stripped(self) -> None:
        # 失败语料：<script> 连内容一起剥离（nh3 clean_content_tags）
        html, _toc = render_markdown("前文\n\n<script>alert(1)</script>\n\n后文")
        assert "<script" not in html
        assert "alert" not in html
        assert "前文" in html and "后文" in html

    def test_xss_onerror_stripped(self) -> None:
        # 失败语料：onerror 属性剥离，合法 img 属性保留
        html, _toc = render_markdown('<img src="/media/x.png" onerror="alert(1)">')
        assert "onerror" not in html
        assert "/media/x.png" in html

    def test_xss_javascript_href_stripped(self) -> None:
        # 失败语料：javascript: scheme 剥离（url_schemes 白名单外）
        html, _toc = render_markdown("[点我](javascript:alert(1))")
        assert "javascript:" not in html

    def test_xss_data_uri_stripped(self) -> None:
        # 失败语料：data:text/html URI 剥离
        html, _toc = render_markdown("![图](data:text/html;base64,PHNjcmlwdD4=)")
        assert "data:" not in html

    def test_iframe_style_stripped(self) -> None:
        # 失败语料：<iframe>/<style> 连内容剥离（不在标签白名单）
        html, _toc = render_markdown(
            '<iframe src="https://evil.example/x"></iframe>\n\n'
            "<style>body{color:red}</style>\n\n正文"
        )
        assert "<iframe" not in html
        assert "<style" not in html
        assert "color:red" not in html
        assert "正文" in html

    def test_img_external_src_stripped_only_media(self) -> None:
        # 失败语料：外链图床 src 剥离（SEC-5）；站内 /media/ 保留（与 U1 上传流闭环）
        html, _toc = render_markdown(
            "![外链](https://img.example.com/a.png)\n\n![站内](/media/2026/10/x.png)"
        )
        assert "img.example.com" not in html
        assert "/media/2026/10/x.png" in html

    def test_link_noopener_injected(self) -> None:
        # 失败语料：外链 a 注入 rel="noopener noreferrer"（nh3 link_rel）
        html, _toc = render_markdown("[外站](https://example.com/page)")
        assert 'href="https://example.com/page"' in html
        assert 'rel="noopener noreferrer"' in html


class TestRobustness:
    def test_malformed_md_tolerated(self) -> None:
        # 边界：畸形 Markdown 容错渲染，不抛错（净化失败也不抛——security §4）
        html, toc = render_markdown("###没有空格\n****\n[未闭合(链接\n<br|坏标签>")
        assert isinstance(html, str)
        assert isinstance(toc, str)

    def test_empty_input(self) -> None:
        # 边界：空串输入输出空
        assert render_markdown("") == ("", "")


class TestToText:
    def test_to_text_strips_markup(self) -> None:
        # 正常：markdown_to_text 去标记留纯文本（body_text 检索用，database §3.1）
        text = markdown_to_text(
            "## 标题\n\n**加粗** 正文 与 [链接](https://example.com)"
        )
        assert "标题" in text
        assert "加粗" in text
        assert "链接" in text
        assert "**" not in text
        assert "<" not in text
