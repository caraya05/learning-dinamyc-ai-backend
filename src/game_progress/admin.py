from sqladmin import ModelView

from game_progress.models import GameProgress


class GameProgressAdmin(ModelView, model=GameProgress):
    name_plural = "GameProgress"
    column_list = ["id", "game_id", "scene_id", "is_complete", "user_id"]
    # column_searchable_list = ["username", "first_name", "last_name", "email",]
    # column_sorted_list = ["username", "first_name", "last_name", "email",]
    # column_filters = ["username", "first_name", "last_name", "email",]
    can_edit = True
    can_create = True
    can_delete = True
    can_view_details = True
    can_export = True
    icon = "fa-solid fa-bars-progress"
