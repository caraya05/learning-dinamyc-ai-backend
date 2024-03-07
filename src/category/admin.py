from sqladmin import ModelView

from category.models import Category


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
