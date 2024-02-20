from sqladmin import ModelView

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
