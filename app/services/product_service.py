"""
Product service.
Business logic for product management with search, filtering, and pagination.
"""

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from decimal import Decimal
from typing import List, Optional, Dict

from app.models.product import Product
from app.models.category import Category
from app.core.exceptions import NotFoundError, ValidationError, ConflictError
from app.utils.slug import generate_slug
from app.utils.pagination import paginate


class ProductService:
    """Service class for product operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_all_products(
        self,
        page: int = 1,
        limit: int = 20,
        category_id: Optional[str] = None,
        search: Optional[str] = None,
        min_price: Optional[Decimal] = None,
        max_price: Optional[Decimal] = None,
        in_stock: Optional[bool] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        include_inactive: bool = False
    ) -> Dict:
        """
        Get all products with filtering, search, and pagination.

        Args:
            page: Page number (default: 1)
            limit: Items per page (default: 20)
            category_id: Filter by category UUID
            search: Search in name and description
            min_price: Minimum price filter
            max_price: Maximum price filter
            in_stock: Filter by stock availability
            sort_by: Sort field (created_at, price, name)
            sort_order: Sort order (asc, desc)
            include_inactive: Include inactive products (admin only)

        Returns:
            Dict with paginated products and metadata
        """
        query = self.db.query(Product)

        # Filter inactive products (unless admin)
        if not include_inactive:
            query = query.filter(Product.is_active == True)

        # Category filter
        if category_id:
            query = query.filter(Product.category_id == category_id)

        # Search filter
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Product.name.ilike(search_term),
                    Product.description.ilike(search_term)
                )
            )

        # Price filters
        if min_price is not None:
            query = query.filter(Product.price >= min_price)
        if max_price is not None:
            query = query.filter(Product.price <= max_price)

        # Stock filter
        if in_stock is not None:
            if in_stock:
                query = query.filter(Product.stock_quantity > 0)
            else:
                query = query.filter(Product.stock_quantity == 0)

        # Sorting
        sort_column = getattr(Product, sort_by, Product.created_at)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # Paginate
        result = paginate(query, page, limit)
        return result

    def get_product_by_id(self, product_id: str, include_inactive: bool = False) -> Product:
        """
        Get product by ID.

        Args:
            product_id: Product UUID as string
            include_inactive: Include inactive products (admin only)

        Returns:
            Product object

        Raises:
            NotFoundError: If product not found or inactive
        """
        query = self.db.query(Product).filter(Product.id == product_id)

        if not include_inactive:
            query = query.filter(Product.is_active == True)

        product = query.first()
        if not product:
            raise NotFoundError("Product not found")

        return product

    def create_product(
        self,
        name: str,
        price: Decimal,
        stock_quantity: int,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        category_id: Optional[str] = None,
        image_urls: Optional[List[str]] = None,
        is_active: bool = True
    ) -> Product:
        """
        Create a new product.

        Args:
            name: Product name
            price: Product price
            stock_quantity: Available stock
            slug: URL slug (auto-generated if not provided)
            description: Product description
            category_id: Category UUID
            image_urls: List of image URLs
            is_active: Product active status

        Returns:
            Created Product object

        Raises:
            NotFoundError: If category not found
            ConflictError: If slug already exists
        """
        # Verify category exists if provided
        if category_id:
            category = self.db.query(Category).filter(Category.id == category_id).first()
            if not category:
                raise NotFoundError("Category not found")

        # Generate slug if not provided
        if not slug:
            slug = generate_slug(name, self.db, Product)
        else:
            # Check if custom slug is unique
            existing = self.db.query(Product).filter(Product.slug == slug).first()
            if existing:
                raise ConflictError("Slug already exists")

        # Create product
        product = Product(
            name=name,
            slug=slug,
            description=description,
            price=price,
            stock_quantity=stock_quantity,
            category_id=category_id,
            image_urls=image_urls or [],
            is_active=is_active
        )

        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def update_product(
        self,
        product_id: str,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        price: Optional[Decimal] = None,
        stock_quantity: Optional[int] = None,
        category_id: Optional[str] = None,
        image_urls: Optional[List[str]] = None,
        is_active: Optional[bool] = None
    ) -> Product:
        """
        Update a product.

        Args:
            product_id: Product UUID to update
            name: New name
            slug: New slug
            description: New description
            price: New price
            stock_quantity: New stock quantity
            category_id: New category UUID
            image_urls: New image URLs list
            is_active: New active status

        Returns:
            Updated Product object

        Raises:
            NotFoundError: If product or category not found
            ConflictError: If slug already exists
        """
        product = self.get_product_by_id(product_id, include_inactive=True)

        # Update fields
        if name is not None:
            product.name = name

        if slug is not None:
            # Check if slug is unique (excluding current product)
            existing = self.db.query(Product).filter(
                Product.slug == slug,
                Product.id != product_id
            ).first()
            if existing:
                raise ConflictError("Slug already exists")
            product.slug = slug

        if description is not None:
            product.description = description

        if price is not None:
            product.price = price

        if stock_quantity is not None:
            product.stock_quantity = stock_quantity

        if category_id is not None:
            # Verify category exists
            category = self.db.query(Category).filter(Category.id == category_id).first()
            if not category:
                raise NotFoundError("Category not found")
            product.category_id = category_id

        if image_urls is not None:
            product.image_urls = image_urls

        if is_active is not None:
            product.is_active = is_active

        self.db.commit()
        self.db.refresh(product)
        return product

    def delete_product(self, product_id: str) -> None:
        """
        Soft delete a product (set is_active=False).

        Args:
            product_id: Product UUID to delete

        Raises:
            NotFoundError: If product not found
        """
        product = self.get_product_by_id(product_id, include_inactive=True)

        # Soft delete
        product.is_active = False
        self.db.commit()
