import os
import unittest

from werkzeug.security import generate_password_hash

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ADMIN_PASSWORD_HASH", generate_password_hash("primary-pass"))

from app import create_app


class PwaTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_storefront_exposes_pwa_metadata_and_install_button(self):
        response = self.client.get("/")

        try:
            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)
            self.assertIn('rel="manifest"', html)
            self.assertIn('data-pwa-install', html)
            self.assertIn('icon-192.png', html)
        finally:
            response.close()

    def test_manifest_and_root_service_worker_are_available(self):
        manifest = self.client.get("/static/manifest.webmanifest")
        service_worker = self.client.get("/service-worker.js")

        try:
            self.assertEqual(manifest.status_code, 200)
            self.assertIn('"display": "standalone"', manifest.get_data(as_text=True))
            self.assertIn('icon-512.png', manifest.get_data(as_text=True))
            self.assertEqual(service_worker.status_code, 200)
            self.assertEqual(service_worker.headers["Service-Worker-Allowed"], "/")
            self.assertIn("self.addEventListener", service_worker.get_data(as_text=True))
        finally:
            manifest.close()
            service_worker.close()


if __name__ == "__main__":
    unittest.main()
