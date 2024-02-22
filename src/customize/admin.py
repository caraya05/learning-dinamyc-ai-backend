from sqladmin import ModelView

from customize.models import Customize


class CustomizeAdmin(ModelView, model=Customize):
    name_plural = "Customizes"
    column_list = ["id", "name", "description", "type"]
    can_edit = True
    can_create = True
    can_delete = True
    can_view_details = True
    can_export = True
    icon = "fa-solid fa-icons"
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