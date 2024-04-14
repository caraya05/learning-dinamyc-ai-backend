from sqladmin import ModelView
from sqlalchemy import cast, Boolean, String
from sqlalchemy.sql import Select

from user.models import User
from user.utils import get_password_hash

from utils import get_sub_token
from utils import resize_image

from config import settings


class UserAdmin(ModelView, model=User):
    name_plural = "Users"
    column_list = ["username", "email", "number_of_creation_attempts", "attempt_to_create", "stars", ]
    column_searchable_list = [User.attempt_to_create, ]
    # column_sorted_list = ["username", "first_name", "last_name", "email",]
    column_filters = [User.attempt_to_create, ]

    column_details_exclude_list = ["password", "uid", "provider", "last_access", "is_active", "is_superuser", "is_staff",
                                   "created_at", "created_by", "updated_at", "updated_by", "file", ]

    form_columns = ["username", "email", "password", "number_of_creation_attempts", "attempt_to_create", "stars", "file", ]

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

        if form["file"].filename:
            form["file"] = resize_image(form["file"], (200, 200))
            form["file"].filename = f"user/{model.id}.{form['file'].filename.split('.')[-1]}"
            form["photo"] = f"{settings.URL_DIGITAL_OCEAN}{form['file'].filename}"

    def search_query(self, stmt: Select, term: str) -> Select:
        expressions = []
        terms = term.split(",")
        for i in range(len(terms)):
            if terms[i]:
                model = self.model
                parts = self._search_fields[i].split(".")
                field = getattr(model, parts[-1])
                if parts[0] == "attempt_to_create":
                    if terms[i] == "1":
                        expressions.append(cast(field, Boolean) == True)
                    else:
                        expressions.append(cast(field, Boolean) == False, )
                else:
                    expressions.append(cast(field, String).ilike(f"%{terms[i]}%"))
        return stmt.filter(*expressions)
