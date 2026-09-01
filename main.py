from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.config import settings
from app.database import Base, engine
from app.utils.image_gen import ensure_placeholder_assets
from app.routers import auth, products, categories, cart, orders, wishlist, size_recommendation, admin

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(
    title="StyleHub API",
    description="Fashion E-Commerce Store - Remote Python Full Stack Internship Task PY-EC-004",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # relaxed for local dev / grading convenience
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Static & templates ----
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(FRONTEND_DIR / "templates"))

# ---- API routers ----
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(categories.router)
app.include_router(categories.brands_router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(wishlist.router)
app.include_router(size_recommendation.router)
app.include_router(admin.router)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    ensure_placeholder_assets()


@app.get("/api/health", tags=["Health"])
def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "database_mode": settings.DATABASE_MODE}


# =========================================================
# Frontend page routes (server-rendered Jinja2 + Bootstrap5)
# All actual data is fetched client-side via the /api/* JSON
# endpoints above using fetch() + the JWT stored in localStorage.
# =========================================================

@app.get("/", response_class=HTMLResponse)
def home_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "page": "home"})


@app.get("/products", response_class=HTMLResponse)
def products_page(request: Request):
    return templates.TemplateResponse("products.html", {"request": request, "page": "products"})


@app.get("/products/{slug}", response_class=HTMLResponse)
def product_detail_page(request: Request, slug: str):
    return templates.TemplateResponse("product_detail.html", {"request": request, "page": "product_detail", "slug": slug})


@app.get("/cart", response_class=HTMLResponse)
def cart_page(request: Request):
    return templates.TemplateResponse("cart.html", {"request": request, "page": "cart"})


@app.get("/checkout", response_class=HTMLResponse)
def checkout_page(request: Request):
    return templates.TemplateResponse("checkout.html", {"request": request, "page": "checkout"})


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "page": "login"})


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "page": "register"})


@app.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request):
    return templates.TemplateResponse("profile.html", {"request": request, "page": "profile"})


@app.get("/orders", response_class=HTMLResponse)
def orders_page(request: Request):
    return templates.TemplateResponse("orders.html", {"request": request, "page": "orders"})


@app.get("/orders/{order_number}", response_class=HTMLResponse)
def order_detail_page(request: Request, order_number: str):
    return templates.TemplateResponse(
        "order_detail.html", {"request": request, "page": "order_detail", "order_number": order_number}
    )


@app.get("/wishlist", response_class=HTMLResponse)
def wishlist_page(request: Request):
    return templates.TemplateResponse("wishlist.html", {"request": request, "page": "wishlist"})


@app.get("/size-guide", response_class=HTMLResponse)
def size_guide_page(request: Request):
    return templates.TemplateResponse("size_guide.html", {"request": request, "page": "size_guide"})


# ---- Admin pages (client-side guarded: JS checks is_admin and redirects) ----

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard_page(request: Request):
    return templates.TemplateResponse("admin_dashboard.html", {"request": request, "page": "admin"})


@app.get("/admin/products", response_class=HTMLResponse)
def admin_products_page(request: Request):
    return templates.TemplateResponse("admin_products.html", {"request": request, "page": "admin"})


@app.get("/admin/orders", response_class=HTMLResponse)
def admin_orders_page(request: Request):
    return templates.TemplateResponse("admin_orders.html", {"request": request, "page": "admin"})
