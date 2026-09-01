"""
StyleHub - Admin API
====================
Everything here is protected by security.require_admin - only accounts with
is_admin=True (e.g. the seeded 'admin' account) can call these endpoints.
Regular shoppers never see this data or these controls.
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.database import get_db
from app import models, schemas, security
from app.routers.products import _to_card

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ---------------------- Dashboard stats ----------------------

@router.get("/stats")
def get_admin_stats(db: Session = Depends(get_db), _admin: models.User = Depends(security.require_admin)):
    total_products = db.query(models.Product).count()
    active_products = db.query(models.Product).filter(models.Product.is_active == True).count()  # noqa: E712
    total_orders = db.query(models.Order).count()
    total_users = db.query(models.User).filter(models.User.is_admin == False).count()  # noqa: E712
    revenue = db.query(func.sum(models.Order.total_amount)).filter(
        models.Order.payment_status == "paid"
    ).scalar() or 0
    pending_orders = db.query(models.Order).filter(models.Order.order_status == "pending").count()
    low_stock_variants = db.query(models.ProductVariant).filter(
        models.ProductVariant.stock > 0, models.ProductVariant.stock <= 3
    ).count()
    out_of_stock_variants = db.query(models.ProductVariant).filter(models.ProductVariant.stock == 0).count()

    recent_orders = (
        db.query(models.Order)
        .options(joinedload(models.Order.user))
        .order_by(models.Order.created_at.desc())
        .limit(5)
        .all()
    )

    return {
        "total_products": total_products,
        "active_products": active_products,
        "total_orders": total_orders,
        "total_users": total_users,
        "total_revenue": round(revenue, 2),
        "pending_orders": pending_orders,
        "low_stock_variants": low_stock_variants,
        "out_of_stock_variants": out_of_stock_variants,
        "recent_orders": [
            {
                "order_number": o.order_number,
                "customer": o.user.username if o.user else "Unknown",
                "total_amount": o.total_amount,
                "order_status": o.order_status,
                "created_at": o.created_at,
            }
            for o in recent_orders
        ],
    }


# ---------------------- Product management ----------------------

@router.get("/products")
def admin_list_products(
    db: Session = Depends(get_db),
    _admin: models.User = Depends(security.require_admin),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Unlike the public /api/products endpoint, this includes inactive
    products and returns stock/variant detail admins need to manage inventory."""
    q = db.query(models.Product).options(
        joinedload(models.Product.variants),
        joinedload(models.Product.images),
        joinedload(models.Product.category),
        joinedload(models.Product.brand),
    )
    if search:
        q = q.filter(models.Product.name.ilike(f"%{search}%"))
    total = q.count()
    products = q.order_by(models.Product.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "slug": p.slug,
                "price": p.price,
                "discount_price": p.discount_price,
                "is_active": p.is_active,
                "is_featured": p.is_featured,
                "is_bestseller": p.is_bestseller,
                "category": p.category.name if p.category else None,
                "brand": p.brand.name if p.brand else None,
                "primary_image": next((i.image_url for i in p.images if i.is_primary), None),
                "total_stock": sum(v.stock for v in p.variants),
                "variant_count": len(p.variants),
            }
            for p in products
        ],
    }


@router.get("/products/{product_id}", response_model=schemas.ProductDetailOut)
def admin_get_product(
    product_id: int, db: Session = Depends(get_db), _admin: models.User = Depends(security.require_admin)
):
    product = db.query(models.Product).options(
        joinedload(models.Product.variants), joinedload(models.Product.images),
        joinedload(models.Product.category), joinedload(models.Product.brand),
    ).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    return schemas.ProductDetailOut(
        id=product.id, name=product.name, slug=product.slug, description=product.description,
        price=product.price, discount_price=product.discount_price,
        effective_price=product.effective_price, discount_percent=product.discount_percent,
        rating=product.rating, total_reviews=product.total_reviews,
        is_featured=product.is_featured, is_bestseller=product.is_bestseller,
        gender=product.gender, fit_type=product.fit_type, material=product.material,
        category=product.category, brand=product.brand,
        images=product.images, variants=product.variants,
    )


from pydantic import BaseModel


class ProductUpdatePayload(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    discount_price: Optional[float] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    is_bestseller: Optional[bool] = None


@router.put("/products/{product_id}")
def admin_update_product(
    product_id: int,
    payload: ProductUpdatePayload,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(security.require_admin),
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    return {"message": "Product updated successfully."}


@router.delete("/products/{product_id}")
def admin_deactivate_product(
    product_id: int, db: Session = Depends(get_db), _admin: models.User = Depends(security.require_admin)
):
    """Soft delete - deactivates the product instead of removing order history."""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    product.is_active = False
    db.commit()
    return {"message": "Product deactivated."}


@router.put("/variants/{variant_id}/stock")
def admin_update_variant_stock(
    variant_id: int,
    stock: int = Query(..., ge=0),
    db: Session = Depends(get_db),
    _admin: models.User = Depends(security.require_admin),
):
    variant = db.query(models.ProductVariant).filter(models.ProductVariant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found.")
    variant.stock = stock
    db.commit()
    return {"message": "Stock updated.", "variant_id": variant.id, "stock": variant.stock}


# ---------------------- Order management ----------------------

VALID_STATUSES = ["pending", "confirmed", "shipped", "delivered", "cancelled"]


@router.get("/orders")
def admin_list_orders(
    db: Session = Depends(get_db),
    _admin: models.User = Depends(security.require_admin),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    q = db.query(models.Order).options(joinedload(models.Order.user), joinedload(models.Order.items))
    if status_filter:
        q = q.filter(models.Order.order_status == status_filter)
    total = q.count()
    orders = q.order_by(models.Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "orders": [
            {
                "order_number": o.order_number,
                "customer": o.user.username if o.user else "Unknown",
                "customer_email": o.user.email if o.user else None,
                "item_count": len(o.items),
                "total_amount": o.total_amount,
                "payment_method": o.payment_method,
                "payment_status": o.payment_status,
                "order_status": o.order_status,
                "created_at": o.created_at,
            }
            for o in orders
        ],
    }


class OrderStatusUpdate(BaseModel):
    order_status: str


@router.put("/orders/{order_number}/status")
def admin_update_order_status(
    order_number: str,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
    _admin: models.User = Depends(security.require_admin),
):
    if payload.order_status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Status must be one of {VALID_STATUSES}.")

    order = db.query(models.Order).options(joinedload(models.Order.items)).filter(
        models.Order.order_number == order_number
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")

    # restock if moving into cancelled from a non-cancelled state
    if payload.order_status == "cancelled" and order.order_status != "cancelled":
        for item in order.items:
            variant = db.query(models.ProductVariant).filter(
                models.ProductVariant.product_id == item.product_id,
                models.ProductVariant.size == item.variant_size,
                models.ProductVariant.color == item.variant_color,
            ).first()
            if variant:
                variant.stock += item.quantity
        if order.payment_status == "paid":
            order.payment_status = "refunded"

    order.order_status = payload.order_status
    if payload.order_status == "delivered" and order.payment_method == "cod":
        order.payment_status = "paid"

    db.commit()
    return {"message": "Order status updated.", "order_number": order.order_number, "order_status": order.order_status}


# ---------------------- User management (read-only) ----------------------

@router.get("/users", response_model=List[schemas.UserOut])
def admin_list_users(db: Session = Depends(get_db), _admin: models.User = Depends(security.require_admin)):
    return db.query(models.User).filter(models.User.is_admin == False).order_by(  # noqa: E712
        models.User.created_at.desc()
    ).all()
