from sqladmin import ModelView

from prompt.models import Prompt


class PromptAdmin(ModelView, model=Prompt):
    name_plural = "Prompts"
    column_list = ["is_active", "title", "description", ]
    can_edit = True
    can_create = True
    can_delete = True
    can_view_details = True
    can_export = True
    icon = "fa-solid fa-prompt"
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
