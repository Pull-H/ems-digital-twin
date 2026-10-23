"""Build, verify, and install the frozen NYC EMS evidence archive."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = "20260909T040537085584Z-56d48fe7ce9b"
ARCHIVE_NAME = f"nyc_ems_{SNAPSHOT}_evidence.zip"
MANIFEST_NAME = "EVIDENCE_MANIFEST.json"
PREFIXES = (
    f"data/nyc_ems/{SNAPSHOT}",
    f"research/artifacts/nyc_ems/{SNAPSHOT}/phase5",
    f"reports/nyc_ems/{SNAPSHOT}",
    "docs/article_assets/peer_review_2026",
)


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def allowed(name: str) -> bool:
    path = PurePosixPath(name)
    return (
        not path.is_absolute()
        and ".." not in path.parts
        and "\\" not in name
        and any(name.startswith(prefix + "/") for prefix in PREFIXES)
    )


def build(archive: Path) -> None:
    files = sorted(path for prefix in PREFIXES for path in (ROOT / prefix).rglob("*") if path.is_file())
    if not files or not any("/raw/" in path.as_posix() for path in files):
        raise ValueError("Frozen snapshot or raw pages are missing")
    if any(path.is_symlink() for path in files):
        raise ValueError("Symbolic links are not allowed in the evidence bundle")
    archive.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": 1,
        "snapshot_id": SNAPSHOT,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source": "https://data.cityofnewyork.us/Public-Safety/EMS-Incident-Dispatch-Data/76xm-jjuj",
        "files": [],
    }
    with ZipFile(archive, "w", compression=ZIP_DEFLATED, compresslevel=6, allowZip64=True) as bundle:
        for path in files:
            name = path.relative_to(ROOT).as_posix()
            if not allowed(name):
                raise ValueError(f"Unexpected path: {name}")
            manifest["files"].append({"path": name, "size": path.stat().st_size, "sha256": digest_file(path)})
            bundle.write(path, name)
        bundle.writestr(MANIFEST_NAME, json.dumps(manifest, indent=2, ensure_ascii=True) + "\n")
    print(f"{archive}\nSHA-256: {digest_file(archive)}\nFiles: {len(files)}")


def inspect(archive: Path) -> tuple[dict, list[dict]]:
    with ZipFile(archive) as bundle:
        manifest = json.loads(bundle.read(MANIFEST_NAME))
        if manifest.get("schema_version") != 1 or manifest.get("snapshot_id") != SNAPSHOT:
            raise ValueError("Unknown evidence manifest")
        entries = manifest["files"]
        names = [entry["path"] for entry in entries]
        if len(names) != len(set(names)) or any(not allowed(name) for name in names):
            raise ValueError("Unsafe or duplicate archive path")
        if set(bundle.namelist()) != set(names) | {MANIFEST_NAME}:
            raise ValueError("Archive contents do not match the manifest")
        for entry in entries:
            info = bundle.getinfo(entry["path"])
            if info.file_size != entry["size"]:
                raise ValueError(f"Size mismatch: {entry['path']}")
            digest = hashlib.sha256()
            with bundle.open(info) as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != entry["sha256"]:
                raise ValueError(f"SHA-256 mismatch: {entry['path']}")
    return manifest, entries


def install(archive: Path, destination: Path) -> None:
    _, entries = inspect(archive)
    destination = destination.resolve()
    targets = [destination / entry["path"] for entry in entries]
    if any(not target.resolve().is_relative_to(destination) for target in targets):
        raise ValueError("Destination contains a symbolic link outside the target directory")
    if any(target.exists() for target in targets):
        raise FileExistsError("Destination already contains evidence files; use an empty clone/directory")
    with ZipFile(archive) as bundle:
        for entry, target in zip(entries, targets):
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(entry["path"]) as source, target.open("xb") as output:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    output.write(chunk)
    print(f"Installed {len(entries)} files in {destination}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify", "install"))
    parser.add_argument("--archive", type=Path, default=ROOT / "release_assets" / ARCHIVE_NAME)
    parser.add_argument("--destination", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        if args.command == "build":
            build(args.archive)
        elif args.command == "verify":
            _, entries = inspect(args.archive)
            print(f"Verified {len(entries)} files; archive SHA-256: {digest_file(args.archive)}")
        else:
            install(args.archive, args.destination)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
