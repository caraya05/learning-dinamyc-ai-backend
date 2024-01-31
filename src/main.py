# from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles

from database import engine
from database import SessionLocal
from fastapi import FastAPI
from fastapi import Request
from fastapi import Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_jwt_auth.exceptions import AuthJWTException
from fastapi_jwt_auth import AuthJWT

from user import routers as user_routers
from user import models as user_base
from user.admin import UserAdmin

from auth import routers as token_routers

from character import routers as character_routers
from character import models as character_base
from character.admin import CharacterAdmin

from game_progress import routers as game_progress_routers
from game_progress import models as game_progress_base
from game_progress.admin import GameProgressAdmin

from game import routers as game_routers
from game import models as game_base
from game.admin import GameAdmin

from location import routers as location_routers
from location import models as location_base
from location.admin import LocationAdmin

from scene import routers as scene_routers
from scene import models as scene_base
from scene.admin import SceneAdmin

from prompt import routers as prompt_routers
from prompt import models as prompt_base
from prompt.admin import PromptAdmin

from admin_config import authentication_backend

from sqladmin import Admin

app = FastAPI(
    title="Qwestar AI API",
    description="Qwestar AI is a game that uses AI to generate stories, characters, and images.",
    version="1.0",
    docs_url="/v1/api/docs",
    redoc_url="/v1/api/redocs",
    openapi_url="/openapi/openapi.json",
    swagger_ui_parameters={
        "syntaxHighlight": False,
    },
)

app.mount("/statics", StaticFiles(directory="statics"), name="statics")

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_routers.router, prefix="/v1/api")
app.include_router(token_routers.router, prefix="/v1/api")
app.include_router(character_routers.router, prefix="/v1/api")
app.include_router(game_progress_routers.router, prefix="/v1/api")
app.include_router(game_routers.router, prefix="/v1/api")
app.include_router(location_routers.router, prefix="/v1/api")
app.include_router(scene_routers.router, prefix="/v1/api")
app.include_router(prompt_routers.router, prefix="/v1/api")

admin = Admin(
    app,
    engine,
    title="Qwestar AI Admin",
    authentication_backend=authentication_backend,
    base_url="/admin",
)

admin.add_view(UserAdmin)
admin.add_view(CharacterAdmin)
admin.add_view(GameProgressAdmin)
admin.add_view(GameAdmin)
admin.add_view(LocationAdmin)
admin.add_view(SceneAdmin)
admin.add_view(PromptAdmin)



user_base.Base.metadata.create_all(bind=engine)
character_base.Base.metadata.create_all(bind=engine)
game_progress_base.Base.metadata.create_all(bind=engine)
game_base.Base.metadata.create_all(bind=engine)
location_base.Base.metadata.create_all(bind=engine)
scene_base.Base.metadata.create_all(bind=engine)
prompt_base.Base.metadata.create_all(bind=engine)


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    response = Response("Internal server error", status_code=500)
    try:
        request.state.db = SessionLocal()
        response = await call_next(request)
    finally:
        request.state.db.close()
    return response


@app.exception_handler(AuthJWTException)
def authjwt_exception_handler(request: Request, exc: AuthJWTException):
    if exc.message == "Signature has expired":
        return JSONResponse(status_code=401, content={"detail": exc.message})
    elif exc.message == "Signature verification failed":
        return JSONResponse(status_code=401, content={"detail": exc.message})

    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


denylist = set()


@AuthJWT.token_in_denylist_loader
def check_if_token_in_denylist(decrypted_token):
    jti = decrypted_token['jti']
    return jti in denylist


# def custom_openapi():
#     if app.openapi_schema:
#         return app.openapi_schema
#
#     openapi_schema = get_openapi(
#         title="Custom title",
#         version="2.5.0",
#         description="This is a very custom OpenAPI schema",
#         routes=app.routes,
#     )
#
#     # Custom documentation fastapi-jwt-auth
#     headers = {
#         "name": "Authorization",
#         "in": "header",
#         "required": True,
#         "schema": {
#             "title": "Authorization",
#             "type": "string"
#         },
#     }
#
#     # Get routes from index 4 because before that fastapi define router for /openapi.json, /redoc, /docs, etc
#     # Get all router where operation_id is authorize
#     router_authorize = [route for route in app.routes[4:] if route.operation_id == "authorize"]
#     print(router_authorize)
#     for route in router_authorize:
#         method = list(route.methods)[0].lower()
#         try:
#             # If the router has another parameter
#             openapi_schema["paths"][route.path][method]['parameters'].append(headers)
#         except Exception:
#             # If the router doesn't have a parameter
#             openapi_schema["paths"][route.path][method].update({"parameters":[headers]})
#
#     app.openapi_schema = openapi_schema
#     return app.openapi_schema
#
#
# app.openapi = custom_openapi

@app.get("/")
async def root():
    return {"message": "AI toys"}
