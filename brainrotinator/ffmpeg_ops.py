"""Thin wrappers around ffmpeg / ffprobe.

Replaces the moviepy + ImageMagick + cleanvid stack with direct FFmpeg calls.
Each helper builds a command list and runs it; callers handle orchestration.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Iterable


def _run(cmd: list[str], quiet: bool = False) -> None:
    if not quiet:
        print("[ffmpeg] " + " ".join(cmd))
    # Use PIPE so subprocess never calls fileno() on sys.stdout/stderr —
    # Gradio replaces them with StringIO wrappers that don't have real fds.
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    if out:
        sys.stdout.write(out.decode(errors="replace"))
    if err:
        sys.stderr.write(err.decode(errors="replace"))
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, cmd)


def probe_duration(path: str) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json", path,
    ])
    return float(json.loads(out)["format"]["duration"])


def probe_dimensions(path: str) -> tuple[int, int]:
    out = subprocess.check_output([
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json", path,
    ])
    s = json.loads(out)["streams"][0]
    return int(s["width"]), int(s["height"])


def extract_audio_wav(input_path: str, output_wav: str, sample_rate: int = 16000) -> None:
    """Extract mono PCM wav. Vosk + Whisper both accept wav directly."""
    _run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", input_path,
        "-vn", "-ac", "1", "-ar", str(sample_rate),
        "-f", "wav", output_wav,
    ])


def cut_crop_scale_burn(
    input_path: str,
    output_path: str,
    start: float,
    end: float,
    target_w: int,
    target_h: int,
    ass_path: str | None,
    blur_letterbox: bool,
    mute_ranges: Iterable[tuple[float, float]] = (),
    fonts_dir: str | None = None,
) -> None:
    """One-pass cut + format + (optional) blur + (optional) subtitle burn + (optional) mute.

    `start`/`end` are absolute seconds in the source.
    `mute_ranges` are absolute seconds too — converted to chunk-relative below.
    """
    src_w, src_h = probe_dimensions(input_path)
    duration = end - start

    if blur_letterbox:
        # Background: blur+scale to target. Foreground: scaled source centered.
        fg_h = target_h
        fg_w = int(round(src_w * (fg_h / src_h)))
        if fg_w > target_w:
            fg_w = target_w
            fg_h = int(round(src_h * (fg_w / src_w)))
        vf = (
            f"[0:v]split=2[bg][fg];"
            f"[bg]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
            f"crop={target_w}:{target_h},gblur=sigma=20[bgb];"
            f"[fg]scale={fg_w}:{fg_h}[fgs];"
            f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2[v]"
        )
    else:
        # 9:16 center crop, then scale.
        target_ar = target_w / target_h
        src_ar = src_w / src_h
        if src_ar > target_ar:
            crop_h = src_h
            crop_w = int(round(src_h * target_ar))
        else:
            crop_w = src_w
            crop_h = int(round(src_w / target_ar))
        vf = (
            f"[0:v]crop={crop_w}:{crop_h}:(in_w-{crop_w})/2:(in_h-{crop_h})/2,"
            f"scale={target_w}:{target_h}[v]"
        )

    if ass_path:
        ass_for_filter = _escape_ass_path(ass_path)
        ass_arg = ass_for_filter
        if fonts_dir:
            ass_arg += f":fontsdir={_escape_ass_path(fonts_dir)}"
        vf = vf.replace("[v]", f"[vbase];[vbase]ass={ass_arg}[v]")

    # Audio mute filter — convert absolute ranges to chunk-relative.
    af_parts = []
    for ms_start, ms_end in mute_ranges:
        rel_start = max(0.0, ms_start - start)
        rel_end = max(0.0, ms_end - start)
        if rel_end <= 0 or rel_start >= duration:
            continue
        rel_end = min(rel_end, duration)
        af_parts.append(
            f"volume=enable='between(t,{rel_start:.3f},{rel_end:.3f})':volume=0"
        )
    af = ",".join(af_parts) if af_parts else None

    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
        "-i", input_path,
        "-filter_complex", vf,
        "-map", "[v]",
        "-map", "0:a?",
    ]
    if af:
        cmd += ["-af", af]
    cmd += [
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        output_path,
    ]
    _run(cmd)


def _escape_ass_path(path: str) -> str:
    """ffmpeg's filtergraph parser needs Windows backslashes and `:` (drive letter) escaped."""
    p = path.replace("\\", "/")
    # Escape drive-letter colon for filter syntax: C:/foo -> C\:/foo
    if len(p) >= 2 and p[1] == ":":
        p = p[0] + "\\:" + p[2:]
    return p
