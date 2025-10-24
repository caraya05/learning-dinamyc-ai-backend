from fastapi import APIRouter, HTTPException, status, Depends, Query
from .schemas import ItemCreate, Item
from .services import create_item, get_items
from typing import Annotated

router = APIRouter(prefix="/model-test", tags=["Model Test"])

# Ejemplo de dependencia: autenticación simulada
def get_current_user(token: str = Depends(lambda: "fake-token")):
    if token != "fake-token":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return {"username": "testuser"}

def pagination_params(
    skip: int = Query(0, ge=0, description="Número de elementos a omitir"),
    limit: int = Query(10, ge=1, le=100, description="Número máximo de elementos a retornar")
):
    return {"skip": skip, "limit": limit}

@router.post("/items", response_model=Item, status_code=status.HTTP_201_CREATED)
async def create_new_item(
    item: ItemCreate,
    user: Annotated[dict, Depends(get_current_user)]
):
    return await create_item(item)

@router.get("/items", response_model=list[Item])
async def list_items(
    user: Annotated[dict, Depends(get_current_user)],
    pagination: Annotated[dict, Depends(pagination_params)]
):
    """Lista todos los ítems de prueba con paginación."""
    items = await get_items()
    skip = pagination["skip"]
    limit = pagination["limit"]
    return items[skip:skip+limit]
