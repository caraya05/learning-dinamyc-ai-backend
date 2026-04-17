# AGENTS.md - Qwestar AI Backend Guide for AI Assistants

## Project Overview

**Qwestar AI** is a FastAPI-based collaborative RPG game creation platform enabling users to generate games with AI-powered content (narratives, characters, images, voiceovers). The backend orchestrates game creation/management, multi-user team collaboration, authentication, AI service integration (OpenAI/ElevenLabs), and asynchronous task processing.

**Tech Stack:**
- **Framework:** FastAPI 0.95.0, Uvicorn ASGI server
- **Database:** MongoDB (Motor async driver for non-blocking I/O)
- **Task Queue:** Celery 5.4.0 + Redis 5.0.8 (multi-queue routing)
- **Authentication:** Firebase Admin SDK, JWT/refresh tokens
- **Cloud Storage:** Digital Ocean Spaces (S3-compatible)
- **AI Services:** OpenAI API (GPT-4, DALL-E), ElevenLabs (TTS), voice detection
- **Monitoring:** Flower UI (Celery task monitoring), request tracking middleware

---

## Architecture Fundamentals

### High-Level Request Flow

```
FastAPI Router (Domain-specific)
    ↓ (Depends injection: auth, auth_admin)
Service Layer (Business logic, async DB queries)
    ↓ (core.database.db)
MongoDB Collections (via Motor AsyncIOMotorClient)
    
↴ (For long operations)
Celery Task Queue (Redis broker)
    ↓ (Multi-queue routing)
Worker Pool (character_queue, image_character_queue, default, etc.)
    ↓ (External APIs)
OpenAI, ElevenLabs, Digital Ocean Spaces
```

### Module Organization Pattern

**Directory Structure:**
Each domain (game, user, character, team, etc.) follows this layered pattern:

```
src/{domain}/
├── __init__.py
├── models.py              # Pydantic BaseModel (DB schema-like) + validation rules
├── schemas.py             # Request/response DTOs (SchemaCreate*, SchemaRetrieve*, ResponseModel wrapper)
├── services.py            # Business logic (async Service classes or standalone functions)
├── routers.py             # FastAPI APIRouter endpoints (GET, POST, PATCH, DELETE)
├── routers_admin.py       # Admin-only endpoints (protected by auth_admin dependency)
├── routers_ws.py          # WebSocket endpoints (if domain needs real-time communication)
├── tasks.py               # Celery async tasks (prefixed async_*, registered in celery_worker.py)
├── utils.py               # Domain-specific helpers (DB queries, validation, formatting)
├── error_handlers.py      # Custom exceptions (domain-specific)
├── conftest.py            # Pytest fixtures for domain tests
└── tests_*.py             # Unit/integration tests (pytest-asyncio)
```

**Key Files:**
- `src/main.py` - FastAPI app init, middleware setup, router registration, lifespan context
- `src/config.py` - Settings management (Pydantic BaseSettings, env vars only)
- `src/core/database.py` - Motor client initialization, PyObjectId validator, index creation
- `src/core/schemas.py` - Base classes (CreateModel, UpdateModel, ResponseModel) with JSON encoders
- `src/celery_worker.py` - Celery app config, task routing, periodic tasks (Celery Beat), worker signals
- `src/tasks_shared.py` - Shared utilities for tasks (logging, error handling)

---

## Critical Patterns & Conventions

### 1. Dependency Injection & Authentication

**All protected endpoints inject dependencies:**

```python
from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from auth.auth import auth, auth_admin
from auth.utils import auth_schema

router = APIRouter(prefix="/team", tags=["team"])

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_team(
    team_data: SchemaCreateTeam,
    user: dict = Depends(auth),              # JWT-validated user dict
    token: HTTPAuthorizationCredentials = Depends(auth_schema)
) -> dict:
    """user contains: _id (str), email, is_superuser, is_active, is_staff"""
    owner_id = str(user.get("_id"))
    return await create_team_service(team_data, owner_id)

@router.delete("/{team_id}", dependencies=[Depends(auth_admin)])
async def delete_team_admin(team_id: str):
    """Admin-only: requires is_superuser + is_staff + is_active"""
    pass
```

**Auth Flow:**
- Bearer token extracted by `auth_header()` → validated by `auth_access()` service
- Returns user dict from JWT payload or Firebase UID lookup
- `auth_admin` checks `is_superuser and is_staff and is_active` flags
- Firebase integration: `firebase_auth.verify_token_firebase(uid)`

### 2. Service Classes & Async Functions

**Most domains use Service classes for dependency injection:**

```python
from core.database import db
from bson import ObjectId

class GameService:
    def __init__(self, db_instance=None):
        self.db = db_instance or db  # Optional DI for testing/mocking
        self.logger = logging.getLogger(__name__)
    
    async def get_game(self, game_id: str) -> dict | None:
        """Always convert string IDs to ObjectId for queries"""
        try:
            game_db = await self.db['game'].find_one({'_id': ObjectId(game_id)})
            if game_db:
                game_db['_id'] = str(game_db['_id'])  # Convert back to string for JSON
                return game_db
            return None
        except Exception as e:
            self.logger.error(f"Error fetching game: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to fetch game")

# Getter function (used in Depends if needed):
def get_game_service():
    return GameService()
```

**Note:** Some older modules use standalone async functions (e.g., `event.services.create_event_service()`). Prefer class-based services for new code.

### 3. MongoDB & Object ID Handling

**Strict Pattern for MongoDB Operations:**

```python
from core.database import db, PyObjectId
from bson import ObjectId

# QUERY: Always convert string → ObjectId
game_db = await db['game'].find_one({'_id': ObjectId(game_id)})

# RESPONSE: Always convert ObjectId → string for JSON serialization
if game_db:
    game_db['_id'] = str(game_db['_id'])
    for member in game_db.get('members', []):
        member['user_id'] = str(member['user_id'])
return game_db

# SCHEMA: Use PyObjectId validator for type hints/OpenAPI docs
from core.database import PyObjectId
from pydantic import BaseModel, Field

class ResponseModel(BaseModel):
    id: PyObjectId = Field(alias="_id")  # Validates ObjectId strings
    
    class Config:
        json_encoders = {ObjectId: str}  # Auto-encode ObjectId on response
```

**Indexes:** Auto-created on app startup via `create_indexes()` in `main.py` lifespan event. Add new indexes in `core/database.py`.

### 4. Request/Response Schemas

**Standard Pattern:**

```python
from pydantic import BaseModel, Field, EmailStr
from core.schemas import ResponseModel
from typing import Optional, List

# Request (Input):
class SchemaCreateTeam(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None

# Response (Output) - wraps models with _id → id aliasing:
class SchemaRetrieveTeam(ResponseModel):
    """ResponseModel automatically aliases _id → id and encodes ObjectId"""
    id: PyObjectId = Field(..., alias="_id")
    name: str
    owner_id: str
    members: List[dict]
    is_active: bool

# List responses (pagination pattern):
class SchemaListTeams(BaseModel):
    results: List[SchemaRetrieveTeam]
    count: int
    page: int
    total_pages: int
```

### 5. Celery Async Tasks

**Task Definition & Registration:**

```python
# src/game/tasks.py
from celery_worker import celery
from core.database import db
import logging

logger = logging.getLogger(__name__)

@celery.task(name='identify_category_game_task', bind=True)
async def async_identify_category_game_task(self, game_id: str):
    """
    Long-running task: AI analysis, image generation, etc.
    - self: Celery task instance (for self.retry, logging)
    - Name must be registered in celery_worker.py task_routes
    """
    try:
        game = await db['game'].find_one({'_id': ObjectId(game_id)})
        # ... perform AI call, image upload, etc.
        await db['game'].update_one(
            {'_id': ObjectId(game_id)},
            {'$set': {'category': 'rpg', 'category_updated_at': datetime.utcnow()}}
        )
    except Exception as e:
        logger.error(f"Task failed: {e}", exc_info=True)
        # Optional: self.retry(exc=e, countdown=60)

# src/celery_worker.py (register task):
from game.tasks import async_identify_category_game_task

task_routes = {
    'identify_category_game_task': {'queue': 'default'},
    'generate_character_task': {'queue': 'character_queue'},
    'generate_image_character_shared_task': {'queue': 'image_character_queue'},
    '*': {'queue': 'default'},
}

# Invoke from router:
from game.tasks import async_identify_category_game_task

@router.post("/game/{game_id}/analyze")
async def trigger_analysis(game_id: str, user: dict = Depends(auth)):
    async_identify_category_game_task.delay(game_id=game_id)
    return {"status": "analysis_started"}
```

**Task Queue Routing:** Celery distributes tasks across named queues (character_queue, image_character_queue, default) based on `task_routes` config. Workers can consume specific queues via command line flags.

**Broker:** Redis at `CELERY_BROKER_URL` (default: `redis://redis:6379/0`). Use `CELERY_RESULT_BACKEND` for task result storage.

### 6. Error Handling & Logging

**Consistent Error Pattern:**

```python
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)

async def create_team_service(team_data: SchemaCreateTeam, owner_id: str):
    try:
        new_team = Team(**team_data.dict(), owner_id=owner_id, created_by=owner_id)
        result = await db["team"].insert_one(new_team.dict())
        return await db["team"].find_one({"_id": result.inserted_id})
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail="Invalid input")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
```

**Best Practices:**
- Import logger per module: `logger = logging.getLogger(__name__)`
- Use `.warning()` for expected client errors, `.error()` for unexpected
- Always include `exc_info=True` on error logs for stack traces
- Define domain-specific exceptions in `{domain}/error_handlers.py` (e.g., `GameNotFoundError`)
- Middleware catches unhandled exceptions; currently no global handler registered

### 7. User Context & Team Integration

**User Object Structure (from auth):**
```python
user = {
    "_id": "507f1f77bcf86cd799439011",  # String ObjectId
    "email": "user@example.com",
    "username": "user",
    "is_superuser": False,
    "is_active": True,
    "is_staff": False,
    "plan_type": "team",              # "individual" or "team"
    "team_id": "507f1f77bcf86cd799439012",  # Team they belong to
    "team_role": "creator",           # owner, admin, creator, viewer
    "is_team_owner": False
}
```

**Team Roles & Permissions:**
```python
TEAM_ROLES = {
    "owner": ["invite", "remove", "edit_team", "edit_members", "create", "view"],
    "admin": ["invite", "remove", "edit_members", "create", "view"],
    "creator": ["create", "view"],
    "viewer": ["view"]
}
```

---

## Key Integration Points

### OpenAI API (GPT-4, DALL-E)

**Character/Narrative Generation:**
```python
from openai import OpenAI
from config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY, organization=settings.OPENAI_API_ORG_ID)

# Text generation:
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are a game designer..."},
        {"role": "user", "content": "Create a character..."}
    ]
)
narrative = response.choices[0].message.content

# Image generation:
img_response = client.images.generate(prompt="A fantasy warrior...", n=1, size="1024x1024")
image_url = img_response.data[0].url
```

**Used in:** `gpt_ai/` module for character backgrounds, game narratives, scene descriptions.

### ElevenLabs Text-to-Speech

**Voice Generation:**
```python
from voice.elevenlabs import get_voices
from voice.task import async_generate_voice_task

# Cached list of available voices:
voices = await get_voices()  # Returns {voice_id: voice_name}

# Trigger async voice generation (in tasks):
async_generate_voice_task.delay(character_id=character_id, text=dialogue)
```

**Used in:** Character dialogue generation, game narration audio.

### Digital Ocean Spaces (S3-compatible)

**File Upload:**
```python
from utils import upload_image

# Upload image/audio to DO Spaces:
url = await upload_image(
    file_bytes=image_data,
    bucket="games",
    filename="character_portrait.png"
)
# Returns: https://qwestar.cdn.digitaloceanspaces.com/games/character_portrait.png

# Store URL in database:
await db['character'].update_one(
    {'_id': ObjectId(char_id)},
    {'$set': {'image_url': url}}
)
```

**Used in:** Character portraits, game covers, sound effects, voice files.

### Firebase Authentication

**Token Verification:**
```python
from firebase_auth import verify_token_firebase

# From JWT token payload or Firebase UID:
user_data = verify_token_firebase(uid)
# Returns Firebase user object (email, display_name, etc.)
```

---

## Development Workflows

### Local Setup & Running

**Build & Start (Development):**
```bash
# Build Docker images
make dev-build

# Start services (FastAPI, MongoDB, Redis, Celery Worker, Flower)
make dev-up

# Access Swagger API docs: http://localhost/v1/api/docs
# Access ReDoc: http://localhost/v1/api/redocs
# Flower (Celery monitoring): http://localhost:5555 (admin:admin)
```

**Code Quality:**
```bash
# Format all code (Black, 100 char limit in pyproject.toml)
make dev-black

# Lint (Flake8)
make dev-flake8

# Lint (Pylint)
make dev-pylint

# Run tests from container
make dev-bash
pytest src/team/tests_team.py -v
pytest --cov=src/ --cov-report=html
```

### Environment Configuration

**`.env` file (Docker Compose loads via env_file):**
```
DATABASE_URL=mongodb://user:pass@mongo:27017/
DATABASE_NAME=qwestar_db
JWT_SECRET_KEY=your-secret-key
REFRESH_TOKEN_EXPIRES_IN=604800
ACCESS_TOKEN_EXPIRES_IN=3600
JWT_ALGORITHM=HS256

OPENAI_API_KEY=sk-...
OPENAI_API_ORG_ID=org-...
ELEVENLABS_API_KEY=...

ACCESS_ID_DIGITAL_OCEAN=...
SECRET_KEY_DIGITAL_OCEAN=...
URL_DIGITAL_OCEAN=https://qwestar.cdn.digitaloceanspaces.com

CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

FLOWER_USER=admin
FLOWER_PASSWORD=admin

NAME_ENV=development
URL_API=http://localhost

MODE_TEST=False
```

**Database Indexes:** Auto-created on app startup (main.py lifespan event → `create_indexes()` in core/database.py). Add custom indexes there.

### Testing

**Test File Location & Structure:**
```bash
# Unit tests live in domain folders:
src/{domain}/tests_*.py

# Shared fixtures:
src/{domain}/conftest.py (pytest)

# Run tests:
make dev-bash
pytest src/team/tests_team.py::test_create_team -v
pytest --cov=src/team --cov-report=term-missing

# Async test pattern:
import pytest
from pytest_asyncio import fixture

@pytest.mark.asyncio
async def test_get_team(db_mock):
    team = await team_service.get_team("507f...")
    assert team is not None
```

---

## Module Highlights & Patterns

### Team Module (Collaborative Planning)
- **Key Services:** `create_team_service`, `add_member_to_team_service`, `update_member_role_service`
- **Role-based Access Control:** Owner > Admin > Creator > Viewer
- **Patterns:** Service class validation, HTTPException (400/403/404), membership lookup
- **See:** `src/team/README.md` for detailed API and role matrix

### Game Module (Core Creation)
- **Complexity:** Largest module; handles full game lifecycle (create → generate → update)
- **Services:** GameService class; separate logic files (narrative_services.py, text_update_services.py)
- **Tasks:** Multiple queues (character generation, image generation, voice detection)
- **Pattern:** Aggregates child entities (characters, locations, events, objects) on retrieval

### Character/Location/Object Modules
- **Shared Pattern:** Service class → routers → tasks for async generation
- **Image Generation:** Upload to DO Spaces → store URL in DB
- **Voice Integration:** Text → ElevenLabs TTS → upload to DO Spaces → store URL

### Analytics Module
- **Dashboard endpoints:** User stats, game progress tracking
- **Responses:** SchemaListGame pattern (results, count, page, total_pages)
- **Logging:** Custom logging config (src/analytics/logging_config.py)

---

## Architecture Refactoring Context

**Current State (As-Is):**
- Routers → Services access global `core.database.db` directly
- Some mixed patterns (class-based and function-based services)
- No repository abstraction layer

**Planned State (See `refacori/PLAN_REFAC_MULTI_CAPAS.md`):**
- **Presentation Layer:** Routers (auth, validation, response formatting)
- **Application Layer:** Use cases / service orchestrators
- **Domain Layer:** Models, schemas, validation, business rules
- **Infrastructure Layer:** Repository adapters (MongoDB, storage, external APIs)

**Impact for Agents:**
1. When adding features, keep business logic in services (not routers)
2. Dependency inject DB/config (plan ahead; don't use global `db` in new code)
3. Define repository interfaces in `core/ports/` if feasible
4. Avoid tight coupling to MongoDB (use abstraction)

---

## Common Tasks & Commands

| Task | Pattern |
|------|---------|
| **Add API endpoint** | Create schema in `schemas.py` → service method in `services.py` → route in `routers.py` with auth dependency |
| **Create Celery task** | Define `async def` in `{domain}/tasks.py` → register in `celery_worker.py` task_routes → invoke with `.delay()` |
| **Query MongoDB** | Use `await db['collection'].find_one(filter)` → convert string ID with `ObjectId()` → convert result ObjectId to `str()` |
| **Handle errors** | Catch domain-specific exceptions → log with logger → raise `HTTPException(status_code=..., detail=...)` |
| **Add auth** | Inject `auth` or `auth_admin` from `auth.auth` → extract `user_id = str(user.get("_id"))` |
| **Upload file** | Use `utils.upload_image()` → returns DO Spaces URL → store in DB |
| **Call OpenAI** | Use `OpenAI(api_key=settings.OPENAI_API_KEY).chat.completions.create(...)` |
| **Generate voice** | Trigger `async_generate_voice_task.delay()` → listen for completion via webhook/polling |
| **Test async code** | Mark test with `@pytest.mark.asyncio` → use `pytest-asyncio` fixture |
| **Format code before commit** | Run `make dev-black && make dev-flake8` |

---

## File Locations Quick Reference

**Core Infrastructure:**
- `src/main.py` - FastAPI app, middleware, route registration, lifespan
- `src/config.py` - Pydantic Settings (env vars only)
- `src/core/database.py` - Motor client, PyObjectId, indexes
- `src/core/schemas.py` - Base response classes (ResponseModel, CreateModel)

**Authentication:**
- `src/auth/auth.py` - Dependency functions (auth, auth_admin, auth_header)
- `src/auth/services.py` - Token validation (auth_access)
- `src/firebase_auth.py` - Firebase integration

**Task Queue:**
- `src/celery_worker.py` - Celery config, task routes, beat schedule, Flower
- `src/tasks_shared.py` - Shared task utilities
- `src/{domain}/tasks.py` - Domain-specific async tasks

**API Routes & Business Logic:**
- `src/{domain}/routers.py` - FastAPI endpoints
- `src/{domain}/routers_admin.py` - Admin-only endpoints
- `src/{domain}/routers_ws.py` - WebSocket endpoints (if applicable)
- `src/{domain}/services.py` - Business logic (Service classes or async functions)
- `src/{domain}/models.py` - Pydantic models (DB schema representation)
- `src/{domain}/schemas.py` - Request/response DTOs

**Utilities & Testing:**
- `src/{domain}/utils.py` - Domain-specific helpers
- `src/{domain}/error_handlers.py` - Custom exceptions
- `src/{domain}/conftest.py` - Pytest fixtures
- `src/{domain}/tests_*.py` - Unit/integration tests

**Middleware & Monitoring:**
- `src/main.py` - CORS, process-time header, auth validation comments
- Flower UI - http://localhost:5555 (task monitoring)

---

## Observability & Debugging Tips

**Logging:**
```python
import logging
logger = logging.getLogger(__name__)
logger.info("User created: %s", user_id)
logger.error("DB error: %s", e, exc_info=True)
```

**Request Tracing:**
- Middleware adds `X-Process-Time` header to all responses
- Useful for identifying slow endpoints

**Celery Monitoring:**
- Flower UI at http://localhost:5555
- Monitor task status, worker health, queue depth
- Credentials: admin:admin (configurable in celery_worker.py)

**API Documentation:**
- Swagger UI: http://localhost/v1/api/docs (interactive)
- ReDoc: http://localhost/v1/api/redocs (static)
- Auto-generated from route docstrings + response_model

**Database Inspection:**
```bash
# From container:
make dev-bash
python
>>> from core.database import db
>>> await db['team'].find_one({'_id': ObjectId('...')})
```

---

## Code Style & Standards

**Formatting:**
- **Black:** 100 char line length (configured in `pyproject.toml`)
- **Command:** `make dev-black`

**Linting:**
- **Flake8:** Style compliance, unused imports, complexity
- **Pylint:** Extended checks
- **Commands:** `make dev-flake8`, `make dev-pylint`

**Type Hints:**
- Use in all function signatures (validated at runtime in Pydantic schemas)
- Python 3.9+ union syntax: `dict | None` instead of `Optional[dict]`

**Async/Await:**
- Consistent use; all DB/external API calls are async
- Never block event loop with sync operations
- Use Motor (async MongoDB), httpx (async HTTP)

**Commit Checklist:**
```bash
make dev-black
make dev-flake8
pytest src/{domain}/tests_*.py -v
git commit -m "feat: add team member role update endpoint"
```

---

## Troubleshooting & Common Patterns

**ObjectId Serialization Errors:**
- **Problem:** `TypeError: Object of type ObjectId is not JSON serializable`
- **Solution:** Convert ObjectId to string in service before returning: `result['_id'] = str(result['_id'])`
- **Or:** Use ResponseModel with `json_encoders = {ObjectId: str}`

**Pydantic Validation Errors on Response:**
- **Problem:** `ValidationError: field required (type=value_error.missing)`
- **Likely Cause:** Schema expects field that's missing from DB document
- **Solution:** Verify all fields in response schema are present in service return value; use `Optional` for nullable fields

**Celery Task Not Executing:**
- **Problem:** Task queued but never runs
- **Check:** Is worker listening to correct queue? `task_routes` in celery_worker.py must match task name
- **Debug:** Check Flower UI for task status, worker connection

**Async/Await Errors:**
- **Problem:** `RuntimeError: Event loop is closed`
- **Cause:** Calling async functions without proper event loop (pytest-asyncio missing)
- **Solution:** Use `@pytest.mark.asyncio` on tests, ensure `pytest-asyncio` installed

---

## Project Health Indicators

✅ **Well-Established Patterns:**
- Domain-driven folder structure
- Service layer abstraction (mostly)
- Async-first architecture
- Multi-queue Celery routing
- Team/RBAC integration complete

⚠️ **Areas Under Refinement:**
- Refactoring toward layered architecture (see `refacori/` folder)
- Mixed service patterns (class + function-based)
- Some modules with multiple implementation versions (tasks_provisional.py, tasks_provisional_2.py)

📋 **Conventions to Follow:**
- Always namespace Celery tasks in celery_worker.py
- Use ResponseModel for consistent _id → id aliasing
- Inject auth dependency on all protected routes
- Convert ObjectId ↔ string at DB boundaries
- Log errors with `exc_info=True` for debugging


