"""Gradio UI for brainrotinator.

Tabs:
  - Edit: upload a file or YouTube URL, run the splitter, watch logs stream.
  - Library: list / preview / delete clips in done_split/.
  - Settings: read/write config.json.

The CLI (`main.py -e/-u`) still works; this UI is additive.
"""

from __future__ import annotations

import io
import json
import logging
import os
import shutil
import sys
import threading
import time
from contextlib import redirect_stdout
from pathlib import Path

import gradio as gr

from brainrotinator.video_editor import VideoEditor
from config import Config
from downloader.downloadVid import download_vid


PROJECT_ROOT = Path(__file__).resolve().parent
TO_SPLIT = PROJECT_ROOT / "to_split"
DONE_SPLIT = PROJECT_ROOT / "done_split"
EDITED = TO_SPLIT / "edited"


class _StreamCapture(io.TextIOBase):
    """Tee writes into a thread-safe buffer so a Gradio generator can drain it."""

    def __init__(self):
        self._buf: list[str] = []
        self._lock = threading.Lock()

    def write(self, s: str) -> int:
        with self._lock:
            self._buf.append(s)
        return len(s)

    def drain(self) -> str:
        with self._lock:
            out = "".join(self._buf)
            self._buf.clear()
        return out


def _run_edit_job(
    uploaded_file: str | None,
    youtube_url: str,
    chunk_duration: int,
    blur: bool,
    use_whisper: bool,
    filter_profanity: bool,
):
    """Generator that yields cumulative log text as the edit job runs."""

    TO_SPLIT.mkdir(exist_ok=True)
    DONE_SPLIT.mkdir(exist_ok=True)
    EDITED.mkdir(exist_ok=True)

    cfg = Config.load()
    log = ""
    capture = _StreamCapture()

    def emit(line: str) -> str:
        nonlocal log
        log += line
        return log

    yield emit("Preparing input...\n")

    # Resolve input.
    if uploaded_file:
        dest = TO_SPLIT / Path(uploaded_file).name
        shutil.copy(uploaded_file, dest)
        input_path = dest
        yield emit(f"Copied uploaded file to {dest}\n")
    elif youtube_url.strip():
        yield emit(f"Downloading {youtube_url}...\n")
        try:
            with redirect_stdout(capture):
                download_vid(youtube_url.strip(), str(TO_SPLIT))
            yield emit(capture.drain())
        except Exception as e:
            yield emit(f"Download failed: {e}\n")
            return
        # Pick the newest mp4 in to_split that isn't in edited/.
        mp4s = sorted(
            [p for p in TO_SPLIT.glob("*.mp4") if p.is_file()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not mp4s:
            yield emit("No mp4 found after download.\n")
            return
        input_path = mp4s[0]
    else:
        yield emit("Provide a file or a YouTube URL.\n")
        return

    yield emit(f"Editing: {input_path}\n")

    editor = VideoEditor(
        input_path=str(input_path),
        output_folder=str(DONE_SPLIT),
        chunk_duration=int(chunk_duration),
        name=input_path.stem,
        useWhisper=use_whisper,
        filterProfanityInSubtitles=filter_profanity,
        voskModelDir=cfg.voskModelDir,
        tinyLlamaDir=cfg.tinyLlamaDir,
    )

    # Run the splitter on a background thread so we can stream prints.
    error_box: list[BaseException] = []

    def _runner():
        try:
            with redirect_stdout(capture):
                if blur:
                    editor.split_video_into_chunks_blur()
                else:
                    editor.split_video_into_chunks()
        except BaseException as e:
            error_box.append(e)

    t = threading.Thread(target=_runner, daemon=True)
    t.start()

    while t.is_alive():
        time.sleep(0.4)
        chunk = capture.drain()
        if chunk:
            yield emit(chunk)

    chunk = capture.drain()
    if chunk:
        yield emit(chunk)

    if error_box:
        yield emit(f"\nERROR: {error_box[0]}\n")
        return

    # Move source to edited/.
    try:
        shutil.move(str(input_path), str(EDITED / input_path.name))
        yield emit(f"\nMoved source to {EDITED / input_path.name}\n")
    except Exception as e:
        yield emit(f"\nCouldn't move source: {e}\n")

    yield emit("\nDone.\n")


def _list_clips() -> list[str]:
    if not DONE_SPLIT.exists():
        return []
    return sorted(str(p) for p in DONE_SPLIT.glob("*.mp4"))


def _delete_clip(path: str) -> tuple[list[str], str]:
    if path and os.path.exists(path):
        os.remove(path)
        return _list_clips(), f"Deleted {path}"
    return _list_clips(), "Nothing to delete."


def build_ui() -> gr.Blocks:
    cfg = Config.load()

    with gr.Blocks(title="Brainrotinator") as demo:
        gr.Markdown("# Brainrotinator\nPodcast clip automation — FFmpeg edition.")

        with gr.Tab("Edit"):
            with gr.Row():
                with gr.Column():
                    file_in = gr.File(label="Upload mp4", file_types=[".mp4"], type="filepath")
                    url_in = gr.Textbox(label="...or YouTube URL")
                    chunk_dur = gr.Slider(15, 120, value=cfg.chunkDuration, step=1, label="Chunk duration (s)")
                    blur = gr.Checkbox(value=cfg.blurTopBottomOfClip, label="Blur top/bottom (letterbox)")
                    whisper = gr.Checkbox(value=cfg.useWhisperForTranscription, label="Use Whisper (else Vosk)")
                    filt = gr.Checkbox(value=cfg.filterProfanityInSubtitles, label="Filter profanity in burned subtitles")
                    run_btn = gr.Button("Run", variant="primary")
                with gr.Column():
                    log_box = gr.Textbox(label="Logs", lines=25, max_lines=25, autoscroll=True)

            run_btn.click(
                _run_edit_job,
                inputs=[file_in, url_in, chunk_dur, blur, whisper, filt],
                outputs=log_box,
            )

        with gr.Tab("Library"):
            gallery = gr.Files(label="Clips in done_split/", value=_list_clips())
            refresh = gr.Button("Refresh")
            with gr.Row():
                to_delete = gr.Textbox(label="Path to delete")
                delete_btn = gr.Button("Delete", variant="stop")
            delete_status = gr.Textbox(label="Status", interactive=False)

            refresh.click(lambda: _list_clips(), outputs=gallery)
            delete_btn.click(_delete_clip, inputs=to_delete, outputs=[gallery, delete_status])

        with gr.Tab("Settings"):
            gr.Markdown("Edit `config.json`. Uploader fields are still consumed by the CLI uploader.")
            settings_box = gr.Code(value=json.dumps(cfg.model_dump(), indent=4), language="json", label="config.json")
            save_btn = gr.Button("Save")
            save_status = gr.Textbox(label="Status", interactive=False)

            def _save(text: str) -> str:
                try:
                    new_cfg = Config.model_validate_json(text)
                except Exception as e:
                    return f"Invalid: {e}"
                new_cfg.save()
                return "Saved."

            save_btn.click(_save, inputs=settings_box, outputs=save_status)

    return demo


if __name__ == "__main__":
    ui = build_ui()
    ui.queue().launch(server_name="0.0.0.0", server_port=7860)
