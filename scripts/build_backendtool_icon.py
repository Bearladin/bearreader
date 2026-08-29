"""Build the dedicated backendtool terminal icon without using BearReader artwork."""

import argparse
from io import BytesIO
from pathlib import Path
import struct
from typing import Final

from PIL import Image, ImageDraw

PROJECT_ROOT: Final = Path(__file__).resolve().parents[1]
OUTPUT: Final = PROJECT_ROOT / "res" / "backendtool.ico"
ICON_SIZES: Final = (16, 20, 24, 32, 40, 48, 64, 128, 256)
BACKGROUND: Final = "#4B4B48"
FOREGROUND: Final = "#F1F1EE"
SUPERSAMPLING: Final = 4


def _render_icon(size: int) -> Image.Image:
    """Render one target size directly from the shared geometric definition."""
    canvas_size = size * SUPERSAMPLING
    image = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    radius = round(canvas_size * 0.19)
    draw.rounded_rectangle(
        (0, 0, canvas_size - 1, canvas_size - 1),
        radius=radius,
        fill=BACKGROUND,
    )

    width = max(SUPERSAMPLING * 2, round(canvas_size * 0.085))
    chevron = (
        (round(canvas_size * 0.27), round(canvas_size * 0.30)),
        (round(canvas_size * 0.48), round(canvas_size * 0.50)),
        (round(canvas_size * 0.27), round(canvas_size * 0.70)),
    )
    draw.line(chevron, fill=FOREGROUND, width=width, joint="curve")
    draw.line(
        (
            (round(canvas_size * 0.54), round(canvas_size * 0.70)),
            (round(canvas_size * 0.77), round(canvas_size * 0.70)),
        ),
        fill=FOREGROUND,
        width=width,
    )

    return image.resize((size, size), Image.Resampling.LANCZOS)


def _png_bytes(image: Image.Image) -> bytes:
    output = BytesIO()
    image.save(output, format="PNG", optimize=False)
    return output.getvalue()


def build_ico() -> bytes:
    """Create an ICO containing independently rendered PNG frames."""
    frames = [(size, _png_bytes(_render_icon(size))) for size in ICON_SIZES]
    directory_size = 6 + 16 * len(frames)
    offset = directory_size
    entries: list[bytes] = []
    payloads: list[bytes] = []

    for size, payload in frames:
        encoded_size = 0 if size == 256 else size
        entries.append(
            struct.pack(
                "<BBBBHHII",
                encoded_size,
                encoded_size,
                0,
                0,
                1,
                32,
                len(payload),
                offset,
            )
        )
        payloads.append(payload)
        offset += len(payload)

    header = struct.pack("<HHH", 0, 1, len(frames))
    return b"".join((header, *entries, *payloads))


def verify_icon(path: Path = OUTPUT) -> None:
    """Verify that the committed ICO contains every required target size."""
    if not path.is_file():
        raise ValueError(f"Missing backendtool icon: {path}")
    with Image.open(path) as image:
        sizes = image.info.get("sizes")
    if sizes != set((size, size) for size in ICON_SIZES):
        raise ValueError(f"Unexpected backendtool icon sizes: {sizes}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate the existing ICO")
    args = parser.parse_args()

    if args.check:
        verify_icon()
        print(f"Verified backendtool icon: {OUTPUT}")
        return

    OUTPUT.write_bytes(build_ico())
    verify_icon()
    print(f"Created backendtool icon: {OUTPUT}")


if __name__ == "__main__":
    main()
