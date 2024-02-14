from sqladmin import ModelView

from .models import Game


class GameAdmin(ModelView, model=Game):
    name_plural = "Games"
    column_list = ["title", "story_line", "image"]
    column_searchable_list = ["id"]
    column_sorted_list = ["id"]
    column_filters = ["id"]
    can_edit = True
    can_create = True
    can_delete = True
    can_view_details = True
    can_export = True
    icon = "fa-solid device-gamepad"
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
