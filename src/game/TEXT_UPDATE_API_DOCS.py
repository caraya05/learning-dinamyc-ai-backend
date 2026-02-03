"""
Documentación y Ejemplos de Uso - API de Actualización de Textos
================================================================

Este archivo contiene ejemplos de cómo usar cada uno de los 9 endpoints implementados.

Todos los endpoints requieren autenticación mediante Bearer token en el header:
Authorization: Bearer {token}
"""

# ============================================================================
# 1. ACTUALIZAR TÍTULO DEL JUEGO
# ============================================================================
"""
ENDPOINT: PATCH /v1/api/game/{gameId}/title
Descripción: Actualiza el título del juego/episodio

Request:
{
  "title": "Nuevo título del episodio"
}

Response (200 OK):
{
  "_id": "507f1f77bcf86cd799439011",
  "title": "Nuevo título del episodio",
  "updated_at": "2024-01-27T10:00:00Z"
}

Errores:
- 404: Game not found
- 400: Title cannot be empty
- 403: Permission denied
"""

# Ejemplo con curl:
# curl -X PATCH "http://localhost:8000/v1/api/game/507f1f77bcf86cd799439011/title" \
#      -H "Authorization: Bearer {token}" \
#      -H "Content-Type: application/json" \
#      -d '{"title": "Nuevo título del episodio"}'


# ============================================================================
# 2. ACTUALIZAR DATOS DE PERSONAJE
# ============================================================================
"""
ENDPOINT: PATCH /v1/api/character/{characterId}/state/{stateId}
Descripción: Actualiza nombre y/o descripción de un personaje

Request:
{
  "name": "Nuevo nombre del personaje",
  "description": "Nueva descripción del personaje"
}

Response (200 OK):
{
  "_id": "507f1f77bcf86cd799439012",
  "state_glic": [
    {
      "element_id": "507f1f77bcf86cd799439012",
      "state": "state_001",
      "data": {
        "name": "Nuevo nombre del personaje",
        "description": "Nueva descripción del personaje",
        ...
      }
    }
  ],
  "updated_at": "2024-01-27T10:00:00Z"
}

Errores:
- 404: Character not found, State not found
- 400: At least one field (name or description) must be provided
- 403: Permission denied
"""

# Ejemplo con curl:
# curl -X PATCH "http://localhost:8000/v1/api/character/507f1f77bcf86cd799439012/state/state_001" \
#      -H "Authorization: Bearer {token}" \
#      -H "Content-Type: application/json" \
#      -d '{"name": "Nuevo nombre", "description": "Nueva descripción"}'


# ============================================================================
# 3. ACTUALIZAR DATOS DE LOCACIÓN
# ============================================================================
"""
ENDPOINT: PATCH /v1/api/location/{locationId}/state/{stateId}
Descripción: Actualiza título y/o descripción de una locación

Request:
{
  "title": "Nuevo nombre de la locación",
  "description": "Nueva descripción de la locación"
}

Response (200 OK):
{
  "_id": "507f1f77bcf86cd799439013",
  "state_glic": [
    {
      "element_id": "507f1f77bcf86cd799439013",
      "state": "state_001",
      "data": {
        "title": "Nuevo nombre de la locación",
        "description": "Nueva descripción de la locación",
        ...
      }
    }
  ],
  "updated_at": "2024-01-27T10:00:00Z"
}

Errores:
- 404: Location not found, State not found
- 400: At least one field (title or description) must be provided
- 403: Permission denied
"""

# Ejemplo con curl:
# curl -X PATCH "http://localhost:8000/v1/api/location/507f1f77bcf86cd799439013/state/state_001" \
#      -H "Authorization: Bearer {token}" \
#      -H "Content-Type: application/json" \
#      -d '{"title": "Nuevo título", "description": "Nueva descripción"}'


# ============================================================================
# 4. ACTUALIZAR DIÁLOGO DE INTERACCIÓN
# ============================================================================
"""
ENDPOINT: PATCH /v1/api/character/{characterId}/state/{stateId}/interaction/{interactionIndex}/dialog/{dialogIndex}
Descripción: Actualiza el texto de un diálogo en una interacción de personaje

Request:
{
  "dialog": "Nuevo texto del diálogo"
}

Response (200 OK):
{
  "success": true,
  "dialog": {
    "id_character": "507f1f77bcf86cd799439012",
    "dialog": "Nuevo texto del diálogo",
    "audio": "url_audio",
    "audio_mp3": "url_audio_mp3"
  },
  "updated_at": "2024-01-27T10:00:00Z"
}

Ruta de Datos:
Character → state_glic[stateId] → data → interaction[interactionIndex] → conversation[dialogIndex] → dialog

Errores:
- 404: Character not found, State not found
- 400: Dialog text cannot be empty, Invalid interaction/dialog index
- 403: Permission denied
"""

# Ejemplo con curl:
# curl -X PATCH "http://localhost:8000/v1/api/character/507f1f77bcf86cd799439012/state/state_001/interaction/0/dialog/0" \
#      -H "Authorization: Bearer {token}" \
#      -H "Content-Type: application/json" \
#      -d '{"dialog": "Nuevo texto del diálogo"}'


# ============================================================================
# 5. ACTUALIZAR PREGUNTA DE OPCIÓN
# ============================================================================
"""
ENDPOINT: PATCH /v1/api/character/{characterId}/state/{stateId}/interaction/{interactionIndex}/option/{optionIndex}/question
Descripción: Actualiza la pregunta de una opción múltiple

Request:
{
  "dialog": "Nueva pregunta de opción"
}

Response (200 OK):
{
  "success": true,
  "option": {
    "prompt_user_option": {
      "id_character": "507f1f77bcf86cd799439012",
      "dialog": "Nueva pregunta de opción",
      "audio": "url_audio",
      "audio_mp3": "url_audio_mp3"
    },
    "prompt_user_answer": {
      "id_character": "507f1f77bcf86cd799439012",
      "dialog": "Respuesta",
      "audio": "url_audio",
      "audio_mp3": "url_audio_mp3"
    },
    "prompt_user_guideline": "Guía"
  },
  "updated_at": "2024-01-27T10:00:00Z"
}

Ruta de Datos:
Character → state_glic[stateId] → data → interaction[interactionIndex] → options_dialog → options[optionIndex] → prompt_user_option → dialog

Errores:
- 404: Character not found, State not found
- 400: Dialog text cannot be empty, Invalid interaction/option index
- 403: Permission denied
"""

# Ejemplo con curl:
# curl -X PATCH "http://localhost:8000/v1/api/character/507f1f77bcf86cd799439012/state/state_001/interaction/0/option/0/question" \
#      -H "Authorization: Bearer {token}" \
#      -H "Content-Type: application/json" \
#      -d '{"dialog": "Nueva pregunta"}'


# ============================================================================
# 6. ACTUALIZAR RESPUESTA DE OPCIÓN
# ============================================================================
"""
ENDPOINT: PATCH /v1/api/character/{characterId}/state/{stateId}/interaction/{interactionIndex}/option/{optionIndex}/answer
Descripción: Actualiza la respuesta de una opción múltiple

Request:
{
  "dialog": "Nueva respuesta de opción"
}

Response (200 OK):
{
  "success": true,
  "option": {
    "prompt_user_option": { ... },
    "prompt_user_answer": {
      "id_character": "507f1f77bcf86cd799439012",
      "dialog": "Nueva respuesta de opción",
      "audio": "url_audio",
      "audio_mp3": "url_audio_mp3"
    },
    "prompt_user_guideline": "Guía"
  },
  "updated_at": "2024-01-27T10:00:00Z"
}

Ruta de Datos:
Character → state_glic[stateId] → data → interaction[interactionIndex] → options_dialog → options[optionIndex] → prompt_user_answer → dialog

Errores:
- 404: Character not found, State not found
- 400: Dialog text cannot be empty, Invalid interaction/option index
- 403: Permission denied
"""

# Ejemplo con curl:
# curl -X PATCH "http://localhost:8000/v1/api/character/507f1f77bcf86cd799439012/state/state_001/interaction/0/option/0/answer" \
#      -H "Authorization: Bearer {token}" \
#      -H "Content-Type: application/json" \
#      -d '{"dialog": "Nueva respuesta"}'


# ============================================================================
# 7. ACTUALIZAR GUÍA DE OPCIÓN
# ============================================================================
"""
ENDPOINT: PATCH /v1/api/character/{characterId}/state/{stateId}/interaction/{interactionIndex}/option/{optionIndex}/guideline
Descripción: Actualiza la guía de una opción (para preguntas abiertas)

Request:
{
  "guideline": "Nueva guía para la respuesta abierta"
}

Response (200 OK):
{
  "success": true,
  "guideline": "Nueva guía para la respuesta abierta",
  "updated_at": "2024-01-27T10:00:00Z"
}

Ruta de Datos:
Character → state_glic[stateId] → data → interaction[interactionIndex] → options_dialog → options[optionIndex] → prompt_user_guideline

Errores:
- 404: Character not found, State not found
- 400: Guideline text cannot be empty, Invalid interaction/option index
- 403: Permission denied
"""

# Ejemplo con curl:
# curl -X PATCH "http://localhost:8000/v1/api/character/507f1f77bcf86cd799439012/state/state_001/interaction/0/option/0/guideline" \
#      -H "Authorization: Bearer {token}" \
#      -H "Content-Type: application/json" \
#      -d '{"guideline": "Nueva guía"}'


# ============================================================================
# 8. ACTUALIZAR DATOS DE EVENTO
# ============================================================================
"""
ENDPOINT: PATCH /v1/api/event/{eventId}
Descripción: Actualiza los datos de un evento

Request:
{
  "text_image": "Texto que aparece en la imagen del evento",
  "description": "Descripción del evento",
  "prompt_user_text": "Texto adicional para el usuario"
}

Response (200 OK):
{
  "_id": "507f1f77bcf86cd799439014",
  "text_image": "Texto que aparece en la imagen del evento",
  "description": "Descripción del evento",
  "prompt_user_text": "Texto adicional para el usuario",
  "updated_at": "2024-01-27T10:00:00Z"
}

Errores:
- 404: Event not found
- 400: At least one field must be provided
- 403: Permission denied
"""

# Ejemplo con curl:
# curl -X PATCH "http://localhost:8000/v1/api/event/507f1f77bcf86cd799439014" \
#      -H "Authorization: Bearer {token}" \
#      -H "Content-Type: application/json" \
#      -d '{"text_image": "Nuevo texto", "description": "Nueva descripción"}'


# ============================================================================
# 9. ACTUALIZAR DIÁLOGO DE PREGUNTA ABIERTA
# ============================================================================
"""
ENDPOINT: PATCH /v1/api/character/{characterId}/state/{stateId}/interaction/{interactionIndex}/question/{questionIndex}
Descripción: Actualiza el texto de una pregunta abierta

Request:
{
  "dialog": "Nuevo texto de la pregunta"
}

Response (200 OK):
{
  "success": true,
  "question": {
    "id_character": "507f1f77bcf86cd799439012",
    "dialog": "Nuevo texto de la pregunta",
    "audio": "url_audio",
    "audio_mp3": "url_audio_mp3"
  },
  "updated_at": "2024-01-27T10:00:00Z"
}

Ruta de Datos:
Character → state_glic[stateId] → data → interaction[interactionIndex] → options_dialog → prompt_user_question[questionIndex] → dialog

Errores:
- 404: Character not found, State not found
- 400: Dialog text cannot be empty, Invalid interaction/question index
- 403: Permission denied
"""

# Ejemplo con curl:
# curl -X PATCH "http://localhost:8000/v1/api/character/507f1f77bcf86cd799439012/state/state_001/interaction/0/question/0" \
#      -H "Authorization: Bearer {token}" \
#      -H "Content-Type: application/json" \
#      -d '{"dialog": "Nuevo texto de pregunta"}'


# ============================================================================
# CÓDIGOS DE ERROR ESTÁNDAR
# ============================================================================
"""
404 - Not Found:
{
  "error": "Not Found",
  "message": "Character/Location/Event/Game not found",
  "code": "RESOURCE_NOT_FOUND"
}

400 - Validation Error:
{
  "error": "Validation Error",
  "message": "Dialog text cannot be empty",
  "code": "VALIDATION_ERROR"
}

403 - Permission Denied:
{
  "error": "Forbidden",
  "message": "You don't have permission to edit this game",
  "code": "PERMISSION_DENIED"
}

500 - Internal Server Error:
{
  "error": "Internal Server Error",
  "message": "An error occurred while updating the data",
  "code": "INTERNAL_ERROR"
}
"""


# ============================================================================
# CASOS DE PRUEBA RECOMENDADOS
# ============================================================================
"""
Para cada endpoint, asegúrate de probar:

✅ Caso exitoso con datos válidos
✅ Actualización de campos opcionales
✅ Actualización de múltiples campos simultáneamente

❌ Character/Location/Event/Game no existe (404)
❌ State no existe (404)
❌ Índice fuera de rango (400)
❌ Texto vacío (400)
❌ Usuario sin permisos (403)
❌ Token de autenticación inválido (401)
❌ Request sin bearer token (401)

Validaciones Implementadas:
- Verificación de existencia de recursos (Character, Location, Event, Game, State)
- Validación de índices dentro del rango válido
- Validación de campos no vacíos
- Control de permisos (verificando que el juego pertenece al usuario autenticado)
- Actualización automática de timestamp updated_at
- Registro de updated_by con ID del usuario
"""


# ============================================================================
# CONSIDERACIONES DE IMPLEMENTACIÓN
# ============================================================================
"""
1. Validación
   ✅ Todos los endpoints validan que los IDs existen
   ✅ Validan que los índices están dentro del rango válido
   ✅ Validan que el texto no esté vacío

2. Auditoría
   ✅ Se actualiza el campo updated_at en cada modificación
   ✅ Se guarda el campo updated_by con el ID del usuario que realizó el cambio

3. Audio
   Nota: En esta implementación, cuando se actualiza un texto que tiene audio:
   - El audio existente se conserva pero podría estar desactualizado
   - Se recomienda implementar un sistema adicional para invalidar/regenerar audio
   - El timestamp updated_at en el diálogo permite identificar cuándo fue actualizado

4. Caché
   Recomendación: Si el backend usa caché, invalidar después de cada actualización

5. Permisos
   ✅ Se valida que el usuario tiene permisos para editar el juego
   ✅ Se verifica que el juego pertenece al usuario autenticado

6. Respuestas de Error
   ✅ 404 - Recurso no encontrado
   ✅ 400 - Error de validación
   ✅ 403 - Sin permisos
   ✅ 500 - Error interno del servidor
"""
