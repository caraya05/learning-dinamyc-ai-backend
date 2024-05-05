from bson import ObjectId
from fastapi import HTTPException
from fastapi import status

from core.database import db

from category.models import Category

from category.schemas import SchemaUpdateDocumentCategory


async def get_categories_service(skip: int, limit: int):
    try:
        count_categories = 0
        if categories := await db["category"].find().to_list(None):
            count_categories = len(categories)
            categories = await db["category"].find().skip(skip).limit(limit).to_list(None)
        return categories, count_categories
    except Exception as e:
        print(f"Error get categories service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Categories not found",
        )


async def get_categories_active_service(skip: int, limit: int):
    try:
        count_categories = 0
        if categories_db := await db["category"].find({"is_active": True}).to_list(None):
            count_categories = len(categories_db)
            categories_db = await db["category"].find({"is_active": True}).skip(skip).limit(limit).to_list(None)
        return categories_db, count_categories
    except Exception as e:
        print(f"Error get categories actives service: {str(e)}")
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Categories not found",
    )


async def get_category_by_id_service(category_id: str):
    try:
        if category := await db["category"].find_one({"_id": ObjectId(category_id)}):
            return category
    except Exception as e:
        print(f"Error get category by id service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not found",
        )


async def create_category_service(category: Category):
    try:
        new_category = await db["category"].insert_one(category.dict())
        category_created = await db["category"].find_one({"_id": new_category.inserted_id})
        return category_created
    except Exception as e:
        print(f"Error create category service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not created",
        )


async def update_category_service(category_id: str, category: SchemaUpdateDocumentCategory):
    try:
        if category_updated := await db["category"].update_one({"_id": ObjectId(category_id)}, {"$set": category.dict()}):
            if category_updated.modified_count:
                category_db = await db["category"].find_one({"_id": ObjectId(category_id)})
                return category_db
    except Exception as e:
        print(f"Error update category service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not updated",
        )


async def delete_category_service(category_id: str):
    try:
        if category_deleted := await db["category"].delete_one({"_id": ObjectId(category_id)}):
            if category_deleted.deleted_count:
                return True
    except Exception as e:
        print(f"Error delete category service: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category not deleted",
        )
