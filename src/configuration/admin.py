import ast
from sqladmin import ModelView

from configuration.models import Configuration
from utils import get_sub_token


class ConfigurationAdmin(ModelView, model=Configuration):
    name_plural = "Configurations"
    column_list = ["featured_games", "popular_games", "games_by_category"]
    # column_searchable_list = ["id"]
    # column_sorted_list = ["id"]
    # column_filters = ["id"]
    can_edit = True
    can_create = True
    can_delete = False
    can_view_details = True
    can_export = True
    icon = "fa-solid fa-gear"
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

        if isinstance(form["featured_games"], str):
            form["featured_games"] = ast.literal_eval(form["featured_games"])
        if isinstance(form["popular_games"], str):
            form["popular_games"] = ast.literal_eval(form["popular_games"])
        if isinstance(form["games_by_category"], str):
            form["games_by_category"] = ast.literal_eval(form["games_by_category"])

        if is_created:
            form["created_by"] = sub
            form["updated_by"] = sub
        else:
            form["updated_by"] = sub
