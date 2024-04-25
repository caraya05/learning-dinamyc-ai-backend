import time
import logging
from fastapi import HTTPException

from fastapi import FastAPI
from fastapi import Request
from fastapi import Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_jwt_auth.exceptions import AuthJWTException
from fastapi_jwt_auth import AuthJWT

# from database import engine
# from database import SessionLocal

# from user import routers as user_routers
# from user.models import Author, Book
from user.models import Category, Product
# from user.admin import AuthorView
from user.admin import CategoryView, ProductView
#
# from auth import routers as token_routers
#
# from character import routers as character_routers
# from character import models as character_base
# from character.admin import CharacterAdmin
#
# from game_progress import routers as game_progress_routers
# from game_progress import models as game_progress_base
# from game_progress.admin import GameProgressAdmin
#
# from game import routers as game_routers
# from game import models as game_base
# from game.admin import GameAdmin
#
# from location import routers as location_routers
# from location import models as location_base
# from location.admin import LocationAdmin
#
# from scene import routers as scene_routers
# from scene import models as scene_base
# from scene.admin import SceneAdmin
#
# from prompt import models as prompt_base
# from prompt.admin import PromptAdmin
#
# from script import routers as script_routers
# from script import models as script_base
# from script.admin import ScriptAdmin
#
# from object import models as object_base
# from object.admin import ObjectAdmin
# from object import routers as object_routers
#
# from weapon import routers as weapon_routers
# from weapon import models as weapon_base
# from weapon.admin import WeaponAdmin
#
# from customize import models as customize_base
# from customize.admin import CustomizeAdmin
# from customize import routers as customize_routers
#
# from category import models as category_base
# from category.admin import CategoryAdmin
# from category import routers as category_routers
#
# from configuration import models as configuration_base
# from configuration.admin import ConfigurationAdmin
# from configuration import routers as configuration_routers
#
# from record_daily import models as record_daily_base
# from record_daily.admin import DailyRecordAdmin
# from record_daily import routers as record_daily_routers
#
# from sound import models as sound_base
# from sound.admin import SoundAdmin
#
from admin_config import UsernameAndPasswordProvider

from starlette_admin.views import Link
from starlette_admin import I18nConfig
# from starlette_admin.contrib.odmantic import Admin, ModelView
from starlette_admin.contrib.mongoengine import Admin, ModelView
from database import db
from database import engine
from database import connection

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

#
# app.include_router(user_routers.router, prefix="/v1/api")
# app.include_router(token_routers.router, prefix="/v1/api")
# app.include_router(game_routers.router, prefix="/v1/api")
# app.include_router(game_progress_routers.router, prefix="/v1/api")
# app.include_router(script_routers.router, prefix="/v1/api")
# app.include_router(character_routers.router, prefix="/v1/api")
# app.include_router(location_routers.router, prefix="/v1/api")
# app.include_router(scene_routers.router, prefix="/v1/api")
# # app.include_router(prompt_routers.router, prefix="/v1/api")
# app.include_router(object_routers.router, prefix="/v1/api")
# app.include_router(weapon_routers.router, prefix="/v1/api")
# app.include_router(customize_routers.router, prefix="/v1/api")
# app.include_router(configuration_routers.router, prefix="/v1/api")
# app.include_router(category_routers.router, prefix="/v1/api")
#
# # url export data admin
# app.include_router(record_daily_routers.router, prefix="/admin")
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware

admin = Admin(
    # engine,
    logo_url="https://qwestar.ai/wp-content/uploads/2024/01/Logo-Qwestar-Color.png",
    title="Qwestar AI Admin",
    auth_provider=UsernameAndPasswordProvider(),
    middlewares=[Middleware(SessionMiddleware, secret_key="2ssss")],
    base_url="/admin",
)
from starlette_admin import DropDown

admin.add_view(
    DropDown(
        label="Store",
        icon="fa fa-store",
        views=[ProductView(Product), CategoryView(Category, label="Categories")],
    )
)
admin.add_view(
    Link(
        "StarletteAdmin Docs",
        url="https://jowilf.github.io/starlette-admin/",
        icon="fa fa-book",
        target="_blank",
    )
)
admin.add_view(Link(label="Go Back to Home", icon="fa fa-link", url="/admin/"))

# admin.add_view(CharacterAdmin)
# admin.add_view(GameProgressAdmin)
# admin.add_view(GameAdmin)
# admin.add_view(LocationAdmin)
# admin.add_view(SceneAdmin)
# admin.add_view(PromptAdmin)
# admin.add_view(ScriptAdmin)
# admin.add_view(ObjectAdmin)
# admin.add_view(WeaponAdmin)
# admin.add_view(CustomizeAdmin)
# admin.add_view(CategoryAdmin)
# admin.add_view(ConfigurationAdmin)
# admin.add_view(DailyRecordAdmin)
# admin.add_view(SoundAdmin)

admin.mount_to(app)


# user_base.Base.metadata.create_all(bind=engine)
# character_base.Base.metadata.create_all(bind=engine)
# game_progress_base.Base.metadata.create_all(bind=engine)
# game_base.Base.metadata.create_all(bind=engine)
# location_base.Base.metadata.create_all(bind=engine)
# scene_base.Base.metadata.create_all(bind=engine)
# prompt_base.Base.metadata.create_all(bind=engine)
# script_base.Base.metadata.create_all(bind=engine)
# object_base.Base.metadata.create_all(bind=engine)
# weapon_base.Base.metadata.create_all(bind=engine)
# customize_base.Base.metadata.create_all(bind=engine)
# category_base.Base.metadata.create_all(bind=engine)
# configuration_base.Base.metadata.create_all(bind=engine)
# record_daily_base.Base.metadata.create_all(bind=engine)
# sound_base.Base.metadata.create_all(bind=engine)

@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    response = Response("Internal server error", status_code=500)
    try:
        start_time = time.time()
        request.state.db = connection
        response = await call_next(request)
    except HTTPException as e:
        response = JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        process_time = time.time() - start_time
        logging.info(f"Processed request in {process_time} seconds")
        request.state.db = None
    return response


# @app.on_event("startup")
# def startup_db_client():
#     app.mongodb_client = client
#     app.database = app.mongodb_client[INITIAL_DATABASE]
#
#
# @app.on_event("shutdown")
# def shutdown_db_client():
#     app.mongodb_client.close()


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


from pydantic import BaseModel
from typing import Optional


class ProductModel(BaseModel):
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    dimension: Optional[str] = None
    image: Optional[str] = None
    manual: Optional[str] = None
    created_at: Optional[str] = None
    category: Optional[str] = None

    class Config:
        orm_mode = True


@app.get("/")
async def root():
    print(Product.objects().all())
    for product in Product.objects().all():
        print(product.id)
    category = Product.objects().get(id="662ae74950b1d4c8cf3f290e")
    print(category.image)
    return {"message": "Qwestar AI API"}


@app.get("/product/{product_id}", response_model=ProductModel)
async def get_product(product_id: str):
    product = Product.objects().get(id=product_id)
    return {
        "id": str(product.id),
        "title": product.title,
        "description": product.description,
        "price": product.price,
        "dimension": str(product.dimension),
        "image": str(product.image),
        "manual": str(product.manual),
        "created_at": str(product.created_at),
        "category": product.category
    }
