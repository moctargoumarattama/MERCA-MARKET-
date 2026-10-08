"""Create bounded image derivatives without modifying their source files.

This module has no Flask or database side effects. Animated images are explicitly
reported to callers so that they can keep serving the original animation.
"""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError


MAX_IMAGE_PIXELS = 40_000_000
SUPPORTED_SOURCE_FORMATS = frozenset({
    "JPEG", "PNG", "WEBP", "GIF", "BMP", "TIFF", "ICO", "PPM", "SUN", "XBM", "SGI",
})


class ImageProcessingError(ValueError):
    """The image cannot safely be converted to a derivative."""


class InvalidImageError(ImageProcessingError):
    """The input is unsupported, damaged or exceeds the pixel limit."""


class AnimatedImageError(ImageProcessingError):
    """Serve the original animation instead of silently extracting one frame."""


def optimize_image(
    source: Path,
    target: Path,
    *,
    width: int,
    output_format: str = "WEBP",
) -> dict:
    """Write an optimized derivative and return dimensions and byte counts.

    ``width`` bounds both edges, preserving the aspect ratio and never enlarging
    the source. WEBP uses quality 82; PNG remains lossless. EXIF orientation is
    applied before resizing, alpha is kept, and EXIF metadata is removed. Writes
    are atomic, including when an existing derivative is being replaced.

    Animated sources raise ``AnimatedImageError`` after their format, dimensions
    and first frame are checked. Encoding and write errors remain ``OSError`` so
    callers can distinguish a storage failure from invalid input.
    """
    source = Path(source)
    target = Path(target)
    if not isinstance(width, int) or isinstance(width, bool) or not 1 <= width <= 4096:
        raise ValueError("Image width must be an integer between 1 and 4096.")
    output_format = output_format.upper()
    if output_format not in {"WEBP", "PNG"}:
        raise ValueError("Only WEBP and PNG derivatives are supported.")
    if source.resolve() == target.resolve():
        raise ValueError("The derivative must not overwrite its original image.")

    source_bytes = source.stat().st_size
    normalized = None
    icc_profile = None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(source) as original:
                if original.format not in SUPPORTED_SOURCE_FORMATS:
                    raise InvalidImageError("Unsupported image format.")
                if original.width * original.height > MAX_IMAGE_PIXELS:
                    raise InvalidImageError("Image dimensions exceed the 40 megapixel limit.")
                original.load()
                if getattr(original, "is_animated", False):
                    raise AnimatedImageError("Animated images must keep their original file.")
                profile = original.info.get("icc_profile")
                if original.mode in {"RGB", "RGBA", "P"} and isinstance(profile, bytes):
                    if len(profile) <= 1_048_576:
                        icc_profile = profile
                ImageOps.exif_transpose(original, in_place=True)
                has_alpha = "A" in original.getbands() or "transparency" in original.info
                # Palette and color-key transparency need conversion before
                # filtering, otherwise their transparent edges become opaque.
                if original.mode == "P" or "transparency" in original.info:
                    normalized = original.convert("RGBA" if has_alpha else "RGB")
                    normalized.thumbnail((width, width), Image.Resampling.LANCZOS, reducing_gap=3.0)
                else:
                    original.thumbnail((width, width), Image.Resampling.LANCZOS, reducing_gap=3.0)
                    normalized = original.convert("RGBA" if has_alpha else "RGB")
        normalized.info.clear()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        if normalized is not None:
            normalized.close()
        raise InvalidImageError("Image dimensions exceed the safe pixel limit.") from exc
    except (UnidentifiedImageError, OSError, SyntaxError, EOFError) as exc:
        if normalized is not None:
            normalized.close()
        raise InvalidImageError("The image is damaged or cannot be decoded.") from exc

    temporary_path = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            prefix=f".{target.name}.", suffix=".tmp", dir=target.parent, delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
        save_options = {"icc_profile": icc_profile} if icc_profile else {}
        if output_format == "WEBP":
            save_options.update(quality=82, method=6)
        else:
            save_options.update(optimize=True)
        normalized.save(temporary_path, format=output_format, **save_options)
        output_bytes = temporary_path.stat().st_size
        os.replace(temporary_path, target)
        return {
            "width": normalized.width,
            "height": normalized.height,
            "format": output_format,
            "source_bytes": source_bytes,
            "output_bytes": output_bytes,
        }
    finally:
        normalized.close()
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
