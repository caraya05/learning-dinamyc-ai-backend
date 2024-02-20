from sqladmin import ModelView

from scene.models import Scene


class SceneAdmin(ModelView, model=Scene):
    name_plural = "Scenes"
    column_list = ["id", "order", "title", "description", "script_id", "location_id", "characters_id", ]
    column_searchable_list = ["order", "title", "description", "script_id", "location_id", "game_id", ]
    column_default_sort = [("created_at", True), ("script_id", True), ("order", False)]
    column_filters = ["order", "title", "description", "script_id", "location_id", "game_id", ]
    can_edit = True
    can_create = True
    can_delete = True
    can_view_details = True
    can_export = True
    export_types = ["csv"]
    icon = "fa-solid fa-film"
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
