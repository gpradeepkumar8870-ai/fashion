"""
StyleHub - Database Seeder
==========================
Populates the database with realistic demo data: categories, brands,
products (with size/color variants + generated images), demo user
accounts, a couple of sample orders, and product reviews.

Run with:  python seed_data.py
Safe to re-run: it wipes and recreates all tables first.
"""
import random
import string
import sys
from datetime import datetime, timedelta

sys.path.insert(0, ".")

from app.database import Base, engine, SessionLocal
from app import models
from app.security import hash_password
from app.utils.image_gen import generate_product_image, generate_category_image, generate_brand_logo, ensure_placeholder_assets

random.seed(42)

SIZES = ["XS", "S", "M", "L", "XL", "XXL"]
COLOR_PALETTE = [
    ("Black", "#1A1A1A"), ("White", "#F5F5F5"), ("Navy", "#1B2A4A"),
    ("Maroon", "#6E1B25"), ("Olive", "#6B6E1B"), ("Beige", "#D9C7A3"),
    ("Grey", "#8A8A8A"), ("Mustard", "#D9A441"), ("Rust", "#B5502F"),
    ("Sky Blue", "#7EC8E3"), ("Blush Pink", "#E8B4BC"), ("Charcoal", "#36454F"),
]

CATEGORIES = [
    {"name": "Men's T-Shirts", "slug": "mens-tshirts", "kind": "tshirt", "gender": "men"},
    {"name": "Men's Shirts", "slug": "mens-shirts", "kind": "shirt", "gender": "men"},
    {"name": "Men's Jeans", "slug": "mens-jeans", "kind": "jeans", "gender": "men"},
    {"name": "Women's Tops", "slug": "womens-tops", "kind": "top", "gender": "women"},
    {"name": "Women's Dresses", "slug": "womens-dresses", "kind": "dress", "gender": "women"},
    {"name": "Women's Jeans", "slug": "womens-jeans", "kind": "jeans", "gender": "women"},
    {"name": "Footwear", "slug": "footwear", "kind": "shoes", "gender": "unisex"},
    {"name": "Bags & Accessories", "slug": "bags-accessories", "kind": "bag", "gender": "unisex"},
    {"name": "Kids Wear", "slug": "kids-wear", "kind": "tshirt", "gender": "kids"},
    {"name": "Winter Wear", "slug": "winter-wear", "kind": "jacket", "gender": "unisex"},
]

BRANDS = ["Urban Thread", "Nova Fit", "StyleCraft", "Denim Republic", "Loomier", "Vantage Wear"]

ADJECTIVES = [
    "Classic", "Slim-Fit", "Relaxed", "Premium", "Casual", "Vintage",
    "Oversized", "Everyday", "Signature", "Essential", "Modern", "Heritage",
]

PRODUCT_NOUNS = {
    "mens-tshirts": ["Crew Neck T-Shirt", "Polo T-Shirt", "Graphic Tee", "Henley T-Shirt", "V-Neck Tee"],
    "mens-shirts": ["Formal Shirt", "Checked Shirt", "Linen Shirt", "Denim Shirt", "Oxford Shirt"],
    "mens-jeans": ["Straight Fit Jeans", "Slim Fit Jeans", "Tapered Jeans", "Distressed Jeans", "Jogger Jeans"],
    "womens-tops": ["Wrap Top", "Off-Shoulder Top", "Crop Top", "Peplum Top", "Tunic Top"],
    "womens-dresses": ["Maxi Dress", "A-Line Dress", "Wrap Dress", "Bodycon Dress", "Shirt Dress"],
    "womens-jeans": ["High-Waist Jeans", "Skinny Jeans", "Bootcut Jeans", "Mom Jeans", "Flared Jeans"],
    "footwear": ["Running Sneakers", "Canvas Shoes", "Loafers", "Sandals", "Ankle Boots"],
    "bags-accessories": ["Tote Bag", "Sling Bag", "Backpack", "Leather Wallet", "Clutch"],
    "kids-wear": ["Kids Graphic Tee", "Kids Joggers", "Kids Hoodie", "Kids Dungaree", "Kids Shorts"],
    "winter-wear": ["Puffer Jacket", "Wool Sweater", "Hooded Sweatshirt", "Denim Jacket", "Fleece Jacket"],
}

MATERIALS = ["100% Cotton", "Cotton Blend", "Polyester", "Denim", "Linen", "Wool Blend", "Synthetic Leather"]
FIT_TYPES = ["slim", "regular", "loose", "oversized"]

DEMO_MEASUREMENTS = {
    "height_cm": 172, "weight_kg": 68, "chest_cm": 96, "waist_cm": 82, "hip_cm": 98, "preferred_fit": "regular",
}


def slugify(text: str) -> str:
    return text.lower().replace("'", "").replace("&", "and").replace(" ", "-").replace("--", "-")


def random_sku(prefix: str) -> str:
    return f"{prefix}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"


def reset_database():
    print("Dropping and recreating all tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def seed_categories(db):
    print("Seeding categories...")
    cat_objs = {}
    for c in CATEGORIES:
        img_file = f"{c['slug']}.jpg"
        img_path = generate_category_image(img_file, c["name"])
        cat = models.Category(name=c["name"], slug=c["slug"], description=f"Shop the latest {c['name']}.", image=img_path)
        db.add(cat)
        cat_objs[c["slug"]] = cat
    db.commit()
    for c in CATEGORIES:
        db.refresh(cat_objs[c["slug"]])
    return cat_objs


def seed_brands(db):
    print("Seeding brands...")
    brand_objs = {}
    for name in BRANDS:
        logo_file = f"{slugify(name)}.png"
        logo_path = generate_brand_logo(logo_file, name)
        brand = models.Brand(name=name, logo=logo_path, description=f"{name} - quality fashion, made to last.")
        db.add(brand)
        brand_objs[name] = brand
    db.commit()
    for name in BRANDS:
        db.refresh(brand_objs[name])
    return brand_objs


def seed_products(db, cat_objs, brand_objs):
    print("Seeding products, variants, and images (this generates images locally, may take a moment)...")
    products = []
    product_counter = 0

    for cat in CATEGORIES:
        cat_obj = cat_objs[cat["slug"]]
        nouns = PRODUCT_NOUNS[cat["slug"]]
        for noun in nouns:
            for adj in random.sample(ADJECTIVES, 2):  # 2 variations per noun -> 10 products/category
                product_counter += 1
                name = f"{adj} {noun}"
                slug = f"{slugify(name)}-{product_counter}"
                brand = random.choice(list(brand_objs.values()))
                base_price = round(random.uniform(499, 3499), 2)
                has_discount = random.random() < 0.4
                discount_price = round(base_price * random.uniform(0.6, 0.85), 2) if has_discount else None

                product = models.Product(
                    name=name,
                    slug=slug,
                    description=(
                        f"{name} from {brand.name}. Crafted for everyday comfort with a "
                        f"{random.choice(FIT_TYPES)} fit, made from {random.choice(MATERIALS)}. "
                        f"Pairs perfectly with your favourite basics for a versatile, put-together look."
                    ),
                    price=base_price,
                    discount_price=discount_price,
                    is_active=True,
                    is_featured=random.random() < 0.2,
                    is_bestseller=random.random() < 0.15,
                    gender=cat["gender"],
                    fit_type=random.choice(FIT_TYPES),
                    material=random.choice(MATERIALS),
                    category_id=cat_obj.id,
                    brand_id=brand.id,
                    created_at=datetime.utcnow() - timedelta(days=random.randint(0, 120)),
                )
                db.add(product)
                db.flush()

                # images (2 per product: primary + alt angle, same generated art, distinct files)
                img1_file = f"{slug}-1.jpg"
                img2_file = f"{slug}-2.jpg"
                img1_url = generate_product_image(img1_file, name, kind=cat["kind"])
                img2_url = generate_product_image(img2_file, name + " ", kind=cat["kind"])
                db.add(models.ProductImage(product_id=product.id, image_url=img1_url, is_primary=True))
                db.add(models.ProductImage(product_id=product.id, image_url=img2_url, is_primary=False))

                # variants: 3-4 colors x applicable sizes
                is_footwear = cat["slug"] == "footwear"
                is_accessory = cat["slug"] == "bags-accessories"
                variant_sizes = ["6", "7", "8", "9", "10"] if is_footwear else (["One Size"] if is_accessory else SIZES)
                colors = random.sample(COLOR_PALETTE, k=min(3, len(COLOR_PALETTE)))

                for color_name, color_code in colors:
                    for size in variant_sizes:
                        stock = random.choice([0, 3, 5, 8, 12, 20, 25])
                        db.add(models.ProductVariant(
                            product_id=product.id,
                            size=size,
                            color=color_name,
                            color_code=color_code,
                            stock=stock,
                            sku=random_sku(cat["slug"][:3].upper()),
                        ))

                products.append(product)

    db.commit()
    print(f"Seeded {len(products)} products.")
    return products


def seed_demo_users(db):
    print("Seeding demo user accounts...")
    users = []

    admin = models.User(
        username="admin", email="admin@stylehub.com",
        password_hash=hash_password("Admin@123"),
        first_name="Store", last_name="Admin",
        phone="9876500000", address="StyleHub HQ, MG Road",
        city="Bengaluru", state="Karnataka", zip_code="560001", country="India",
        is_admin=True,
        **DEMO_MEASUREMENTS,
    )
    db.add(admin)

    demo = models.User(
        username="demo_user", email="demo@stylehub.com",
        password_hash=hash_password("Demo@1234"),
        first_name="Priya", last_name="Kumar",
        phone="9876543210", address="12 Residency Road",
        city="Chennai", state="Tamil Nadu", zip_code="600002", country="India",
        height_cm=165, weight_kg=58, chest_cm=88, waist_cm=70, hip_cm=94, preferred_fit="regular",
    )
    db.add(demo)

    users.extend([admin, demo])
    db.commit()
    for u in users:
        db.refresh(u)
        cart = models.Cart(user_id=u.id)
        db.add(cart)
    db.commit()
    return {"admin": admin, "demo": demo}


def seed_orders_and_reviews(db, users, products):
    print("Seeding a sample order + product reviews for the demo account...")
    demo = users["demo"]

    sample_products = random.sample(products, 3)
    order = models.Order(
        order_number="SH-20260615-100234",
        user_id=demo.id,
        total_amount=0,
        shipping_address="12 Residency Road, Near City Mall",
        shipping_city="Chennai", shipping_state="Tamil Nadu",
        shipping_zip="600002", shipping_country="India",
        payment_method="upi", payment_status="paid", order_status="delivered",
        notes="Please leave the package with the security guard.",
        created_at=datetime.utcnow() - timedelta(days=20),
    )
    db.add(order)
    db.flush()

    total = 0.0
    for p in sample_products:
        variant = p.variants[0] if p.variants else None
        qty = random.randint(1, 2)
        price = p.effective_price
        total += price * qty
        db.add(models.OrderItem(
            order_id=order.id,
            product_id=p.id,
            product_name=p.name,
            product_image=p.images[0].image_url if p.images else None,
            variant_size=variant.size if variant else "M",
            variant_color=variant.color if variant else "Black",
            quantity=qty,
            price=price,
        ))
        # leave a review on purchased products
        db.add(models.Review(
            product_id=p.id, user_id=demo.id,
            rating=random.randint(4, 5),
            comment=random.choice([
                "Great quality and fits true to size. Would buy again!",
                "Loved the fabric, very comfortable for daily wear.",
                "Good product, delivery was quick too.",
            ]),
            is_verified_purchase=True,
            created_at=datetime.utcnow() - timedelta(days=10),
        ))
        p.total_reviews += 1

    order.total_amount = round(total * 1.05, 2)  # + estimated tax
    db.commit()

    # a few extra standalone reviews from admin on random products for richer listings
    for p in random.sample(products, 8):
        db.add(models.Review(
            product_id=p.id, user_id=users["admin"].id,
            rating=random.randint(3, 5),
            comment=random.choice([
                "Nice fit and color, matches the pictures.",
                "Decent product for the price.",
                "Fabric quality could be a bit better, but overall satisfied.",
                "Exactly what I was looking for!",
            ]),
            is_verified_purchase=False,
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 60)),
        ))
        p.total_reviews += 1

    db.commit()

    # recompute ratings for all reviewed products
    reviewed_product_ids = {r.product_id for r in db.query(models.Review).all()}
    for pid in reviewed_product_ids:
        product = db.query(models.Product).filter(models.Product.id == pid).first()
        reviews = db.query(models.Review).filter(models.Review.product_id == pid).all()
        product.rating = round(sum(r.rating for r in reviews) / len(reviews), 2)
    db.commit()


def main():
    ensure_placeholder_assets()
    reset_database()
    db = SessionLocal()
    try:
        cat_objs = seed_categories(db)
        brand_objs = seed_brands(db)
        products = seed_products(db, cat_objs, brand_objs)
        users = seed_demo_users(db)
        seed_orders_and_reviews(db, users, products)

        print("\n" + "=" * 60)
        print("  StyleHub database seeded successfully!")
        print("=" * 60)
        print(f"  Categories : {len(cat_objs)}")
        print(f"  Brands     : {len(brand_objs)}")
        print(f"  Products   : {len(products)}")
        print("\n  Demo login credentials:")
        print("  ---------------------------------------")
        print("  Admin  -> username: admin      | password: Admin@123")
        print("  Shopper-> username: demo_user  | password: Demo@1234")
        print("=" * 60 + "\n")
    finally:
        db.close()


if __name__ == "__main__":
    main()
