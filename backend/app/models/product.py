"""
BidSmart Analytics — Product ORM Model
"""

import enum
from sqlalchemy import Column, Integer, String, Text, Enum as SQLEnum, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class ProductCondition(str, enum.Enum):
    NEW = "NEW"
    LIKE_NEW = "LIKE_NEW"
    USED = "USED"
    VINTAGE = "VINTAGE"


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    seller_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True)
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    condition_status = Column(SQLEnum(ProductCondition, native_enum=True), default=ProductCondition.USED, nullable=False)
    image_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    seller = relationship("User", back_populates="products", foreign_keys=[seller_id])
    category = relationship("Category", back_populates="products", foreign_keys=[category_id])
    auction = relationship("Auction", back_populates="product", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Product(id={self.id}, title='{self.title[:30]}', seller_id={self.seller_id})>"
