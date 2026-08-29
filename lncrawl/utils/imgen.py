# https://github.com/alexwlchan/specktre

import random
from typing import Optional, Set

from PIL import Image, ImageDraw

from .material_colors import ColorName, ColorWeight, generate_colors
from .tilings import generate_tiles

good_color_names = set(ColorName).difference(
    [
        ColorName.black,
        ColorName.white,
        ColorName.light_blue,
        ColorName.light_green,
    ]
)
good_color_weights = set(ColorWeight).difference(
    [
        ColorWeight.main,
        ColorWeight.w50,
        ColorWeight.w100,
        ColorWeight.w200,
        ColorWeight.w800,
        ColorWeight.w900,
        ColorWeight.a100,
        ColorWeight.a200,
    ]
)


def generate_image(
    width: int = 512,
    height: int = 512,
    side_length: int = 50,
    color_names: Optional[Set[ColorName]] = None,
    color_weights: Optional[Set[ColorWeight]] = None,
):
    tiles = generate_tiles(
        width,
        height,
        side_length,
    )
    colors = generate_colors(
        color_names,
        color_weights,
    )
    im = Image.new(
        mode="RGB",
        size=(width, height),
    )
    for tile, color in zip(tiles, colors):
        ImageDraw.Draw(im).polygon(tile, fill=color)

    return im


def generate_cover_image(
    width: int = 800,
    height: int = 1032,
):
    return generate_image(
        width=width,
        height=height,
        color_names=good_color_names,
        color_weights=good_color_weights,
        side_length=random.randint(300, 750),
    )
