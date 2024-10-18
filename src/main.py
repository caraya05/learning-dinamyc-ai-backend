import time

from fastapi import FastAPI
from fastapi import Request

from fastapi.middleware.cors import CORSMiddleware

from core.database import create_indexes
from user import routers as user_routers
from auth import routers as token_routers
from prompt import routers as prompt_routers
from category import routers as category_routers
from configuration import routers as configuration_routers
from configuration import routers_admin as configuration_admin_routers
from game import routers as game_routers
from game import routers_stats as stats_routers
from game import routers_admin as game_pending_admin_routers
from game import routers_admin as game_admin_routers
from script import routers as script_routers
from object import routers as object_routers
from scene import routers as scene_routers
from location import routers as location_routers
from character import routers as character_routers
from character import routers_admin as character_admin_routers
from customize import routers as customize_routers
from weapon import routers as weapon_routers
from voice import routers as voice_routers
from shortener import routers as shortener_routers
from contextlib import asynccontextmanager
from user import router_admin as user_admin_routers
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_indexes()
    yield


app = FastAPI(
    title=f"Qwestar AI API V1 {settings.NAME_ENV} ",
    description="Qwestar AI is a game that uses AI to generate stories, characters, and images.",
    version="1.0",
    docs_url="/v1/api/docs",
    redoc_url="/v1/api/redocs",
    openapi_url="/openapi/openapi.json",
    swagger_ui_parameters={
        "syntaxHighlight": False,
    },
    lifespan=lifespan
)

origins = [
    "*",
]

# app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


app.include_router(token_routers.router, prefix="/v1/api")
app.include_router(category_routers.router, prefix="/v1/api")
app.include_router(character_routers.router, prefix="/v1/api")
app.include_router(configuration_routers.router, prefix="/v1/api")
app.include_router(customize_routers.router, prefix="/v1/api")
app.include_router(game_routers.router, prefix="/v1/api")
app.include_router(location_routers.router, prefix="/v1/api")
app.include_router(object_routers.router, prefix="/v1/api")
# app.include_router(place_routers.router, prefix="/v1/api")
app.include_router(prompt_routers.router, prefix="/v1/api")
app.include_router(scene_routers.router, prefix="/v1/api")
app.include_router(script_routers.router, prefix="/v1/api")
app.include_router(user_routers.router, prefix="/v1/api")
app.include_router(weapon_routers.router, prefix="/v1/api")
# app.include_router(weapon_routers.router2, prefix="/v2/api")
app.include_router(shortener_routers.router, prefix="/v1/api")
app.include_router(voice_routers.router, prefix="/v1/api")
app.include_router(shortener_routers.routerAPP)


@app.get("/health", tags=["Health Check"])
async def root():
    return {"message": "Ok"}


admin = FastAPI(
    title=f"Qwestar AI Admin API {settings.NAME_ENV}",
    description="Qwestar AI is a game that uses AI to generate stories, characters, and images.",
    version="0.0",
    # docs_url="/v1/admin/docs",
    # redoc_url="/v1/admin/redocs",
    openapi_url="/openapi/openapi.json",
    swagger_ui_parameters={
        "syntaxHighlight": False,
    },
    lifespan=lifespan
)

admin.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@admin.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


admin.include_router(user_admin_routers.router)
admin.include_router(stats_routers.router)
admin.include_router(game_admin_routers.router_admin)
admin.include_router(game_pending_admin_routers.router)

app.mount("/v1/admin", admin)

appv2 = FastAPI(
    title=f"Qwestar AI API V2 {settings.NAME_ENV}",
    description="Qwestar AI is a game that uses AI to generate stories, characters, and images.",
    version="2.0",
    # docs_url="/v2/api/docs",
    # redoc_url="/v2/api/redocs",
    openapi_url="/openapi/openapi.json",
    swagger_ui_parameters={
        "syntaxHighlight": False,
    },
    lifespan=lifespan
)

appv2.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@appv2.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


appv2.include_router(character_routers.router2)
appv2.include_router(object_routers.router2)
appv2.include_router(game_routers.router2)
appv2.include_router(location_routers.router2)
admin.include_router(character_admin_routers.router)
admin.include_router(configuration_admin_routers.router)

app.mount("/v2/api", appv2)
