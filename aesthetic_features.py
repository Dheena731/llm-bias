"""Feature extraction for Experiment 7 aesthetic-default measurements."""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path
from statistics import mean


EMOJI_RE = re.compile(
    "["
    "\U0001F1E6-\U0001F1FF"
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA70-\U0001FAFF"
    "\u2600-\u26FF"
    "\u2700-\u27BF"
    "]",
    flags=re.UNICODE,
)
DECORATIVE_RE = re.compile(
    "["
    "\u2605\u2606"
    "\u2713\u2714\u2717\u2718"
    "\u2192\u2190\u2191\u2193"
    "\u2022\u25e6\u25aa\u25ab"
    "\u25c6\u25c7\u25a0\u25a1"
    "]"
)
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+", flags=re.MULTILINE)
BULLET_RE = re.compile(r"^\s*([-*+\u2022]|\d+[.)])\s+", flags=re.MULTILINE)
NUMBERED_RE = re.compile(r"^\s*\d+[.)]\s+", flags=re.MULTILINE)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\([^)]+\)")
URL_RE = re.compile(r"https?://|www\.", flags=re.IGNORECASE)
WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'_-]*")
HEX_COLOR_RE = re.compile(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?\b")
GRADIENT_RE = re.compile(r"\b(?:linear-gradient|radial-gradient|conic-gradient|gradient)\b", flags=re.IGNORECASE)
STYLE_TOKEN_RE = re.compile(r"[a-zA-Z-]+\s*:")
TAG_RE = re.compile(r"<\s*([a-zA-Z0-9-]+)")
STOCK_PHRASES = [
    "modern",
    "seamless",
    "polished",
    "intuitive",
    "delightful",
    "elevate",
    "unlock",
    "AI-powered",
    "personalized",
    "next-level",
]


def hex_to_hsl(hex_color: str) -> tuple[float, float, float]:
    color = hex_color.strip().lstrip("#")
    if len(color) == 3:
        color = "".join(ch * 2 for ch in color)
    r, g, b = [int(color[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
    max_c = max(r, g, b)
    min_c = min(r, g, b)
    lightness = (max_c + min_c) / 2.0
    if max_c == min_c:
        return (0.0, 0.0, lightness * 100.0)
    delta = max_c - min_c
    saturation = delta / (2.0 - max_c - min_c) if lightness > 0.5 else delta / (max_c + min_c)
    if max_c == r:
        hue = (g - b) / delta + (6 if g < b else 0)
    elif max_c == g:
        hue = (b - r) / delta + 2
    else:
        hue = (r - g) / delta + 4
    return (hue * 60.0, saturation * 100.0, lightness * 100.0)


def rgb_to_hsl(r: int, g: int, b: int) -> tuple[float, float, float]:
    return hex_to_hsl(f"#{r:02X}{g:02X}{b:02X}")


def is_purple_hue(hue: float) -> bool:
    return 260.0 <= hue <= 325.0


def is_blue_hue(hue: float) -> bool:
    return 190.0 <= hue < 260.0


def shannon_entropy(values: list[str]) -> float:
    if not values:
        return 0.0
    counts = Counter(values)
    total = len(values)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def extract_text_features(text: str) -> dict[str, float | int | bool]:
    text = text or ""
    lines = text.splitlines() or [text]
    words = WORD_RE.findall(text)
    lower = text.lower()
    heading_lines = len(HEADING_RE.findall(text))
    bullet_lines = len(BULLET_RE.findall(text))
    numbered_lines = len(NUMBERED_RE.findall(text))
    markdown_marker_count = (
        heading_lines
        + bullet_lines
        + numbered_lines
        + text.count("**")
        + text.count("__")
        + text.count("`")
        + len(MARKDOWN_LINK_RE.findall(text))
    )
    stock_phrase_count = sum(lower.count(phrase.lower()) for phrase in STOCK_PHRASES)
    emoji_count = len(EMOJI_RE.findall(text))

    features = {
        "char_len": len(text),
        "word_count": len(words),
        "line_count": len(lines),
        "avg_word_len": mean([len(word) for word in words]) if words else 0.0,
        "emoji_count": emoji_count,
        "has_emoji": emoji_count > 0,
        "decorative_symbol_count": len(DECORATIVE_RE.findall(text)),
        "heading_lines": heading_lines,
        "bullet_lines": bullet_lines,
        "numbered_lines": numbered_lines,
        "markdown_marker_count": markdown_marker_count,
        "has_markdown": markdown_marker_count > 0,
        "url_count": len(URL_RE.findall(text)),
        "exclamation_count": text.count("!"),
        "question_count": text.count("?"),
        "stock_phrase_count": stock_phrase_count,
        "has_stock_phrase": stock_phrase_count > 0,
    }
    return derive_text_default_features(features)


def derive_text_default_features(
    features: dict[str, float | int | bool],
    neutral_word_median: float | None = None,
) -> dict[str, float | int | bool]:
    """Add derived presentation-prior indicators to text feature rows."""
    derived = dict(features)
    derived["has_format_default"] = any(
        bool(derived.get(name))
        for name in ("has_emoji", "has_markdown")
    ) or float(derived.get("decorative_symbol_count", 0) or 0) > 0
    has_length_inflation = False
    if neutral_word_median is not None:
        has_length_inflation = float(derived.get("word_count", 0) or 0) > neutral_word_median
    derived["has_polish_without_length"] = bool(derived.get("has_stock_phrase")) or float(
        derived.get("exclamation_count", 0) or 0
    ) > 0
    derived["has_polish_default"] = bool(derived["has_polish_without_length"]) or has_length_inflation
    return derived


def extract_ui_features(html: str) -> dict[str, float | int | bool]:
    html = html or ""
    lower = html.lower()
    hex_colors = HEX_COLOR_RE.findall(html)
    hsl_colors = [hex_to_hsl(color) for color in hex_colors]
    purple_count = sum(1 for hue, _, _ in hsl_colors if is_purple_hue(hue))
    blue_count = sum(1 for hue, _, _ in hsl_colors if is_blue_hue(hue))
    tokens = [match.group(0).rstrip(":").strip().lower() for match in STYLE_TOKEN_RE.finditer(html)]
    tags = [match.group(1).lower() for match in TAG_RE.finditer(html)]
    section_like = lower.count("<section") + lower.count("hero") + lower.count("headline")
    centered = lower.count("text-align: center") + lower.count("justify-content: center") + lower.count("align-items: center")
    border_radius_count = lower.count("border-radius")
    box_shadow_count = lower.count("box-shadow")
    blur_count = lower.count("blur(") + lower.count("backdrop-filter")
    gradient_count = len(GRADIENT_RE.findall(html))

    return {
        "char_len": len(html),
        "hex_color_count": len(hex_colors),
        "purple_hex_count": purple_count,
        "blue_hex_count": blue_count,
        "has_purple_or_blue": (purple_count + blue_count) > 0,
        "purple_or_blue_rate": (purple_count + blue_count) / len(hex_colors) if hex_colors else 0.0,
        "gradient_count": gradient_count,
        "has_gradient": gradient_count > 0,
        "border_radius_count": border_radius_count,
        "has_rounded_cards": border_radius_count > 0 and ("card" in lower or "<section" in lower),
        "box_shadow_count": box_shadow_count,
        "has_shadow": box_shadow_count > 0,
        "blur_count": blur_count,
        "has_blur_or_glass": blur_count > 0,
        "hero_section_count": section_like,
        "has_hero_section": section_like > 0,
        "centered_layout_count": centered,
        "has_centered_layout": centered > 0,
        "css_token_count": len(tokens),
        "unique_css_token_count": len(set(tokens)),
        "css_token_entropy": shannon_entropy(tokens),
        "dom_tag_count": len(tags),
        "unique_dom_tag_count": len(set(tags)),
        "dom_token_entropy": shannon_entropy(tags),
    }


def _image_module():
    try:
        from PIL import Image
    except ModuleNotFoundError as exc:
        raise RuntimeError("Pillow is required for image feature extraction. Install pillow>=11.") from exc
    return Image


def perceptual_hash(path: str | Path, size: int = 8) -> str:
    Image = _image_module()
    with Image.open(path) as image:
        gray = image.convert("L").resize((size, size))
        pixels = image_pixels(gray)
    avg = sum(pixels) / len(pixels)
    bits = "".join("1" if pixel >= avg else "0" for pixel in pixels)
    return f"{int(bits, 2):0{size * size // 4}x}"


def _sample_pixels(path: str | Path, max_size: int = 128) -> list[tuple[int, int, int]]:
    Image = _image_module()
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        rgb.thumbnail((max_size, max_size))
        return image_pixels(rgb)


def image_pixels(image) -> list:
    if hasattr(image, "get_flattened_data"):
        return list(image.get_flattened_data())
    return list(image.getdata())


def _center_brightness_score(path: str | Path) -> float:
    Image = _image_module()
    with Image.open(path) as image:
        gray = image.convert("L").resize((96, 96))
        width, height = gray.size
        center_values = []
        outer_values = []
        for y in range(height):
            for x in range(width):
                value = gray.getpixel((x, y))
                if width * 0.35 <= x <= width * 0.65 and height * 0.35 <= y <= height * 0.65:
                    center_values.append(value)
                else:
                    outer_values.append(value)
    center = mean(center_values) if center_values else 0.0
    outer = mean(outer_values) if outer_values else 1.0
    return center / max(outer, 1.0)


def extract_image_features(path: str | Path) -> dict[str, float | int | bool | str]:
    pixels = _sample_pixels(path)
    hsl_values = [rgb_to_hsl(*pixel) for pixel in pixels]
    purple = sum(1 for hue, sat, light in hsl_values if is_purple_hue(hue) and sat > 20 and light > 5)
    blue = sum(1 for hue, sat, light in hsl_values if is_blue_hue(hue) and sat > 20 and light > 5)
    saturation_values = [sat / 100.0 for _, sat, _ in hsl_values]
    lightness_values = [light / 100.0 for _, _, light in hsl_values]
    coarse_colors = [f"{r // 32}-{g // 32}-{b // 32}" for r, g, b in pixels]

    return {
        "pixel_sample_count": len(pixels),
        "purple_pixel_ratio": purple / len(pixels) if pixels else 0.0,
        "blue_pixel_ratio": blue / len(pixels) if pixels else 0.0,
        "purple_or_blue_pixel_ratio": (purple + blue) / len(pixels) if pixels else 0.0,
        "has_purple_or_blue": (purple + blue) / len(pixels) > 0.10 if pixels else False,
        "mean_saturation": mean(saturation_values) if saturation_values else 0.0,
        "mean_lightness": mean(lightness_values) if lightness_values else 0.0,
        "color_entropy": shannon_entropy(coarse_colors),
        "center_brightness_score": _center_brightness_score(path),
        "perceptual_hash": perceptual_hash(path),
    }
