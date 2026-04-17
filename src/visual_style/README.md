# Visual Style Module

Módulo para análisis y aplicación de estilos visuales IA.

## Overview

El módulo **visual_style** permite a los usuarios:

1. **Crear estilos visuales** especificando un prompt y nombre descriptivo
2. **Cargar imágenes de referencia** (hasta 5) que ejemplifiquen el estilo deseado
3. **Analizar automáticamente** los estilos usando GPT-4 Vision para extraer:
   - Tipo visual primario (cartoon, 2D, 3D, volumétrico, realista, etc.)
   - Estilos secundarios
   - Prompts optimizados para generar personajes y locaciones
   - Paleta de colores
   - Elementos artísticos
   - Detalles técnicos

4. **Aplicar estilos a generaciones** de personajes y locaciones para mantener consistencia visual

## Archivo Structure

```
src/visual_style/
├── __init__.py           # Inicialización del módulo
├── enums.py              # Enums para tipos de estilos y estados
├── models.py             # Modelos Pydantic (representación BD)
├── schemas.py            # Schemas para requests/responses
├── services.py           # Lógica de negocio
├── routers.py            # Endpoints REST
├── tasks.py              # Tareas Celery async
└── README.md             # Este archivo
```

## API Endpoints

### 1. Crear Estilo Visual
```
POST /v1/api/visual-style/
```

**Parámetros:**
- `name` (string, required): Nombre del estilo (min 1, max 200 caracteres)
- `description` (string, optional): Descripción del estilo
- `prompt` (string, required): Descripción del estilo visual deseado (min 10 caracteres)

**Respuesta (201):**
```json
{
  "_id": "507f1f77bcf86cd799439011",
  "user_id": "507f1f77bcf86cd799439010",
  "name": "Fantasy Cartoon",
  "description": "Estilo cartoon inspirado en RPGs fantasy",
  "original_prompt": "Create a vibrant cartoon style with bold outlines...",
  "status": "pending",
  "created_at": "2026-04-10T13:00:00Z"
}
```

### 2. Subir Imágenes de Referencia
```
POST /v1/api/visual-style/{style_id}/upload-reference-images
```

**Parámetros:**
- `images` (list[UploadFile], required): Archivos de imagen (máx 5 imágenes)

**Respuesta (200):**
```json
{
  "_id": "507f1f77bcf86cd799439011",
  "reference_image_urls": [
    "https://cdn.example.com/ref1.jpg",
    "https://cdn.example.com/ref2.jpg"
  ],
  "status": "pending"
}
```

### 3. Analizar Estilo Visual
```
POST /v1/api/visual-style/{style_id}/analyze
```

**Respuesta (202):**
```json
{
  "status": "analyzing",
  "style_id": "507f1f77bcf86cd799439011"
}
```

> El análisis es asincrónico y se ejecuta en background. Usa el endpoint `GET /{style_id}` para ver el estado.

### 4. Obtener Estilo Visual
```
GET /v1/api/visual-style/{style_id}
```

**Respuesta (200):**
```json
{
  "_id": "507f1f77bcf86cd799439011",
  "name": "Fantasy Cartoon",
  "primary_style": "cartoon",
  "secondary_styles": ["2d", "flat"],
  "style_prompts": {
    "character_style": "in vibrant cartoon style with bold outlines and exaggerated features",
    "location_style": "in 2D cartoon environment with dynamic lighting",
    "color_palette": "vibrant primary colors with bold outlines"
  },
  "color_description": "vibrant primary colors with bold outlines",
  "artistic_elements": ["bold_outlines", "flat_colors", "exaggerated_features"],
  "status": "completed"
}
```

### 5. Listar Estilos del Usuario
```
GET /v1/api/visual-style/user/my-styles?page=1&limit=10
```

**Respuesta (200):**
```json
{
  "results": [
    {
      "_id": "507f1f77bcf86cd799439011",
      "name": "Fantasy Cartoon",
      "status": "completed",
      "times_used": 3
    }
  ],
  "count": 1,
  "page": 1,
  "total_pages": 1
}
```

### 6. Aplicar Estilo a Personaje
```
POST /v1/api/visual-style/{style_id}/apply-to-character
```

**Parámetros:**
- `character_id` (string, required): ID del personaje

**Respuesta (200):**
```json
{
  "style_id": "507f1f77bcf86cd799439011",
  "character_style": "in vibrant cartoon style with bold outlines...",
  "color_palette": "vibrant primary colors with bold outlines",
  "primary_style": "cartoon"
}
```

### 7. Aplicar Estilo a Localización
```
POST /v1/api/visual-style/{style_id}/apply-to-location
```

**Parámetros:**
- `location_id` (string, required): ID de la localización

**Respuesta (200):**
```json
{
  "style_id": "507f1f77bcf86cd799439011",
  "location_style": "in 2D cartoon environment with dynamic lighting",
  "color_palette": "vibrant primary colors with bold outlines",
  "primary_style": "cartoon"
}
```

### 8. Eliminar Estilo
```
DELETE /v1/api/visual-style/{style_id}
```

**Respuesta (200):**
```json
{
  "deleted": true,
  "style_id": "507f1f77bcf86cd799439011"
}
```

## Tipos de Estilos Soportados

- `cartoon` - Estilo cartoon clásico
- `2d` - Arte 2D plano
- `3d` - Modelado 3D
- `volumetric` - Volumétrico/Cel-shading
- `realistic` - Realista fotográfico
- `anime` - Anime/manga
- `pixel_art` - Arte pixelado retro
- `watercolor` - Acuarela
- `oil_painting` - Óleo
- `comic` - Cómic
- `flat` - Diseño plano
- `sketched` - Dibujado/bosquejado

## Estados del Análisis

- `pending` - Esperando análisis
- `analyzing` - En proceso de análisis con GPT-4 Vision
- `completed` - Análisis completado exitosamente
- `failed` - Error durante el análisis

## Integración con Generación de Imágenes

### Personajes

Cuando se aplica un estilo a un personaje, los prompts se inyectan en la generación:

```python
# En character/tasks.py
visual_style_prompts = await service.apply_style_to_character(style_id, character_id)

prompt = f"Generate {character_name} {visual_style_prompts['character_style']}, "
prompt += f"with {visual_style_prompts['color_palette']}"

image = await openai_generator.generate_image(prompt=prompt, ...)
```

### Localizaciones

Similar para localizaciones:

```python
# En location/tasks.py
visual_style_prompts = await service.apply_style_to_location(style_id, location_id)

prompt = f"Generate location {location_name} {visual_style_prompts['location_style']}, "
prompt += f"colors: {visual_style_prompts['color_palette']}"

image = await openai_generator.generate_image(prompt=prompt, ...)
```

## Base de Datos

### Colección: `visual_style`

```json
{
  "_id": ObjectId,
  "user_id": "string",
  "name": "string",
  "description": "string",
  "original_prompt": "string",
  "reference_image_urls": ["string"],
  "primary_style": "enum",
  "secondary_styles": ["enum"],
  "style_prompts": {
    "character_style": "string",
    "location_style": "string",
    "color_palette": "string"
  },
  "color_description": "string",
  "artistic_elements": ["string"],
  "technical_details": "object",
  "status": "enum",
  "analysis_error": "string or null",
  "created_at": "datetime",
  "created_by": "string",
  "updated_at": "datetime",
  "updated_by": "string",
  "is_active": "boolean",
  "times_used": "int",
  "games_using_style": ["string"]
}
```

### Índices

```
- user_id
- created_at
- is_active
- (user_id, is_active)
```

## Celery Tasks

### `analyze_visual_style_task`

Ejecuta el análisis de estilo visual de forma asincrónica.

```python
async_analyze_visual_style_task.delay(style_id=style_id, user_id=user_id)
```

- **Queue:** default
- **Timeout:** 1 hora
- **Retries:** Configurado en celery_worker.py

## Flujo de Uso Típico

1. **Usuario crea estilo:**
   ```bash
   POST /v1/api/visual-style/
   name=MyStyle
   prompt="Cartoon style with vibrant colors"
   ```

2. **Usuario sube imágenes de referencia:**
   ```bash
   POST /v1/api/visual-style/{style_id}/upload-reference-images
   images=[ref1.jpg, ref2.jpg, ref3.jpg]
   ```

3. **Sistema analiza automáticamente o usuario dispara:**
   ```bash
   POST /v1/api/visual-style/{style_id}/analyze
   ```

4. **Usuario espera análisis (status = "analyzing" → "completed")**

5. **Usuario aplica estilo al crear personaje/localización:**
   - Recibe prompts mejorados via `apply-to-character` o `apply-to-location`
   - Usa estos prompts en generación DALL-E

6. **Imágenes generadas mantienen consistencia visual**

## Notas Técnicas

- Limita a **5 imágenes de referencia** para optimizar tokens de GPT-4 Vision
- Usa **GPT-4 Vision** (`gpt-4o`) para análisis visual detallado
- Análisis **asincrónico** mediante Celery para no bloquear requests
- Soporta **soft delete** (marca `is_active = False`)
- Mantiene **contador de uso** por estilo para analytics
- Respuestas JSON con `_id` → `id` aliasing automático

## Ejemplo de Uso Completo

```bash
# 1. Crear estilo
curl -X POST http://localhost:8000/v1/api/visual-style/ \
  -H "Authorization: Bearer {token}" \
  -F "name=Cyberpunk" \
  -F "prompt=Cyberpunk neon style with dark backgrounds and bright colors" \
  -F "description=Futuristic cyberpunk aesthetic"

# Response: {"_id": "...", "status": "pending", ...}

# 2. Subir imágenes
curl -X POST http://localhost:8000/v1/api/visual-style/{style_id}/upload-reference-images \
  -H "Authorization: Bearer {token}" \
  -F "images=@cyberpunk1.jpg" \
  -F "images=@cyberpunk2.jpg"

# 3. Analizar
curl -X POST http://localhost:8000/v1/api/visual-style/{style_id}/analyze \
  -H "Authorization: Bearer {token}"

# Response: {"status": "analyzing", ...}

# 4. Esperar a que se complete
curl -X GET http://localhost:8000/v1/api/visual-style/{style_id} \
  -H "Authorization: Bearer {token}"

# Esperar hasta que "status" sea "completed"

# 5. Usar en generación
curl -X POST http://localhost:8000/v1/api/visual-style/{style_id}/apply-to-character \
  -H "Authorization: Bearer {token}" \
  -F "character_id={char_id}"

# Recibir prompts mejorados para generar imagen
```

## Futuras Mejoras

1. Cachés de análisis para estilos similares
2. Pre-set de estilos predefinidos del sistema
3. Galería de estilos populares de la comunidad
4. Comparación visual entre estilos
5. Editor visual de prompts
6. Versionamiento de estilos

