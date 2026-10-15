"""Tạo database SQLite giả lập một cửa hàng: sản phẩm + đánh giá.

Chạy: python bench/seed_db.py
"""
import random
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # in tiếng Việt được trên mọi terminal Windows

DB_PATH = Path(__file__).with_name("shop.db")
N_PRODUCTS = 1000
N_CATEGORIES = 20
N_REVIEWS = 300_000

random.seed(42)  # cố định để lần nào tạo cũng ra cùng dữ liệu


def main():
    DB_PATH.unlink(missing_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
        CREATE TABLE products (
            id       INTEGER PRIMARY KEY,
            name     TEXT NOT NULL,
            category TEXT NOT NULL,
            price    INTEGER NOT NULL
        );
        CREATE TABLE reviews (
            id         INTEGER PRIMARY KEY,
            product_id INTEGER NOT NULL,
            rating     INTEGER NOT NULL,
            comment    TEXT NOT NULL
        );
    """)

    db.executemany(
        "INSERT INTO products VALUES (?, ?, ?, ?)",
        [(i, f"Sản phẩm {i}", f"Danh mục {i % N_CATEGORIES + 1}", random.randint(10, 500) * 1000)
         for i in range(1, N_PRODUCTS + 1)],
    )
    db.executemany(
        "INSERT INTO reviews (product_id, rating, comment) VALUES (?, ?, ?)",
        [(random.randint(1, N_PRODUCTS), random.randint(1, 5), f"Nhận xét số {i}")
         for i in range(N_REVIEWS)],
    )
    db.commit()
    db.close()
    print(f"Đã tạo {DB_PATH.name}: {N_PRODUCTS} sản phẩm, {N_REVIEWS:,} đánh giá")


if __name__ == "__main__":
    main()
