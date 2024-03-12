from sqladmin import ModelView

from prompt.models import Prompt


class PromptAdmin(ModelView, model=Prompt):
    name_plural = "Prompts"
    column_list = ["is_active", "title", "description", ]
    can_edit = True
    can_create = True
    can_delete = True
    can_view_details = True
    column_export_list = ["id", "created_at", "created_by", "updated_at", "updated_by", "title", "description",
                          "category", "prompt_system", "is_active", ]
    can_export = True
    page_size = 50
    icon = "fa-solid fa-brain"
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
