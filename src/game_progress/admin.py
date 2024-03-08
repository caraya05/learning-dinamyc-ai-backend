from sqladmin import ModelView

from game_progress.models import GameProgress
from utils import get_sub_token


class GameProgressAdmin(ModelView, model=GameProgress):
    name_plural = "Game Progress"
    column_list = ["id", "game_id", "scene_id", "is_complete", "user_id"]
    # column_searchable_list = ["username", "first_name", "last_name", "email",]
    # column_sorted_list = ["username", "first_name", "last_name", "email",]
    # column_filters = ["username", "first_name", "last_name", "email",]
    can_edit = True
    can_create = True
    can_delete = True
    can_view_details = True
    can_export = True
    icon = "fa-solid fa-bars-progress"

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

