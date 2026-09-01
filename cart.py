from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app import models, schemas, security

router = APIRouter(prefix="/api/cart", tags=["Cart"])

TAX_RATE = 0.05          # 5% GST-style estimate
FREE_SHIPPING_THRESHOLD = 999.0
SHIPPING_FLAT_FEE = 79.0


def _get_or_create_cart(db: Session, user: models.User) -> models.Cart:
    cart = db.query(models.Cart).filter(models.Cart.user_id == user.id).first()
    if not cart:
        cart = models.Cart(user_id=user.id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


def _build_cart_response(db: Session, cart: models.Cart) -> schemas.CartOut:
    items = (
        db.query(models.CartItem)
        .options(
            joinedload(models.CartItem.variant).joinedload(models.ProductVariant.product).joinedload(models.Product.images)
        )
        .filter(models.CartItem.cart_id == cart.id)
        .all()
    )

    out_items = []
    subtotal = 0.0
    for item in items:
        variant = item.variant
        product = variant.product
        primary_img = next((i.image_url for i in product.images if i.is_primary), None) or (
            product.images[0].image_url if product.images else None
        )
        unit_price = product.effective_price
        line_subtotal = round(unit_price * item.quantity, 2)
        subtotal += line_subtotal
        out_items.append(
            schemas.CartItemOut(
                id=item.id,
                variant_id=variant.id,
                product_id=product.id,
                product_name=product.name,
                product_image=primary_img,
                size=variant.size,
                color=variant.color,
                unit_price=unit_price,
                quantity=item.quantity,
                stock=variant.stock,
                subtotal=line_subtotal,
            )
        )

    subtotal = round(subtotal, 2)
    tax = round(subtotal * TAX_RATE, 2)
    shipping = 0.0 if (subtotal >= FREE_SHIPPING_THRESHOLD or subtotal == 0) else SHIPPING_FLAT_FEE
    total = round(subtotal + tax + shipping, 2)

    return schemas.CartOut(
        items=out_items,
        total_items=sum(i.quantity for i in out_items),
        subtotal=subtotal,
        estimated_tax=tax,
        estimated_shipping=shipping,
        total=total,
    )


@router.get("", response_model=schemas.CartOut)
def get_cart(db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    cart = _get_or_create_cart(db, current_user)
    return _build_cart_response(db, cart)


@router.post("/items", response_model=schemas.CartOut, status_code=201)
def add_to_cart(
    payload: schemas.CartItemAdd,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    variant = db.query(models.ProductVariant).filter(models.ProductVariant.id == payload.variant_id).first()
    if not variant:
        raise HTTPException(status_code=404, detail="Selected size/color variant not found.")
    if variant.stock < payload.quantity:
        raise HTTPException(status_code=400, detail=f"Only {variant.stock} unit(s) left in stock for this size/color.")

    cart = _get_or_create_cart(db, current_user)
    existing_item = db.query(models.CartItem).filter(
        models.CartItem.cart_id == cart.id, models.CartItem.variant_id == variant.id
    ).first()

    if existing_item:
        new_qty = existing_item.quantity + payload.quantity
        if new_qty > variant.stock:
            raise HTTPException(status_code=400, detail=f"Only {variant.stock} unit(s) available in stock.")
        existing_item.quantity = new_qty
    else:
        db.add(models.CartItem(cart_id=cart.id, variant_id=variant.id, quantity=payload.quantity))

    db.commit()
    return _build_cart_response(db, cart)


@router.put("/items/{item_id}", response_model=schemas.CartOut)
def update_cart_item(
    item_id: int,
    payload: schemas.CartItemUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    cart = _get_or_create_cart(db, current_user)
    item = db.query(models.CartItem).filter(models.CartItem.id == item_id, models.CartItem.cart_id == cart.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found.")
    if payload.quantity > item.variant.stock:
        raise HTTPException(status_code=400, detail=f"Only {item.variant.stock} unit(s) available in stock.")

    item.quantity = payload.quantity
    db.commit()
    return _build_cart_response(db, cart)


@router.delete("/items/{item_id}", response_model=schemas.CartOut)
def remove_cart_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    cart = _get_or_create_cart(db, current_user)
    item = db.query(models.CartItem).filter(models.CartItem.id == item_id, models.CartItem.cart_id == cart.id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Cart item not found.")
    db.delete(item)
    db.commit()
    return _build_cart_response(db, cart)


@router.delete("", response_model=schemas.CartOut)
def clear_cart(db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    cart = _get_or_create_cart(db, current_user)
    db.query(models.CartItem).filter(models.CartItem.cart_id == cart.id).delete()
    db.commit()
    return _build_cart_response(db, cart)
