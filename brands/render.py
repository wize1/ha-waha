"""Render brand icons for the WAHA HA integration.

Generates PNG files matching the SVG design (icon.svg) using only Pillow
primitives, so it works on Windows without GTK/Cairo native libs.

Outputs:
  brands/icon.png       256x256
  brands/icon@2x.png    512x512

Run from the repo root:
  python brands/render.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

GREEN = "#25D366"
WHITE = "#FFFFFF"
SUPERSAMPLE = 4  # render at Nx and downscale for AA


def render(size: int, out_path: Path) -> None:
    s = size * SUPERSAMPLE
    scale = s / 512.0  # design coordinates are in 512-unit viewBox

    def sx(v: float) -> float:
        return v * scale

    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    d.rounded_rectangle(
        (0, 0, s - 1, s - 1),
        radius=int(sx(112)),
        fill=GREEN,
    )

    d.rounded_rectangle(
        (sx(104), sx(112), sx(408), sx(352)),
        radius=int(sx(48)),
        fill=WHITE,
    )
    d.polygon(
        [(sx(160), sx(352)), (sx(232), sx(352)), (sx(160), sx(424))],
        fill=WHITE,
    )
    d.rectangle(
        (sx(160), sx(304), sx(232), sx(353)),
        fill=WHITE,
    )

    for cx in (200, 256, 312):
        r = sx(20)
        d.ellipse(
            (sx(cx) - r, sx(232) - r, sx(cx) + r, sx(232) + r),
            fill=GREEN,
        )

    img = img.resize((size, size), Image.LANCZOS)
    img.save(out_path, "PNG", optimize=True)
    print(f"wrote {out_path} ({size}x{size}, {out_path.stat().st_size} bytes)")


def main() -> None:
    out_dir = Path(__file__).resolve().parent
    render(256, out_dir / "icon.png")
    render(512, out_dir / "icon@2x.png")


if __name__ == "__main__":
    main()
