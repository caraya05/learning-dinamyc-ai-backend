# 📋 RUTAS FINALES IMPLEMENTADAS - REFERENCIA PARA FRONTEND

## 🎯 TODAS LAS RUTAS DE OPCIONES MÚLTIPLES

---

## 📝 RUTAS DE TEXTO EN OPCIONES

### 1. ✅ Editar Pregunta de Opción
```
PATCH /characters/{character_id}/state/{state_id}/interaction/{interaction_index}/option/{option_index}/question/
```
**Content-Type:** `application/json`

**Request Body:**
```json
{
    "dialog": "Nuevo texto de la pregunta"
}
```

**Response (200 OK):**
```json
{
    "message": "Question dialog updated successfully",
    "dialog": "Nuevo texto de la pregunta"
}
```

**Ejemplo:**
```bash
curl -X PATCH "http://localhost:8000/characters/507f1f77bcf86cd799439011/state/69781923bd767a9af08a7496/interaction/0/option/0/question/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dialog": "¿Quieres ir al parque?"}'
```

---

### 2. ✅ Editar Respuesta de Opción
```
PATCH /characters/{character_id}/state/{state_id}/interaction/{interaction_index}/option/{option_index}/answer/
```
**Content-Type:** `application/json`

**Request Body:**
```json
{
    "dialog": "Nuevo texto de la respuesta"
}
```

**Response (200 OK):**
```json
{
    "message": "Answer dialog updated successfully",
    "dialog": "Nuevo texto de la respuesta"
}
```

**Ejemplo:**
```bash
curl -X PATCH "http://localhost:8000/characters/507f1f77bcf86cd799439011/state/69781923bd767a9af08a7496/interaction/0/option/0/answer/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dialog": "Sí, me encantaría ir"}'
```

---

### 3. ✅ Editar Guía de Opción
```
PATCH /characters/{character_id}/state/{state_id}/interaction/{interaction_index}/option/{option_index}/guideline/
```
**Content-Type:** `application/json`

**Request Body:**
```json
{
    "guideline": "Respuesta positiva y entusiasta"
}
```

**Response (200 OK):**
```json
{
    "message": "Guideline updated successfully",
    "guideline": "Respuesta positiva y entusiasta"
}
```

**Ejemplo:**
```bash
curl -X PATCH "http://localhost:8000/characters/507f1f77bcf86cd799439011/state/69781923bd767a9af08a7496/interaction/0/option/0/guideline/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"guideline": "Respuesta positiva y entusiasta"}'
```

---

## 🎵 RUTAS DE AUDIO EN OPCIONES

### 4. ✅ Subir Audio - Pregunta de Opción
```
POST /characters/{character_id}/state/{state_id}/interaction/{interaction_index}/option/{option_index}/question/audio/
```
**Content-Type:** `multipart/form-data`

**Form Data:**
- `audio`: File (MP3, WAV, OGG, M4A - Máximo 10MB)

**Response (200 OK):**
```json
{
    "message": "Audio updated successfully",
    "audio_url": "https://storage.googleapis.com/.../option-0-question.mp3",
    "database_url": "https://storage.googleapis.com/.../option-0-question.mp3",
    "urls_match": true,
    "updated_at": "2026-02-02T10:30:00",
    "metadata": {
        "size": 245760,
        "format": "mp3"
    }
}
```

**Ejemplo:**
```bash
curl -X POST "http://localhost:8000/characters/507f1f77bcf86cd799439011/state/69781923bd767a9af08a7496/interaction/0/option/0/question/audio/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "audio=@question.mp3"
```

---

### 5. ✅ Subir Audio - Respuesta de Opción
```
POST /characters/{character_id}/state/{state_id}/interaction/{interaction_index}/option/{option_index}/answer/audio/
```
**Content-Type:** `multipart/form-data`

**Form Data:**
- `audio`: File (MP3, WAV, OGG, M4A - Máximo 10MB)

**Response (200 OK):**
```json
{
    "message": "Audio updated successfully",
    "audio_url": "https://storage.googleapis.com/.../option-0-answer.mp3",
    "database_url": "https://storage.googleapis.com/.../option-0-answer.mp3",
    "urls_match": true,
    "updated_at": "2026-02-02T10:30:00",
    "metadata": {
        "size": 245760,
        "format": "mp3"
    }
}
```

**Ejemplo:**
```bash
curl -X POST "http://localhost:8000/characters/507f1f77bcf86cd799439011/state/69781923bd767a9af08a7496/interaction/0/option/0/answer/audio/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "audio=@answer.mp3"
```

---

### 6. ✅ Eliminar Audio - Pregunta de Opción
```
DELETE /characters/{character_id}/state/{state_id}/interaction/{interaction_index}/option/{option_index}/question/audio/
```

**Response (204 No Content)**
```
(sin contenido)
```

**Ejemplo:**
```bash
curl -X DELETE "http://localhost:8000/characters/507f1f77bcf86cd799439011/state/69781923bd767a9af08a7496/interaction/0/option/0/question/audio/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 7. ✅ Eliminar Audio - Respuesta de Opción
```
DELETE /characters/{character_id}/state/{state_id}/interaction/{interaction_index}/option/{option_index}/answer/audio/
```

**Response (204 No Content)**
```
(sin contenido)
```

**Ejemplo:**
```bash
curl -X DELETE "http://localhost:8000/characters/507f1f77bcf86cd799439011/state/69781923bd767a9af08a7496/interaction/0/option/0/answer/audio/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🔐 HEADERS REQUERIDOS EN TODAS LAS RUTAS

```
Authorization: Bearer {YOUR_TOKEN}
Content-Type: application/json (para PATCH)
Content-Type: multipart/form-data (para POST con archivos)
```

---

## 📊 RESUMEN DE RUTAS

| # | Método | Ruta | Descripción |
|---|--------|------|-------------|
| 1 | PATCH | `/characters/{id}/state/{state}/interaction/{i}/option/{j}/question/` | Editar pregunta |
| 2 | PATCH | `/characters/{id}/state/{state}/interaction/{i}/option/{j}/answer/` | Editar respuesta |
| 3 | PATCH | `/characters/{id}/state/{state}/interaction/{i}/option/{j}/guideline/` | Editar guía |
| 4 | POST | `/characters/{id}/state/{state}/interaction/{i}/option/{j}/question/audio/` | Subir audio pregunta |
| 5 | POST | `/characters/{id}/state/{state}/interaction/{i}/option/{j}/answer/audio/` | Subir audio respuesta |
| 6 | DELETE | `/characters/{id}/state/{state}/interaction/{i}/option/{j}/question/audio/` | Eliminar audio pregunta |
| 7 | DELETE | `/characters/{id}/state/{state}/interaction/{i}/option/{j}/answer/audio/` | Eliminar audio respuesta |

---

## 🎨 PARÁMETROS DE RUTA

### character_id
- **Tipo:** string (ObjectId)
- **Descripción:** ID del personaje
- **Ejemplo:** `507f1f77bcf86cd799439011`

### state_id
- **Tipo:** string
- **Descripción:** ID del estado del juego
- **Ejemplo:** `69781923bd767a9af08a7496`

### interaction_index
- **Tipo:** integer (0-based)
- **Descripción:** Índice de la interacción (comienza en 0)
- **Ejemplo:** `0` (primera interacción)

### option_index
- **Tipo:** integer (0-based)
- **Descripción:** Índice de la opción (comienza en 0)
- **Ejemplo:** `0` (primera opción)

---

## ⚠️ CÓDIGOS DE ERROR

### 400 Bad Request
```json
{
    "detail": {
        "error": "Validation Error",
        "message": "Dialog cannot be empty",
        "code": "VALIDATION_ERROR"
    }
}
```

### 403 Forbidden
```json
{
    "detail": {
        "error": "Forbidden",
        "message": "Permission denied",
        "code": "PERMISSION_DENIED"
    }
}
```

### 404 Not Found
```json
{
    "detail": {
        "error": "Not Found",
        "message": "Character not found",
        "code": "RESOURCE_NOT_FOUND"
    }
}
```

### 500 Internal Server Error
```json
{
    "detail": {
        "error": "Internal Server Error",
        "code": "INTERNAL_ERROR"
    }
}
```

---

## 🚀 GUÍA DE IMPLEMENTACIÓN FRONTEND

### Paso 1: Crear Servicio
```typescript
class OptionService {
  async updateQuestionDialog(characterId, stateId, interactionIndex, optionIndex, dialog, token) {
    return fetch(`/characters/${characterId}/state/${stateId}/interaction/${interactionIndex}/option/${optionIndex}/question/`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ dialog })
    });
  }
}
```

### Paso 2: Usar en Componentes
```typescript
const handleEditQuestion = async (text) => {
  const response = await optionService.updateQuestionDialog(
    characterId,
    stateId,
    interactionIndex,
    optionIndex,
    text,
    token
  );
  if (response.ok) {
    showSuccessMessage('Pregunta actualizada');
    reloadData();
  }
}
```

### Paso 3: Integrar en UI
```typescript
<input 
  value={questionText}
  onChange={(e) => setQuestionText(e.target.value)}
  onBlur={() => handleEditQuestion(questionText)}
/>
```

---

## 📚 DOCUMENTACIÓN RELACIONADA

- **OPCIONES_TEXTO_VERIFICADO.md** - Verificación detallada de endpoints de texto
- **IMPLEMENTACION_AUDIO_OPCIONES.md** - Especificación técnica de audio
- **GUIA_INTEGRACION_FRONTEND.md** - Código TypeScript/React completo

---

## ✅ CHECKLIST PARA FRONTEND

- [ ] Token de autenticación válido
- [ ] character_id es un ObjectId válido
- [ ] state_id existe
- [ ] interaction_index es válido (< cantidad de interacciones)
- [ ] option_index es válido (< cantidad de opciones)
- [ ] Para PATCH: dialog/guideline no está vacío
- [ ] Para POST: archivo de audio válido (MP3, WAV, OGG, M4A)
- [ ] Para POST: archivo < 10MB
- [ ] Headers correctos (Authorization, Content-Type)

---

## 🎯 PASOS TÍPICOS DE FLUJO

### Editar Pregunta
```
1. Usuario abre editor de opciones
2. Usuario hace click en pregunta
3. Abre campo de edición
4. Usuario escribe nuevo texto
5. Usuario presiona Enter o hace blur
6. Frontend: PATCH /characters/.../option/{j}/question/
7. Backend: Valida y actualiza en MongoDB
8. Frontend: Recibe 200 OK
9. Frontend: Toast "Pregunta actualizada"
10. Frontend: Recarga datos (opcional)
11. UI: Se actualiza con nuevo texto
```

### Subir Audio Pregunta
```
1. Usuario hace click en "Subir Audio"
2. Se abre selector de archivos
3. Usuario selecciona archivo MP3
4. Frontend valida (formato, tamaño)
5. Frontend muestra loading
6. Frontend: POST /characters/.../option/{j}/question/audio/
7. Backend: Valida, sube a GCS, actualiza MongoDB
8. Backend: Retorna URL del audio
9. Frontend: Toast "Audio cargado"
10. Frontend: Recarga datos (opcional)
11. UI: Muestra icono de audio disponible
```

---

## 📞 CONTACTO Y SOPORTE

Si tienes dudas:
1. Revisa Swagger: `http://localhost:8000/docs`
2. Lee documentación: `OPCIONES_TEXTO_VERIFICADO.md`
3. Ejecuta tests: `test_option_audio_endpoints.http`

---

**Última actualización:** 2 de febrero de 2026
**Estado:** ✅ Todas las rutas implementadas y funcionales

