"""Warm the image cache without opening or modifying the shop database."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from flask import Flask
from image_delivery import optimized_image_path
from image_processing import InvalidImageError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=ROOT / "static" / "images")
    parser.add_argument("--cache-dir", type=Path)
    args = parser.parse_args()
    folder = args.directory.resolve()
    app = Flask(__name__, static_folder=None)
    app.config.update(UPLOAD_FOLDER=str(folder), IMAGE_CACHE_FOLDER=args.cache_dir)
    special = {"LOGO.png": ["logo128"], "3.png": ["hero600", "hero900"],
               "icon-192.png": ["icon192"], "icon-512.png": ["icon512"]}
    processed = skipped = 0
    with app.app_context():
        for source in sorted(folder.rglob("*")):
            relative = source.relative_to(folder)
            if (not source.is_file() or any(part.startswith(".") for part in relative.parts)
                    or source.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".ico", ".ppm", ".pgm", ".pbm"}):
                continue
            try:
                for preset in ["card480", "product1200", *special.get(source.name, [])]:
                    target = optimized_image_path(relative.as_posix(), preset)
                    if preset in special.get(source.name, []):
                        print(f"{source.name} ({preset}): {source.stat().st_size:,} -> {target.stat().st_size:,} bytes")
                processed += 1
            except (InvalidImageError, FileNotFoundError) as exc:
                skipped += 1
                print(f"Skipped {relative}: {exc}")
    print(f"{processed} images prepared; {skipped} skipped. Original files unchanged.")


if __name__ == "__main__":
    main()
