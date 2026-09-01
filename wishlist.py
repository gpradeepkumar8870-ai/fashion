from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app import models, schemas, security
from app.routers.products import _to_card

router = APIRouter(prefix="/api/wishlist", tags=["Wishlist"])


@router.get("", response_model=List[schemas.WishlistOut])
def get_wishlist(db: Session = Depends(get_db), current_user: models.User = Depends(security.get_current_user)):
    items = (
        db.query(models.WishlistItem)
        .options(
            joinedload(models.WishlistItem.product).joinedload(models.Product.images),
            joinedload(models.WishlistItem.product).joinedload(models.Product.variants),
            joinedload(models.WishlistItem.product).joinedload(models.Product.category),
            joinedload(models.WishlistItem.product).joinedload(models.Product.brand),
        )
        .filter(models.WishlistItem.user_id == current_user.id)
        .order_by(models.WishlistItem.created_at.desc())
        .all()
    )
    return [
        schemas.WishlistOut(id=i.id, product=_to_card(i.product), created_at=i.created_at)
        for i in items
    ]


@router.post("/{product_id}", status_code=201)
def add_to_wishlist(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    existing = db.query(models.WishlistItem).filter(
        models.WishlistItem.user_id == current_user.id, models.WishlistItem.product_id == product_id
    ).first()
    if existing:
        return {"message": "Already in wishlist.", "id": existing.id}

    item = models.WishlistItem(user_id=current_user.id, product_id=product_id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"message": "Added to wishlist.", "id": item.id}


@router.delete("/{product_id}")
def remove_from_wishlist(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    item = db.query(models.WishlistItem).filter(
        models.WishlistItem.user_id == current_user.id, models.WishlistItem.product_id == product_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="This product is not in your wishlist.")
    db.delete(item)
    db.commit()
    return {"message": "Removed from wishlist."}
