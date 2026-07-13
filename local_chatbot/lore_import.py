from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from .paths import (
    CHARACTER_METADATA_DIR,
    CHARACTERS_DIR,
    GENERATED_LORE_DIR,
    LORE_DIR,
    PLACES_DIR,
    SESSION_NOTES_DIR,
    ensure_base_dirs,
)


@dataclass(frozen=True)
class LoreImportSummary:
    characters: int = 0
    places: int = 0
    session_notes: int = 0

    @property
    def total(self) -> int:
        return self.characters + self.places + self.session_notes


LORE_SUBDIRECTORIES = {
    "character_sheets": "characters",
    "places": "places",
    "session_notes": "session_notes",
}


def import_lore_directory(source_dir: Path, overwrite: bool = True) -> LoreImportSummary:
    ensure_base_dirs()
    source_dir = source_dir.expanduser().resolve()
    if not source_dir.exists() or not source_dir.is_dir():
        raise FileNotFoundError(source_dir)

    counts = {"characters": 0, "places": 0, "session_notes": 0}
    destinations = {
        "characters": CHARACTERS_DIR,
        "places": PLACES_DIR,
        "session_notes": SESSION_NOTES_DIR,
    }
    for subdir_name, bucket in LORE_SUBDIRECTORIES.items():
        source_subdir = source_dir / subdir_name
        if not source_subdir.exists():
            continue
        destination_subdir = destinations[bucket]
        destination_subdir.mkdir(parents=True, exist_ok=True)
        for source_path in lore_markdown_files(source_subdir):
            destination_path = destination_subdir / source_path.name
            if source_path.resolve() == destination_path.resolve():
                continue
            if destination_path.exists() and not overwrite:
                continue
            shutil.copyfile(source_path, destination_path)
            counts[bucket] += 1

    return LoreImportSummary(
        characters=counts["characters"],
        places=counts["places"],
        session_notes=counts["session_notes"],
    )


def clear_local_lore() -> LoreImportSummary:
    ensure_base_dirs()
    summary = LoreImportSummary(
        characters=count_files(CHARACTERS_DIR),
        places=count_files(PLACES_DIR),
        session_notes=count_files(SESSION_NOTES_DIR),
    )
    for lore_dir in unique_paths(LORE_DIR, GENERATED_LORE_DIR, CHARACTER_METADATA_DIR):
        clear_directory_contents(lore_dir)
    ensure_base_dirs()
    return summary


def unique_paths(*paths: Path) -> list[Path]:
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen:
            unique.append(path)
            seen.add(resolved)
    return unique


def count_files(directory: Path) -> int:
    if not directory.exists():
        return 0
    return sum(1 for path in directory.rglob("*.md") if path.is_file())


def clear_directory_contents(directory: Path) -> None:
    if not directory.exists():
        return
    for path in directory.iterdir():
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        else:
            path.unlink()


def lore_markdown_files(source_dir: Path) -> list[Path]:
    return [
        path
        for path in sorted(source_dir.glob("*.md"))
        if not path.name.startswith(".") and "TEMPLATE" not in path.name.upper()
    ]
