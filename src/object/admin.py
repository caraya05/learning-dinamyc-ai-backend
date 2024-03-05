from sqladmin import ModelView

from object.models import Object


class ObjectAdmin(ModelView, model=Object):
    name_plural = "Objects"
    column_list = ["id", "description", "script_id", "game_id"]
    column_searchable_list = ["characters_id", "type", "game_id"]
    # column_sorted_list = ["order", "title", "description", "script_id", "location_id", "characters_id",]
    # column_filters = ["order", "title", "description", "script_id", "location_id", "characters_id",]
    can_edit = True
    can_create = True
    can_delete = True
    can_view_details = True
    can_export = True
    icon = "fa-solid fa-boxes-packing"
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
