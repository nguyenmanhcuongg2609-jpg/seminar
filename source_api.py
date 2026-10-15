import json
import secrets
import sqlite3
import threading
import time
from pathlib import Path

import redis
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

app = FastAPI()
# cho phép trang demo ở cổng 3000 gọi sang server cổng 3001 (khác origin)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
r = redis.Redis(host="localhost", port=6379, db=0)

SESSION_TTL = 500  # giây, cố định kể từ lúc đăng nhập (không gia hạn)

# "Database" giả: 3 người dùng
USERS = {
    "1": {"id": 1, "name": "Nguyen Van A", "city": "Ho Chi Minh"},
    "2": {"id": 2, "name": "Tran Thi B", "city": "Ha Noi"},
    "3": {"id": 3, "name": "Le Van C", "city": "Da Nang"},
}


# ---------- Nguồn dữ liệu (dùng cho demo caching) ----------

@app.get("/api/users")
def list_users():
    return list(USERS.values())


@app.get("/api/users/{user_id}")
def get_user(user_id: str):
    time.sleep(0)  # giả lập nguồn dữ liệu chậm 2 giây
    user = USERS.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="not found")
    return user


# ---------- Session storage (Redis + TTL) ----------

def session_key(session_id: str) -> str:
    return f"session:{session_id}"


def get_session(session_id: str | None) -> dict:
    """Trả về dữ liệu session, hoặc 401 nếu không có / đã hết hạn."""
    if not session_id:
        raise HTTPException(status_code=401, detail="thiếu session_id")
    data = r.get(session_key(session_id))
    if data is None:
        raise HTTPException(status_code=401, detail="session không tồn tại hoặc đã hết hạn")
    return json.loads(data)


def served_by(request: Request) -> str:
    """Cho biết server nào (cổng nào) đã xử lý yêu cầu."""
    return f"localhost:{request.url.port}"


@app.post("/login")
def login(user_id: str, request: Request):
    user = USERS.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user không tồn tại")
    session_id = secrets.token_urlsafe(32)
    r.set(session_key(session_id), json.dumps(user), ex=SESSION_TTL)
    return {"session_id": session_id, "expires_in": SESSION_TTL,
            "served_by": served_by(request)}


@app.get("/profile")
def profile(request: Request, x_session_id: str | None = Header(default=None)):
    return {**get_session(x_session_id), "served_by": served_by(request)}


@app.get("/session/ttl")
def session_ttl(x_session_id: str | None = Header(default=None)):
    get_session(x_session_id)
    return {"ttl_seconds": r.ttl(session_key(x_session_id))}


@app.post("/logout")
def logout(request: Request, x_session_id: str | None = Header(default=None)):
    get_session(x_session_id)
    r.delete(session_key(x_session_id))
    return {"message": "đã đăng xuất", "served_by": served_by(request)}


# ---------- Đối chứng: session lưu trong RAM của từng server (KHÔNG dùng Redis) ----------
# Mỗi tiến trình server có dict riêng => server khác không thấy session này.

MEMORY_SESSIONS: dict[str, dict] = {}


@app.post("/memory/login")
def memory_login(user_id: str, request: Request):
    user = USERS.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user không tồn tại")
    session_id = secrets.token_urlsafe(32)
    MEMORY_SESSIONS[session_id] = user
    return {"session_id": session_id, "served_by": served_by(request)}


@app.get("/memory/profile")
def memory_profile(request: Request, x_session_id: str | None = Header(default=None)):
    user = MEMORY_SESSIONS.get(x_session_id or "")
    if user is None:
        raise HTTPException(status_code=401, detail=f"server {served_by(request)} không có session này trong RAM")
    return {**user, "served_by": served_by(request)}


@app.post("/memory/logout")
def memory_logout(request: Request, x_session_id: str | None = Header(default=None)):
    if MEMORY_SESSIONS.pop(x_session_id or "", None) is None:
        raise HTTPException(status_code=401, detail=f"server {served_by(request)} không có session này trong RAM")
    return {"message": "đã đăng xuất", "served_by": served_by(request)}


# ---------- Trang demo trực quan (phục vụ thuyết trình) ----------

DEMO_DELAY = 2   # giây: giả lập API gốc chậm
CACHE_TTL = 400   # giây: thời gian sống của cache trong demo


@app.get("/", include_in_schema=False)
def demo_page():
    return FileResponse(Path(__file__).with_name("demo.html"))


@app.get("/demo/cache/{user_id}")
def demo_cache(user_id: str):
    """Cache-aside: hỏi Redis trước, MISS thì mới gọi nguồn gốc (chậm) rồi lưu lại."""
    start = time.perf_counter()
    key = f"user:{user_id}"
    cached = r.get(key)
    if cached is not None:
        source, data = "redis", json.loads(cached)
    else:
        time.sleep(DEMO_DELAY)
        data = USERS.get(user_id)
        if data is None:
            raise HTTPException(status_code=404, detail="not found")
        r.set(key, json.dumps(data), ex=CACHE_TTL)
        source = "api"
    return {"source": source, "ms": round((time.perf_counter() - start) * 1000),
            "data": data, "ttl": CACHE_TTL}


@app.delete("/demo/cache")
def demo_clear_cache():
    keys = list(r.scan_iter("user:*"))
    if keys:
        r.delete(*keys)
    return {"deleted": len(keys)}


@app.get("/demo/redis")
def demo_redis():
    """Liệt kê các key hiện có trong Redis (kèm TTL) để hiển thị trực tiếp."""
    items = []
    for k in sorted(r.scan_iter("*")):
        v = r.get(k)
        items.append({"key": k.decode(), "ttl": r.ttl(k),
                      "value": v.decode() if v is not None else None})
    return items


# ---------- Demo 3: Benchmark có Redis / không Redis (database SQLite thật) ----------
# Tạo dữ liệu trước: python bench/seed_db.py

SHOP_DB = Path(__file__).parent / "bench" / "shop.db"
BENCH_CACHE_TTL = 60  # giây
_local = threading.local()          # mỗi luồng một kết nối SQLite
_stats_lock = threading.Lock()
bench_stats = {"db_queries": 0, "cache_hits": 0, "cache_misses": 0}

PRODUCT_SQL = """
    SELECT p.id, p.name, p.category, p.price, COUNT(r.id), ROUND(AVG(r.rating), 2)
    FROM products p LEFT JOIN reviews r ON r.product_id = p.id
    WHERE p.id = ? GROUP BY p.id"""
SIMILAR_SQL = """
    SELECT p.id, p.name, ROUND(AVG(r.rating), 2) AS avg_rating
    FROM products p JOIN reviews r ON r.product_id = p.id
    WHERE p.category = ? AND p.id <> ?
    GROUP BY p.id ORDER BY avg_rating DESC LIMIT 5"""


def _db() -> sqlite3.Connection:
    if not hasattr(_local, "conn"):
        _local.conn = sqlite3.connect(SHOP_DB)
    return _local.conn


def _count(name: str):
    with _stats_lock:
        bench_stats[name] += 1


def query_product_page(product_id: int) -> dict:
    """Truy vấn NẶNG (~100 ms): thông tin + điểm đánh giá + 5 sản phẩm tương tự cùng danh mục."""
    _count("db_queries")
    row = _db().execute(PRODUCT_SQL, (product_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="not found")
    similar = _db().execute(SIMILAR_SQL, (row[2], product_id)).fetchall()
    return {"id": row[0], "name": row[1], "category": row[2], "price": row[3],
            "review_count": row[4], "avg_rating": row[5],
            "similar": [{"id": s[0], "name": s[1], "avg_rating": s[2]} for s in similar]}


def query_product_light(product_id: int) -> dict:
    """Truy vấn NHẸ (<1 ms): lấy 1 dòng theo khóa chính."""
    _count("db_queries")
    row = _db().execute("SELECT id, name, category, price FROM products WHERE id = ?",
                        (product_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="not found")
    return {"id": row[0], "name": row[1], "category": row[2], "price": row[3]}


def cached(key: str, loader, *args) -> dict:
    """Cache-aside: hỏi Redis trước, MISS thì gọi loader (database) rồi lưu lại."""
    hit = r.get(key)
    if hit is not None:
        _count("cache_hits")
        return json.loads(hit)
    _count("cache_misses")
    data = loader(*args)
    r.set(key, json.dumps(data), ex=BENCH_CACHE_TTL)
    return data


@app.get("/products/{product_id}")
def product_no_cache(product_id: int):
    return query_product_page(product_id)


@app.get("/products-cached/{product_id}")
def product_cached(product_id: int):
    return cached(f"product:{product_id}", query_product_page, product_id)


@app.get("/products-light/{product_id}")
def product_light_no_cache(product_id: int):
    return query_product_light(product_id)


@app.get("/products-light-cached/{product_id}")
def product_light_cached(product_id: int):
    return cached(f"product-light:{product_id}", query_product_light, product_id)


@app.get("/bench/stats")
def get_bench_stats():
    with _stats_lock:
        s = dict(bench_stats)
    total = s["cache_hits"] + s["cache_misses"]
    s["hit_rate"] = round(s["cache_hits"] / total * 100, 1) if total else None
    return s


@app.post("/bench/reset")
def reset_bench(flush_cache: bool = True):
    """Đưa bộ đếm về 0 và (mặc định) xóa cache sản phẩm để bắt đầu lần đo mới."""
    with _stats_lock:
        for k in bench_stats:
            bench_stats[k] = 0
    deleted = 0
    if flush_cache:
        keys = list(r.scan_iter("product*"))
        if keys:
            deleted = r.delete(*keys)
    return {"reset": True, "cache_keys_deleted": deleted}


if __name__ == "__main__":
    import sys
    import uvicorn
    # chạy nhiều server: python source_api.py 3000  |  python source_api.py 3001
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    uvicorn.run("source_api:app", port=port, reload=True)
