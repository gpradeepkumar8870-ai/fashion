"""
StyleHub - Pydantic Schemas (request/response validation)
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# ---------------------- Auth / User ----------------------

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=80)
    email: EmailStr
    password: str = Field(..., min_length=6)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None


class UserLogin(BaseModel):
    username: str  # username OR email
    password: str


class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    chest_cm: Optional[float] = None
    waist_cm: Optional[float] = None
    hip_cm: Optional[float] = None
    preferred_fit: Optional[str] = None


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    is_admin: bool = False
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    chest_cm: Optional[float] = None
    waist_cm: Optional[float] = None
    hip_cm: Optional[float] = None
    preferred_fit: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------------------- Category / Brand ----------------------

class CategoryOut(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    image: Optional[str] = None
    parent_id: Optional[int] = None

    class Config:
        from_attributes = True


class BrandOut(BaseModel):
    id: int
    name: str
    logo: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------- Product ----------------------

class ProductImageOut(BaseModel):
    id: int
    image_url: str
    is_primary: bool

    class Config:
        from_attributes = True


class ProductVariantOut(BaseModel):
    id: int
    size: str
    color: str
    color_code: Optional[str] = None
    stock: int
    sku: str

    class Config:
        from_attributes = True


class ProductCardOut(BaseModel):
    """Lightweight product representation used in listing grids."""
    id: int
    name: str
    slug: str
    price: float
    discount_price: Optional[float] = None
    effective_price: float
    discount_percent: int
    rating: float
    total_reviews: int
    is_featured: bool
    is_bestseller: bool
    category: Optional[CategoryOut] = None
    brand: Optional[BrandOut] = None
    primary_image: Optional[str] = None
    available_sizes: List[str] = []
    available_colors: List[str] = []

    class Config:
        from_attributes = True


class ProductDetailOut(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    price: float
    discount_price: Optional[float] = None
    effective_price: float
    discount_percent: int
    rating: float
    total_reviews: int
    is_featured: bool
    is_bestseller: bool
    gender: str
    fit_type: str
    material: Optional[str] = None
    category: Optional[CategoryOut] = None
    brand: Optional[BrandOut] = None
    images: List[ProductImageOut] = []
    variants: List[ProductVariantOut] = []

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    products: List[ProductCardOut]


# ---------------------- Cart ----------------------

class CartItemAdd(BaseModel):
    variant_id: int
    quantity: int = Field(1, ge=1, le=20)


class CartItemUpdate(BaseModel):
    quantity: int = Field(..., ge=1, le=20)


class CartItemOut(BaseModel):
    id: int
    variant_id: int
    product_id: int
    product_name: str
    product_image: Optional[str] = None
    size: str
    color: str
    unit_price: float
    quantity: int
    stock: int
    subtotal: float

    class Config:
        from_attributes = True


class CartOut(BaseModel):
    items: List[CartItemOut]
    total_items: int
    subtotal: float
    estimated_tax: float
    estimated_shipping: float
    total: float


# ---------------------- Orders / Checkout ----------------------

class ShippingInfo(BaseModel):
    shipping_address: str
    shipping_city: str
    shipping_state: str
    shipping_zip: str
    shipping_country: str = "India"


class CheckoutRequest(BaseModel):
    shipping: ShippingInfo
    payment_method: str = Field(..., description="card | upi | cod | netbanking")
    notes: Optional[str] = None


class OrderItemOut(BaseModel):
    id: int
    product_name: str
    product_image: Optional[str] = None
    variant_size: str
    variant_color: str
    quantity: int
    price: float

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: int
    order_number: str
    total_amount: float
    shipping_address: str
    shipping_city: str
    shipping_state: str
    shipping_zip: str
    shipping_country: str
    payment_method: str
    payment_status: str
    order_status: str
    notes: Optional[str] = None
    created_at: datetime
    items: List[OrderItemOut] = []

    class Config:
        from_attributes = True


# ---------------------- Reviews ----------------------

class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class ReviewOut(BaseModel):
    id: int
    rating: int
    comment: Optional[str] = None
    is_verified_purchase: bool
    username: str
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------- Wishlist ----------------------

class WishlistOut(BaseModel):
    id: int
    product: ProductCardOut
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------- Size Recommendation ----------------------

class SizeRecommendationRequest(BaseModel):
    height_cm: float = Field(..., gt=50, lt=250)
    weight_kg: float = Field(..., gt=10, lt=300)
    chest_cm: Optional[float] = None
    waist_cm: Optional[float] = None
    hip_cm: Optional[float] = None
    age: Optional[int] = None
    gender: str = Field("unisex", description="men | women | unisex")
    fit_preference: str = Field("regular", description="slim | regular | loose")
    category_slug: Optional[str] = None


class SizeRecommendationResponse(BaseModel):
    recommended_size: str
    confidence: float
    bmi: float
    alternate_size: Optional[str] = None
    explanation: str
    size_chart: dict
