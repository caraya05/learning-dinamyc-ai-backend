import ast
from sqladmin import ModelView

from scene.models import Scene
from utils import get_sub_token


class SceneAdmin(ModelView, model=Scene):
    name_plural = "Scenes"
    column_list = ["id", "dynamic", "order", "title", "description", "script_id", "location_id", "characters_id", ]
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

    async def on_model_change(self, form, model, is_created, request):

        sub = get_sub_token(request.session.get("token"))

        if form["characters_id"] and isinstance(form["characters_id"], str):
            form["characters_id"] = ast.literal_eval(form["characters_id"])

        if form["start_dialogues"] and isinstance(form["start_dialogues"], str):
            form["start_dialogues"] = ast.literal_eval(form["start_dialogues"])

        if form["end_dialogues"] and isinstance(form["end_dialogues"], str):
            form["end_dialogues"] = ast.literal_eval(form["end_dialogues"])

        if form["questions"] and isinstance(form["questions"], str):
            form["questions"] = ast.literal_eval(form["questions"])

        if is_created:
            form["created_by"] = sub
            form["updated_by"] = sub
        else:
            form["updated_by"] = sub
