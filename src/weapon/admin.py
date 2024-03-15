import ast

from sqladmin import ModelView

from utils import get_sub_token
from weapon.models import Weapon


class WeaponAdmin(ModelView, model=Weapon):
    name_plural = "Weapons"
    column_list = ["id", "order", "title", "description", "script_id", "location_id", "characters_id"]
    # column_searchable_list = ["order", "title", "description", "script_id", "location_id", "characters_id",]
    # column_sorted_list = ["order", "title", "description", "script_id", "location_id", "characters_id",]
    # column_filters = ["order", "title", "description", "script_id", "location_id", "characters_id",]
    can_edit = True
    can_create = True
    can_delete = True
    can_view_details = True
    can_export = True
    icon = "fa-solid fa-gun"
    column_default_sort = ("created_at", True)
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

    async def on_model_change(self, form, model, is_created, request):

        sub = get_sub_token(request.session.get("token"))

        if form["extra_data"] and isinstance(form["extra_data"], str):
            form["extra_data"] = ast.literal_eval(form["extra_data"])

        if is_created:
            form["created_by"] = sub
            form["updated_by"] = sub
        else:
            form["updated_by"] = sub

