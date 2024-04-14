from sqladmin import ModelView
from sqladmin import action
from fastapi import Request
from sqlalchemy import cast, String, Boolean
from sqlalchemy.sql import Select
from starlette.responses import RedirectResponse

from game.models import Game
from utils import get_sub_token


class GameAdmin(ModelView, model=Game):
    name_plural = "Games"
    column_list = ["id", "title", "is_wrong", "story_line", ]
    column_searchable_list = ["id", "title", "category", "created_by", "is_wrong"]
    column_sorted_list = ["id"]
    column_filters = ["is_wrong"]
    can_edit = True
    can_create = False
    can_delete = True
    can_view_details = True
    can_export = True
    icon = "fa-solid fa-gamepad"
    column_default_sort = ("created_at", True)
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

    def search_query(self, stmt: Select, term: str) -> Select:
        expressions = []
        terms = term.split(",")
        for i in range(len(terms)):
            if terms[i]:
                model = self.model
                parts = self._search_fields[i].split(".")
                field = getattr(model, parts[-1])
                if parts[0] == "is_wrong":
                    if terms[i] == "1":
                        expressions.append(cast(field, Boolean) == True)
                    else:
                        expressions.append(cast(field, Boolean) == False, )
                else:
                    expressions.append(cast(field, String).ilike(f"%{terms[i]}%"))
        return stmt.filter(*expressions)

    async def on_model_change(self, form, model, is_created, request):

        sub = get_sub_token(request.session.get("token"))

        if is_created:
            form["created_by"] = sub
            form["updated_by"] = sub
        else:
            form["updated_by"] = sub

    @action("mark_wrong",
            "Mark as not wrong",
            "Are you sure you want to mark as wrong?",
            add_in_list=True,
            add_in_detail=True)
    async def action_mark_wrong(self, request: Request):
        try:
            db = request.state.db
            pks = request.query_params.get("pks").split(",")
            if pks:
                for pk in pks:
                    model: Game = await self.get_object_for_details(pk)
                    if model.is_wrong is None:
                        model.is_wrong = False
                        db.add(model)
                        db.commit()
            referer = request.headers.get("Referer")
            if referer:
                return RedirectResponse(referer)
        except Exception as e:
            print(e)
            return RedirectResponse(request.url_for("admin:list", identity=self.identity))
