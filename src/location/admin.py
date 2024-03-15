import ast
from sqladmin import ModelView

from location.models import Location
from utils import get_sub_token


class LocationAdmin(ModelView, model=Location):
    name_plural = "Location"
    column_list = ["id", "title", "description", "image"]
    column_searchable_list = ["id", "game_id"]
    column_sorted_list = ["id"]
    # column_filters = ["username", "first_name", "last_name", "email",]
    can_edit = True
    can_create = True
    can_delete = True
    can_view_details = True
    can_export = True
    icon = "fa-solid fa-map-location-dot"
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

        if form["config"] and isinstance(form["config"], str):
            form["config"] = ast.literal_eval(form["config"])

        if is_created:
            form["created_by"] = sub
            form["updated_by"] = sub
        else:
            form["updated_by"] = sub
