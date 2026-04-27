import sys
import os
import subprocess
import re
from termcolor import colored


def _sanitize_title(title: str) -> str:
    return re.sub(r'[^\w\-]', '_', title)[:100]


def download_vid(url: str, path: str) -> None:
    os.makedirs(path, exist_ok=True)

    # Probe the video title first so we can predict the output filename.
    title_result = subprocess.run(
        ["yt-dlp", "--print", "title", "--no-playlist", url],
        capture_output=True, text=True, check=True,
    )
    raw_title = title_result.stdout.strip()
    safe_title = _sanitize_title(raw_title)
    output_path = os.path.join(path, safe_title + ".mp4")

    print(colored(f"Downloading: {raw_title}", "green"))
    print(colored(f"Output: {output_path}", "blue"))

    proc = subprocess.Popen(
        [
            "yt-dlp",
            "--no-playlist",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
            "--merge-output-format", "mp4",
            "-o", output_path,
            url,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    out, err = proc.communicate()
    if out:
        sys.stdout.write(out.decode(errors="replace"))
    if err:
        sys.stderr.write(err.decode(errors="replace"))
    if proc.returncode != 0:
        raise subprocess.CalledProcessError(proc.returncode, ["yt-dlp"])

    print(colored(f"Saved to: {output_path}", "green"))
    return output_path


def main():
    if len(sys.argv) < 3:
        print("Usage: python downloadVid.py <url> <path>")
        sys.exit(1)

    url = sys.argv[1]
    path = sys.argv[2]
    print(f"URL: {url}\nPath: {path}")
    download_vid(url, path)


if __name__ == "__main__":
    main()
