from sqladmin import ModelView

from script.models import Script


class ScriptAdmin(ModelView, model=Script):
    name_plural = "Scripts"
    column_list = ["id", "title", "description", "game_id",]
    # column_searchable_list = ["title", "description", "game_id",]
    # column_sorted_list = ["title", "description", "game_id",]
    # column_filters = ["title", "description", "game_id",]
    can_edit = True
    can_create = True
    can_delete = True
    can_view_details = True
    can_export = True
    icon = "fa-solid fa-script"