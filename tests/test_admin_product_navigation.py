import os
import tempfile
import unittest

from werkzeug.security import generate_password_hash

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ADMIN_USERNAME", "primary@example.com")
os.environ.setdefault("ADMIN_PASSWORD_HASH", generate_password_hash("primary-pass"))

from app import create_app
from models.database import get_db, init_db


class AdminProductNavigationTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["DATABASE"] = os.path.join(tempfile.mkdtemp(), "test_admin_products.db")
        self.app.config["ADMIN_USERNAME"] = "primary@example.com"
        self.app.config["ADMIN_PASSWORD_HASH"] = generate_password_hash("primary-pass")

        with self.app.app_context():
            init_db()
            database = get_db()
            category = database.execute(
                "INSERT INTO categories(name) VALUES (?)",
                ("Epicerie",),
            )
            database.execute(
                "INSERT INTO products(name, price, category_id) VALUES (?, ?, ?)",
                ("Amande", 42.0, category.lastrowid),
            )
            database.commit()
            self.category_id = category.lastrowid

        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["admin_logged_in"] = True
            session["admin_is_primary"] = True
            session["admin_username"] = "primary@example.com"

    def test_products_panel_shows_category_chooser_before_products(self):
        response = self.client.get("/admin/?panel=products")

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Choisir une categorie", html)
        self.assertIn("Epicerie", html)
        self.assertNotIn("Amande", html)
        self.assertIn("data-admin-realtime-search", html)

    def test_selected_category_shows_products_with_realtime_filter(self):
        response = self.client.get(f"/admin/?panel=products&category={self.category_id}")

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Amande", html)
        self.assertIn("data-admin-filter-item", html)
        self.assertIn("Rechercher un produit dans ce rayon", html)


if __name__ == "__main__":
    unittest.main()
