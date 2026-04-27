"""Video editor — FFmpeg-only.

Replaces the old moviepy/ImageMagick/cleanvid stack. For each chunk we do:
  1. Extract wav for transcription (via ffmpeg).
  2. Run Vosk or Whisper -> {name}_notClean.srt + {name}.srt + {name}_summary.txt.
  3. Convert {name}.srt -> {name}.ass with our subtitle style.
  4. Build mute ranges from {name}_notClean.srt against swears.txt.
  5. Single ffmpeg pass: cut + crop/scale (or blur letterbox) + burn ASS + mute.
"""

from __future__ import annotations

import os

from termcolor import colored

from . import ffmpeg_ops
from . import subtitles as subs_mod
from .transcribe import Transcribe


TARGET_W = 1080
TARGET_H = 1920


class VideoEditor:
    def __init__(
        self,
        input_path: str,
        output_folder: str,
        chunk_duration: int,
        name: str,
        useWhisper: bool,
        filterProfanityInSubtitles: bool,
        voskModelDir: str,
        tinyLlamaDir: str,
        subtitleFontSize: int = 100,
        subtitleMarginV: int = 400,
    ):
        self.input_path = input_path
        self.output_folder = output_folder
        self.chunk_duration = chunk_duration
        self.name = name
        self.useWhisper = useWhisper
        self.filterProfanityInSubtitles = filterProfanityInSubtitles
        self.voskModelDir = voskModelDir
        self.tinyLlamaDir = tinyLlamaDir
        self.subtitleFontSize = subtitleFontSize
        self.subtitleMarginV = subtitleMarginV
        self.abort_flag = False

    def split_video_into_chunks(self):
        self._split(blur_letterbox=False)

    def split_video_into_chunks_blur(self):
        self._split(blur_letterbox=True)

    def _split(self, blur_letterbox: bool) -> None:
        print(colored(f"\n Splitting video: {self.input_path}", "green"))
        duration = int(ffmpeg_ops.probe_duration(self.input_path))
        os.makedirs(self.output_folder, exist_ok=True)

        project_root = os.getcwd()
        subtitles_path = os.path.join(project_root, "subtitles")
        os.makedirs(subtitles_path, exist_ok=True)
        assets_dir = os.path.join(project_root, "assets")
        fonts_dir = os.path.join(assets_dir, "fonts")
        font_path = os.path.join(fonts_dir, "Bangers.ttf")
        swears_path = os.path.join(assets_dir, "swears.txt")
        swears = subs_mod.load_swears(swears_path) if os.path.exists(swears_path) else []

        for start in range(0, duration, self.chunk_duration):
            if self.abort_flag:
                print(colored("\n[!] Editing aborted by user.", "red"))
                break

            end = min(start + self.chunk_duration, duration)

            num = int(end / 60)
            chunk_name = f"{self.name}_{num}"
            output_video = os.path.join(self.output_folder, f"{chunk_name}.mp4")

            if os.path.exists(output_video):
                print(colored(f"File {chunk_name} already exists. Skipping...", "yellow"))
                continue

            wav_path = os.path.join(subtitles_path, f"{chunk_name}.wav")
            chunk_for_transcription = os.path.join(subtitles_path, f"{chunk_name}_src.mp4")

            # 1. Cut a temp source clip + extract wav for transcription.
            #    (We re-encode the final clip in step 5; this temp is just for audio.)
            ffmpeg_ops._run([
                "ffmpeg", "-y", "-loglevel", "error",
                "-ss", str(start), "-to", str(end),
                "-i", self.input_path,
                "-c", "copy",
                chunk_for_transcription,
            ])
            ffmpeg_ops.extract_audio_wav(chunk_for_transcription, wav_path)

            # 2. Transcribe.
            print(colored(f"Transcribing: {wav_path}", "yellow"))
            transcribe = Transcribe(
                wav_path,
                subtitles_path,
                name=chunk_name,
                filterProfanityInSubtitles=self.filterProfanityInSubtitles,
                voskModelDir=self.voskModelDir,
                tinyLlamaDir=self.tinyLlamaDir,
            )
            if self.useWhisper:
                transcribe.transcribeVideoWhisper()
            else:
                transcribe.transcribeVideoVosk()

            os.remove(wav_path)
            os.remove(chunk_for_transcription)

            srt_clean = os.path.join(subtitles_path, f"{chunk_name}.srt")
            srt_unfiltered = os.path.join(subtitles_path, f"{chunk_name}_notClean.srt")
            ass_path = os.path.join(subtitles_path, f"{chunk_name}.ass")

            # 3. Build styled ASS for burn-in.
            subs_mod.srt_to_ass(
                srt_clean,
                ass_path,
                font_name="Bangers",
                font_size=self.subtitleFontSize,
                margin_v=self.subtitleMarginV,
            )

            # 4. Compute mute ranges from the unfiltered SRT (absolute seconds in source = chunk-relative + start).
            chunk_relative_ranges = subs_mod.mute_ranges_from_srt(srt_unfiltered, swears)
            absolute_ranges = [(s + start, e + start) for s, e in chunk_relative_ranges]
            if absolute_ranges:
                print(colored(f"Muting {len(absolute_ranges)} profanity range(s)", "yellow"))

            # 5. Final single-pass render.
            print(colored(f"Rendering: {output_video}", "green"))
            ffmpeg_ops.cut_crop_scale_burn(
                input_path=self.input_path,
                output_path=output_video,
                start=float(start),
                end=float(end),
                target_w=TARGET_W,
                target_h=TARGET_H,
                ass_path=ass_path,
                blur_letterbox=blur_letterbox,
                mute_ranges=absolute_ranges,
                fonts_dir=fonts_dir,
            )
            print(colored(f"Saved: {output_video}", "green"))
            print(colored("-------------------------------------------", "green"))
