from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from core.database import create_index

from user import routers as user_routers

from auth import routers as token_routers

from prompt import routers as prompt_routers

from category import routers as category_routers

from configuration import routers as configuration_routers

from game import routers as game_routers

from script import routers as script_routers

from object import routers as object_routers

from scene import routers as scene_routers

from location import routers as location_routers

from character import routers as character_routers

from customize import routers as customize_routers

from weapon import routers as weapon_routers

from place import routers as place_routers

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # await create_index()
    yield


app = FastAPI(
    title="Qwestar AI API",
    description="Qwestar AI is a game that uses AI to generate stories, characters, and images.",
    version="2.0",
    docs_url="/v1/api/docs",
    redoc_url="/v1/api/redocs",
    openapi_url="/openapi/openapi.json",
    swagger_ui_parameters={
        "syntaxHighlight": False,
    },
    # root_path="/admin",
    # root_path_in_servers=False,
    # debug=True,
    # servers=[
    #     {
    #         "url": "http://localhost",
    #         "description": "Localhost server",
    #     },
    #     {
    #         "url": "https://backend-dev.qwestar.ai",
    #         "description": "DO server",
    #     },
    # ],
    lifespan=lifespan
)

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
app.include_router(token_routers.router, prefix="/v1/api")
app.include_router(category_routers.router, prefix="/v1/api")
app.include_router(character_routers.router, prefix="/v1/api")
app.include_router(configuration_routers.router, prefix="/v1/api")
app.include_router(customize_routers.router, prefix="/v1/api")
app.include_router(game_routers.router, prefix="/v1/api")
app.include_router(location_routers.router, prefix="/v1/api")
app.include_router(object_routers.router, prefix="/v1/api")
app.include_router(place_routers.router, prefix="/v1/api")
app.include_router(prompt_routers.router, prefix="/v1/api")
app.include_router(scene_routers.router, prefix="/v1/api")
app.include_router(script_routers.router, prefix="/v1/api")
app.include_router(user_routers.router, prefix="/v1/api")
app.include_router(weapon_routers.router, prefix="/v1/api")


@app.get("/health", tags=["Health Check"])
async def root():
    return {"message": "Ok"}