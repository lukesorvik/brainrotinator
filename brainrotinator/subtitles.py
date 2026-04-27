"""Subtitle helpers: SRT -> styled ASS, plus profanity mute-range extraction.

Replaces moviepy's TextClip/SubtitlesClip and the cleanvid subprocess.
"""

from __future__ import annotations

import os
import re
from typing import Iterable

import pysrt
import pysubs2


def srt_to_ass(
    srt_path: str,
    ass_path: str,
    font_name: str = "Bangers",
    font_size: int = 90,
    primary_color: str = "&H00FFFFFF",      # white (AABBGGRR)
    outline_color: str = "&H00000000",      # black
    outline: int = 3,
    shadow: int = 0,
    alignment: int = 8,                     # top-center; 2 = bottom-center, 5 = middle-center
    margin_v: int = 480,                    # vertical offset; tuned for 1920px tall video
    play_res_x: int = 1080,
    play_res_y: int = 1920,
) -> None:
    """Convert SRT to ASS with a styled `Default` style.

    Designed for vertical 1080x1920 output. Caller still needs the .ttf font
    available to libass — either installed system-wide or referenced via
    `fontsdir=...` in the ffmpeg `ass=` filter.
    """
    subs = pysubs2.load(srt_path, encoding="utf-8")
    subs.info["PlayResX"] = str(play_res_x)
    subs.info["PlayResY"] = str(play_res_y)
    subs.info["ScaledBorderAndShadow"] = "yes"

    style = subs.styles["Default"]
    style.fontname = font_name
    style.fontsize = font_size
    style.primarycolor = pysubs2.Color(255, 255, 255, 0)
    style.outlinecolor = pysubs2.Color(0, 0, 0, 0)
    style.bold = True
    style.outline = outline
    style.shadow = shadow
    style.alignment = alignment
    style.marginv = margin_v

    subs.save(ass_path, format_="ass")


def load_swears(swears_path: str) -> list[str]:
    with open(swears_path, "r", encoding="utf-8") as f:
        return [w.strip().lower() for w in f if w.strip()]


def mute_ranges_from_srt(
    srt_path: str,
    swears: Iterable[str],
    pad_seconds: float = 0.05,
) -> list[tuple[float, float]]:
    """Return (start, end) seconds for every subtitle line containing a swear.

    Uses word-boundary matching so 'ass' doesn't match 'class'.
    Pads each range by `pad_seconds` on both sides to account for transcription drift.
    """
    swear_list = [s for s in swears if s]
    if not swear_list:
        return []
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(w) for w in swear_list) + r")\b",
        re.IGNORECASE,
    )

    ranges: list[tuple[float, float]] = []
    for sub in pysrt.open(srt_path, encoding="utf-8"):
        if not pattern.search(sub.text):
            continue
        start_s = _pysrt_to_seconds(sub.start) - pad_seconds
        end_s = _pysrt_to_seconds(sub.end) + pad_seconds
        ranges.append((max(0.0, start_s), end_s))
    return _merge_overlapping(ranges)


def _pysrt_to_seconds(t) -> float:
    return t.hours * 3600 + t.minutes * 60 + t.seconds + t.milliseconds / 1000.0


def _merge_overlapping(ranges: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not ranges:
        return []
    ranges = sorted(ranges)
    merged = [ranges[0]]
    for s, e in ranges[1:]:
        ps, pe = merged[-1]
        if s <= pe:
            merged[-1] = (ps, max(pe, e))
        else:
            merged.append((s, e))
    return merged
