from sqladmin import ModelView

from category.models import Category
from utils import get_sub_token


class CategoryAdmin(ModelView, model=Category):
    name_plural = "Categories"
    column_list = ["id", "is_active", "name", "description", ]
    column_searchable_list = ["name", "description", ]
    can_edit = True
    can_create = True
    can_delete = True
    can_view_details = True
    can_export = True
    column_export_list = ["id", "name", "description", "created_at", "created_by", "updated_at", "updated_by", ]
    icon = "fa-solid fa-layer-group"
    export_types = ["csv", ]
    column_default_sort = [("name", True)]
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
