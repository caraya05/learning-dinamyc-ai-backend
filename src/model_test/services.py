from .models import ItemModel
from .schemas import ItemCreate, Item

# Simulación de base de datos en memoria
_db_items = []

async def create_item(item: ItemCreate) -> Item:
    new_id = len(_db_items) + 1
    item_model = ItemModel(id=new_id, name=item.name, description=item.description)
    _db_items.append(item_model)
    return Item(**item_model.dict())

async def get_items() -> list[Item]:
    return [Item(**item.dict()) for item in _db_items]

