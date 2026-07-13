from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .paths import (
    CHARACTER_METADATA_DIR,
    CHARACTERS_DIR,
    GENERATED_LORE_DIR,
    LORE_DIR,
    META_DATA_DIR,
    PLACES_DIR,
    SESSION_NOTES_DIR,
    WORLD_BUILDING_BACKUP_DIR,
    ensure_base_dirs,
)


@dataclass(frozen=True)
class LoreImportSummary:
    characters: int = 0
    places: int = 0
    session_notes: int = 0
    metadata: int = 0

    @property
    def total(self) -> int:
        return self.characters + self.places + self.session_notes + self.metadata


@dataclass(frozen=True)
class LoreBackupSummary:
    files: int = 0
    backup_dir: Path = WORLD_BUILDING_BACKUP_DIR
    updated_at: datetime | None = None


@dataclass(frozen=True)
class LoreBackupOption:
    label: str
    path: Path
    updated_at: datetime | None = None


LORE_SUBDIRECTORIES = {
    "character_sheets": "characters",
    "places": "places",
    "session_notes": "session_notes",
}
LORE_BACKUP_STAMP = ".last_backup"
LORE_BACKUP_SNAPSHOT_FORMAT = "%Y-%m-%d_%H-%M-%S"


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

    metadata_source = source_dir / "meta_data"
    metadata_count = copy_directory_files(metadata_source, META_DATA_DIR, overwrite=overwrite)

    return LoreImportSummary(
        characters=counts["characters"],
        places=counts["places"],
        session_notes=counts["session_notes"],
        metadata=metadata_count,
    )


def clear_local_lore() -> LoreImportSummary:
    ensure_base_dirs()
    summary = LoreImportSummary(
        characters=count_files(CHARACTERS_DIR),
        places=count_files(PLACES_DIR),
        session_notes=count_files(SESSION_NOTES_DIR),
        metadata=count_files(META_DATA_DIR, pattern="*"),
    )
    for lore_dir in unique_paths(LORE_DIR, GENERATED_LORE_DIR, CHARACTER_METADATA_DIR, META_DATA_DIR):
        clear_directory_contents(lore_dir)
    ensure_base_dirs()
    return summary


def backup_lore_files(
    source_dir: Path = LORE_DIR,
    backup_dir: Path = WORLD_BUILDING_BACKUP_DIR,
    updated_at: datetime | None = None,
    snapshot: bool = False,
) -> LoreBackupSummary:
    ensure_base_dirs()
    source_dir = source_dir.expanduser().resolve()
    backup_dir = backup_dir.expanduser().resolve()
    backup_dir.mkdir(parents=True, exist_ok=True)
    updated_at = updated_at or datetime.now().astimezone()
    target_dir = create_backup_snapshot_dir(backup_dir, updated_at) if snapshot else backup_dir

    file_count = 0
    file_count += copy_directory_files(source_dir, target_dir, pattern="*.md", overwrite=True)
    file_count += copy_directory_files(META_DATA_DIR, target_dir / "meta_data", overwrite=True, include_dotfiles=False)

    write_backup_stamp(target_dir, updated_at)
    write_backup_stamp(backup_dir, updated_at)
    return LoreBackupSummary(files=file_count, backup_dir=target_dir, updated_at=updated_at)


def read_lore_backup_date(backup_dir: Path = WORLD_BUILDING_BACKUP_DIR) -> datetime | None:
    stamp_path = backup_dir / LORE_BACKUP_STAMP
    if not stamp_path.exists():
        return None
    try:
        return datetime.fromisoformat(stamp_path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def write_backup_stamp(backup_dir: Path, updated_at: datetime) -> None:
    (backup_dir / LORE_BACKUP_STAMP).write_text(updated_at.isoformat(timespec="seconds"), encoding="utf-8")


def list_lore_backups(backup_dir: Path = WORLD_BUILDING_BACKUP_DIR) -> list[LoreBackupOption]:
    backup_dir = backup_dir.expanduser().resolve()
    if not backup_dir.exists():
        return []

    options: list[LoreBackupOption] = []
    latest_date = read_lore_backup_date(backup_dir)
    if backup_contains_lore(backup_dir):
        options.append(
            LoreBackupOption(
                label=format_backup_option_label("Latest Backup", latest_date),
                path=backup_dir,
                updated_at=latest_date,
            )
        )

    lore_subdirectory_names = set(LORE_SUBDIRECTORIES)
    for path in sorted((child for child in backup_dir.iterdir() if child.is_dir()), reverse=True):
        if path.name in lore_subdirectory_names:
            continue
        if not backup_contains_lore(path):
            continue
        updated_at = read_lore_backup_date(path)
        options.append(
            LoreBackupOption(
                label=format_backup_option_label("Backup", updated_at, fallback=path.name),
                path=path,
                updated_at=updated_at,
            )
        )

    return sorted(options, key=backup_option_sort_key, reverse=True)


def backup_option_sort_key(option: LoreBackupOption) -> float:
    if option.updated_at is None:
        return 0.0
    return option.updated_at.timestamp()


def backup_contains_lore(path: Path) -> bool:
    return any((path / subdirectory).exists() for subdirectory in LORE_SUBDIRECTORIES) or (path / "meta_data").exists()


def create_backup_snapshot_dir(backup_dir: Path, updated_at: datetime) -> Path:
    base_name = updated_at.strftime(LORE_BACKUP_SNAPSHOT_FORMAT)
    candidate = backup_dir / base_name
    suffix = 2
    while candidate.exists():
        candidate = backup_dir / f"{base_name}_{suffix}"
        suffix += 1
    candidate.mkdir(parents=True)
    return candidate


def format_backup_option_label(prefix: str, updated_at: datetime | None, fallback: str = "") -> str:
    if updated_at is None:
        return f"{prefix} - {fallback or 'Unknown Date'}"
    return f"{prefix} - {updated_at.astimezone().strftime('%Y-%m-%d %H:%M')}"


def unique_paths(*paths: Path) -> list[Path]:
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen:
            unique.append(path)
            seen.add(resolved)
    return unique


def count_files(directory: Path, pattern: str = "*.md") -> int:
    if not directory.exists():
        return 0
    return sum(1 for path in directory.rglob(pattern) if path.is_file() and not path.name.startswith("."))


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


def copy_directory_files(
    source_dir: Path,
    destination_dir: Path,
    pattern: str = "*",
    overwrite: bool = True,
    include_dotfiles: bool = True,
) -> int:
    if not source_dir.exists():
        return 0

    file_count = 0
    for source_path in sorted(source_dir.rglob(pattern)):
        if not source_path.is_file():
            continue
        if not include_dotfiles and any(part.startswith(".") for part in source_path.relative_to(source_dir).parts):
            continue
        destination_path = destination_dir / source_path.relative_to(source_dir)
        if source_path.resolve() == destination_path.resolve():
            continue
        if destination_path.exists() and not overwrite:
            continue
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)
        file_count += 1
    return file_count
