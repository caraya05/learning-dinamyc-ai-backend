from sqladmin import ModelView

from .models import User


class UserAdmin(ModelView, model=User):
    name_plural = "Users"
    column_list = ["username", "company_name", "email",]
    # column_searchable_list = ["username", "first_name", "last_name", "email",]
    # column_sorted_list = ["username", "first_name", "last_name", "email",]
    # column_filters = ["username", "first_name", "last_name", "email",]
    can_edit = True
    can_create = True
    can_delete = True
    can_view_details = True
    can_export = True
    icon = "fa-solid fa-user"

