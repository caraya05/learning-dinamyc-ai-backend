from sqladmin import ModelView

from record_daily.models import DailyRecord

from utils import get_sub_token


class DailyRecordAdmin(ModelView, model=DailyRecord):
    name_plural = "Daily Records"
    column_list = ["balance", "expenses", "games_created", "sets_with_errors", "attempts_to_create_without_balance", ]
    # column_searchable_list = [User.attempt_to_create, ]
    # column_sorted_list = ["username", "first_name", "last_name", "email",]
    # column_filters = [User.attempt_to_create, ]

    # column_details_exclude_list = ["password", "uid", "provider", "last_access", "is_active", "is_superuser", "is_staff",
    #                                "created_at", "created_by", "updated_at", "updated_by", "file", ]

    # form_columns = ["balance", "expenses", "games_created", "sets_with_errors", "attempts_to_create_without_balance", ]
    # can_edit = True
    # can_create = True
    # can_delete = True
    # can_view_details = True
    # can_export = True
    icon = "fa-solid fa-newspaper"
    export_types = ["csv", "by_date", "by_user", ]

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
