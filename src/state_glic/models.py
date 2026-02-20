from datetime import datetime

from pydantic import BaseModel


class StateGLIC(BaseModel):
    element_id: str
    type_element: str
    order: int
    state: str
    data: dict = None
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str
