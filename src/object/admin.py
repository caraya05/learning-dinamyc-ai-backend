from sqladmin import ModelView

from object.models import Object


class ObjectAdmin(ModelView, model=Object):
    name_plural = "Objects"
    column_list = ["id", "order", "title", "description", "script_id", "location_id", "characters_id"]
    # column_searchable_list = ["order", "title", "description", "script_id", "location_id", "characters_id",]
    # column_sorted_list = ["order", "title", "description", "script_id", "location_id", "characters_id",]
    # column_filters = ["order", "title", "description", "script_id", "location_id", "characters_id",]
    can_edit = True
    can_create = True
    can_delete = True
    can_view_details = True
    can_export = True
    icon = "fa-solid fa-boxes-packing"
