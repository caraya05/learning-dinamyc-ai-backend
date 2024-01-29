from fastapi import Request
from fastapi_jwt_auth import AuthJWT
import jwt

from config import settings
from datetime import datetime, timedelta
from sqladmin.authentication import AuthenticationBackend

from auth.schemas import SchemaTokenAccess

from user.services import get_user_by_field
from user.utils import verify_password
from user.schemas import SchemaRetrieveUser


def get_db(request: Request):
    return request.state.db


auth = AuthJWT()


class AdminAuth(AuthenticationBackend):

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username, password = form["username"], form["password"]
        if not username or not password:
            return False
        if username != settings.admin_superuser or password != settings.admin_superuser_password:
            print("user")
            user_db = get_user_by_field(get_db(request), "username", username)
            if not user_db:
                return False
            if not verify_password(password, user_db.password):
                return False
            if not user_db.is_superuser or not user_db.is_active:
                return False
            request.session.update({"token": auth.create_access_token(
                subject=user_db.id,
                expires_time=timedelta(minutes=120)
            )})
            return True
        else:
            request.session.update({
                "token": auth.create_access_token(
                    subject="admin",
                    expires_time=timedelta(days=1),
                    algorithm="HS512")})

            return True
        # request.session.update(
        #     {"valid": int(datetime.now().timestamp() + (60 * 120))}
        # )  # 10 minutes
        # return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        # token = request.session.get("token")
        # valid = request.session.get("valid")
        # if valid and int(datetime.now().timestamp()) > valid:
        #     request.session.clear()
        #     return False
        # if not token:
        #     request.session.clear()
        #     return False

        token = request.session.get("token")
        if not token:
            request.session.clear()
            return False
        try:
            print("token_access", token)
            payload = jwt.decode(token, settings.authjwt_secret_key, algorithms="HS512")
            if payload["exp"] < datetime.now().timestamp():
                print("exp ......")
                request.session.clear()
                return False
            print("payload", payload)
            request.session.update({
                "access": auth.create_access_token(
                    subject="admin",
                    expires_time=timedelta(minutes=120))
            })
            return True
        except Exception as e:
            print(e)
            request.session.clear()
            return False


authentication_backend = AdminAuth(secret_key=settings.authjwt_secret_key)
