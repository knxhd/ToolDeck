"""托盘 / 程序图标生成工具（Windows 打包时由 build-windows.ps1 调用）。

图标来源优先级：
1. frontend/public/favicon.svg（与浏览器标签页图标同源，默认）；
   需要 resvg-py 负责 SVG 栅格化（纯 wheel，无需系统级 cairo）；
2. image/ 下的品牌图（logo.png / logo.ico，可选覆盖）；
3. 内置占位图形（主色圆角方块 + 白色 T）。

用法：
    python backend/tray_icon.py --out backend/build/tray.ico
"""
from __future__ import annotations

import argparse
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 默认图标源：前端 favicon（改前端图标即同步改托盘图标）
FAVICON_CANDIDATES = (
    "frontend/public/favicon.svg",
    "frontend/public/logo.svg",
)
# 备用：仓库自带的位图品牌资源
BRAND_CANDIDATES = (
    "image/tray-icon.png",
    "image/tray-icon.ico",
    "image/logo.png",
    "image/logo.ico",
)

ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

# 与前端主色 --primary-6 保持一致（Arco 默认蓝）
BRAND_COLOR = (22, 93, 255)


def _load_font(size: int):
    from PIL import ImageFont

    for name in ("seguisb.ttf", "arialbd.ttf", "seguisb.ttc", "arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def build_placeholder(min_size: int = 256):
    """生成占位图标：圆角方块底色 + 居中的白色 T。"""
    from PIL import Image, ImageDraw

    size = max(min_size, 256)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        [(0, 0), (size - 1, size - 1)],
        radius=int(size * 0.22),
        fill=(*BRAND_COLOR, 255),
    )
    font = _load_font(int(size * 0.56))
    text = "T"
    box = draw.textbbox((0, 0), text, font=font)
    offset_x = (size - (box[2] - box[0])) / 2 - box[0]
    offset_y = (size - (box[3] - box[1])) / 2 - box[1]
    draw.text((offset_x, offset_y), text, font=font, fill=(255, 255, 255, 255))
    return img


def render_svg(src: Path, size: int = 256):
    """把 SVG 栅格化为 PIL 图像；resvg-py 不可用时返回 None。"""
    try:
        import resvg_py
    except Exception:
        return None
    try:
        from PIL import Image

        png = resvg_py.svg_to_bytes(svg_path=str(src), width=size, height=size)
        img = Image.open(io.BytesIO(bytes(png)))
        img.load()
        return img.convert("RGBA")
    except Exception:
        return None


def ensure_icon(out: Path, force_placeholder: bool = False) -> tuple[Path, str]:
    """确保 out 处存在 .ico，返回 (路径, 来源说明)。"""
    from PIL import Image

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)

    if not force_placeholder:
        for candidate in FAVICON_CANDIDATES:
            src = ROOT / candidate
            if not src.exists():
                continue
            img = render_svg(src)
            if img is None:
                print(
                    "[tray-icon] 未安装 resvg-py，无法栅格化 SVG，改用备用图标源"
                    "（pip install resvg-py 即可）"
                )
                continue
            img.save(out, format="ICO", sizes=ICO_SIZES)
            return out, f"前端图标 {candidate}"

        for candidate in BRAND_CANDIDATES:
            src = ROOT / candidate
            if src.exists():
                img = Image.open(src).convert("RGBA")
                side = max(img.size)
                canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
                canvas.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
                canvas.save(out, format="ICO", sizes=ICO_SIZES)
                return out, f"品牌图 {candidate}"

    build_placeholder().save(out, format="ICO", sizes=ICO_SIZES)
    return out, "内置占位图标"


def main() -> None:
    parser = argparse.ArgumentParser(description="生成托盘 / 程序图标 (.ico)")
    parser.add_argument("--out", default=str(Path("backend") / "build" / "tray.ico"))
    parser.add_argument("--force", action="store_true", help="忽略 favicon/image 资源，强制用占位图标")
    args = parser.parse_args()

    path, source = ensure_icon(Path(args.out), force_placeholder=args.force)
    print(f"[tray-icon] {path} （来源：{source}）")


if __name__ == "__main__":
    main()
