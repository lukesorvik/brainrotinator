"""Typed config for brainrotinator.

Replaces the old `global` block in main.py and the dict access scattered
across the codebase. Loaded from `config.json` at the project root.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


CONFIG_PATH = Path(__file__).resolve().parent / "config.json"


class Config(BaseModel):
    # Upload metadata
    tags: list[str] = Field(default_factory=list)
    description: str = "#shorts"

    # Upload scheduling
    howManyUploads: int = 1
    howManyHoursBetweenSchedule: int = 0
    howManyMinsBetweenUpload: int = 5
    howManyHoursLongToSleep: int = 23
    sleepXMinsBeforeStartingUploader: int = 0

    # Editing
    chunkDuration: int = 58
    blurTopBottomOfClip: bool = True
    useWhisperForTranscription: bool = False
    filterProfanityInSubtitles: bool = False

    # Subtitles
    subtitleFontSize: int = 100
    subtitleMarginV: int = 480

    # Upload targets
    uploadToYoutube: bool = True
    uploadToInstagram: bool = True
    uploadToTiktok: bool = False

    # Selenium
    firefoxHeadless: bool = True

    # Model dirs (empty = use cwd)
    voskModelDir: str = "models"
    tinyLlamaDir: str = "models"

    @classmethod
    def load(cls, path: Path | str = CONFIG_PATH) -> "Config":
        with open(path) as f:
            return cls.model_validate(json.load(f))

    def save(self, path: Path | str = CONFIG_PATH) -> None:
        with open(path, "w") as f:
            json.dump(self.model_dump(), f, indent=4)
