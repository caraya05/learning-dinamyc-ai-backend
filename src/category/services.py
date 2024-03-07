from fastapi import HTTPException
from fastapi import status
from sqlalchemy.orm import Session

from category.models import Category

from category.schemas import SchemaListCategory


def get_categories_service(db: Session):
    try:
        categories = db.query(Category).all()
        return SchemaListCategory(results=categories, count=len(categories))
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Categories not found",
        )


def get_categories_active_service(db: Session):
    try:
        categories = db.query(Category).filter(Category.is_active==True).all()
        return SchemaListCategory(results=categories, count=len(categories))
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Categories not found",
        )
