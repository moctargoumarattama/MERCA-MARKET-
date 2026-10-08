import io
import os
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from flask import render_template_string
from werkzeug.security import generate_password_hash


# Importing app initializes its database; the import must be isolated as well.
_import_directory = tempfile.TemporaryDirectory(prefix="merca-images-import-")
with patch.dict(os.environ, {
    "DATABASE": str(Path(_import_directory.name) / "bootstrap.db"),
    "SECRET_KEY": "image-delivery-test-secret",
    "ADMIN_PASSWORD_HASH": generate_password_hash("test-password"),
}):
    from app import create_app
    from config import Config
    from models.database import get_db
    from security import limiter


def image_bytes(size=(1600, 800), image_format="PNG", color=(20, 130, 80), **options):
    output = io.BytesIO()
    mode = "RGBA" if len(color) == 4 else "RGB"
    with Image.new(mode, size, color) as image:
        image.save(output, format=image_format, **options)
    return output.getvalue()


class ImageDeliveryTests(unittest.TestCase):
    ajax_headers = {"X-Requested-With": "XMLHttpRequest"}

    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="merca-image-delivery-")
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.uploads = self.directory / "uploads"
        self.cache = self.directory / "cache"
        self.static = self.directory / "static"
        (self.static / "images").mkdir(parents=True)
        config = patch.multiple(
            Config,
            DATABASE=str(self.directory / "catalogue.db"),
            UPLOAD_FOLDER=str(self.uploads),
            SECRET_KEY="image-delivery-test-secret",
            SESSION_COOKIE_SECURE=False,
        )
        config.start()
        self.addCleanup(config.stop)
        limiter._buckets.clear()
        self.addCleanup(limiter._buckets.clear)
        self.app = create_app()
        self.app.config.update(TESTING=True, IMAGE_CACHE_FOLDER=str(self.cache))
        self.app.static_folder = str(self.static)
        self.client = self.app.test_client()
        self.original = image_bytes(size=(160, 80))
        (self.uploads / "original.png").write_bytes(self.original)
        with self.app.app_context():
            db = get_db()
            self.category_id = db.execute("SELECT id FROM categories ORDER BY id LIMIT 1").fetchone()["id"]
            self.product_id = db.execute(
                "INSERT INTO products(name, price, category_id, image) VALUES (?, ?, ?, ?)",
                ("Amande", 42, self.category_id, "original.png"),
            ).lastrowid
            db.commit()
        with self.client.session_transaction() as session:
            session["admin_logged_in"] = True
            session["ui_lang"] = "fr"
            session["_csrf_token"] = "image-test-csrf"

    def get(self, path, **kwargs):
        response = self.client.get(path, buffered=True, **kwargs)
        response.get_data()
        response.close()
        return response

    def post_image(self, path, content, filename="photo.png"):
        return self.client.post(path, data={
            "name": "Noix",
            "description": "Selection",
            "price": "15.50",
            "category_id": str(self.category_id),
            "available": "on",
            "_csrf_token": "image-test-csrf",
            "image": (io.BytesIO(content), filename),
        }, headers=self.ajax_headers)

    def products(self):
        with self.app.app_context():
            return [dict(row) for row in get_db().execute("SELECT * FROM products ORDER BY id")]

    def cache_files(self):
        return sorted(path for path in self.cache.rglob("*") if path.is_file())

    def assert_webp(self, response, size):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "image/webp")
        with Image.open(io.BytesIO(response.data)) as image:
            self.assertEqual(image.format, "WEBP")
            self.assertEqual(image.size, size)
            image.load()

    def test_existing_images_get_presets_without_modifying_originals(self):
        source = self.uploads / "large.png"
        original = image_bytes()
        source.write_bytes(original)
        original_stat = source.stat()
        expected_sizes = {
            "logo128": (128, 64),
            "hero600": (600, 300),
            "hero900": (900, 450),
            "card480": (480, 240),
            "product1200": (1200, 600),
        }
        for preset, size in expected_sizes.items():
            with self.subTest(preset=preset):
                self.assert_webp(self.get(f"/media/{preset}/large.png"), size)
        self.assertEqual(source.read_bytes(), original)
        self.assertEqual(source.stat().st_mtime_ns, original_stat.st_mtime_ns)
        self.assertEqual(len(self.cache_files()), len(expected_sizes))

    def test_small_images_are_not_enlarged_and_transparency_is_preserved(self):
        (self.uploads / "transparent.png").write_bytes(image_bytes(
            size=(64, 32), color=(200, 80, 25, 80),
        ))
        response = self.get("/media/product1200/transparent.png")
        self.assert_webp(response, (64, 32))
        with Image.open(io.BytesIO(response.data)) as image:
            self.assertIn("A", image.getbands())
            self.assertEqual(image.getextrema()[-1], (80, 80))

    def test_large_photo_becomes_smaller_and_keeps_aspect_ratio(self):
        output = io.BytesIO()
        with Image.frombytes("RGB", (1600, 800), random.Random(7).randbytes(1600 * 800 * 3)) as image:
            image.save(output, format="PNG")
        original = output.getvalue()
        (self.uploads / "photo.png").write_bytes(original)
        response = self.get("/media/hero600/photo.png")
        self.assert_webp(response, (600, 300))
        self.assertLess(len(response.data), len(original) // 4)

    def test_exif_rotation_is_applied_before_resize(self):
        exif = Image.Exif()
        exif[274] = 6
        (self.uploads / "portrait.jpg").write_bytes(image_bytes(
            size=(800, 400), image_format="JPEG", exif=exif,
        ))
        response = self.get("/media/card480/portrait.jpg")
        self.assert_webp(response, (240, 480))

    def test_cache_is_reused_and_source_change_invalidates_etag(self):
        source = self.uploads / "cache-source.bmp"
        original = image_bytes(size=(160, 80), image_format="BMP")
        source.write_bytes(original)
        stamp = 1_700_000_000_000_000_000
        os.utime(source, ns=(stamp, stamp))
        url = "/media/card480/cache-source.bmp"
        first = self.get(url)
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.headers.get("ETag"))
        self.assertTrue(first.cache_control.no_cache or first.cache_control.max_age == 0)
        files_before = {path: (path.stat().st_mtime_ns, path.read_bytes()) for path in self.cache_files()}
        self.assertEqual(len(files_before), 1)
        second = self.get(url)
        self.assertEqual(second.data, first.data)
        self.assertEqual({path: (path.stat().st_mtime_ns, path.read_bytes()) for path in self.cache_files()}, files_before)
        revalidated = self.get(url, headers={"If-None-Match": first.headers["ETag"]})
        self.assertEqual(revalidated.status_code, 304)
        self.assertEqual(revalidated.data, b"")

        old_stat = source.stat()
        changed = image_bytes(size=(160, 80), image_format="BMP", color=(230, 15, 20))
        self.assertEqual(len(changed), len(original))
        source.write_bytes(changed)
        os.utime(source, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns + 1_000_000))
        self.assertEqual(int(source.stat().st_mtime), int(old_stat.st_mtime))
        updated = self.get(url, headers={"If-None-Match": first.headers["ETag"]})
        self.assertEqual(updated.status_code, 200)
        self.assertNotEqual(updated.headers["ETag"], first.headers["ETag"])
        self.assertNotEqual(updated.data, first.data)
        self.assertEqual(source.read_bytes(), changed)

    def test_static_fallback_and_configured_upload_folder(self):
        (self.static / "images" / "brand.png").write_bytes(image_bytes(size=(256, 128)))
        self.assert_webp(self.get("/media/logo128/brand.png"), (128, 64))
        # An uploaded file with the same name takes precedence over bundled images.
        (self.uploads / "brand.png").write_bytes(image_bytes(size=(64, 128)))
        self.assert_webp(self.get("/media/logo128/brand.png"), (64, 128))

    def test_image_requests_do_not_create_sessions_or_count_visits(self):
        with self.app.app_context():
            before = [tuple(row) for row in get_db().execute("SELECT * FROM visitor_stats ORDER BY visit_date")]
        for client in (self.app.test_client(), self.client):
            with client.get("/media/logo128/original.png", buffered=True) as response:
                self.assertEqual(response.status_code, 200)
                self.assertNotIn("Set-Cookie", response.headers)
                etag = response.headers["ETag"]
            with client.get("/media/logo128/original.png", buffered=True, headers={"If-None-Match": etag}) as response:
                self.assertEqual(response.status_code, 304)
                self.assertNotIn("Set-Cookie", response.headers)
        with self.app.app_context():
            after = [tuple(row) for row in get_db().execute("SELECT * FROM visitor_stats ORDER BY visit_date")]
        self.assertEqual(after, before)

    def test_default_cache_folder_and_icon_formats(self):
        self.app.config.pop("IMAGE_CACHE_FOLDER", None)
        for preset, limit in (("icon192", 192), ("icon512", 512)):
            (self.uploads / "brand.png").write_bytes(image_bytes(size=(800, 800), color=(20, 80, 160, 90)))
            response = self.get(f"/media/{preset}/brand.png")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, "image/png")
            with Image.open(io.BytesIO(response.data)) as image:
                self.assertEqual(image.format, "PNG")
                self.assertEqual(image.size, (limit, limit))
        self.assertEqual(len(list((self.uploads / ".optimized").rglob("*.png"))), 2)

    def test_animation_is_preserved(self):
        output = io.BytesIO()
        with Image.new("RGB", (80, 40), "red") as first, Image.new("RGB", (80, 40), "blue") as second:
            first.save(output, format="GIF", save_all=True, append_images=[second], duration=100, loop=0)
        original = output.getvalue()
        (self.uploads / "animated.gif").write_bytes(original)
        response = self.get("/media/card480/animated.gif")
        self.assertEqual(response.status_code, 200)
        with Image.open(io.BytesIO(response.data)) as image:
            self.assertTrue(image.is_animated)
            self.assertEqual(image.n_frames, 2)
        self.assertEqual((self.uploads / "animated.gif").read_bytes(), original)

    def test_media_rejects_missing_unknown_and_traversal_requests(self):
        (self.directory / "outside.png").write_bytes(image_bytes(size=(20, 20)))
        hidden = self.uploads / ".optimized"
        hidden.mkdir()
        (hidden / "internal.png").write_bytes(image_bytes(size=(20, 20)))
        paths = (
            "/media/card480/missing.png",
            "/media/arbitrary/original.png",
            "/media/card480/../outside.png",
            "/media/card480/%2e%2e/outside.png",
            "/media/card480/..%5coutside.png",
            "/media/card480/.optimized/internal.png",
            "/media/card480/%2eoptimized/internal.png",
            "/media/card480/C:%5cWindows%5cwin.ini",
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.get(path).status_code, 404)

    def test_template_image_url_uses_preset_and_encodes_filename(self):
        with self.app.test_request_context():
            default = render_template_string("{{ image_url('photo.png') }}")
            card = render_template_string("{{ image_url('photo espace.png', 'card480') }}")
            base = render_template_string("{{ image_url('') }}")
        self.assertEqual(default, "/media/product1200/photo.png")
        self.assertEqual(card, "/media/card480/photo%20espace.png")
        self.assertEqual(base, "/media/product1200/")

    def test_png_upload_add_creates_derivative_and_preserves_original_bytes(self):
        original = image_bytes(color=(20, 140, 70, 100))
        response = self.post_image("/admin/products/add", original)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ok"])
        added = self.products()[-1]
        self.assertNotEqual(added["id"], self.product_id)
        self.assertTrue(added["image"].endswith(".png"))
        self.assertNotEqual(added["image"], "photo.png")
        self.assertEqual((self.uploads / added["image"]).read_bytes(), original)
        # Saving prepares the full-size derivative before an image is first requested.
        self.assertTrue(self.cache_files())
        self.assert_webp(self.get(f'/media/product1200/{added["image"]}'), (1200, 600))
        self.assertEqual((self.uploads / "original.png").read_bytes(), self.original)

    def test_jpeg_upload_edit_prepares_new_image_and_changes_existing_product(self):
        original = image_bytes(image_format="JPEG")
        response = self.post_image(f"/admin/products/edit/{self.product_id}", original, "photo.jpg")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["ok"])
        rows = self.products()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], self.product_id)
        self.assertEqual(rows[0]["name"], "Noix")
        self.assertTrue(rows[0]["image"].endswith(".jpg"))
        self.assertEqual((self.uploads / rows[0]["image"]).read_bytes(), original)
        self.assertTrue(self.cache_files())
        self.assert_webp(self.get(f'/media/product1200/{rows[0]["image"]}'), (1200, 600))

    def test_corrupt_uploads_leave_product_and_previous_image_unchanged(self):
        before = self.products()
        valid = image_bytes()
        invalid_images = (b"not an image", valid[:48], valid[:len(valid) // 2])
        for path in ("/admin/products/add", f"/admin/products/edit/{self.product_id}"):
            for content in invalid_images:
                with self.subTest(path=path, size=len(content)):
                    response = self.post_image(path, content)
                    self.assertEqual(response.status_code, 400)
                    self.assertFalse(response.get_json()["ok"])
                    self.assertEqual(self.products(), before)
                    self.assertEqual((self.uploads / "original.png").read_bytes(), self.original)
        self.assertEqual(sorted(path.name for path in self.uploads.iterdir() if path.is_file()), ["original.png"])

    def test_excessive_pixel_uploads_leave_database_and_previous_image_unchanged(self):
        before = self.products()
        content = image_bytes(size=(50, 50))
        with patch("image_processing.MAX_IMAGE_PIXELS", 1000):
            for path in ("/admin/products/add", f"/admin/products/edit/{self.product_id}"):
                with self.subTest(path=path):
                    response = self.post_image(path, content)
                    self.assertEqual(response.status_code, 400)
                    self.assertFalse(response.get_json()["ok"])
                    self.assertEqual(self.products(), before)
                    self.assertEqual((self.uploads / "original.png").read_bytes(), self.original)
        self.assertEqual(sorted(path.name for path in self.uploads.iterdir() if path.is_file()), ["original.png"])


if __name__ == "__main__":
    unittest.main()
