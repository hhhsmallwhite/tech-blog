"""core.uploads——图片校验与存储（T-013，⚠I）：恶意文件进不来、隐私信息出不去。

处理链（security §5）：接收 → 大小检查（≤2MB）→ Pillow 打开+verify（魔数+完整性）
→ 格式 ∈ {JPEG, PNG, WebP, GIF} → 重编码存储（JPEG/PNG/WebP 天然剥离 EXIF 含 GPS；
GIF 原样保动画）→ base62-8 随机文件名 → MEDIA_ROOT/uploads/%Y/%m/ → 返回 (url, path)。

拒绝语义（T-014 端点映射状态码/错误码）：
- UnsupportedTypeError（UNSUPPORTED_TYPE）：非图片（SVG/文本/改后缀伪装——魔数判定）
- TooLargeError（TOO_LARGE）：file.size > 2MB（边界：恰好 2MB 放行）
- CorruptFileError（CORRUPT_FILE）：有图片魔数但 verify/解码失败（截断等）

文件扩展名不参与判定（魔数为准）；存储目录 MEDIA_ROOT 未配置时的兜底与
MEDIA_URL 同理（settings 注册缺口已登记，随 T-042 类缺陷卡处理）。
"""

from __future__ import annotations

import io
import secrets
import string
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from PIL import Image, UnidentifiedImageError

MAX_IMAGE_BYTES = 2 * 1024 * 1024  # ≤2MB（Q-05）
_NAME_LENGTH = 8  # base62-8 随机名（62^8 不可枚举 capability URL，security §5）
_ALPHABET = string.ascii_letters + string.digits

_ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "GIF"}
_EXTENSIONS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp", "GIF": ".gif"}
_MAGICS: tuple[tuple[bytes, ...], ...] = (
    (b"\xff\xd8",),  # JPEG
    (b"\x89PNG\r\n\x1a\n",),  # PNG
    (b"GIF87a", b"GIF89a"),  # GIF
    (b"RIFF",),  # WebP（RIFF 容器，偏移 8 处 WEBP；魔数前缀即可判族）
)


class UploadRejected(Exception):
    """上传拒绝基类（T-014 按拦截 .code 映射错误码）。"""

    code = "REJECTED"


class UnsupportedTypeError(UploadRejected):
    code = "UNSUPPORTED_TYPE"


class TooLargeError(UploadRejected):
    code = "TOO_LARGE"


class CorruptFileError(UploadRejected):
    code = "CORRUPT_FILE"


def _looks_like_image(data: bytes) -> bool:
    return any(data.startswith(prefix) for prefixes in _MAGICS for prefix in prefixes)


def _media_root() -> Path:
    root = getattr(settings, "MEDIA_ROOT", None)
    return Path(root) if root else Path(settings.BASE_DIR) / "media"


def _media_url() -> str:
    """URL 前缀：security §5 固定 /media/uploads/...（Caddy 映射与 T-014 契约）。

    settings 未配置 MEDIA_URL（Django 默认空串）时兜底 /media/；根路径 "/"
    视同未配置（本机沙箱曾见注入值，CI 干净环境为空串）。
    """
    url = getattr(settings, "MEDIA_URL", "")
    if not url or url == "/":
        return "/media/"
    return url


def _random_name(ext: str) -> str:
    name = "".join(secrets.choice(_ALPHABET) for _ in range(_NAME_LENGTH))
    return f"{name}{ext}"


def store_image(file) -> tuple[str, str]:
    """校验并存储图片；返回 (访问 URL, 绝对路径)。

    拒绝时抛 UploadRejected 子类，不产生任何落盘（先校验后写盘）。
    """
    if file.size is not None and file.size > MAX_IMAGE_BYTES:
        raise TooLargeError("图片超过 2MB 上限（Q-05）")
    data = file.read()

    try:
        probe = Image.open(io.BytesIO(data))
        fmt = probe.format
        probe.verify()
    except UnidentifiedImageError:
        # 魔数不符：SVG/文本/改后缀伪装一律 UNSUPPORTED_TYPE（security §5）
        if _looks_like_image(data):
            raise CorruptFileError("图片魔数存在但无法解析") from None
        raise UnsupportedTypeError("不支持的图片格式（仅 JPEG/PNG/WebP/GIF）") from None
    except Exception as exc:  # 有魔数但结构损坏
        if _looks_like_image(data):
            raise CorruptFileError("图片完整性校验失败") from exc
        raise UnsupportedTypeError("不支持的图片格式（仅 JPEG/PNG/WebP/GIF）") from None

    if fmt not in _ALLOWED_FORMATS:
        raise UnsupportedTypeError("不支持的图片格式（仅 JPEG/PNG/WebP/GIF）")

    # verify() 后需重开并完整解码（截断可能在此暴露）
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:
        raise CorruptFileError("图片完整性校验失败") from exc

    if fmt == "GIF":
        final = data  # GIF 原样存储保动画（SEC-6；GIF 无 EXIF）
    else:
        buf = io.BytesIO()
        to_save = img
        if fmt == "JPEG" and img.mode not in ("RGB", "L", "CMYK"):
            to_save = img.convert("RGB")
        to_save.save(buf, fmt)  # 不带 exif 参数 → 重编码天然剥离 EXIF（SEC-6）
        final = buf.getvalue()

    today = timezone.localdate()
    rel_dir = Path("uploads") / f"{today:%Y}" / f"{today:%m}"
    abs_dir = _media_root() / rel_dir
    abs_dir.mkdir(parents=True, exist_ok=True)
    filename = _random_name(_EXTENSIONS[fmt])
    abs_path = abs_dir / filename
    abs_path.write_bytes(final)

    url = f"{_media_url().rstrip('/')}/{rel_dir.as_posix()}/{filename}"
    return url, str(abs_path)
