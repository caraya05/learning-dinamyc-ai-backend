import ast
from sqladmin import ModelView

from character.models import Character
from utils import get_sub_token


class CharacterAdmin(ModelView, model=Character):
    name_plural = "Characters"
    column_list = ["id", "type", "name", "description", ]
    column_searchable_list = ["id", "type", "game_id"]
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

    async def on_model_change(self, form, model, is_created, request):

        sub = get_sub_token(request.session.get("token"))

        if form["extra_data"] and isinstance(form["extra_data"], str):
            form["extra_data"] = ast.literal_eval(form["extra_data"])

        if form["text_idle"] and isinstance(form["text_idle"], str):
            form["text_idle"] = ast.literal_eval(form["text_idle"])

        if is_created:
            form["created_by"] = sub
            form["updated_by"] = sub
        else:
            form["updated_by"] = sub
