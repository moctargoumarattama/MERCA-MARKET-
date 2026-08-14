import sqlite3
import math
from functools import wraps
from pathlib import Path
from uuid import uuid4

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
import os
from time import time
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from security import rate_limit

from i18n import translate as t
from models.database import get_db

admin_bp = Blueprint("admin", __name__)


def verify_admin_credentials(username, password):
    username = (username or "").strip()
    password = password or ""

    if not username or not password:
        return False

    if username == current_app.config["ADMIN_USERNAME"]:
        return check_password_hash(current_app.config["ADMIN_PASSWORD_HASH"], password)

    db = get_db()
    row = db.execute(
        "SELECT password_hash FROM admin_accounts WHERE username = ? AND is_active = 1",
        (username,),
    ).fetchone()
    if row is None:
        return False

    return check_password_hash(row["password_hash"], password)


ALLOWED_ADMIN_IMAGE_FORMATS = {
    "jpeg",
    "png",
    "webp",
    "gif",
    "bmp",
    "tiff",
    "ico",
    "pbm",
    "pgm",
    "ppm",
    "rast",
    "xbm",
    "rgb",
}
ALLOWED_ADMIN_PANELS = {"overview", "catalogue", "products", "add-category", "add-product"}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin.login"))
        return view(*args, **kwargs)

    return wrapped


def _parse_stock(raw_value):
    value = (raw_value or "").strip()
    if not value:
        return None

    try:
        stock = int(value)
    except ValueError as exc:
        raise ValueError(t("validation.stock_integer")) from exc

    return max(stock, 0)


def _parse_price(raw_value):
    value = (raw_value or "").strip()

    try:
        price = float(value)
    except ValueError:
        return None

    if not math.isfinite(price) or price < 0:
        return None

    return price


def _determine_image_format(stream) -> str | None:
    header = stream.read(8192)
    stream.seek(0)

    if header.startswith(b"\xFF\xD8\xFF"):
        return "jpeg"
    if header.startswith(b"\x89PNG\r\n\x1A\n"):
        return "png"
    if header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
        return "gif"
    if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        return "webp"
    if header.startswith(b"BM"):
        return "bmp"
    if header.startswith(b"II\x2A\x00") or header.startswith(b"MM\x00\x2A"):
        return "tiff"
    if header.startswith(b"\x00\x00\x01\x00") or header.startswith(b"\x00\x00\x02\x00"):
        return "ico"
    if header.startswith(b"P1") or header.startswith(b"P2") or header.startswith(b"P3"):
        return "pbm"
    if header.startswith(b"P4") or header.startswith(b"P5") or header.startswith(b"P6"):
        return "pgm"
    if header.startswith(b"P7"):
        return "ppm"
    if header.startswith(b"NPR1"):
        return "rast"
    if header.startswith(b"#define") or header.startswith(b"#ifndef"):
        return "xbm"
    if header.startswith(b"RGB"):
        return "rgb"

    return None


def _image_extension(image_format: str) -> str:
    format_mapping = {
        "jpeg": ".jpg",
        "png": ".png",
        "webp": ".webp",
        "gif": ".gif",
        "bmp": ".bmp",
        "tiff": ".tiff",
        "ico": ".ico",
        "pbm": ".pbm",
        "pgm": ".pgm",
        "ppm": ".ppm",
        "rast": ".rast",
        "xbm": ".xbm",
        "rgb": ".rgb",
    }
    return format_mapping.get(image_format, f".{image_format}")


def _save_product_image(image, current_image=""):
    if not image or not image.filename:
        return current_image

    filename = secure_filename(image.filename)
    image_format = _determine_image_format(image.stream)

    if not image_format or image_format not in ALLOWED_ADMIN_IMAGE_FORMATS:
        raise ValueError(t("validation.image_format"))

    extension = _image_extension(image_format)
    new_image_name = f"{Path(filename).stem}-{uuid4().hex}{extension}"

    image.stream.seek(0)
    image.save(Path(current_app.config["UPLOAD_FOLDER"]) / new_image_name)

    if current_image:
        old_image_path = Path(current_app.config["UPLOAD_FOLDER"]) / current_image
        if old_image_path.exists():
            old_image_path.unlink()

    return new_image_name


def load_admin_categories(db):
    return db.execute(
        """
        SELECT
            c.id,
            c.name,
            COUNT(p.id) AS product_count,
            (
                SELECT p2.image
                FROM products p2
                WHERE p2.category_id = c.id
                  AND p2.image <> ''
                ORDER BY p2.id DESC
                LIMIT 1
            ) AS cover_image
        FROM categories c
        LEFT JOIN products p ON p.category_id = c.id
        GROUP BY c.id, c.name
        ORDER BY c.name
        """
    ).fetchall()


def load_admin_category(db, category_id):
    return db.execute(
        """
        SELECT
            c.id,
            c.name,
            COUNT(p.id) AS product_count,
            (
                SELECT p2.image
                FROM products p2
                WHERE p2.category_id = c.id
                  AND p2.image <> ''
                ORDER BY p2.id DESC
                LIMIT 1
            ) AS cover_image
        FROM categories c
        LEFT JOIN products p ON p.category_id = c.id
        WHERE c.id = ?
        GROUP BY c.id, c.name
        """,
        (category_id,),
    ).fetchone()


def load_admin_category_products(db, category_id):
    return db.execute(
        """
        SELECT p.*, c.name AS category_name
        FROM products p
        LEFT JOIN categories c ON c.id = p.category_id
        WHERE p.category_id = ?
        ORDER BY p.available DESC, p.id DESC
        """,
        (category_id,),
    ).fetchall()


def normalize_admin_panel(raw_panel):
    panel = (raw_panel or "overview").strip()
    return panel if panel in ALLOWED_ADMIN_PANELS else "overview"


@admin_bp.route("/login", methods=["GET", "POST"])
@rate_limit(limit=10, window_seconds=60)
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if verify_admin_credentials(username, password):
            # Prevent session fixation: clear existing session and create a fresh one
            preserved_lang = session.get("ui_lang")
            session.clear()
            if preserved_lang:
                session["ui_lang"] = preserved_lang
            # fresh CSRF token and admin flag
            session["_csrf_token"] = os.urandom(32).hex()
            session["admin_logged_in"] = True
            session["admin_username"] = username
            session["admin_is_primary"] = username == current_app.config["ADMIN_USERNAME"]
            session["admin_login_at"] = int(time())
            return redirect(url_for("admin.dashboard"))

        flash(t("flash.login_invalid"), "error")

    return render_template("admin/login.html")


@admin_bp.route("/admins", methods=["GET", "POST"])
@rate_limit(limit=20, window_seconds=60)
@login_required
def manage_admins():
    db = get_db()
    is_primary = bool(session.get("admin_is_primary"))
    primary_admin = current_app.config["ADMIN_USERNAME"]

    if request.method == "POST":
        if not is_primary:
            flash(t("flash.admin_access_denied"), "info")
            return redirect(url_for("admin.manage_admins"))

        action = request.form.get("action", "create").strip()

        if action == "create":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            if not username or not password:
                flash(t("flash.admin_credentials_required"), "error")
                return redirect(url_for("admin.manage_admins"))

            if username == primary_admin:
                flash(t("flash.admin_already_exists"), "error")
                return redirect(url_for("admin.manage_admins"))

            try:
                db.execute(
                    "INSERT INTO admin_accounts(username, password_hash) VALUES (?, ?)",
                    (username, generate_password_hash(password)),
                )
                db.commit()
                flash(t("flash.admin_created"), "success")
            except sqlite3.IntegrityError:
                flash(t("flash.admin_exists"), "error")

            return redirect(url_for("admin.manage_admins"))

        if action == "delete":
            target_username = request.form.get("username", "").strip()
            if not target_username:
                flash(t("flash.admin_credentials_required"), "error")
                return redirect(url_for("admin.manage_admins"))

            if target_username == primary_admin:
                flash(t("flash.admin_primary_cannot_be_deleted"), "error")
                return redirect(url_for("admin.manage_admins"))

            deleted = db.execute(
                "DELETE FROM admin_accounts WHERE username = ? AND is_active = 1",
                (target_username,),
            )
            db.commit()

            if deleted.rowcount:
                flash(t("flash.admin_deleted"), "success")
            else:
                flash(t("flash.admin_not_found"), "error")

            return redirect(url_for("admin.manage_admins"))

        if action == "update":
            target_username = request.form.get("username", "").strip()
            new_username = request.form.get("new_username", "").strip()
            password = request.form.get("password", "")

            if not target_username:
                flash(t("flash.admin_credentials_required"), "error")
                return redirect(url_for("admin.manage_admins"))

            if target_username == primary_admin:
                flash(t("flash.admin_primary_cannot_be_deleted"), "error")
                return redirect(url_for("admin.manage_admins"))

            row = db.execute(
                "SELECT username FROM admin_accounts WHERE username = ? AND is_active = 1",
                (target_username,),
            ).fetchone()
            if row is None:
                flash(t("flash.admin_not_found"), "error")
                return redirect(url_for("admin.manage_admins"))

            if not new_username:
                new_username = target_username

            if new_username == primary_admin:
                flash(t("flash.admin_already_exists"), "error")
                return redirect(url_for("admin.manage_admins"))

            if new_username and new_username != target_username:
                existing = db.execute(
                    "SELECT 1 FROM admin_accounts WHERE username = ? AND username != ? AND is_active = 1",
                    (new_username, target_username),
                ).fetchone()
                if existing:
                    flash(t("flash.admin_exists"), "error")
                    return redirect(url_for("admin.manage_admins"))

            if password:
                db.execute(
                    "UPDATE admin_accounts SET username = ?, password_hash = ? WHERE username = ? AND is_active = 1",
                    (new_username, generate_password_hash(password), target_username),
                )
            else:
                db.execute(
                    "UPDATE admin_accounts SET username = ? WHERE username = ? AND is_active = 1",
                    (new_username, target_username),
                )

            db.commit()
            flash(t("flash.admin_updated"), "success")
            return redirect(url_for("admin.manage_admins"))

    secondary_admins = db.execute(
        "SELECT username FROM admin_accounts WHERE is_active = 1 ORDER BY username"
    ).fetchall()

    if not is_primary:
        flash(t("flash.admin_access_denied"), "info")

    return render_template(
        "admin/admins.html",
        primary_admin=primary_admin,
        secondary_admins=secondary_admins,
        can_manage_admins=is_primary,
    )


@admin_bp.route("/logout", methods=["POST"])
@rate_limit(limit=20, window_seconds=60)
@login_required
def logout():
    session.clear()
    return redirect(url_for("admin.login"))


@admin_bp.route("/")
@login_required
def dashboard():
    db = get_db()
    panel = normalize_admin_panel(request.args.get("panel"))
    if panel == "add-category":
        panel = "catalogue"
    selected_category_id = request.args.get("category", type=int)
    categories = load_admin_categories(db)

    if selected_category_id is not None:
        session["admin_selected_category_id"] = selected_category_id

    selected_category = load_admin_category(db, selected_category_id) if selected_category_id else None

    category_products = load_admin_category_products(db, selected_category_id) if selected_category_id else []
    stats = db.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM categories) AS category_count,
            (SELECT COUNT(*) FROM products) AS product_count,
            (SELECT COUNT(*) FROM products WHERE available = 1) AS active_product_count,
            (SELECT COUNT(*) FROM products WHERE available = 1 AND stock = 0) AS sold_out_count
        """
    ).fetchone()
    today = db.execute(
        "SELECT visitor_count FROM visitor_stats WHERE visit_date = date('now')"
    ).fetchone()
    daily_visits = db.execute(
        """
        SELECT visit_date, visitor_count
        FROM visitor_stats
        WHERE visit_date >= date('now', '-6 days')
        ORDER BY visit_date ASC
        """
    ).fetchall()

    return render_template(
        "admin/dashboard.html",
        categories=categories,
        selected_category=selected_category,
        category_products=category_products,
        selected_category_id=selected_category_id,
        panel=panel,
        stats=stats,
        today_visitor_count=(today["visitor_count"] if today else 0),
        daily_visits=daily_visits,
    )


@admin_bp.route("/categories/add", methods=["POST"])
@rate_limit(limit=20, window_seconds=60)
@login_required
def add_category():
    name = request.form.get("name", "").strip()
    panel = normalize_admin_panel(request.args.get("panel"))

    if not name:
        flash(t("flash.category_name_required"), "error")
        return redirect(url_for("admin.dashboard", panel=panel))

    db = get_db()
    try:
        db.execute("INSERT INTO categories(name) VALUES (?)", (name,))
        db.commit()
        flash(t("flash.category_added"), "success")
    except sqlite3.IntegrityError:
        flash(t("flash.category_exists"), "error")

    return redirect(url_for("admin.dashboard", panel="catalogue"))


@admin_bp.route("/categories/edit/<int:category_id>", methods=["GET", "POST"])
@rate_limit(limit=20, window_seconds=60)
@login_required
def edit_category(category_id):
    db = get_db()
    category = db.execute(
        """
        SELECT c.id, c.name, COUNT(p.id) AS product_count
        FROM categories c
        LEFT JOIN products p ON p.category_id = c.id
        WHERE c.id = ?
        GROUP BY c.id, c.name
        """,
        (category_id,),
    ).fetchone()

    if category is None:
        flash(t("flash.category_not_found"), "error")
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()

        if not name:
            flash(t("flash.category_name_required"), "error")
            return redirect(url_for("admin.edit_category", category_id=category_id))

        try:
            db.execute("UPDATE categories SET name = ? WHERE id = ?", (name, category_id))
            db.commit()
            flash(t("flash.category_updated"), "success")
            return redirect(url_for("admin.dashboard", panel="catalogue"))
        except sqlite3.IntegrityError:
            flash(t("flash.category_exists"), "error")

    return render_template("admin/edit_category.html", category=category)


@admin_bp.route("/categories/delete/<int:category_id>", methods=["POST"])
@rate_limit(limit=20, window_seconds=60)
@login_required
def delete_category(category_id):
    db = get_db()
    category = db.execute("SELECT id FROM categories WHERE id = ?", (category_id,)).fetchone()
    if category is None:
        flash(t("flash.category_not_found"), "error")
        return redirect(url_for("admin.dashboard", panel="catalogue"))

    fallback_category = db.execute(
        "SELECT id FROM categories WHERE id != ? ORDER BY id LIMIT 1",
        (category_id,),
    ).fetchone()

    if fallback_category is None:
        product_count = db.execute("SELECT COUNT(*) FROM products WHERE category_id = ?", (category_id,)).fetchone()[0]
        if product_count:
            flash(t("flash.category_delete_requires_reassignment"), "error")
            return redirect(url_for("admin.dashboard", panel="catalogue"))

    if fallback_category is not None:
        db.execute(
            "UPDATE products SET category_id = ? WHERE category_id = ?",
            (fallback_category["id"], category_id),
        )

    db.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    db.commit()
    flash(t("flash.category_deleted"), "success")
    return redirect(url_for("admin.dashboard", panel="catalogue"))


@admin_bp.route("/products/add", methods=["POST"])
@rate_limit(limit=20, window_seconds=60)
@login_required
def add_product():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    price = _parse_price(request.form.get("price", ""))
    category_id = request.form.get("category_id", type=int)
    available = 1 if request.form.get("available") else 0
    stock_raw = request.form.get("stock", "")
    panel = normalize_admin_panel(request.args.get("panel"))

    if not name or price is None or price < 0:
        flash(t("flash.product_name_price_required"), "error")
        return redirect(url_for("admin.dashboard", panel=panel))

    if category_id is None:
        flash(t("flash.product_category_required"), "error")
        return redirect(url_for("admin.dashboard", panel=panel))

    db = get_db()
    category = db.execute("SELECT 1 FROM categories WHERE id = ?", (category_id,)).fetchone()
    if category is None:
        flash(t("flash.product_category_required"), "error")
        return redirect(url_for("admin.dashboard", panel=panel))

    try:
        stock = _parse_stock(stock_raw)
        image_name = _save_product_image(request.files.get("image"))
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("admin.dashboard", panel=panel))

    db.execute(
        """
        INSERT INTO products(name, description, price, image, category_id, available, stock)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (name, description, price, image_name, category_id, available, stock),
    )
    db.commit()

    flash(t("flash.product_added"), "success")
    return redirect(url_for("admin.dashboard", panel="add-product"))


@admin_bp.route("/products/edit/<int:product_id>", methods=["GET", "POST"])
@rate_limit(limit=20, window_seconds=60)
@login_required
def edit_product(product_id):
    db = get_db()
    product = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if product is None:
        flash(t("flash.product_not_found"), "error")
        return redirect(url_for("admin.dashboard"))

    categories = db.execute("SELECT * FROM categories ORDER BY name").fetchall()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        price = _parse_price(request.form.get("price", ""))
        category_id = request.form.get("category_id", type=int)
        available = 1 if request.form.get("available") else 0
        stock_raw = request.form.get("stock", "")
        image_name = product["image"]

        if not name or price is None or price < 0:
            flash(t("flash.product_name_price_required"), "error")
            return redirect(url_for("admin.edit_product", product_id=product_id))

        if category_id is None:
            flash(t("flash.product_category_required"), "error")
            return redirect(url_for("admin.edit_product", product_id=product_id))

        category = db.execute("SELECT 1 FROM categories WHERE id = ?", (category_id,)).fetchone()
        if category is None:
            flash(t("flash.product_category_required"), "error")
            return redirect(url_for("admin.edit_product", product_id=product_id))

        try:
            stock = _parse_stock(stock_raw)
            image_name = _save_product_image(request.files.get("image"), image_name)
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("admin.edit_product", product_id=product_id))

        db.execute(
            """
            UPDATE products
            SET name = ?, description = ?, price = ?, image = ?, category_id = ?, available = ?, stock = ?
            WHERE id = ?
            """,
            (name, description, price, image_name, category_id, available, stock, product_id),
        )
        db.commit()

        flash(t("flash.product_updated"), "success")
        return redirect(url_for("admin.dashboard", panel="products", category=category_id or product["category_id"]))

    return render_template("admin/edit_product.html", product=product, categories=categories)


@admin_bp.route("/products/delete/<int:product_id>", methods=["POST"])
@rate_limit(limit=20, window_seconds=60)
@login_required
def delete_product(product_id):
    db = get_db()
    row = db.execute("SELECT image FROM products WHERE id = ?", (product_id,)).fetchone()

    if row and row["image"]:
        image_path = Path(current_app.config["UPLOAD_FOLDER"]) / row["image"]
        if image_path.exists():
            image_path.unlink()

    db.execute("DELETE FROM products WHERE id = ?", (product_id,))
    db.commit()

    flash(t("flash.product_deleted"), "success")
    return redirect(url_for("admin.dashboard", panel="products"))


@admin_bp.route("/products/toggle/<int:product_id>", methods=["POST"])
@rate_limit(limit=20, window_seconds=60)
@login_required
def toggle_product(product_id):
    db = get_db()
    db.execute(
        """
        UPDATE products
        SET available = CASE available WHEN 1 THEN 0 ELSE 1 END
        WHERE id = ?
        """,
        (product_id,),
    )
    db.commit()
    return redirect(url_for("admin.dashboard", panel="products"))
