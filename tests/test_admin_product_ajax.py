import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from werkzeug.security import generate_password_hash


# app.py creates an application (and initializes its database) during import.
# Always isolate that initial database too, before loading the module.
_import_directory = tempfile.TemporaryDirectory(prefix="merca-product-ajax-import-")
with patch.dict(os.environ, {
    "DATABASE": str(Path(_import_directory.name) / "bootstrap.db"),
    "SECRET_KEY": "product-ajax-test-secret",
    "ADMIN_PASSWORD_HASH": generate_password_hash("test-password"),
}):
    from app import create_app
    from config import Config
    from models.database import get_db
    from security import limiter


class AdminProductAjaxTests(unittest.TestCase):
    ajax_headers = {"X-Requested-With": "XMLHttpRequest"}

    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="merca-product-ajax-")
        self.addCleanup(directory.cleanup)
        self.uploads = Path(directory.name) / "images"
        config = patch.multiple(
            Config,
            DATABASE=str(Path(directory.name) / "catalogue.db"),
            UPLOAD_FOLDER=str(self.uploads),
            SECRET_KEY="product-ajax-test-secret",
            SESSION_COOKIE_SECURE=False,
        )
        config.start()
        self.addCleanup(config.stop)
        limiter._buckets.clear()
        self.addCleanup(limiter._buckets.clear)
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.app.app_context():
            db = get_db()
            categories = db.execute("SELECT id FROM categories ORDER BY id").fetchall()
            self.category_id, self.other_category_id = [row["id"] for row in categories[:2]]
            self.product_id = db.execute(
                "INSERT INTO products(name, price, category_id, image) VALUES (?, ?, ?, ?)",
                ("Amande", 42, self.category_id, "existing.png"),
            ).lastrowid
            db.commit()
        (self.uploads / "existing.png").write_bytes(b"existing-test-image")
        with self.client.session_transaction() as session:
            session["admin_logged_in"] = True
            session["ui_lang"] = "fr"
            session["_csrf_token"] = "test-csrf"

    def form_data(self, **changes):
        data = {
            "name": "Noix",
            "description": "Selection",
            "price": "15.50",
            "category_id": str(self.category_id),
            "available": "on",
            "_csrf_token": "test-csrf",
        }
        data.update(changes)
        return data

    def post(self, path, data=None):
        return self.client.post(path, data=self.form_data() if data is None else data, headers=self.ajax_headers)

    def products(self):
        with self.app.app_context():
            return [dict(row) for row in get_db().execute("SELECT * FROM products ORDER BY id")]

    def assert_category_counts(self, payload, expected):
        self.assertEqual({category["id"]: category["product_count"] for category in payload["categories"]}, expected)
        for category in payload["categories"]:
            self.assertIn("count_label", category)
            self.assertIn("subtitle", category)
            self.assertIn("cover_image", category)

    def test_add_returns_real_id_rendered_card_and_fresh_counts(self):
        response = self.post("/admin/products/add?panel=add-product")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        added = self.products()[-1]
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["product_id"], added["id"])
        self.assertEqual(payload["product"]["id"], added["id"])
        self.assertNotEqual(added["id"], self.product_id)
        self.assertIsNone(payload["previous_category_id"])
        self.assertIn("Noix", payload["product_html"])
        self.assertIn(f'/admin/products/edit/{added["id"]}', payload["product_html"])
        self.assert_category_counts(payload, {self.category_id: 2, self.other_category_id: 0})
        self.assertEqual(payload["stats"], {"category_count": 2, "product_count": 2, "active_product_count": 2})
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_edit_moves_category_and_updates_weight_prices_without_redirect(self):
        response = self.post(f"/admin/products/edit/{self.product_id}", self.form_data(
            category_id=str(self.other_category_id), price="", available="",
            weight_label=["100 g", "200 g"], weight_price=["12,50", "22"],
        ))
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["previous_category_id"], self.category_id)
        self.assertEqual(payload["product"]["category_id"], self.other_category_id)
        self.assertEqual(payload["product"]["available"], 0)
        self.assertIn("Noix", payload["product_html"])
        self.assertIn('data-admin-edit-product-form', payload["form_html"])
        self.assertIn(f'category={self.other_category_id}', payload["form_html"])
        self.assertIn('value="100 g"', payload["form_html"])
        self.assert_category_counts(payload, {self.category_id: 0, self.other_category_id: 1})
        self.assertEqual(payload["stats"]["active_product_count"], 0)
        row = self.products()[0]
        self.assertEqual(row["price"], 12.5)
        self.assertEqual(json.loads(row["weight_options"]), [{"label": "100 g", "price": 12.5}, {"label": "200 g", "price": 22}])
        self.assertTrue((self.uploads / "existing.png").exists())

    def test_toggle_and_delete_return_updated_card_and_category_counts(self):
        path = f"/admin/products/toggle/{self.product_id}"
        first = self.post(path).get_json()
        self.assertEqual(first["product"]["available"], 0)
        self.assertEqual(first["stats"]["active_product_count"], 0)
        self.assertIn("Amande", first["product_html"])
        second = self.post(path).get_json()
        self.assertEqual(second["product"]["available"], 1)
        self.assertEqual(second["stats"]["active_product_count"], 1)
        response = self.post(f"/admin/products/delete/{self.product_id}")
        self.assertEqual(response.status_code, 200)
        deleted = response.get_json()
        self.assertIsNone(deleted["product"])
        self.assertEqual(deleted["product_id"], self.product_id)
        self.assertEqual(deleted["previous_category_id"], self.category_id)
        self.assertEqual(deleted["product_html"], "")
        self.assertEqual(deleted["stats"]["product_count"], 0)
        self.assert_category_counts(deleted, {self.category_id: 0, self.other_category_id: 0})
        self.assertFalse((self.uploads / "existing.png").exists())
        self.assertEqual(self.products(), [])

    def test_edit_get_supports_json_accept_and_keeps_csrf_and_escaping(self):
        with self.app.app_context():
            db = get_db()
            db.execute("UPDATE products SET name = ? WHERE id = ?", ('<script>alert("x")</script>', self.product_id))
            db.commit()
        response = self.client.get(f"/admin/products/edit/{self.product_id}", headers={"Accept": "application/json"})
        self.assertEqual(response.status_code, 200)
        html = response.get_json()["form_html"]
        self.assertIn('name="_csrf_token"', html)
        self.assertIn('name="category_id"', html)
        self.assertNotIn('<script>alert("x")</script>', html)
        self.assertIn("&lt;script&gt;", html)
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_invalid_add_and_edit_leave_database_and_image_unchanged(self):
        before = self.products()
        invalid_changes = (
            {"name": "  "}, {"price": "NaN"}, {"price": "-1"},
            {"category_id": ""}, {"category_id": "999999"},
            {"weight_label": ["100 g"], "weight_price": [""]},
            {"weight_label": ["100 g", "100 g"], "weight_price": ["10", "20"]},
        )
        for path in ("/admin/products/add", f"/admin/products/edit/{self.product_id}"):
            for changes in invalid_changes:
                with self.subTest(path=path, changes=changes):
                    response = self.post(path, self.form_data(**changes))
                    self.assertEqual(response.status_code, 400)
                    self.assertFalse(response.get_json()["ok"])
                    self.assertTrue(response.get_json()["error"])
                    self.assertEqual(self.products(), before)
            response = self.post(path, self.form_data(image=(io.BytesIO(b"not an image"), "photo.png")))
            self.assertEqual(response.status_code, 400)
            self.assertFalse(response.get_json()["ok"])
            self.assertEqual(self.products(), before)
        self.assertEqual([path.name for path in self.uploads.iterdir()], ["existing.png"])
        self.assertEqual((self.uploads / "existing.png").read_bytes(), b"existing-test-image")

    def test_missing_products_are_404_and_do_not_write(self):
        before = self.products()
        for action in ("edit", "toggle", "delete"):
            response = self.post(f"/admin/products/{action}/999999")
            self.assertEqual(response.status_code, 404)
            self.assertFalse(response.get_json()["ok"])
        response = self.client.get("/admin/products/edit/999999", headers=self.ajax_headers)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.products(), before)

    def test_auth_and_csrf_remain_required_for_all_product_mutations(self):
        before = self.products()
        paths = ["/admin/products/add"] + [f"/admin/products/{action}/{self.product_id}" for action in ("edit", "toggle", "delete")]
        for path in paths:
            self.assertEqual(self.post(path, self.form_data(_csrf_token="invalid")).status_code, 400)
        with self.client.session_transaction() as session:
            session.pop("admin_logged_in")
        for path in paths:
            response = self.post(path)
            self.assertEqual(response.status_code, 401)
            self.assertFalse(response.get_json()["ok"])
        response = self.client.get(f"/admin/products/edit/{self.product_id}", headers=self.ajax_headers)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.products(), before)

    def test_html_clients_keep_existing_pages_and_redirects(self):
        response = self.client.get(f"/admin/products/edit/{self.product_id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn("<!doctype html>", response.get_data(as_text=True))
        for path in ("/admin/products/add?panel=add-product", f"/admin/products/edit/{self.product_id}", f"/admin/products/toggle/{self.product_id}", f"/admin/products/delete/{self.product_id}"):
            response = self.client.post(path, data=self.form_data())
            self.assertEqual(response.status_code, 302)
            self.assertIn("/admin/?", response.headers["Location"])
        with self.client.session_transaction() as session:
            session.pop("admin_logged_in")
        response = self.client.get(f"/admin/products/edit/{self.product_id}")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/admin/login"))

    def test_rate_limit_still_blocks_product_mutation(self):
        path = f"/admin/products/toggle/{self.product_id}"
        for _ in range(20):
            self.assertEqual(self.post(path).status_code, 200)
        before = self.products()
        self.assertEqual(self.post(path).status_code, 429)
        self.assertEqual(self.products(), before)


if __name__ == "__main__":
    unittest.main()
