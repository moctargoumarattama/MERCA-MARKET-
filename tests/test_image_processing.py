import hashlib
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, features

import image_processing
from image_processing import AnimatedImageError, InvalidImageError, optimize_image


class ImageProcessingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def source(self, size=(1600, 900), mode="RGB", color=(32, 110, 70), suffix=".png"):
        path = self.root / ("source" + suffix)
        with Image.new(mode, size, color) as image:
            image.save(path)
        return path

    def test_bounds_size_and_compresses_without_changing_original(self):
        source = self.source()
        digest = hashlib.sha256(source.read_bytes()).digest()
        target = self.root / "derived" / "photo.webp"
        result = optimize_image(source, target, width=600)
        with Image.open(target) as image:
            self.assertEqual(image.format, "WEBP")
            self.assertEqual(image.size, (600, 338))
        self.assertEqual(result["width"], 600)
        self.assertEqual(result["height"], 338)
        self.assertEqual(result["output_bytes"], target.stat().st_size)
        self.assertLess(result["output_bytes"], result["source_bytes"])
        self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), digest)

    def test_portrait_is_bounded_and_small_images_are_not_enlarged(self):
        source = self.source(size=(100, 300))
        target = self.root / "portrait.webp"
        optimize_image(source, target, width=120)
        with Image.open(target) as image:
            self.assertEqual(image.size, (40, 120))
        optimize_image(source, target, width=1200)
        with Image.open(target) as image:
            self.assertEqual(image.size, (100, 300))

    def test_exif_orientation_is_applied_and_removed(self):
        source = self.root / "rotated.jpg"
        with Image.new("RGB", (100, 200), "green") as image:
            exif = image.getexif()
            exif[274] = 6
            image.save(source, exif=exif)
        target = self.root / "upright.webp"
        optimize_image(source, target, width=100)
        with Image.open(target) as image:
            self.assertEqual(image.size, (100, 50))
            self.assertNotIn(274, image.getexif())

    def test_transparency_survives_webp_and_png_conversion(self):
        source = self.source(size=(20, 20), mode="RGBA", color=(200, 30, 20, 0))
        for output_format in ("WEBP", "PNG"):
            with self.subTest(output_format=output_format):
                target = self.root / ("alpha." + output_format.lower())
                optimize_image(source, target, width=128, output_format=output_format)
                with Image.open(target) as image:
                    self.assertEqual(image.size, (20, 20))
                    self.assertEqual(image.convert("RGBA").getpixel((10, 10))[3], 0)

    def test_palette_transparency_survives_conversion(self):
        source = self.root / "palette.png"
        with Image.new("P", (20, 20), 0) as image:
            image.putpalette([255, 0, 0] + [0] * 765)
            image.save(source, transparency=0)
        target = self.root / "palette.webp"
        optimize_image(source, target, width=128)
        with Image.open(target) as image:
            self.assertEqual(image.convert("RGBA").getpixel((10, 10))[3], 0)

    def test_color_key_transparency_is_applied_before_resizing(self):
        source = self.root / "color-key.png"
        with Image.new("RGB", (200, 100), "white") as image:
            image.paste("red", (100, 0, 200, 100))
            image.save(source, transparency=(255, 255, 255))
        target = self.root / "color-key.webp"
        optimize_image(source, target, width=100)
        with Image.open(target) as image:
            alpha = image.convert("RGBA").getchannel("A")
            self.assertEqual(alpha.getpixel((10, 10)), 0)
            self.assertTrue(any(0 < alpha.getpixel((x, 10)) < 255 for x in range(45, 55)))

    def test_animated_sources_are_explicitly_preserved(self):
        formats = ["GIF"]
        if features.check("webp"):
            formats.append("WEBP")
        for image_format in formats:
            with self.subTest(image_format=image_format):
                source = self.root / ("animated." + image_format.lower())
                frames = [Image.new("RGB", (10, 10), color) for color in ("red", "blue")]
                try:
                    frames[0].save(source, save_all=True, append_images=frames[1:], duration=100, loop=0)
                finally:
                    for frame in frames:
                        frame.close()
                digest = hashlib.sha256(source.read_bytes()).digest()
                target = self.root / "animation.webp"
                with self.assertRaises(AnimatedImageError):
                    optimize_image(source, target, width=128)
                self.assertFalse(target.exists())
                self.assertEqual(hashlib.sha256(source.read_bytes()).digest(), digest)

    def test_corrupt_and_oversized_images_are_rejected(self):
        corrupt = self.root / "broken.png"
        corrupt.write_bytes(b"this is not an image")
        target = self.root / "broken.webp"
        with self.assertRaises(InvalidImageError):
            optimize_image(corrupt, target, width=128)
        source = self.source(size=(20, 20))
        with patch.object(image_processing, "MAX_IMAGE_PIXELS", 100):
            with self.assertRaises(InvalidImageError):
                optimize_image(source, target, width=128)
        self.assertFalse(target.exists())

    def test_failed_encode_preserves_existing_derivative_and_cleans_temporary_file(self):
        source = self.source(size=(10, 10))
        target = self.root / "existing.webp"
        target.write_bytes(b"previous derivative")

        def fail_save(image, filename, *args, **kwargs):
            Path(filename).write_bytes(b"partial data")
            raise OSError("disk full")

        with patch.object(Image.Image, "save", fail_save):
            with self.assertRaises(OSError):
                optimize_image(source, target, width=128)
        self.assertEqual(target.read_bytes(), b"previous derivative")
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["existing.webp", "source.png"])

    def test_original_cannot_be_used_as_target(self):
        source = self.source(size=(10, 10))
        before = source.read_bytes()
        with self.assertRaises(ValueError):
            optimize_image(source, source, width=128)
        self.assertEqual(source.read_bytes(), before)

    def test_previously_supported_upload_formats_still_convert(self):
        cases = [
            ("ICO", ".ico", "RGB"),
            ("PPM", ".ppm", "RGB"),
            ("PPM", ".pgm", "L"),
            ("PPM", ".pbm", "1"),
            ("XBM", ".xbm", "1"),
            ("SGI", ".rgb", "RGB"),
            ("SUN", ".rast", "L"),
        ]
        for source_format, suffix, mode in cases:
            with self.subTest(source_format=source_format, suffix=suffix):
                source = self.root / ("legacy" + suffix)
                if source_format == "SUN":
                    # Pillow reads SUN raster files but does not write them.
                    header = struct.pack(">8I", 0x59A66A95, 16, 16, 8, 256, 1, 0, 0)
                    source.write_bytes(header + bytes([90]) * 256)
                else:
                    with Image.new(mode, (16, 16), 1) as image:
                        image.save(source, format=source_format)
                target = self.root / (source.name + ".webp")
                optimize_image(source, target, width=128)
                with Image.open(target) as converted:
                    self.assertEqual(converted.format, "WEBP")
                    self.assertEqual(converted.size, (16, 16))


if __name__ == "__main__":
    unittest.main()
