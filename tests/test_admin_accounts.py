import os
import tempfile
import unittest

from werkzeug.security import check_password_hash, generate_password_hash

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ADMIN_USERNAME", "primary@example.com")
os.environ.setdefault("ADMIN_PASSWORD_HASH", generate_password_hash("primary-pass"))

from app import create_app
from models.database import get_db, init_db


class AdminAccountsManagementTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["DATABASE"] = os.path.join(tempfile.mkdtemp(), "test_admin_accounts.db")
        self.app.config["ADMIN_USERNAME"] = "primary@example.com"
        self.app.config["ADMIN_PASSWORD_HASH"] = generate_password_hash("primary-pass")

        with self.app.app_context():
            init_db()
            db = get_db()
            db.execute(
                "INSERT INTO admin_accounts(username, password_hash) VALUES (?, ?)",
                ("secondary@example.com", generate_password_hash("secondary-pass")),
            )
            db.commit()

        self.client = self.app.test_client()

    def login_primary(self):
        with self.client.session_transaction() as session:
            session["admin_logged_in"] = True
            session["admin_is_primary"] = True
            session["admin_username"] = "primary@example.com"
            session["_csrf_token"] = "test-csrf-token"

    def test_manage_admins_lists_all_accounts(self):
        self.login_primary()

        response = self.client.get("/admin/admins")

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("primary@example.com", html)
        self.assertIn("secondary@example.com", html)

    def test_primary_account_cannot_be_deleted(self):
        self.login_primary()

        response = self.client.post(
            "/admin/admins",
            data={"action": "delete", "username": "primary@example.com", "_csrf_token": "test-csrf-token"},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Le compte principal ne peut pas etre supprime", response.get_data(as_text=True))

    def test_secondary_account_can_be_deleted(self):
        self.login_primary()

        response = self.client.post(
            "/admin/admins",
            data={"action": "delete", "username": "secondary@example.com", "_csrf_token": "test-csrf-token"},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Compte supprime", response.get_data(as_text=True))

        with self.app.app_context():
            db = get_db()
            row = db.execute(
                "SELECT COUNT(*) FROM admin_accounts WHERE username = ?",
                ("secondary@example.com",),
            ).fetchone()
            self.assertEqual(row[0], 0)

    def test_secondary_account_can_be_updated(self):
        self.login_primary()

        response = self.client.post(
            "/admin/admins",
            data={
                "action": "update",
                "username": "secondary@example.com",
                "new_username": "secondary-updated@example.com",
                "password": "new-secret",
                "_csrf_token": "test-csrf-token",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Compte modifie", response.get_data(as_text=True))

        with self.app.app_context():
            db = get_db()
            row = db.execute(
                "SELECT username, password_hash FROM admin_accounts WHERE username = ?",
                ("secondary-updated@example.com",),
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertTrue(check_password_hash(row["password_hash"], "new-secret"))


if __name__ == "__main__":
    unittest.main()
