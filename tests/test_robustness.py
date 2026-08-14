import os
import tempfile
import unittest
import json
from datetime import date

from werkzeug.security import generate_password_hash

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ADMIN_USERNAME", "primary@example.com")
os.environ.setdefault("ADMIN_PASSWORD_HASH", generate_password_hash("primary-pass"))

from app import create_app
from models.database import get_db, init_db
from security import RateLimiter


class RobustnessTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["DATABASE"] = os.path.join(tempfile.mkdtemp(), "test_robustness.db")
        self.app.config["ADMIN_USERNAME"] = "primary@example.com"
        self.app.config["ADMIN_PASSWORD_HASH"] = generate_password_hash("primary-pass")

        with self.app.app_context():
            init_db()
            database = get_db()
            category = database.execute(
                "INSERT INTO categories(name) VALUES (?)",
                ("Epicerie",),
            )
            product = database.execute(
                "INSERT INTO products(name, price, category_id) VALUES (?, ?, ?)",
                ("Amande", 42.0, category.lastrowid),
            )
            self.category_id = category.lastrowid
            self.product_id = product.lastrowid
            database.execute(
                "INSERT INTO admin_accounts(username, password_hash) VALUES (?, ?)",
                ("secondary@example.com", generate_password_hash("secondary-pass")),
            )
            database.commit()

        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session["admin_logged_in"] = True
            session["admin_is_primary"] = True
            session["admin_username"] = "primary@example.com"
            session["_csrf_token"] = "test-csrf-token"

    def test_public_search_accepts_normal_and_punctuation_queries(self):
        normal_search = self.client.get("/api/search", query_string={"q": "amande"})
        punctuation_search = self.client.get("/api/search", query_string={"q": "!!"})

        self.assertEqual(normal_search.status_code, 200)
        self.assertEqual(punctuation_search.status_code, 200)
        self.assertEqual(normal_search.get_json()["products"][0]["name"], "Amande")
        self.assertEqual(punctuation_search.get_json()["products"], [])

    def test_product_creation_rejects_unknown_category_and_non_finite_price(self):
        unknown_category = self.client.post(
            "/admin/products/add?panel=add-product",
            data={
                "name": "Produit invalide",
                "price": "12",
                "category_id": "999999",
                "_csrf_token": "test-csrf-token",
            },
            follow_redirects=True,
        )
        non_finite_price = self.client.post(
            "/admin/products/add?panel=add-product",
            data={
                "name": "Produit non fini",
                "price": "nan",
                "category_id": str(self.category_id),
                "_csrf_token": "test-csrf-token",
            },
            follow_redirects=True,
        )

        self.assertEqual(unknown_category.status_code, 200)
        self.assertEqual(non_finite_price.status_code, 200)

        with self.app.app_context():
            database = get_db()
            invalid_product_count = database.execute(
                "SELECT COUNT(*) FROM products WHERE name IN (?, ?)",
                ("Produit invalide", "Produit non fini"),
            ).fetchone()[0]
            self.assertEqual(invalid_product_count, 0)

    def test_secondary_admin_cannot_take_primary_username(self):
        response = self.client.post(
            "/admin/admins",
            data={
                "action": "update",
                "username": "secondary@example.com",
                "new_username": "primary@example.com",
                "_csrf_token": "test-csrf-token",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Le compte principal est deja utilise", response.get_data(as_text=True))

        with self.app.app_context():
            database = get_db()
            account = database.execute(
                "SELECT username FROM admin_accounts WHERE username = ?",
                ("secondary@example.com",),
            ).fetchone()
            self.assertIsNotNone(account)

    def test_checkout_uses_the_server_price_instead_of_browser_data(self):
        response = self.client.post(
            "/api/checkout",
            data={
                "items": json.dumps([
                    {"id": self.product_id, "quantity": 2, "price": 0.01, "name": "Prix falsifie"}
                ]),
                "_csrf_token": "test-csrf-token",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["items"], [{"name": "Amande", "price": 42.0, "quantity": 2}])
        self.assertEqual(payload["total"], 84.0)

    def test_rate_limiter_uses_remote_address_not_forwarded_header(self):
        limiter = RateLimiter()

        with self.app.test_request_context(
            "/api/search",
            environ_base={"REMOTE_ADDR": "198.51.100.22"},
            headers={"X-Forwarded-For": "203.0.113.99"},
        ):
            self.assertEqual(limiter._client_key(), "198.51.100.22:public.api_search")

    def test_first_public_visit_creates_a_daily_counter(self):
        self.client.get("/")

        with self.app.app_context():
            database = get_db()
            visitor_count = database.execute(
                "SELECT visitor_count FROM visitor_stats WHERE visit_date = ?",
                (date.today().isoformat(),),
            ).fetchone()[0]
            self.assertEqual(visitor_count, 1)


if __name__ == "__main__":
    unittest.main()
