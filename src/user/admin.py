from sqladmin import ModelView

from user.models import User
from user.utils import get_password_hash

from utils import get_sub_token


class UserAdmin(ModelView, model=User):
    name_plural = "Users"
    column_list = ["username", "email", "number_of_creation_attempts", "attempt_to_create", "stars", ]
    # column_searchable_list = ["username", "first_name", "last_name", "email",]
    # column_sorted_list = ["username", "first_name", "last_name", "email",]
    # column_filters = ["username", "first_name", "last_name", "email",]
    can_edit = True
    can_create = True
    can_delete = True
    can_view_details = True
    can_export = True
    icon = "fa-solid fa-user"

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
            form["password"] = get_password_hash(form["password"])
            form["created_by"] = sub
            form["updated_by"] = sub
        else:
            if str(model.password) != form["password"]:
                form["password"] = get_password_hash(form["password"])
            form["updated_by"] = sub
