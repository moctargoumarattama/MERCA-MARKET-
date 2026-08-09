import sqlite3
from pathlib import Path

from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _table_columns(conn, table_name):
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def _ensure_column(conn, table_name, column_name, column_definition):
    if column_name not in _table_columns(conn, table_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")


def init_db():
    Path(current_app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    Path(current_app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            price REAL NOT NULL DEFAULT 0,
            image TEXT DEFAULT '',
            category_id INTEGER,
            available INTEGER NOT NULL DEFAULT 1,
            stock INTEGER DEFAULT NULL,
            FOREIGN KEY(category_id) REFERENCES categories(id)
        );

        CREATE INDEX IF NOT EXISTS idx_products_available ON products(available);
        CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id);

        CREATE VIRTUAL TABLE IF NOT EXISTS products_fts USING fts5(
            name,
            description,
            category_name,
            tokenize = 'unicode61'
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS categories_fts USING fts5(
            name,
            tokenize = 'unicode61'
        );
        """
    )

    if conn.execute("SELECT COUNT(*) FROM products_fts").fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO products_fts(rowid, name, description, category_name) "
            "SELECT p.id, p.name, p.description, COALESCE(c.name, '') "
            "FROM products p LEFT JOIN categories c ON c.id = p.category_id"
        )

    if conn.execute("SELECT COUNT(*) FROM categories_fts").fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO categories_fts(rowid, name) "
            "SELECT id, name FROM categories"
        )

    conn.executescript(
        """
        CREATE TRIGGER IF NOT EXISTS products_ai AFTER INSERT ON products BEGIN
            INSERT INTO products_fts(rowid, name, description, category_name)
            VALUES (
                new.id,
                new.name,
                new.description,
                COALESCE((SELECT name FROM categories WHERE id = new.category_id), '')
            );
        END;

        CREATE TRIGGER IF NOT EXISTS products_ad AFTER DELETE ON products BEGIN
            DELETE FROM products_fts WHERE rowid = old.id;
        END;

        CREATE TRIGGER IF NOT EXISTS products_au AFTER UPDATE ON products BEGIN
            DELETE FROM products_fts WHERE rowid = old.id;
            INSERT INTO products_fts(rowid, name, description, category_name)
            VALUES (
                new.id,
                new.name,
                new.description,
                COALESCE((SELECT name FROM categories WHERE id = new.category_id), '')
            );
        END;

        CREATE TRIGGER IF NOT EXISTS categories_ai AFTER INSERT ON categories BEGIN
            INSERT INTO categories_fts(rowid, name) VALUES (new.id, new.name);
        END;

        CREATE TRIGGER IF NOT EXISTS categories_ad AFTER DELETE ON categories BEGIN
            DELETE FROM categories_fts WHERE rowid = old.id;
            UPDATE products_fts
            SET category_name = ''
            WHERE rowid IN (SELECT id FROM products WHERE category_id = old.id);
        END;

        CREATE TRIGGER IF NOT EXISTS categories_au AFTER UPDATE ON categories BEGIN
            DELETE FROM categories_fts WHERE rowid = old.id;
            INSERT INTO categories_fts(rowid, name) VALUES (new.id, new.name);
            UPDATE products_fts
            SET category_name = new.name
            WHERE rowid IN (SELECT id FROM products WHERE category_id = new.id);
        END;
        """
    )

    _ensure_column(conn, "products", "stock", "INTEGER DEFAULT NULL")

    count = conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
    if count == 0:
        conn.execute("INSERT INTO categories(name) VALUES (?)", ("Cosmétique",))
        conn.execute("INSERT INTO categories(name) VALUES (?)", ("Fruit sec",))

    conn.commit()
