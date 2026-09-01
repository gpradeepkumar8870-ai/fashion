import random
import string
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app import models, schemas, security
from app.routers.cart import _get_or_create_cart, _build_cart_response, TAX_RATE, FREE_SHIPPING_THRESHOLD, SHIPPING_FLAT_FEE

router = APIRouter(prefix="/api/orders", tags=["Orders"])

VALID_PAYMENT_METHODS = {"card", "upi", "cod", "netbanking"}
VALID_ORDER_STATUSES = ["pending", "confirmed", "shipped", "delivered", "cancelled"]


def _generate_order_number() -> str:
    date_part = datetime.utcnow().strftime("%Y%m%d")
    rand_part = "".join(random.choices(string.digits, k=6))
    return f"SH-{date_part}-{rand_part}"


@router.post("/checkout", response_model=schemas.OrderOut, status_code=201)
def checkout(
    payload: schemas.CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    if payload.payment_method not in VALID_PAYMENT_METHODS:
        raise HTTPException(status_code=400, detail="Invalid payment method selected.")

    cart = _get_or_create_cart(db, current_user)
    cart_items = db.query(models.CartItem).options(
        joinedload(models.CartItem.variant).joinedload(models.ProductVariant.product).joinedload(models.Product.images)
    ).filter(models.CartItem.cart_id == cart.id).all()

    if not cart_items:
        raise HTTPException(status_code=400, detail="Your cart is empty. Add items before checking out.")

    # Validate stock and compute totals
    subtotal = 0.0
    for item in cart_items:
        variant = item.variant
        if item.quantity > variant.stock:
            raise HTTPException(
                status_code=400,
                detail=f"Only {variant.stock} unit(s) left for {variant.product.name} "
                       f"({variant.size}/{variant.color}). Please update your cart.",
            )
        subtotal += variant.product.effective_price * item.quantity

    subtotal = round(subtotal, 2)
    tax = round(subtotal * TAX_RATE, 2)
    shipping = 0.0 if subtotal >= FREE_SHIPPING_THRESHOLD else SHIPPING_FLAT_FEE
    total = round(subtotal + tax + shipping, 2)

    # "Payment integration" demo: card/upi/netbanking are marked paid immediately
    # (simulated gateway - no real money moves), COD stays pending until delivery.
    payment_status = "pending" if payload.payment_method == "cod" else "paid"

    order = models.Order(
        order_number=_generate_order_number(),
        user_id=current_user.id,
        total_amount=total,
        shipping_address=payload.shipping.shipping_address,
        shipping_city=payload.shipping.shipping_city,
        shipping_state=payload.shipping.shipping_state,
        shipping_zip=payload.shipping.shipping_zip,
        shipping_country=payload.shipping.shipping_country,
        payment_method=payload.payment_method,
        payment_status=payment_status,
        order_status="confirmed",
        notes=payload.notes,
    )
    db.add(order)
    db.flush()

    for item in cart_items:
        variant = item.variant
        product = variant.product
        primary_img = next((i.image_url for i in product.images if i.is_primary), None) or (
            product.images[0].image_url if product.images else None
        )
        db.add(models.OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_name=product.name,
            product_image=primary_img,
            variant_size=variant.size,
            variant_color=variant.color,
            quantity=item.quantity,
            price=product.effective_price,
        ))
        # decrement stock
        variant.stock -= item.quantity

    # empty the cart
    db.query(models.CartItem).filter(models.CartItem.cart_id == cart.id).delete()

    db.commit()
    db.refresh(order)
    return order


@router.get("", response_model=List[schemas.OrderOut])
def get_my_orders(db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    orders = (
        db.query(models.Order)
        .options(joinedload(models.Order.items))
        .filter(models.Order.user_id == current_user.id)
        .order_by(models.Order.created_at.desc())
        .all()
    )
    return orders


@router.get("/{order_number}", response_model=schemas.OrderOut)
def get_order_detail(
    order_number: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    order = (
        db.query(models.Order)
        .options(joinedload(models.Order.items))
        .filter(models.Order.order_number == order_number, models.Order.user_id == current_user.id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    return order


@router.post("/{order_number}/cancel", response_model=schemas.OrderOut)
def cancel_order(
    order_number: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    order = db.query(models.Order).options(joinedload(models.Order.items)).filter(
        models.Order.order_number == order_number, models.Order.user_id == current_user.id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    if order.order_status in ("shipped", "delivered", "cancelled"):
        raise HTTPException(status_code=400, detail=f"An order that is already '{order.order_status}' cannot be cancelled.")

    order.order_status = "cancelled"
    if order.payment_status == "paid":
        order.payment_status = "refunded"

    # restock items
    for item in order.items:
        variant = db.query(models.ProductVariant).filter(
            models.ProductVariant.product_id == item.product_id,
            models.ProductVariant.size == item.variant_size,
            models.ProductVariant.color == item.variant_color,
        ).first()
        if variant:
            variant.stock += item.quantity

    db.commit()
    db.refresh(order)
    return order


# --- Simple admin-style endpoint to progress an order's status (kept open,
#     no separate admin panel is in scope for this task) ---
@router.post("/{order_number}/advance-status", response_model=schemas.OrderOut)
def advance_order_status(
    order_number: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    order = db.query(models.Order).options(joinedload(models.Order.items)).filter(
        models.Order.order_number == order_number, models.Order.user_id == current_user.id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found.")
    if order.order_status in ("cancelled", "delivered"):
        raise HTTPException(status_code=400, detail=f"Order is already '{order.order_status}'.")

    current_index = VALID_ORDER_STATUSES.index(order.order_status)
    if current_index < len(VALID_ORDER_STATUSES) - 2:  # don't auto-advance into "cancelled"
        order.order_status = VALID_ORDER_STATUSES[current_index + 1]
        if order.order_status == "delivered" and order.payment_method == "cod":
            order.payment_status = "paid"

    db.commit()
    db.refresh(order)
    return order
