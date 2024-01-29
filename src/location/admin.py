from sqladmin import ModelView

from location.models import Location


class LocationAdmin(ModelView, model=Location):
    name_plural = "Location"
    column_list = ["id", "title", "description", "image"]
    # column_searchable_list = ["username", "first_name", "last_name", "email",]
    # column_sorted_list = ["username", "first_name", "last_name", "email",]
    # column_filters = ["username", "first_name", "last_name", "email",]
    can_edit = True
    can_create = True
    can_delete = True
    can_view_details = True
    can_export = True
    icon = "fa-solid fa-user"
