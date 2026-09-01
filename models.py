"""
StyleHub - Database Models (SQLAlchemy ORM)
Works identically on SQLite (default/dev) and MySQL (production) -
just flip DATABASE_MODE in .env.
"""
from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    image = Column(String(255))
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    products = relationship("Product", back_populates="category")
    children = relationship("Category", back_populates="parent", remote_side=[parent_id])
    parent = relationship("Category", back_populates="children", remote_side=[id])


class Brand(Base):
    __tablename__ = "brands"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    logo = Column(String(255))
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    products = relationship("Product", back_populates="brand")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    discount_price = Column(Float, nullable=True)
    rating = Column(Float, default=0)
    total_reviews = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    is_bestseller = Column(Boolean, default=False)
    gender = Column(String(20), default="unisex")  # men, women, kids, unisex
    fit_type = Column(String(30), default="regular")  # slim, regular, loose, oversized
    material = Column(String(100), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    brand_id = Column(Integer, ForeignKey("brands.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    category = relationship("Category", back_populates="products")
    brand = relationship("Brand", back_populates="products")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="product", cascade="all, delete-orphan")
    wishlisted_by = relationship("WishlistItem", back_populates="product", cascade="all, delete-orphan")

    @property
    def effective_price(self):
        return self.discount_price if self.discount_price else self.price

    @property
    def discount_percent(self):
        if self.discount_price and self.price:
            return round((1 - (self.discount_price / self.price)) * 100)
        return 0


class ProductVariant(Base):
    __tablename__ = "product_variants"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    size = Column(String(20))   # XS, S, M, L, XL, XXL, or numeric
    color = Column(String(50))
    color_code = Column(String(7))  # Hex color code, e.g. #1A1A1A
    stock = Column(Integer, default=0)
    sku = Column(String(100), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="variants")
    cart_items = relationship("CartItem", back_populates="variant")


class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    image_url = Column(String(255), nullable=False)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="images")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    first_name = Column(String(50))
    last_name = Column(String(50))
    phone = Column(String(15))
    address = Column(Text)
    city = Column(String(50))
    state = Column(String(50))
    zip_code = Column(String(10))
    country = Column(String(50), default="India")
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Body measurements (used for AI-based size recommendation)
    height_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=True)
    chest_cm = Column(Float, nullable=True)
    waist_cm = Column(Float, nullable=True)
    hip_cm = Column(Float, nullable=True)
    preferred_fit = Column(String(30), nullable=True)  # slim, regular, loose

    orders = relationship("Order", back_populates="user")
    cart = relationship("Cart", back_populates="user", uselist=False)
    reviews = relationship("Review", back_populates="user")
    wishlist_items = relationship("WishlistItem", back_populates="user", cascade="all, delete-orphan")


class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="cart")
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id"))
    variant_id = Column(Integer, ForeignKey("product_variants.id"))
    quantity = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

    cart = relationship("Cart", back_populates="items")
    variant = relationship("ProductVariant", back_populates="cart_items")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    total_amount = Column(Float, nullable=False)
    shipping_address = Column(Text, nullable=False)
    shipping_city = Column(String(50))
    shipping_state = Column(String(50))
    shipping_zip = Column(String(10))
    shipping_country = Column(String(50))
    payment_method = Column(String(50))
    payment_status = Column(String(20), default="pending")   # pending, paid, failed, refunded
    order_status = Column(String(20), default="pending")     # pending, confirmed, shipped, delivered, cancelled
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    product_name = Column(String(200))
    product_image = Column(String(255), nullable=True)
    variant_size = Column(String(20))
    variant_color = Column(String(50))
    quantity = Column(Integer)
    price = Column(Float)

    order = relationship("Order", back_populates="items")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    rating = Column(Integer)
    comment = Column(Text)
    is_verified_purchase = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="reviews")
    user = relationship("User", back_populates="reviews")


class WishlistItem(Base):
    __tablename__ = "wishlist_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="wishlist_items")
    product = relationship("Product", back_populates="wishlisted_by")
