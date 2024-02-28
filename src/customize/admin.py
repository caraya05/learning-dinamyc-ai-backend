from sqladmin import ModelView

from customize.models import Customize


class CustomizeAdmin(ModelView, model=Customize):
    name_plural = "Customizes"
    column_list = ["id", "gender", "type_customize", "reference_ui", "description", ]
    column_searchable_list = ["gender", "type_customize", "reference_ui", ]
    can_edit = True
    can_create = True
    can_delete = True
    can_view_details = True
    can_export = True
    column_export_list = ["id", "reference_ui", "gender", "description", "type_customize",
                          "created_at", "created_by", "updated_at", "updated_by", ]
    icon = "fa-solid fa-icons"
    export_types = ["csv", ]
    column_default_sort = [("gender", True), ("type_customize", True)]
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
