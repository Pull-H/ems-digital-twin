"""Build, verify, and install the July 2026 temporal-holdout evidence archive."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = "20261023T204623425822Z-721cf5988661"
ARCHIVE_NAME = "nyc_ems_july_2026_holdout_evidence.zip"
MANIFEST_NAME = "JULY_HOLDOUT_EVIDENCE_MANIFEST.json"
PREFIXES = (
    f"data/nyc_ems/{SNAPSHOT}",
    "data/nyc_ems/july_holdout_v1",
    "reports/nyc_ems/july_holdout_v1",
)


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def permitted(name: str) -> bool:
    path = PurePosixPath(name)
    return (not path.is_absolute() and ".." not in path.parts and "\\" not in name
            and any(name.startswith(prefix + "/") for prefix in PREFIXES))


def build(archive: Path) -> None:
    files = sorted(path for prefix in PREFIXES for path in (ROOT / prefix).rglob("*") if path.is_file())
    if not files or not any("/raw/" in path.as_posix() for path in files):
        raise ValueError("Complete July raw snapshot is missing")
    if not (ROOT / PREFIXES[2] / "evaluation/analysis.json").exists():
        raise ValueError("July holdout analysis is missing")
    if any(path.is_symlink() for path in files):
        raise ValueError("Symbolic links cannot be packaged")
    archive.parent.mkdir(parents=True, exist_ok=True)
    manifest = {"schema_version": 1, "snapshot_id": SNAPSHOT,
                "created_utc": datetime.now(timezone.utc).isoformat(),
                "source": "https://data.cityofnewyork.us/Public-Safety/EMS-Incident-Dispatch-Data/76xm-jjuj",
                "kind": "supplement_to_v2026.10-repro", "files": []}
    with ZipFile(archive, "w", compression=ZIP_DEFLATED, compresslevel=6, allowZip64=True) as bundle:
        for path in files:
            name = path.relative_to(ROOT).as_posix()
            if not permitted(name):
                raise ValueError(f"Unsafe package path: {name}")
            manifest["files"].append({"path": name, "size": path.stat().st_size, "sha256": digest(path)})
            bundle.write(path, name)
        bundle.writestr(MANIFEST_NAME, json.dumps(manifest, indent=2, ensure_ascii=True) + "\n")
    print(f"{archive}\nSHA-256: {digest(archive)}\nFiles: {len(files)}")


def inspect(archive: Path) -> list[dict]:
    with ZipFile(archive) as bundle:
        manifest = json.loads(bundle.read(MANIFEST_NAME))
        if manifest.get("schema_version") != 1 or manifest.get("snapshot_id") != SNAPSHOT:
            raise ValueError("Unknown July evidence manifest")
        entries = manifest["files"]
        names = [entry["path"] for entry in entries]
        if len(set(names)) != len(names) or any(not permitted(name) for name in names):
            raise ValueError("Unsafe or duplicate archive path")
        if set(bundle.namelist()) != set(names) | {MANIFEST_NAME}:
            raise ValueError("Archive differs from manifest")
        for entry in entries:
            info = bundle.getinfo(entry["path"])
            if info.file_size != entry["size"]:
                raise ValueError(f"Size mismatch: {entry['path']}")
            sha = hashlib.sha256()
            with bundle.open(info) as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    sha.update(chunk)
            if sha.hexdigest() != entry["sha256"]:
                raise ValueError(f"Hash mismatch: {entry['path']}")
    return entries


def install(archive: Path, destination: Path, source_only: bool = False) -> None:
    entries = inspect(archive)
    if source_only:
        prefix = f"data/nyc_ems/{SNAPSHOT}/"
        entries = [entry for entry in entries if entry["path"].startswith(prefix)
                   and not any(entry["path"].startswith(prefix + folder + "/")
                               for folder in ("interim", "processed", "simulation"))]
    destination = destination.resolve()
    targets = [destination / entry["path"] for entry in entries]
    if any(not target.resolve().is_relative_to(destination) for target in targets):
        raise ValueError("Archive target escapes installation directory")
    if any(target.exists() for target in targets):
        raise FileExistsError("Use a clean clone without July evidence at these paths")
    with ZipFile(archive) as bundle:
        for entry, target in zip(entries, targets):
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(entry["path"]) as source, target.open("xb") as output:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    output.write(chunk)
    print(f"Installed {len(entries)} files in {destination}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify", "install", "install-source"))
    parser.add_argument("--archive", type=Path, default=ROOT / "release_assets" / ARCHIVE_NAME)
    parser.add_argument("--destination", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        if args.command == "build":
            build(args.archive)
        elif args.command == "verify":
            entries = inspect(args.archive)
            print(f"Verified {len(entries)} files; SHA-256: {digest(args.archive)}")
        else:
            install(args.archive, args.destination, source_only=args.command == "install-source")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
