from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from fastapi.security import HTTPAuthorizationCredentials

from auth.utils import auth_schema

from auth.auth import auth
from auth.auth import auth_admin

from category.models import Category

from category.schemas import SchemaListCategory
from category.schemas import SchemaListCategoryActive
from category.schemas import SchemaRetrieveCategory
from category.schemas import SchemaUpdateCategory
from category.schemas import SchemaCreateCategory
from category.schemas import SchemaUpdateDocumentCategory

from category.services import get_categories_active_service
from category.services import get_category_by_id_service
from category.services import get_categories_service
from category.services import create_category_service
from category.services import update_category_service
from category.services import delete_category_service

router = APIRouter(prefix="/category", tags=["Category"])


@router.get("/active/", response_model=SchemaListCategoryActive)
async def get_categories_actives(
    skip: int = 0,
    limit: int = 10,
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves a list of categories.

    It expects the category's id in the request path.
    If the category is successfully retrieved, it returns the category's information.
    """

    try:
        categories_db, count = await get_categories_active_service(skip=skip, limit=limit)
        for category in categories_db:
            category["_id"] = str(category["_id"])
        return SchemaListCategoryActive(results=categories_db, count=count)
    except Exception as e:
        print(f"Error get categories actives: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Error get categories actives",
        )


@router.get("/", response_model=SchemaListCategory)
async def get_categories(
    skip: int = 0,
    limit: int = 10,
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves a list of categories.

    It expects the category's id in the request path.
    If the category is successfully retrieved, it returns the category's information.
    """

    try:
        categories_db, count_categories = await get_categories_service(skip=skip, limit=limit)
        for category in categories_db:
            category["_id"] = str(category["_id"])
        return SchemaListCategory(results=categories_db, count=count_categories)

    except Exception as e:
        print(f"Error get categories: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Error get categories",
        )


@router.get("/{category_id}", response_model=SchemaRetrieveCategory)
async def get_category_by_id(
    category_id: str,
    user_db: dict = Depends(auth),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint retrieves a category by its id.

    It expects the category's id in the request path.
    If the category is successfully retrieved, it returns the category's information.
    """

    try:
        return await get_category_by_id_service(category_id)

    except Exception as e:
        print(f"Error get category by id: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Error get category by id",
        )


@router.post("/", response_model=SchemaRetrieveCategory)
async def create_category(
    category: SchemaCreateCategory,
    user_db: dict = Depends(auth_admin),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint creates a new category.

    It expects the category's information in the request body.
    If the category is successfully created, it returns the category's information.
    """

    try:
        category = Category(
            **category.dict(),
            created_by=str(user_db.get("_id")),
            updated_by=str(user_db.get("_id")),
        )
        return await create_category_service(category)

    except Exception as e:
        print(f"Error create category: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Error create category",
        )


@router.put("/{category_id}", response_model=SchemaRetrieveCategory)
async def update_category(
    category_id: str,
    category: SchemaUpdateCategory,
    user_db: dict = Depends(auth_admin),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint updates a category by its id.

    It expects the category's id in the request path.
    If the category is successfully updated, it returns the category's information.
    """

    try:
        category_updated = SchemaUpdateDocumentCategory(
            **category.dict(), updated_by=str(user_db.get("_id"))
        )
        return await update_category_service(category_id, category_updated)

    except Exception as e:
        print(f"Error update category: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Error update category",
        )


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    user_db: dict = Depends(auth_admin),
    Token: HTTPAuthorizationCredentials = Depends(auth_schema),
):
    """
    This endpoint deletes a category by its id.

    It expects the category's id in the request path.
    If the category is successfully deleted, it returns the category's information.
    """

    try:
        return await delete_category_service(category_id)

    except Exception as e:
        print(f"Error delete category: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Error delete category",
        )
