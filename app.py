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
import re
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
        self._buf: list[str] = [""]
        self._lock = threading.Lock()
        self._ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

    def write(self, s: str) -> int:
        with self._lock:
            # Strip ANSI color codes so the Gradio textbox is readable
            clean_s = self._ansi_escape.sub('', s)
            
            # Handle carriage returns so tqdm progress bars don't spam multiple lines
            if '\r' in clean_s:
                parts = clean_s.split('\r')
                if parts[0]:
                    self._buf[-1] += parts[0]
                for p in parts[1:]:
                    if p:
                        self._buf[-1] = p
            else:
                if '\n' in clean_s:
                    lines = clean_s.split('\n')
                    self._buf[-1] += lines[0]
                    self._buf.extend(lines[1:])
                else:
                    self._buf[-1] += clean_s
        return len(s)

    def drain(self) -> str:
        with self._lock:
            # We join the buffer but we don't clear it.
            # This allows Gradio updates to be built cleanly over carriage returns without duplicates.
            return "\n".join(self._buf).strip()

ACTIVE_EDITOR = None

def _list_to_split() -> list[str]:
    if not TO_SPLIT.exists():
        return []
    return sorted(p.name for p in TO_SPLIT.glob("*.*") if p.suffix.lower() in [".mp4", ".mov", ".mkv"])

def _run_edit_job(
    uploaded_file: str | None,
    youtube_url: str,
    existing_file: str | None,
    chunk_duration: int,
    blur: bool,
    use_whisper: bool,
    filter_profanity: bool,
    subtitle_font_size: int,
    subtitle_margin_v: int,
):
    """Generator that yields cumulative log text as the edit job runs."""
    global ACTIVE_EDITOR

    TO_SPLIT.mkdir(exist_ok=True)
    DONE_SPLIT.mkdir(exist_ok=True)
    EDITED.mkdir(exist_ok=True)

    cfg = Config.load()
    capture = _StreamCapture()

    def get_state(final=False):
        if final:
            return gr.update(value="Run", interactive=True), gr.update(value="Stop", interactive=False)
        return gr.update(value="Running...", interactive=False), gr.update(value="Stop", interactive=True)

    def emit_sys(line: str, final=False):
        # Directly write system log changes to the stream capture buffer
        capture.write(line)
        st = get_state(final)
        return capture.drain(), st[0], st[1]

    yield emit_sys("Preparing input...\n")

    # Resolve input.
    if uploaded_file:
        dest = TO_SPLIT / Path(uploaded_file).name
        shutil.copy(uploaded_file, dest)
        input_path = dest
        yield emit_sys(f"Copied uploaded file to {dest}\n")
    elif existing_file:
        input_path = TO_SPLIT / existing_file
        yield emit_sys(f"Using existing file: {input_path}\n")
    elif youtube_url.strip():
        yield emit_sys(f"Downloading {youtube_url}...\n")
        try:
            with redirect_stdout(capture):
                download_vid(youtube_url.strip(), str(TO_SPLIT))
            st = get_state()
            yield capture.drain(), st[0], st[1]
        except Exception as e:
            yield emit_sys(f"Download failed: {e}\n", final=True)
            return
        # Pick the newest mp4 in to_split that isn't in edited/.
        mp4s = sorted(
            [p for p in TO_SPLIT.glob("*.mp4") if p.is_file()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not mp4s:
            yield emit_sys("No mp4 found after download.\n", final=True)
            return
        input_path = mp4s[0]
    else:
        yield emit_sys("Provide a file or a YouTube URL.\n", final=True)
        return

    yield emit_sys(f"Editing: {input_path}\n")

    editor = VideoEditor(
        input_path=str(input_path),
        output_folder=str(DONE_SPLIT),
        chunk_duration=int(chunk_duration),
        name=input_path.stem,
        useWhisper=use_whisper,
        filterProfanityInSubtitles=filter_profanity,
        voskModelDir=cfg.voskModelDir,
        tinyLlamaDir=cfg.tinyLlamaDir,
        subtitleFontSize=int(subtitle_font_size),
        subtitleMarginV=int(subtitle_margin_v),
    )
    ACTIVE_EDITOR = editor

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
            st = get_state()
            yield chunk, st[0], st[1]

    chunk = capture.drain()
    if chunk:
        st = get_state()
        yield chunk, st[0], st[1]

    if error_box:
        yield emit_sys(f"\nERROR: {error_box[0]}\n", final=True)
        ACTIVE_EDITOR = None
        return

    # Move source to edited/.
    try:
        shutil.move(str(input_path), str(EDITED / input_path.name))
        yield emit_sys(f"\nMoved source to {EDITED / input_path.name}\n")
    except Exception as e:
        yield emit_sys(f"\nCouldn't move source: {e}\n")

    yield emit_sys("\nDone.\n", final=True)
    ACTIVE_EDITOR = None


def _list_clips() -> list[str]:
    if not DONE_SPLIT.exists():
        return []
    return sorted(str(p) for p in DONE_SPLIT.glob("*.mp4"))


def _delete_clip(path: str) -> tuple[list[str], str]:
    if path and os.path.exists(path):
        os.remove(path)
        return _list_clips(), f"Deleted {path}"
    return _list_clips(), "Nothing to delete."


def _update_preview(font_size: int, margin_v: int) -> str:
    """Returns HTML for a phone-framed 9:16 preview matching the ASS subtitle render."""
    # ASS renders font_size on a 1080x1920 canvas.
    # 1% cqw = container_width/100; font occupies font_size/1080 of canvas width.
    font_size_pct = (font_size / 1080) * 100

    # margin_v is pixels from top on a 1920px canvas.
    top_pct = (margin_v / 1920) * 100

    # ASS outline=3 at font_size=100 → ~3% of font size; 0.04em is a reasonable approximation.
    shadow = "0.04em 0.04em 0 #000, -0.04em -0.04em 0 #000, 0.04em -0.04em 0 #000, -0.04em 0.04em 0 #000, 0 0.04em 0 #000, 0 -0.04em 0 #000, 0.04em 0 0 #000, -0.04em 0 0 #000"

    return f'''
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Bangers&display=swap" rel="stylesheet">
    <div style="display:flex; justify-content:center; padding:16px 8px;">
      <!-- Phone outer shell -->
      <div style="position:relative; width:200px; background:#111; border-radius:38px; padding:10px;
                  box-shadow: 0 0 0 1px #3a3a3a, inset 0 0 0 1px #222, 0 24px 64px rgba(0,0,0,0.7);
                  border: 2px solid #444;">
        <!-- Volume buttons (left) -->
        <div style="position:absolute; left:-4px; top:70px;  width:4px; height:26px; background:#333; border-radius:3px 0 0 3px;"></div>
        <div style="position:absolute; left:-4px; top:106px; width:4px; height:44px; background:#333; border-radius:3px 0 0 3px;"></div>
        <div style="position:absolute; left:-4px; top:160px; width:4px; height:44px; background:#333; border-radius:3px 0 0 3px;"></div>
        <!-- Power button (right) -->
        <div style="position:absolute; right:-4px; top:110px; width:4px; height:60px; background:#333; border-radius:0 3px 3px 0;"></div>

        <!-- Screen -->
        <div style="width:100%; aspect-ratio:9/16; border-radius:28px; overflow:hidden;
                    position:relative; container-type:inline-size;">

          <!-- Blurred video-like background -->
          <div style="position:absolute; inset:-10%; width:120%; height:120%;
                      background: linear-gradient(160deg,
                        #0d0d0d 0%, #1a1a2e 15%, #16213e 30%,
                        #0f3460 45%, #533483 55%,
                        #0f3460 65%, #16213e 78%,
                        #1a1a2e 90%, #0d0d0d 100%);
                      filter:blur(18px);"></div>
          <!-- Darkening overlay for contrast -->
          <div style="position:absolute; inset:0; background:rgba(0,0,0,0.35);"></div>

          <!-- Dynamic island -->
          <div style="position:absolute; top:8px; left:50%; transform:translateX(-50%);
                      width:72px; height:22px; background:#000; border-radius:11px; z-index:10;"></div>

          <!-- Subtitle text -->
          <div style="position:absolute; top:{top_pct}%; left:50%; transform:translateX(-50%);
                      color:#fff; font-family:'Bangers', Impact, sans-serif; font-weight:700;
                      font-size:{font_size_pct}cqw; text-align:center;
                      text-shadow:{shadow};
                      width:90%; word-wrap:break-word; line-height:1.15; z-index:5;
                      letter-spacing:0.02em;">
            I finally found a use case...
          </div>
        </div>
      </div>
    </div>
    '''

def _stop_job():
    global ACTIVE_EDITOR
    if ACTIVE_EDITOR:
        ACTIVE_EDITOR.abort_flag = True
    from brainrotinator import ffmpeg_ops
    ffmpeg_ops.cancel()
    return gr.update(value="Run", interactive=True), gr.update(value="Stop", interactive=False)

def build_ui() -> gr.Blocks:
    cfg = Config.load()

    with gr.Blocks(title="Brainrotinator") as demo:
        gr.Markdown("# Brainrotinator\nPodcast clip automation — FFmpeg edition.")

        with gr.Tab("Edit"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### Input Video")
                    file_in = gr.File(label="Upload mp4", file_types=[".mp4"], type="filepath")
                    url_in = gr.Textbox(label="...or YouTube URL")
                    
                    with gr.Row():
                        to_split_in = gr.Dropdown(label="...or existing file in to_split/", choices=[None] + _list_to_split(), value=None)
                        refresh_files_btn = gr.Button("↻", size="sm")

                    gr.Markdown("### Edit Settings")
                    chunk_dur = gr.Slider(15, 120, value=cfg.chunkDuration, step=1, label="Chunk duration (s)")
                    blur = gr.Checkbox(value=cfg.blurTopBottomOfClip, label="Blur top/bottom (letterbox)")
                    whisper = gr.Checkbox(value=cfg.useWhisperForTranscription, label="Use Whisper (else Vosk)")
                    filt = gr.Checkbox(value=cfg.filterProfanityInSubtitles, label="Filter profanity in burned subtitles")

                    gr.Markdown("### Subtitle Settings")
                    sub_size = gr.Slider(10, 200, value=cfg.subtitleFontSize, step=1, label="Font Size")
                    sub_margin = gr.Slider(0, 1920, value=cfg.subtitleMarginV, step=10, label="Margin From Top (px)")
                    
                    with gr.Row():
                        run_btn = gr.Button("Run", variant="primary")
                        stop_btn = gr.Button("Stop", variant="stop", interactive=False)
                    
                with gr.Column(scale=1):
                    gr.Markdown("### Subtitle Preview")
                    preview_html = gr.HTML(value=_update_preview(cfg.subtitleFontSize, cfg.subtitleMarginV))
                    log_box = gr.Textbox(label="Logs", lines=20, max_lines=20, autoscroll=True)

            sub_size.change(_update_preview, inputs=[sub_size, sub_margin], outputs=preview_html)
            sub_margin.change(_update_preview, inputs=[sub_size, sub_margin], outputs=preview_html)
            
            refresh_files_btn.click(lambda: gr.update(choices=[None] + _list_to_split(), value=None), outputs=to_split_in)

            run_click_event = run_btn.click(
                _run_edit_job,
                inputs=[file_in, url_in, to_split_in, chunk_dur, blur, whisper, filt, sub_size, sub_margin],
                outputs=[log_box, run_btn, stop_btn],
            )
            
            stop_btn.click(_stop_job, outputs=[run_btn, stop_btn], cancels=[run_click_event])

        with gr.Tab("Library"):
            gr.Markdown("> **Tip:** Click any filename in the list below to download it to your computer.")
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
