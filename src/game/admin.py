from sqladmin import ModelView

from .models import Game


class GameAdmin(ModelView, model=Game):
    name_plural = "Games"
    column_list = ["title", "description", "photo", "is_active"]
    # column_searchable_list = ["username", "first_name", "last_name", "email",]
    # column_sorted_list = ["username", "first_name", "last_name", "email",]
    # column_filters = ["username", "first_name", "last_name", "email",]
    can_edit = True
    can_create = True
    can_delete = True
    can_view_details = True
    can_export = True
    icon = "fa-solid fa-user"
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
