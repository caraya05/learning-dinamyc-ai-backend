# 🔍 SCRIPT DE VERIFICACIÓN DE AUDIO

## ¿Qué hace?

Este script verifica que después de subir un audio, la URL guardada en la base de datos es exactamente la misma que se subió.

## ¿Cómo usarlo?

### Paso 1: Sube el audio con PATCH

```bash
curl -X PATCH \
  'http://localhost:9000/v1/api/characters/69781924bd767a9af08a7499/state/69781923bd767a9af08a7496/interaction/0/dialog/0/audio/' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -F 'audio=@/path/to/audio.mp3'
```

### Paso 2: Copia la respuesta

La respuesta será algo como:

```json
{
  "message": "Audio updated successfully",
  "audio_url": "https://storage.googleapis.com/qwestar/characters/69781924bd767a9af08a7499/audios/abc123def456_dialog.mp3",
  "updated_at": "2026-01-29T10:00:00",
  "metadata": {
    "size": 524288,
    "format": "mp3"
  }
}
```

### Paso 3: Ejecuta el script de verificación

Copia los valores y ejecuta:

```bash
python3 scripts/verify_audio_update.py \
  "69781923bd767a9af08a7496" \
  "https://storage.googleapis.com/qwestar/characters/69781924bd767a9af08a7499/audios/abc123def456_dialog.mp3" \
  0 \
  0
```

**Argumentos:**
- `69781923bd767a9af08a7496` = state_glic_id (el `state_id` de la URL)
- `https://storage.googleapis.com/...` = audio_url (la URL que retornó la API)
- `0` = interaction_index (índice de la interacción)
- `0` = dialog_index (índice del diálogo)

## ¿Qué verifica?

✅ Que el documento state_glic existe  
✅ Que la interacción existe en ese índice  
✅ Que el diálogo existe en ese índice  
✅ Que el campo `audio` tiene la URL  
✅ Que el campo `audio_mp3` tiene la URL  
✅ **Que la URL en BD COINCIDE exactamente con la URL subida** ⭐  
✅ Que ambos campos (`audio` y `audio_mp3`) son iguales  
✅ Que la URL es de Google Cloud Storage  
✅ Que se registró la auditoría (`updated_at`, `updated_by`)  

## Resultado

Si todo está correcto, verás:

```
═════════════════════════════════════════════════════════════════
✅ VERIFICACIÓN COMPLETADA EXITOSAMENTE
═════════════════════════════════════════════════════════════════

✨ El audio se actualizó correctamente en la base de datos
✨ La URL guardada coincide con la URL subida
```

## Requisitos

- Tener Python 3.8+
- Estar en la carpeta del proyecto
- La configuración de MongoDB debe estar en `config.py`

## Ejemplo Completo

```bash
# 1. Subir el audio
curl -X PATCH \
  'http://localhost:9000/v1/api/characters/69781924bd767a9af08a7499/state/69781923bd767a9af08a7496/interaction/0/dialog/0/audio/' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...' \
  -F 'audio=@/Users/caraya/audio.mp3'

# Respuesta:
# {
#   "message": "Audio updated successfully",
#   "audio_url": "https://storage.googleapis.com/qwestar/...",
#   ...
# }

# 2. Verificar que se guardó correctamente
python3 scripts/verify_audio_update.py \
  "69781923bd767a9af08a7496" \
  "https://storage.googleapis.com/qwestar/characters/69781924bd767a9af08a7499/audios/abc123_dialog.mp3" \
  0 \
  0
```

