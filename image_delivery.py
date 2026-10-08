"""Serve cached image derivatives without changing their original files."""
from hashlib import sha256
from pathlib import Path, PurePosixPath
from threading import Lock

from flask import Blueprint, abort, current_app, send_file, url_for
from image_processing import AnimatedImageError, InvalidImageError, optimize_image

media_bp = Blueprint("media", __name__)
PRESETS = {
    "logo128": (128, "WEBP"), "hero600": (600, "WEBP"),
    "hero900": (900, "WEBP"), "card480": (480, "WEBP"),
    "product1200": (1200, "WEBP"),
    "icon192": (192, "PNG"), "icon512": (512, "PNG"),
}
_CACHE_REVISION = "1"
_locks = [Lock() for _ in range(16)]


def image_url(filename, preset="product1200"):
    if preset not in PRESETS:
        raise ValueError("Unknown image preset")
    if not filename:
        return url_for("media.image", preset=preset, filename="__filename__").removesuffix("__filename__")
    return url_for("media.image", preset=preset, filename=filename)


def source_image_path(filename):
    relative = PurePosixPath(filename)
    if (not filename or "\\" in filename or ":" in filename or relative.is_absolute()
            or any(part.startswith(".") for part in relative.parts)):
        raise FileNotFoundError(filename)
    roots = [Path(current_app.config["UPLOAD_FOLDER"])]
    if current_app.static_folder:
        roots.append(Path(current_app.static_folder) / "images")
    for root in roots:
        root = root.resolve()
        source = (root / str(relative)).resolve()
        if source.is_relative_to(root) and source.is_file():
            return source
    raise FileNotFoundError(filename)


def optimized_image_path(filename, preset="product1200"):
    if preset not in PRESETS:
        raise FileNotFoundError(preset)
    source = source_image_path(filename)
    stat = source.stat()
    identity = f"{source}:{stat.st_size}:{stat.st_mtime_ns}:{preset}:{_CACHE_REVISION}"
    digest = sha256(identity.encode("utf-8")).hexdigest()
    width, output_format = PRESETS[preset]
    cache = Path(current_app.config.get("IMAGE_CACHE_FOLDER") or Path(current_app.config["UPLOAD_FOLDER"]) / ".optimized")
    target = cache / f"{digest}.{output_format.lower()}"
    with _locks[int(digest[:2], 16) % len(_locks)]:
        if not target.is_file():
            try:
                optimize_image(source, target, width=width, output_format=output_format)
            except AnimatedImageError:
                return source
    return target


@media_bp.get("/media/<preset>/<path:filename>")
def image(preset, filename):
    try:
        optimized = optimized_image_path(filename, preset)
    except (FileNotFoundError, InvalidImageError):
        abort(404)
    except OSError:
        current_app.logger.exception("Unable to generate image derivative: %s", filename)
        try:
            optimized = source_image_path(filename)
        except FileNotFoundError:
            abort(404)
    mimetype = {".webp": "image/webp", ".png": "image/png", ".gif": "image/gif",
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}.get(optimized.suffix.lower())
    response = send_file(optimized, mimetype=mimetype, conditional=True, max_age=0)
    response.headers["Cache-Control"] = "public, max-age=0, must-revalidate"
    return response
