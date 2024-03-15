from sqladmin import ModelView

from game.models import Game
from utils import get_sub_token


class GameAdmin(ModelView, model=Game):
    name_plural = "Games"
    column_list = ["id", "title", "story_line", "image"]
    column_searchable_list = ["id", "title","category",]
    column_sorted_list = ["id"]
    column_filters = ["id"]
    can_edit = True
    can_create = False
    can_delete = True
    can_view_details = True
    can_export = True
    icon = "fa-solid fa-gamepad"
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

        if is_created:
            form["created_by"] = sub
            form["updated_by"] = sub
        else:
            form["updated_by"] = sub

