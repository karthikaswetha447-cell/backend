"""VelvetAura Beauty backend built with Flask and SQLite."""

from __future__ import annotations

import os
import re
import secrets
import sqlite3
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, session, render_template
from werkzeug.security import check_password_hash, generate_password_hash


BACKEND_DIR = Path(__file__).resolve().parent
WEB_DIR = BACKEND_DIR.parent
DATABASE = Path(os.environ.get("DATABASE_PATH", str(BACKEND_DIR / "velvetaura.db"))).resolve()

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("VELVETAURA_SECRET_KEY") or secrets.token_hex(32),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_HTTPS", "0") == "1",
    MAX_CONTENT_LENGTH=1024 * 1024,
)

PRODUCTS = [
    ("maybelline-lipstick", "Maybelline Color Sensational", "Lip products", 599,
     "https://images.unsplash.com/photo-1586495777744-4413f21062fa?auto=format&fit=crop&w=700&q=80", "Velvet rose lipstick"),
    ("dove-moisturizer", "Dove Nourishing Cream", "Moisturizer", 349,
     "https://images.unsplash.com/photo-1608248543803-ba4f8c70ae0b?auto=format&fit=crop&w=700&q=80", "Soft daily hydration"),
    ("maybelline-eye", "Maybelline Eye Studio", "Eye makeup", 749,
     "https://images.unsplash.com/photo-1512496015851-a90fb38ba796?auto=format&fit=crop&w=700&q=80", "Everyday eye makeup"),
    ("dove-face-wash", "Dove Gentle Face Wash", "Face wash", 299,
     "https://images.unsplash.com/photo-1556228720-195a672e8a03?auto=format&fit=crop&w=700&q=80", "Gentle daily cleanse"),
    ("maybelline-fit-me", "Maybelline Fit Me Glow", "Face makeup", 699,
     "https://images.unsplash.com/photo-1596462502278-27bfdc403348?auto=format&fit=crop&w=700&q=80", "Soft luminous finish"),
    ("dove-beauty-bar", "Dove Beauty Bar", "Daily care", 199,
     "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?auto=format&fit=crop&w=700&q=80", "Comforting cleanse"),
]


def connect_db() -> sqlite3.Connection:
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def initialize_database() -> None:
    BACKEND_DIR.mkdir(parents=True, exist_ok=True)
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    with connect_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL,
                price INTEGER NOT NULL, image TEXT NOT NULL, description TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS enquiries (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL,
                topic TEXT NOT NULL, message TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
                customer_name TEXT NOT NULL, email TEXT NOT NULL, phone TEXT NOT NULL,
                address TEXT NOT NULL, total INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
            );
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL,
                product_id TEXT NOT NULL, product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL, unit_price INTEGER NOT NULL,
                FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
            );
        """)
        db.executemany(
            "INSERT OR IGNORE INTO products (id,name,category,price,image,description) VALUES (?,?,?,?,?,?)",
            PRODUCTS,
        )


def error(message: str, status: int = 400):
    return jsonify({"error": message}), status


def read_json() -> dict[str, Any]:
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else {}


def valid_email(value: str) -> bool:
    return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value))


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/<page>")
def frontend_pages(page):
    allowed_pages = [
        "about.html",
        "cart.html",
        "categories.html",
        "contact.html",
        "login.html",
        "products.html"
    ]

    if page not in allowed_pages:
        return jsonify({"error": "Page not found."}), 404

    return render_template(page)


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "VelvetAura Beauty API"})


@app.get("/api/products")
def get_products():
    with connect_db() as db:
        rows = db.execute("SELECT id,name,category,price,image,description FROM products ORDER BY rowid").fetchall()
    return jsonify([dict(row) for row in rows])


@app.post("/api/auth/register")
def register():
    data = read_json()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    if not valid_email(email):
        return error("Enter a valid email address.")
    if len(password) < 8:
        return error("Password must be at least 8 characters.")
    try:
        with connect_db() as db:
            cursor = db.execute(
                "INSERT INTO users (email,password_hash) VALUES (?,?)",
                (email, generate_password_hash(password)),
            )
            session.clear()
            session["user_id"] = cursor.lastrowid
            session["email"] = email
    except sqlite3.IntegrityError:
        return error("An account with that email already exists. Please log in.", 409)
    return jsonify({"message": "Account created. You are now signed in.", "email": email}), 201


@app.post("/api/auth/login")
def login():
    data = read_json()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    with connect_db() as db:
        user = db.execute("SELECT id,email,password_hash FROM users WHERE email=?", (email,)).fetchone()
    if user is None or not check_password_hash(user["password_hash"], password):
        return error("Email or password is incorrect.", 401)
    session.clear()
    session["user_id"] = user["id"]
    session["email"] = user["email"]
    return jsonify({"message": "You are signed in.", "email": user["email"]})


@app.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify({"message": "You are signed out."})


@app.get("/api/auth/me")
def current_user():
    if "user_id" not in session:
        return error("You are not signed in.", 401)
    return jsonify({"id": session["user_id"], "email": session["email"]})


@app.post("/api/contact")
def create_enquiry():
    data = read_json()
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    topic = str(data.get("topic", "Something else")).strip()
    message = str(data.get("message", "")).strip()
    if not name or not valid_email(email) or not message:
        return error("Please provide your name, a valid email, and a message.")
    if len(name) > 120 or len(topic) > 120 or len(message) > 5000:
        return error("One of the fields is too long.")
    with connect_db() as db:
        cursor = db.execute(
            "INSERT INTO enquiries (name,email,topic,message) VALUES (?,?,?,?)",
            (name, email, topic, message),
        )
    return jsonify({"message": "Thank you. Your enquiry has been received.", "id": cursor.lastrowid}), 201


@app.post("/api/orders")
def create_order():
    data = read_json()
    customer = data.get("customer") if isinstance(data.get("customer"), dict) else {}
    name = str(customer.get("name", "")).strip()
    email = str(customer.get("email", "")).strip().lower()
    phone = str(customer.get("phone", "")).strip()
    address = str(customer.get("address", "")).strip()
    items = data.get("items")
    if not name or not valid_email(email) or not phone or not address:
        return error("Please complete all delivery details with a valid email.")
    if not isinstance(items, list) or not items or len(items) > 50:
        return error("Your cart is empty or contains too many items.")

    with connect_db() as db:
        normalized = []
        total = 0
        for item in items:
            if not isinstance(item, dict):
                return error("The cart contains an invalid item.")
            product_name = str(item.get("name", ""))
            quantity = item.get("qty")
            if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1 or quantity > 20:
                return error("Each product quantity must be between 1 and 20.")
            product = db.execute("SELECT id,name,price FROM products WHERE name=?", (product_name,)).fetchone()
            if product is None:
                return error("A product in your cart is no longer available.")
            normalized.append((product["id"], product["name"], quantity, product["price"]))
            total += quantity * product["price"]

        cursor = db.execute(
            "INSERT INTO orders (user_id,customer_name,email,phone,address,total) VALUES (?,?,?,?,?,?)",
            (session.get("user_id"), name, email, phone, address, total),
        )
        order_id = cursor.lastrowid
        db.executemany(
            "INSERT INTO order_items (order_id,product_id,product_name,quantity,unit_price) VALUES (?,?,?,?,?)",
            [(order_id, *row) for row in normalized],
        )
    return jsonify({"message": "Your order has been placed.", "order_id": order_id, "total": total}), 201


@app.get("/api/orders")
def list_orders():
    user_id = session.get("user_id")
    if user_id is None:
        return error("Please log in to view your orders.", 401)
    with connect_db() as db:
        orders = db.execute(
            "SELECT id,total,created_at FROM orders WHERE user_id=? ORDER BY id DESC", (user_id,)
        ).fetchall()
        result = []
        for order in orders:
            items = db.execute(
                "SELECT product_name,quantity,unit_price FROM order_items WHERE order_id=?", (order["id"],)
            ).fetchall()
            result.append({**dict(order), "items": [dict(item) for item in items]})
    return jsonify(result)


@app.errorhandler(413)
def too_large(_error):
    return jsonify({"error": "Request is too large."}), 413


@app.errorhandler(404)
def not_found(_error):
    if request.path.startswith("/api/"):
        return jsonify({"error": "API endpoint not found."}), 404
    return jsonify({"error": "Page not found."}), 404


initialize_database()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=True)
