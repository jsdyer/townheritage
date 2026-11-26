#!/usr/bin/env python3
"""Build an unlisted, noindex review prototype."""
import argparse
import json
from pathlib import Path
import shutil
ROOT = Path(__file__).resolve().parents[1]


def build(root=ROOT, require_data=False):
    data_path = root / "data/europeana.json"
    if require_data and not data_path.exists():
        raise ValueError("A successful real Europeana capture is required before publication")
    snapshot = json.loads(data_path.read_text()) if data_path.exists() else {"version":1,"capturedAt":None,"records":[],"collections":[],"mode":"not-configured"}
    if not isinstance(snapshot.get("records"), list) or not isinstance(snapshot.get("collections"), list):
        raise ValueError("Invalid snapshot")
    if require_data and (not snapshot.get("capturedAt") or not snapshot.get("requests")):
        raise ValueError("Capture provenance is required")
    output = root / "dist"
    if output.is_symlink() or any(p.is_symlink() for p in (root / "web").rglob("*")):
        raise ValueError("Symlinks are not supported")
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(root / "web", output)
    (output / "data").mkdir(exist_ok=True)
    (output / "data/europeana.json").write_text(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")))
    (output / ".nojekyll").touch()
    (output / "robots.txt").write_text("User-agent: *\nDisallow: /\n")
    print("Built unlisted Town Heritage prototype")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-data", action="store_true")
    args = parser.parse_args()
    build(require_data=args.require_data)
