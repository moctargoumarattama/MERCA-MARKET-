import json
import math
import re

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, send_from_directory, session, url_for

from i18n import normalize_language, safe_redirect_target, set_locale
from models.database import get_db
from security import rate_limit

public_bp = Blueprint("public", __name__)


@public_bp.route("/service-worker.js")
def service_worker():
    response = send_from_directory(current_app.static_folder, "js/service-worker.js")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response


def normalize_search_terms(value):
    return " ".join(re.findall(r"\w+", str(value or ""), flags=re.UNICODE)).strip()


def load_categories(db):
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
                  AND p2.available = 1
                  AND p2.image <> ''
                ORDER BY p2.id DESC
                LIMIT 1
            ) AS cover_image
        FROM categories c
        LEFT JOIN products p ON p.category_id = c.id AND p.available = 1
        GROUP BY c.id, c.name
        ORDER BY c.name
        """
    ).fetchall()


def load_category_details(db, category_id):
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
                  AND p2.available = 1
                  AND p2.image <> ''
                ORDER BY p2.id DESC
                LIMIT 1
            ) AS cover_image
        FROM categories c
        LEFT JOIN products p ON p.category_id = c.id AND p.available = 1
        WHERE c.id = ?
        GROUP BY c.id, c.name
        """,
        (category_id,),
    ).fetchone()


def load_catalog_products(db, q="", category_id=None, limit=None):
    if q:
        fts_query = normalize_search_terms(q)
        if not fts_query:
            return []

        sql = """
            SELECT p.*, c.name AS category_name
            FROM products_fts
            JOIN products p ON p.id = products_fts.rowid
            LEFT JOIN categories c ON c.id = p.category_id
            WHERE p.available = 1
              AND products_fts MATCH ?
        """
        params = [fts_query]

        if category_id:
            sql += " AND p.category_id = ?"
            params.append(category_id)

        sql += " ORDER BY p.id DESC"

        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)

        return db.execute(sql, params).fetchall()

    sql = """
        SELECT p.*, c.name AS category_name
        FROM products p
        LEFT JOIN categories c ON c.id = p.category_id
        WHERE p.available = 1
    """
    params = []

    if category_id:
        sql += " AND p.category_id = ?"
        params.append(category_id)

    sql += " ORDER BY p.id DESC"

    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)

    return db.execute(sql, params).fetchall()


def search_categories(db, query, limit=6):
    fts_query = normalize_search_terms(query)
    if not fts_query:
        return []

    like = f"%{query}%"

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
                  AND p2.available = 1
                  AND p2.image <> ''
                ORDER BY p2.id DESC
                LIMIT 1
            ) AS cover_image
        FROM categories c
        LEFT JOIN products p ON p.category_id = c.id AND p.available = 1
        WHERE (
            EXISTS (
                SELECT 1
                                FROM categories_fts
                                WHERE categories_fts.rowid = c.id
                                    AND categories_fts MATCH ?
            )
            OR EXISTS (
                SELECT 1
                                FROM products_fts
                                JOIN products p2 ON p2.id = products_fts.rowid
                WHERE p2.category_id = c.id
                  AND p2.available = 1
                                    AND products_fts MATCH ?
            )
            OR c.name LIKE ?
        )
        GROUP BY c.id, c.name
        ORDER BY CASE WHEN c.name LIKE ? THEN 0 ELSE 1 END, c.name
        LIMIT ?
        """,
        (fts_query, fts_query, like, like, limit),
    ).fetchall()


def search_products(db, query, limit=12):
    fts_query = normalize_search_terms(query)
    if not fts_query:
        return []

    return db.execute(
        """
        SELECT p.id, p.name, p.description, p.price, p.image, p.stock,
               p.category_id, c.name AS category_name
        FROM products_fts
        JOIN products p ON p.id = products_fts.rowid
        LEFT JOIN categories c ON c.id = p.category_id
        WHERE p.available = 1
          AND products_fts MATCH ?
        ORDER BY p.id DESC
        LIMIT ?
        """,
        (fts_query, limit),
    ).fetchall()


@public_bp.route("/api/checkout", methods=["POST"])
@rate_limit(limit=10, window_seconds=60)
def api_checkout():
    try:
        requested_items = json.loads(request.form.get("items", "[]"))
    except (TypeError, json.JSONDecodeError):
        requested_items = []

    if not isinstance(requested_items, list):
        requested_items = []

    quantities = {}
    for item in requested_items:
        if not isinstance(item, dict):
            continue

        try:
            product_id = int(item.get("id"))
            quantity = int(item.get("quantity"))
        except (TypeError, ValueError):
            continue

        if product_id <= 0 or quantity <= 0:
            continue

        quantities[product_id] = quantities.get(product_id, 0) + quantity

    if not quantities:
        return jsonify({"items": [], "total": 0})

    placeholders = ", ".join("?" for _ in quantities)
    db = get_db()
    rows = db.execute(
        f"""
        SELECT id, name, price, stock
        FROM products
        WHERE available = 1 AND id IN ({placeholders})
        """,
        tuple(quantities),
    ).fetchall()
    products = {row["id"]: row for row in rows}
    validated_items = []
    total = 0.0

    for product_id, requested_quantity in quantities.items():
        product = products.get(product_id)
        if product is None:
            continue

        price = float(product["price"])
        if not math.isfinite(price) or price < 0:
            continue

        quantity = requested_quantity
        if product["stock"] is not None:
            quantity = min(quantity, max(int(product["stock"]), 0))
        if quantity <= 0:
            continue

        validated_items.append(
            {"name": product["name"], "price": price, "quantity": quantity}
        )
        total += price * quantity

    return jsonify({"items": validated_items, "total": total})


@public_bp.route("/")
def index():
    db = get_db()
    categories = load_categories(db)
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category", type=int)
    active_category = load_category_details(db, category_id) if category_id else None
    has_filters = bool(q or category_id)
    products = load_catalog_products(db, q=q, category_id=category_id) if has_filters else []

    return render_template(
        "index.html",
        categories=categories,
        products=products,
        q=q,
        selected_category=category_id,
        active_category=active_category,
        results_count=len(products),
    )


@public_bp.route("/language/<lang_code>")
def set_language(lang_code):
    language = normalize_language(lang_code)
    set_locale(language)

    next_url = request.args.get("next")
    fallback = request.referrer or url_for("public.index")
    return redirect(safe_redirect_target(next_url, fallback))


@public_bp.route("/products")
def products():
    return redirect(url_for("public.index", **request.args.to_dict(flat=True)) + "#products")


@public_bp.route("/cart")
def cart():
    return render_template("cart.html")


@public_bp.route("/api/products")
def api_products():
    db = get_db()
    rows = db.execute(
        """
        SELECT p.id, p.name, p.description, p.price, p.image, p.stock,
               p.category_id, c.name AS category_name
        FROM products p
        LEFT JOIN categories c ON c.id = p.category_id
        WHERE p.available = 1
        ORDER BY p.id DESC
        """
    ).fetchall()

    return jsonify([dict(row) for row in rows])


@public_bp.route("/api/search")
@rate_limit(limit=30, window_seconds=60)
def api_search():
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return jsonify({"query": query, "categories": [], "products": []})

    db = get_db()
    categories = search_categories(db, query)
    products = search_products(db, query)

    return jsonify(
        {
            "query": query,
            "categories": [dict(row) for row in categories],
            "products": [dict(row) for row in products],
        }
    )
