from typing import Any

from sqladmin import ModelView
from sqlalchemy.orm import joinedload

from config import settings
from sound.models import Sound

from utils import get_sub_token


class SoundAdmin(ModelView, model=Sound):
    name_plural = "Sounds"
    column_list = ["id","name", "description", "category", "sound", "is_active", "is_deleted", ]
    column_searchable_list = [Sound.name, Sound.description, Sound.category, Sound.type, ]
    column_sorted_list = ["name", "category", "type", ]
    column_filters = [Sound.is_active, Sound.is_deleted, ]

    column_details_exclude_list = ["created_at", "created_by", "updated_at", "updated_by", "file"]
    form_columns = ["name", "description", "file", "category", "type", "is_active", "is_deleted", ]

    can_edit = True
    can_create = True
    can_delete = True
    can_view_details = True
    can_export = True
    icon = "fa-solid fa-music"

    form_widget_args = {
        "created_at": {
            "readonly": True,
            "disabled": True
        },
        "created_by": {
            "readonly": True,
            "disabled": True
        },
        "updated_at": {
            "readonly": True,
            "disabled": True
        },
        "updated_by": {
            "readonly": True,
            "disabled": True
        },
    }

    async def get_object_for_edit(self, value: Any) -> Any:

        stmt = self._stmt_by_identifier(value)

        for relation in self._form_relations:
            stmt = stmt.options(joinedload(relation))

        obj = await self._get_object_by_pk(stmt)
        obj.file = None
        return obj

    async def on_model_change(self, form, model, is_created, request):

        sub = get_sub_token(request.session.get("token"))

        if is_created:
            form["created_by"] = sub
            form["updated_by"] = sub
        else:
            form["updated_by"] = sub

        if form["file"] and form["file"].filename != None:
            form["file"].filename = f"sounds/{model.id}.{form['file'].filename.split('.')[-1]}"
            form["sound"] = f"{settings.URL_DIGITAL_OCEAN}{form['file'].filename}"
