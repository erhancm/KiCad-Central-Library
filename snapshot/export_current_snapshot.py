"""Copy and verify a read-only legacy asset/catalog snapshot.

The input inventory is produced by inventory_central_cutover.py. No file in
the live data root is changed. Output must be a new directory.
"""

import argparse
import hashlib
import json
import shutil
from pathlib import Path, PurePosixPath


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.output.exists():
        raise SystemExit("Output must not already exist")
    raw_inventory = args.inventory.read_bytes()
    inventory = json.loads(raw_inventory)
    content = {key: value for key, value in inventory.items() if key not in ("captured_at", "report_sha256")}
    calculated = hashlib.sha256(
        json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if calculated != inventory["report_sha256"]:
        raise SystemExit("Inventory report checksum mismatch")
    if inventory["filesystem"]["issues"]:
        raise SystemExit("Inventory contains filesystem issues")
    if "database" not in inventory:
        raise SystemExit("Inventory has no part catalog")

    snapshot = args.output / "snapshot"
    assets = snapshot / "assets"
    assets.mkdir(parents=True)
    count = total = 0
    for item in inventory["filesystem"]["files"]:
        raw_path = item["path"]
        rel = PurePosixPath(raw_path)
        if rel.is_absolute() or any(part in (".", "..") for part in rel.parts):
            raise SystemExit(f"Unsafe inventory path: {raw_path}")
        source = args.data_root.joinpath(*rel.parts)
        if source.is_symlink() or not source.is_file():
            raise SystemExit(f"Missing or linked source: {raw_path}")
        destination = assets.joinpath(*rel.parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        result = hashlib.sha256()
        copied = 0
        with source.open("rb") as src, destination.open("xb") as dst:
            for block in iter(lambda: src.read(1024 * 1024), b""):
                dst.write(block)
                result.update(block)
                copied += len(block)
        if copied != item["bytes"] or result.hexdigest() != item["sha256"]:
            raise SystemExit(f"Source changed after inventory: {raw_path}")
        count += 1
        total += copied
    if count != inventory["filesystem"]["file_count"] or total != inventory["filesystem"]["byte_count"]:
        raise SystemExit("Copied file totals differ from inventory")

    inventory_target = snapshot / "inventory.json"
    inventory_target.write_bytes(raw_inventory)
    shutil.copyfile(__file__, snapshot / "export_current_snapshot.py")
    readme = f"""# Legacy portal snapshot

This branch records the live legacy library at `{inventory['captured_at']}`.
It is an exact asset and catalog snapshot, not a validated KiCad release or a
designer clone target. The portal remains authoritative until a separate
reviewed migration is complete.

- Asset files: {count:,} ({total:,} bytes), under `snapshot/assets/` with their
  original `/data`-relative paths.
- Part catalog rows: {inventory['database']['part_count']:,}; sources:
  {inventory['database']['source_count']:,}. `snapshot/inventory.json` preserves
  each row's status, references, provenance, and approval fields, plus every
  asset SHA-256.
- Inventory report SHA-256: `{inventory['report_sha256']}`.
- Inventory file SHA-256: `{digest(args.inventory)}`.

`snapshot/assets/staging/` is retained as staging evidence. Those files are not
accepted parts and must be reviewed before entering a designer-facing library.
The snapshot preserves existing reference errors and catalog gaps; it does not
repair or silently omit them. The source export script is included here for
reproduction. Do not commit credentials or the full Postgres database dump.
"""
    (snapshot / "README.md").write_text(readme, encoding="utf-8")
    summary = {
        "asset_files": count,
        "asset_bytes": total,
        "catalog_parts": inventory["database"]["part_count"],
        "catalog_sources": inventory["database"]["source_count"],
        "inventory_report_sha256": inventory["report_sha256"],
        "inventory_file_sha256": digest(inventory_target),
    }
    print(json.dumps(summary, sort_keys=True, indent=2), flush=True)


if __name__ == "__main__":
    main()
