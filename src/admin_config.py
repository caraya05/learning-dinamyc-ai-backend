# from fastapi import Request
# from fastapi_jwt_auth import AuthJWT
# import jwt
#
# from config import settings
# from datetime import datetime, timedelta
# from sqladmin.authentication import AuthenticationBackend
#
# from user.services import get_user_by_field
# from user.utils import verify_password

#
# def get_db(request: Request):
#     return request.state.db
#
#
# auth = AuthJWT()
#
#
# class AdminAuth(AuthenticationBackend):
#
#     async def login(self, request: Request) -> bool:
#         form = await request.form()
#         username, password = form["username"], form["password"]
#         if not username or not password:
#             return False
#         if username != settings.admin_superuser or password != settings.admin_superuser_password:
#             user_db = get_user_by_field(get_db(request), "username", username)
#             if not user_db:
#                 return False
#             if not verify_password(password, user_db.password):
#                 return False
#             if not user_db.is_superuser or not user_db.is_active:
#                 return False
#             request.session.update({"token": auth.create_access_token(
#                 subject=user_db.username,
#                 expires_time=timedelta(days=1),
#                 algorithm="HS512"
#             )})
#             return True
#         else:
#             request.session.update({
#                 "token": auth.create_access_token(
#                     subject="admin",
#                     expires_time=timedelta(days=1),
#                     algorithm="HS512")})
#
#             return True
#         # request.session.update(
#         #     {"valid": int(datetime.now().timestamp() + (60 * 120))}
#         # )  # 10 minutes
#         # return True
#
#     async def logout(self, request: Request) -> bool:
#         request.session.clear()
#         return True
#
#     async def authenticate(self, request: Request) -> bool:
#         token = request.session.get("token")
#         if not token:
#             request.session.clear()
#             return False
#         try:
#             payload = jwt.decode(token, settings.authjwt_secret_key, algorithms="HS512")
#             if payload["exp"] < datetime.now().timestamp():
#                 request.session.clear()
#                 return False
#             request.session.update({
#                 "access": auth.create_access_token(
#                     subject=payload["sub"],
#                     expires_time=timedelta(minutes=120))
#             })
#             return True
#         except Exception as e:
#             print(e)
#             request.session.clear()
#             return False
#
#
# authentication_backend = AdminAuth(secret_key=settings.authjwt_secret_key)

from starlette.requests import Request
from starlette.responses import Response
from starlette_admin.auth import AdminConfig, AdminUser, AuthProvider
from starlette_admin.exceptions import FormValidationError, LoginFailed

users = {
    "admin": {
        "name": "Admin",
        "avatar": "admin.png",
        "company_logo_url": "admin.png",
        "roles": ["read", "create", "edit", "delete", "action_make_published"],
    },
    "johndoe": {
        "name": "John Doe",
        "avatar": None, # user avatar is optional
        "roles": ["read", "create", "edit", "action_make_published"],
    },
    "viewer": {"name": "Viewer", "avatar": "guest.png", "roles": ["read"]},
}


class UsernameAndPasswordProvider(AuthProvider):
    """
    This is only for demo purpose, it's not a better
    way to save and validate user credentials
    """

    async def login(
        self,
        username: str,
        password: str,
        remember_me: bool,
        request: Request,
        response: Response,
    ) -> Response:
        if len(username) < 3:
            """Form data validation"""
            raise FormValidationError(
                {"username": "Ensure username has at least 03 characters"}
            )

        if username in users and password == "password":
            """Save `username` in session"""
            request.session.update({"username": username})
            return response

        raise LoginFailed("Invalid username or password")

    async def is_authenticated(self, request) -> bool:
        if request.session.get("username", None) in users:
            """
            Save current `user` object in the request state. Can be used later
            to restrict access to connected user.
            """
            request.state.user = users.get(request.session["username"])
            return True

        return False

    def get_admin_config(self, request: Request) -> AdminConfig:
        user = request.state.user  # Retrieve current user
        # Update app title according to current_user
        custom_app_title = "Hello, " + user["name"] + "!"
        # Update logo url according to current_user
        custom_logo_url = request.url_for("statics", path="qwestart.jpg")
        # if user.get("company_logo_url", None):
        #     custom_logo_url = request.url_for("static", path=user["company_logo_url"])
        return AdminConfig(
            app_title=custom_app_title,
            logo_url=custom_logo_url,
        )

    def get_admin_user(self, request: Request) -> AdminUser:
        user = request.state.user  # Retrieve current user
        photo_url = None
        # if user["avatar"] is not None:
            # photo_url = request.url_for("static", path=user["avatar"])
        return AdminUser(username=user["name"])

    async def logout(self, request: Request, response: Response) -> Response:
        request.session.clear()
        return response