from sqladmin import ModelView

from character.models import Character


class CharacterAdmin(ModelView, model=Character):
    name_plural = "Characters"
    column_list = ["id", "name", "description", "type", "image", "is_active"]
    column_searchable_list = ["type","game_id"]
    # column_sorted_list = ["username", "first_name", "last_name", "email",]
    can_edit = True
    can_create = True
    can_delete = True
    can_view_details = True
    can_export = True
    icon = "fa-solid fa-masks-theater"
    export_types = ["csv", ]
    # column_default_sort = ("created_at", True)
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
