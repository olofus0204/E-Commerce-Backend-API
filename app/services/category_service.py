"""
Category service.
Business logic for category management with hierarchical support.
"""

from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.category import Category
from app.models.product import Product
from app.core.exceptions import NotFoundError, ValidationError, ConflictError
from app.utils.slug import generate_slug


class CategoryService:
    """Service class for category operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_all_categories(
        self,
        parent_id: Optional[str] = None,
        include_children: bool = True
    ) -> List[Category]:
        """
        Get all categories, optionally filtered by parent.

        Args:
            parent_id: Filter by parent category UUID
            include_children: Include subcategories (default: True)

        Returns:
            List of Category objects
        """
        query = self.db.query(Category)

        if parent_id is not None:
            query = query.filter(Category.parent_id == parent_id)
        else:
            # Get only top-level categories if no parent specified
            query = query.filter(Category.parent_id == None)

        categories = query.all()
        return categories

    def get_category_by_id(self, category_id: str) -> Category:
        """
        Get category by ID.

        Args:
            category_id: Category UUID as string

        Returns:
            Category object

        Raises:
            NotFoundError: If category not found
        """
        category = self.db.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise NotFoundError("Category not found")
        return category

    def create_category(
        self,
        name: str,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        parent_id: Optional[str] = None
    ) -> Category:
        """
        Create a new category.

        Args:
            name: Category name
            slug: URL slug (auto-generated if not provided)
            description: Optional description
            parent_id: Optional parent category UUID

        Returns:
            Created Category object

        Raises:
            NotFoundError: If parent category not found
            ConflictError: If slug already exists
        """
        # Verify parent exists if provided
        if parent_id:
            parent = self.db.query(Category).filter(Category.id == parent_id).first()
            if not parent:
                raise NotFoundError("Parent category not found")

        # Generate slug if not provided
        if not slug:
            slug = generate_slug(name, self.db, Category)
        else:
            # Check if custom slug is unique
            existing = self.db.query(Category).filter(Category.slug == slug).first()
            if existing:
                raise ConflictError("Slug already exists")

        # Create category
        category = Category(
            name=name,
            slug=slug,
            description=description,
            parent_id=parent_id
        )

        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def update_category(
        self,
        category_id: str,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        parent_id: Optional[str] = None
    ) -> Category:
        """
        Update a category.

        Args:
            category_id: Category UUID to update
            name: New name
            slug: New slug
            description: New description
            parent_id: New parent UUID (null to remove parent)

        Returns:
            Updated Category object

        Raises:
            NotFoundError: If category or parent not found
            ValidationError: If circular parent reference detected
            ConflictError: If slug already exists
        """
        category = self.get_category_by_id(category_id)

        # Update name
        if name is not None:
            category.name = name

        # Update slug
        if slug is not None:
            # Check if slug is unique (excluding current category)
            existing = self.db.query(Category).filter(
                Category.slug == slug,
                Category.id != category_id
            ).first()
            if existing:
                raise ConflictError("Slug already exists")
            category.slug = slug

        # Update description
        if description is not None:
            category.description = description

        # Update parent
        if parent_id is not None:
            if parent_id == str(category.id):
                raise ValidationError("Category cannot be its own parent")

            # Check for circular reference
            if parent_id:
                parent = self.db.query(Category).filter(Category.id == parent_id).first()
                if not parent:
                    raise NotFoundError("Parent category not found")

                # Check if parent is a descendant of current category
                if self._is_descendant(category.id, parent_id):
                    raise ValidationError("Circular parent reference detected")

            category.parent_id = parent_id

        self.db.commit()
        self.db.refresh(category)
        return category

    def delete_category(self, category_id: str) -> None:
        """
        Delete a category.

        Args:
            category_id: Category UUID to delete

        Raises:
            NotFoundError: If category not found
            ValidationError: If category has products or subcategories
        """
        category = self.get_category_by_id(category_id)

        # Check if category has products
        products_count = self.db.query(Product).filter(Product.category_id == category_id).count()
        if products_count > 0:
            raise ValidationError("Cannot delete category with products")

        # Check if category has subcategories
        subcategories_count = self.db.query(Category).filter(Category.parent_id == category_id).count()
        if subcategories_count > 0:
            raise ValidationError("Cannot delete category with subcategories")

        self.db.delete(category)
        self.db.commit()

    def _is_descendant(self, ancestor_id: str, descendant_id: str) -> bool:
        """
        Check if descendant_id is a descendant of ancestor_id.

        Args:
            ancestor_id: Potential ancestor category ID
            descendant_id: Potential descendant category ID

        Returns:
            True if descendant_id is a descendant of ancestor_id
        """
        current = self.db.query(Category).filter(Category.id == descendant_id).first()

        while current and current.parent_id:
            if str(current.parent_id) == str(ancestor_id):
                return True
            current = self.db.query(Category).filter(Category.id == current.parent_id).first()

        return False
