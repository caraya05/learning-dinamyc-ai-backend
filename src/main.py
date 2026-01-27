import time
from fastapi.responses import JSONResponse
from fastapi import FastAPI, HTTPException, status
from fastapi import Request

from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocket
# Verificar tipo de token
from auth.services import validate_game_token, get_token_type
from core.database import create_indexes
from user import routers as user_routers
from user import router_admin as user_admin_routers
from user import router_ws as user_ws_routers
from auth import routers as token_routers
from prompt import routers as prompt_routers
from category import routers as category_routers
from configuration import routers as configuration_routers
from configuration import routers_admin as configuration_admin_routers
from game import routers as game_routers
from game import routers_stats as stats_routers
from game import routers_admin as game_pending_admin_routers
from game import routers_admin as game_admin_routers
from object import routers as object_routers
from object import routers_admin as object_admin_routers
from location import routers as location_routers
from location import routers_admin as location_admin_routers
from character import routers as character_routers
from character import routers_admin as character_admin_routers
from series import routers as series_routers
from voice import routers as voice_routers
from shortener import routers as shortener_routers
from task import routers as task_routers
from event import routers as event_routers
from event import routers_admin as event_routers_admin
from state_game import routers as state_game_routers
from contextlib import asynccontextmanager
from config import settings

from game.routers_protional import router as game_provisional_routers
from game.routers_protional import router_ws as game_provisional_ws_routers
from proxy import routers as proxy_routers
from analytics import routers as analytics_routers


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_indexes()
    yield


def custom_generate_unique_id(route):
    method = next(iter(route.methods)).lower() if route.methods else "get"
    return f"{route.name}_{method}_{route.path.replace('/', '_')}"


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
    lifespan=lifespan,
    # generate_unique_id_function=custom_generate_unique_id,
)

# Registro de manejadores de errores para el router de game
# app.add_exception_handler(HTTPException, http_exception_handler)
# app.add_exception_handler(Exception, generic_exception_handler)

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
    excluded_paths = ["/health", "/ws/echo"]  # Agrega aquí las rutas que deseas excluir
    if request.url.path in excluded_paths:
        return await call_next(request)

    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response



# @app.middleware("http")
# async def game_token_validation_middleware(request: Request, call_next):
#     """
#     Middleware para validar tokens de game_id en rutas específicas.
#     Solo aplica a rutas que requieren autenticación por game_id.
#     """
#
#     protected_paths = [
#         "/v1/api/state-game/",
#         "/v1/api/category/",
#     ]
#
#     # Verificar si la ruta requiere autenticación por game_id
#     is_protected = any(request.url.path.startswith(path) for path in protected_paths)
#
#     if is_protected:
#         try:
#             authorization = request.headers.get("Authorization")
#             # Validar el token de game_id
#             if not authorization or not authorization.startswith("Bearer "):
#                 return JSONResponse(
#                     status_code=status.HTTP_401_UNAUTHORIZED,
#                     content={"detail": "Missing or invalid Authorization header"},
#                     headers={"WWW-Authenticate": "Bearer"},
#                 )
#
#             token = authorization.split(" ")[1]
#
#             token_type = await get_token_type(token)
#
#             if token_type != "game":
#                 return await call_next(request)
#
#
#             game_id = request.query_params.get("game_id") or request.path_params.get("game_id")
#
#             if not game_id:
#                 return JSONResponse(
#                     status_code=status.HTTP_400_BAD_REQUEST,
#                     content={"detail": "game_id is required"},
#                 )
#
#             client_ip = request.client.host if request.client else "unknown"
#
#             # Validar el token
#             is_valid = await validate_game_token(token, game_id, client_ip)
#             if not is_valid:
#                 return JSONResponse(
#                     status_code=status.HTTP_401_UNAUTHORIZED,
#                     content={"detail": "Invalid or expired token for this game"},
#                     headers={"WWW-Authenticate": "Bearer"},
#                 )
#         except Exception as e:
#             return JSONResponse(
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#                 content={"detail": f"Token validation error: {str(e)}"},
#                 headers={"WWW-Authenticate": "Bearer"},
#             )
#
#     return await call_next(request)

app.include_router(analytics_routers.router, prefix="/v1/api")

app.include_router(token_routers.router, prefix="/v1/api")
app.include_router(category_routers.router, prefix="/v1/api")
app.include_router(character_routers.router, prefix="/v1/api")
app.include_router(configuration_routers.router, prefix="/v1/api")
app.include_router(game_routers.router_community, prefix="/v1/api")
app.include_router(game_routers.router, prefix="/v1/api")
app.include_router(location_routers.router, prefix="/v1/api")
app.include_router(object_routers.router, prefix="/v1/api")
# app.include_router(place_routers.router, prefix="/v1/api")
app.include_router(prompt_routers.router, prefix="/v1/api")
app.include_router(user_routers.router, prefix="/v1/api")
# app.include_router(weapon_routers.router2, prefix="/v2/api")
app.include_router(state_game_routers.router, prefix="/v1/api")
app.include_router(series_routers.router, prefix="/v1/api")
app.include_router(shortener_routers.router, prefix="/v1/api")
app.include_router(voice_routers.router, prefix="/v1/api")
app.include_router(user_ws_routers.router, prefix="")
app.include_router(game_provisional_ws_routers, prefix="")
# app.include_router(gpt_ai_routers.router, prefix="/v1/api")

app.include_router(task_routers.router, prefix="/v1/api")
app.include_router(event_routers.router, prefix="/v1/api")
app.include_router(shortener_routers.routerAPP)
app.include_router(proxy_routers.router, prefix="/v1/api")
# app.include_router(model_test_router)


@app.get("/health", tags=["Health Check"])
async def root():
    return {"message": "Ok"}


@app.websocket("/ws/echo")
async def websocket_echo(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message text was: {data}")
    except Exception as e:
        await websocket.close()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


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
    lifespan=lifespan,
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
    print("middleware admin add_process_time_header")
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


admin.include_router(user_admin_routers.router)
admin.include_router(stats_routers.router)
admin.include_router(game_admin_routers.router_admin)
admin.include_router(location_admin_routers.router)
admin.include_router(character_admin_routers.router)
admin.include_router(game_pending_admin_routers.router)
admin.include_router(configuration_admin_routers.router)
admin.include_router(event_routers_admin.router)
admin.include_router(object_admin_routers.router)

app.mount("/v1/admin", admin)

from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from game.routers_protional import limiter

app.add_middleware(SlowAPIMiddleware)

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


app.state.limiter = limiter

app.include_router(game_provisional_routers, prefix="/v1/api")


# EXCLUDED_AUTH_PATHS = [
#     "/health",
#     "/ws/echo",
#     "/v1/api/game/community-games",
#     "/v1/api/docs",
#     "/v1/api/redocs",
#     "/v1/api/auth/token",
#     "/v1/api/auth/token2",
#     "/openapi/openapi.json",
#     "/model-test"
# ]
#
#
# @app.middleware("http")
# async def auth_middleware(request: Request, call_next):
#     # Excluye rutas públicas
#     print("middleware auth_middleware")
#     for path in EXCLUDED_AUTH_PATHS:
#         if request.url.path.startswith(path):
#             return await call_next(request)
#
#     auth_header = request.headers.get("Authorization")
#     if not auth_header or not auth_header.startswith("Bearer "):
#         return JSONResponse(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             content={"detail": "Invalid or missing Authorization header"},
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     # Aquí podrías validar el token JWT si lo necesitas
#     # Por ejemplo: decode_jwt(auth_header.split(" ")[1])
#     return await call_next(request)

# import time
#
#
# RATE_LIMIT = 10  # solicitudes permitidas
# WINDOW_SIZE = 60  # segundos
# rate_limit_store = {}
#
# RATE_LIMIT_PATHS = [
#     "/v1/api/auth/token",
#     "/v1/api/game/generate",  # ejemplo, agrega aquí las rutas que quieras limitar
# ]
#
#
# @app.middleware("http")
# async def manual_rate_limit_middleware(request: Request, call_next):
#     # Solo aplica a ciertas rutas
#     print("middleware manual_rate_limit_middleware")
#     if any(request.url.path.startswith(path) for path in RATE_LIMIT_PATHS):
#         ip = request.client.host
#         now = time.time()
#         window = int(now // WINDOW_SIZE)
#         key = f"{ip}:{window}:{request.url.path}"
#         count = rate_limit_store.get(key, 0)
#         if count >= RATE_LIMIT:
#             return JSONResponse(
#                 status_code=status.HTTP_429_TOO_MANY_REQUESTS,
#                 content={"detail": "Rate limit exceeded. Try again later."}
#             )
#         rate_limit_store[key] = count + 1
#     return await call_next(request)
