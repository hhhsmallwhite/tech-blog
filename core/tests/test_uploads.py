"""T-013 图片校验与存储验收测试（security §5 处理链逐项 + AC-24，⚠I 语料）。

任务卡点名用例 9 个：test_four_formats_accepted、test_svg_rejected、
test_fake_extension_rejected、test_truncated_image_rejected、
test_exactly_2mb_boundary、test_over_2mb_rejected、
test_random_filename_two_uploads_differ、test_exif_gps_stripped、
test_gif_kept_as_is。纯文件层测试（无数据库），MEDIA_ROOT 用 override 隔离。
"""

import io
import re
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image

from core.uploads import (
    CorruptFileError,
    TooLargeError,
    UnsupportedTypeError,
    store_image,
)

pytestmark = pytest.mark.django_db

MB = 1024 * 1024


def _png_bytes(size: tuple[int, int] = (4, 4), color: str = "red") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


def _jpeg_bytes(exif: Image.Exif | None = None) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (4, 4), "red")
    if exif is None:
        img.save(buf, "JPEG")
    else:
        img.save(buf, "JPEG", exif=exif)
    return buf.getvalue()


def _webp_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "blue").save(buf, "WEBP")
    return buf.getvalue()


def _gif_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("P", (4, 4)).save(buf, "GIF")
    return buf.getvalue()


def _exif_gps_jpeg_bytes() -> bytes:
    """含 GPS/厂商 EXIF 的 JPEG（security §5 隐私剥离语料）。"""
    img = Image.new("RGB", (4, 4), "red")
    exif = Image.Exif()
    exif[0x010F] = "SecretMaker"
    gps = exif.get_ifd(0x8825)
    gps[1] = "N"
    gps[2] = (31.2304, 1.0, 0.0)
    gps[4] = (121.4737, 1.0, 0.0)
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif)
    return buf.getvalue()


def _upload(data: bytes, name: str = "x.png"):
    return SimpleUploadedFile(name, data)


class TestAcceptFourFormats:
    def test_four_formats_accepted(self, tmp_path) -> None:
        # 正常：JPEG/PNG/WebP/GIF 各一张通过并落盘 uploads/%Y/%m/（§5 处理链）
        with override_settings(MEDIA_ROOT=tmp_path):
            for data, ext in [
                (_jpeg_bytes(), ".jpg"),
                (_png_bytes(), ".png"),
                (_webp_bytes(), ".webp"),
                (_gif_bytes(), ".gif"),
            ]:
                url, path = store_image(_upload(data))
                assert url.startswith("/media/uploads/")
                assert url.endswith(ext)
                assert re.search(r"uploads/\d{4}/\d{2}/[0-9A-Za-z]{8}\." + ext[1:], url)
                assert Path(path).exists()


class TestRejections:
    def test_svg_rejected(self, tmp_path) -> None:
        # 失败语料：SVG（内嵌 script）→ UNSUPPORTED_TYPE，不落盘（⚠I 必测）
        svg = (
            b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg">'
            b"<script>alert(1)</script></svg>"
        )
        with override_settings(MEDIA_ROOT=tmp_path):
            with pytest.raises(UnsupportedTypeError):
                store_image(_upload(svg, name="evil.svg"))
        assert list(tmp_path.rglob("*")) == [] or all(
            p.is_dir() for p in tmp_path.rglob("*")
        )

    def test_fake_extension_rejected(self, tmp_path) -> None:
        # 失败语料：改后缀伪装——文本改名 .png、.php 内容改名 .jpg（魔数不符，⚠I 必测）
        with override_settings(MEDIA_ROOT=tmp_path):
            for data, name in [
                (b"hello world, not an image", "fake.png"),
                (b"<?php echo 1; ?>", "shell.jpg"),
            ]:
                with pytest.raises(UnsupportedTypeError):
                    store_image(_upload(data, name=name))

    def test_truncated_image_rejected(self, tmp_path) -> None:
        # 失败语料：真实 PNG 截断 → 魔数在但完整性破坏 → CORRUPT_FILE
        good = _png_bytes()
        truncated = good[: len(good) // 2]
        with override_settings(MEDIA_ROOT=tmp_path):
            with pytest.raises(CorruptFileError):
                store_image(_upload(truncated))


class TestSizeBoundary:
    def test_exactly_2mb_boundary(self, tmp_path) -> None:
        # 边界：恰好 2MB（按 file.size 判定）→ 放行
        upload = _upload(_png_bytes())
        upload.size = 2 * MB  # 边界值；实际字节为合法小图
        with override_settings(MEDIA_ROOT=tmp_path):
            url, _path = store_image(upload)
        assert url.startswith("/media/uploads/")

    def test_over_2mb_rejected(self, tmp_path) -> None:
        # 边界：2MB+1 → TOO_LARGE，且不落盘
        upload = _upload(_png_bytes())
        upload.size = 2 * MB + 1
        with override_settings(MEDIA_ROOT=tmp_path):
            with pytest.raises(TooLargeError):
                store_image(upload)
        assert list(tmp_path.rglob("*.png")) == []


class TestStorageSemantics:
    def test_random_filename_two_uploads_differ(self, tmp_path) -> None:
        # 边界：同名/同字节两次上传文件名不同（base62 随机，不可枚举 capability URL）
        with override_settings(MEDIA_ROOT=tmp_path):
            _url1, path1 = store_image(_upload(_png_bytes()))
            _url2, path2 = store_image(_upload(_png_bytes()))
        assert path1 != path2

    def test_exif_gps_stripped(self, tmp_path) -> None:
        # 失败→隐私出不去：含 GPS/厂商 EXIF 的 JPEG 重编码后 EXIF 消失（SEC-6）
        payload = _exif_gps_jpeg_bytes()
        sanity = Image.open(io.BytesIO(payload))
        assert sanity.getexif().get(0x010F) == "SecretMaker"  # 语料自证带 EXIF
        assert sanity.getexif().get_ifd(0x8825).get(2) is not None  # GPS 在
        with override_settings(MEDIA_ROOT=tmp_path):
            _url, path = store_image(_upload(payload))
        stored = Image.open(path)
        assert stored.getexif().get(0x010F) is None
        assert stored.getexif().get_ifd(0x8825).get(2) is None
        assert dict(stored.getexif()) == {}

    def test_gif_kept_as_is(self, tmp_path) -> None:
        # 正常：GIF 原样存储（保动画，SEC-6；GIF 无 EXIF）——字节级一致
        payload = _gif_bytes()
        with override_settings(MEDIA_ROOT=tmp_path):
            _url, path = store_image(_upload(payload))
        assert Path(path).read_bytes() == payload
