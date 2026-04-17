# Team Module - Qwestar AI Backend

## Overview

El módulo de **Team** (Equipo) proporciona funcionalidad para administrar equipos colaborativos en Qwestar AI. Permite que los usuarios formen equipos, inviten a otros usuarios y colaboren juntos bajo un plan de equipo.

## Features

- ✅ Crear nuevos equipos
- ✅ Administrar miembros del equipo (agregar, remover)
- ✅ Sistema de roles jerárquicos (owner, admin, creator, viewer)
- ✅ Control de permisos basado en roles
- ✅ Actualizar información del equipo
- ✅ Eliminar equipos
- ✅ Listar equipos por usuario
- ✅ Cambiar roles de miembros

## Architecture

```
routers.py          ← API endpoints
    ↓
services.py         ← Lógica de negocio
    ↓
models.py + schemas.py  ← Validación y modelos
    ↓
database.py (MongoDB)  ← Persistencia
```

## Roles y Permisos

| Rol       | Descripción                           | Permisos                                    |
|-----------|---------------------------------------|---------------------------------------------|
| **owner** | Propietario del equipo                | invite, remove, edit_team, edit_members, create, view |
| **admin** | Administrador del equipo              | invite, remove, edit_members, create, view |
| **creator** | Creador de contenido en el equipo    | create, view                                 |
| **viewer** | Solo puede ver contenido del equipo  | view                                         |

## API Endpoints

### Teams

#### Crear Equipo
```
POST /v1/api/team
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "Mi Estudio de Juegos",
  "description": "Un equipo para crear juegos colaborativamente"
}

Response: 201
{
  "id": "507f1f77bcf86cd799439011",
  "name": "Mi Estudio de Juegos",
  "description": "Un equipo para crear juegos colaborativamente",
  "owner_id": "507f1f77bcf86cd799439012",
  "members": [
    {
      "user_id": "507f1f77bcf86cd799439012",
      "role": "owner"
    }
  ],
  "is_active": true
}
```

#### Obtener Equipo
```
GET /v1/api/team/{team_id}
Authorization: Bearer <token>

Response: 200
{
  "id": "507f1f77bcf86cd799439011",
  "name": "Mi Estudio de Juegos",
  "description": "Un equipo para crear juegos colaborativamente",
  "owner_id": "507f1f77bcf86cd799439012",
  "members": [...],
  "is_active": true
}
```

#### Actualizar Equipo
```
PATCH /v1/api/team/{team_id}
Content-Type: application/json
Authorization: Bearer <token>

{
  "name": "Nuevo Nombre del Equipo",
  "description": "Nueva descripción"
}

Response: 200
```

#### Listar Equipos del Usuario
```
GET /v1/api/team
Authorization: Bearer <token>

Response: 200
{
  "results": [...],
  "count": 1
}
```

#### Eliminar Equipo
```
DELETE /v1/api/team/{team_id}
Authorization: Bearer <token>

Response: 204
```

### Members

#### Agregar Miembro
```
POST /v1/api/team/{team_id}/members
Content-Type: application/json
Authorization: Bearer <token>

{
  "user_id": "507f1f77bcf86cd799439013",
  "role": "creator"
}

Response: 201
```

#### Remover Miembro
```
DELETE /v1/api/team/{team_id}/members/{member_id}
Authorization: Bearer <token>

Response: 200
```

#### Actualizar Rol de Miembro
```
PATCH /v1/api/team/{team_id}/members/{member_id}/role
Content-Type: application/json
Authorization: Bearer <token>

{
  "role": "admin"
}

Response: 200
```

## Database Collections

### Teams Collection

```javascript
{
  "_id": ObjectId,
  "name": String,              // Nombre del equipo
  "description": String,        // Descripción opcional
  "owner_id": ObjectId,         // ID del propietario
  "members": [                  // Lista de miembros
    {
      "user_id": ObjectId,
      "role": String,           // owner, admin, creator, viewer
      "joined_at": DateTime
    }
  ],
  "is_active": Boolean,
  "created_at": DateTime,
  "created_by": String,
  "updated_at": DateTime,
  "updated_by": String
}
```

### User Collection (Extended)

```javascript
{
  // ...campos existentes...
  "plan_type": String,          // individual or team
  "team_id": ObjectId,          // ID del equipo (si es miembro)
  "team_role": String,          // Rol en el equipo
  "is_team_owner": Boolean      // ¿Es propietario del equipo?
}
```

## Services

### Principales

- `create_team_service(team_data, owner_id)` - Crear nuevo equipo
- `get_team_service(team_id)` - Obtener equipo por ID
- `update_team_service(team_id, team_data, user_id)` - Actualizar equipo (solo owner)
- `delete_team_service(team_id, user_id)` - Eliminar equipo (solo owner)
- `add_member_to_team_service(team_id, member_data, user_id)` - Agregar miembro
- `remove_member_from_team_service(team_id, member_id, user_id)` - Remover miembro
- `update_member_role_service(team_id, member_id, new_role, user_id)` - Actualizar rol
- `list_teams_by_user_service(user_id)` - Listar equipos del usuario

### Validación

- `validate_team_role(team_id, user_id, required_roles)` - Valida permisos del usuario

## User Services Extendidas

### Nuevos Servicios

- `get_user_plan_service(user_id)` - Obtiene el plan actual del usuario
- `update_user_plan_service(user_id, plan_type)` - Cambia el plan del usuario
- `get_user_teams_service(user_id)` - Obtiene los equipos del usuario

## Ejemplos de Uso

### Python (Backend)

```python
from team.services import create_team_service, add_member_to_team_service
from team.schemas import SchemaCreateTeam, SchemaInviteUserTeam

# Crear equipo
team_data = SchemaCreateTeam(
    name="Game Studio Alpha",
    description="Estudio para crear juegos épicos"
)
team = await create_team_service(team_data, owner_id="507f1f77bcf86cd799439011")

# Agregar miembro
member_data = SchemaInviteUserTeam(
    user_id="507f1f77bcf86cd799439013",
    role="creator"
)
updated_team = await add_member_to_team_service(
    team_id=team["_id"],
    member_data=member_data,
    user_id="507f1f77bcf86cd799439011"
)
```

## Validación de Permisos

Todos los endpoints protegidos validan permisos automáticamente:

```python
# Solo owner puede actualizar el equipo
await update_team_service(team_id, team_data, user_id)

# Solo owner o admin pueden agregar miembros
await add_member_to_team_service(team_id, member_data, user_id)

# Solo owner puede cambiar roles
await update_member_role_service(team_id, member_id, new_role, user_id)
```

## Manejo de Errores

La mayoría de servicios lanzan `HTTPException` con códigos de estado apropiados:

- `400 BAD_REQUEST` - Datos inválidos o usuario ya es miembro
- `403 FORBIDDEN` - Permisos insuficientes
- `404 NOT_FOUND` - Recurso no encontrado
- `500 INTERNAL_SERVER_ERROR` - Error del servidor

## Testing

Para probar los endpoints, se puede usar:

```bash
# Crear equipo
curl -X POST http://localhost:8000/v1/api/team \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Team",
    "description": "Test description"
  }'

# Listar equipos
curl -X GET http://localhost:8000/v1/api/team \
  -H "Authorization: Bearer <token>"
```

## Consideraciones Futuras

- [ ] Invitaciones pendientes por email
- [ ] Auditoría de acciones en equipos
- [ ] Límites de miembros por equipo según plan
- [ ] Histórico de cambios en equipos
- [ ] Integración con sistema de permisos de juegos
- [ ] Soporte para subequipos/departamentos

