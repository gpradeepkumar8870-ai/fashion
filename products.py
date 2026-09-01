import math
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_

from app.database import get_db
from app import models, schemas, security

router = APIRouter(prefix="/api/products", tags=["Products"])


def _to_card(product: models.Product) -> schemas.ProductCardOut:
    primary = next((img.image_url for img in product.images if img.is_primary), None)
    if not primary and product.images:
        primary = product.images[0].image_url
    sizes = sorted({v.size for v in product.variants if v.stock > 0}) or sorted({v.size for v in product.variants})
    colors = sorted({v.color for v in product.variants})
    return schemas.ProductCardOut(
        id=product.id,
        name=product.name,
        slug=product.slug,
        price=product.price,
        discount_price=product.discount_price,
        effective_price=product.effective_price,
        discount_percent=product.discount_percent,
        rating=product.rating,
        total_reviews=product.total_reviews,
        is_featured=product.is_featured,
        is_bestseller=product.is_bestseller,
        category=product.category,
        brand=product.brand,
        primary_image=primary,
        available_sizes=sizes,
        available_colors=colors,
    )


@router.get("", response_model=schemas.ProductListResponse)
def list_products(
    db: Session = Depends(get_db),
    search: Optional[str] = Query(None, description="Search by product name/description"),
    category: Optional[str] = Query(None, description="Category slug"),
    brand: Optional[str] = Query(None, description="Brand name"),
    size: Optional[str] = Query(None, description="Filter by size, e.g. M"),
    color: Optional[str] = Query(None, description="Filter by color"),
    gender: Optional[str] = Query(None, description="men | women | kids | unisex"),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    is_featured: Optional[bool] = Query(None),
    is_bestseller: Optional[bool] = Query(None),
    sort_by: str = Query("newest", description="newest | price_asc | price_desc | rating | popularity"),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=60),
):
    q = db.query(models.Product).options(
        joinedload(models.Product.images),
        joinedload(models.Product.variants),
        joinedload(models.Product.category),
        joinedload(models.Product.brand),
    ).filter(models.Product.is_active == True)  # noqa: E712

    if search:
        like = f"%{search}%"
        q = q.filter(or_(models.Product.name.ilike(like), models.Product.description.ilike(like)))
    if category:
        q = q.join(models.Category).filter(models.Category.slug == category)
    if brand:
        q = q.join(models.Brand).filter(models.Brand.name.ilike(brand))
    if gender:
        q = q.filter(models.Product.gender == gender)
    if is_featured is not None:
        q = q.filter(models.Product.is_featured == is_featured)
    if is_bestseller is not None:
        q = q.filter(models.Product.is_bestseller == is_bestseller)
    if size or color:
        q = q.join(models.ProductVariant)
        if size:
            q = q.filter(models.ProductVariant.size == size)
        if color:
            q = q.filter(models.ProductVariant.color.ilike(color))
        q = q.distinct()
    if min_price is not None:
        q = q.filter(models.Product.price >= min_price)
    if max_price is not None:
        q = q.filter(models.Product.price <= max_price)

    if sort_by == "price_asc":
        q = q.order_by(models.Product.price.asc())
    elif sort_by == "price_desc":
        q = q.order_by(models.Product.price.desc())
    elif sort_by == "rating":
        q = q.order_by(models.Product.rating.desc())
    elif sort_by == "popularity":
        q = q.order_by(models.Product.total_reviews.desc())
    else:
        q = q.order_by(models.Product.created_at.desc())

    total = q.count()
    total_pages = max(1, math.ceil(total / page_size))
    products = q.offset((page - 1) * page_size).limit(page_size).all()

    return schemas.ProductListResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        products=[_to_card(p) for p in products],
    )


@router.get("/filters/options")
def get_filter_options(db: Session = Depends(get_db)):
    """Returns the distinct values available for building filter UI controls."""
    sizes = [r[0] for r in db.query(models.ProductVariant.size).distinct().all() if r[0]]
    colors = [r[0] for r in db.query(models.ProductVariant.color).distinct().all() if r[0]]
    genders = [r[0] for r in db.query(models.Product.gender).distinct().all() if r[0]]
    prices = db.query(models.Product.price).all()
    price_values = [p[0] for p in prices] or [0]

    # sensible size sort order
    size_order = ["XS", "S", "M", "L", "XL", "XXL", "XXXL"]
    sizes_sorted = sorted(sizes, key=lambda s: size_order.index(s) if s in size_order else 99)

    return {
        "sizes": sizes_sorted,
        "colors": sorted(colors),
        "genders": sorted(genders),
        "min_price": min(price_values),
        "max_price": max(price_values),
        "categories": [{"id": c.id, "name": c.name, "slug": c.slug} for c in db.query(models.Category).all()],
        "brands": [{"id": b.id, "name": b.name} for b in db.query(models.Brand).all()],
    }


@router.get("/{slug}", response_model=schemas.ProductDetailOut)
def get_product(slug: str, db: Session = Depends(get_db)):
    product = db.query(models.Product).options(
        joinedload(models.Product.images),
        joinedload(models.Product.variants),
        joinedload(models.Product.category),
        joinedload(models.Product.brand),
    ).filter(models.Product.slug == slug).first()

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


@router.get("/{slug}/reviews", response_model=List[schemas.ReviewOut])
def get_product_reviews(slug: str, db: Session = Depends(get_db)):
    product = db.query(models.Product).filter(models.Product.slug == slug).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    reviews = (
        db.query(models.Review)
        .options(joinedload(models.Review.user))
        .filter(models.Review.product_id == product.id)
        .order_by(models.Review.created_at.desc())
        .all()
    )
    return [
        schemas.ReviewOut(
            id=r.id, rating=r.rating, comment=r.comment,
            is_verified_purchase=r.is_verified_purchase,
            username=r.user.username, created_at=r.created_at,
        )
        for r in reviews
    ]


@router.post("/{slug}/reviews", response_model=schemas.ReviewOut, status_code=201)
def add_review(
    slug: str,
    payload: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    product = db.query(models.Product).filter(models.Product.slug == slug).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")

    existing = db.query(models.Review).filter(
        models.Review.product_id == product.id, models.Review.user_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already reviewed this product.")

    # verified purchase check: has the user ordered this product before?
    has_purchased = (
        db.query(models.OrderItem)
        .join(models.Order)
        .filter(models.Order.user_id == current_user.id, models.OrderItem.product_id == product.id)
        .first()
        is not None
    )

    review = models.Review(
        product_id=product.id, user_id=current_user.id,
        rating=payload.rating, comment=payload.comment,
        is_verified_purchase=has_purchased,
    )
    db.add(review)
    db.flush()

    # recompute aggregate rating
    all_reviews = db.query(models.Review).filter(models.Review.product_id == product.id).all()
    product.total_reviews = len(all_reviews)
    product.rating = round(sum(r.rating for r in all_reviews) / len(all_reviews), 2)

    db.commit()
    db.refresh(review)

    return schemas.ReviewOut(
        id=review.id, rating=review.rating, comment=review.comment,
        is_verified_purchase=review.is_verified_purchase,
        username=current_user.username, created_at=review.created_at,
    )
