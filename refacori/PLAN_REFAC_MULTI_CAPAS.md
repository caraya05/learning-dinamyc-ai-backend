# Plan de refactor: capas, comunicacion y borrado de series

## Objetivos
- Separar responsabilidades en capas: presentacion (FastAPI/routers), aplicacion (casos de uso), dominio (modelos/validaciones) e infraestructura (repositorios Mongo, storage, cola).
- Estandarizar comunicacion interna/externa y contratos (REST, eventos, tasks Celery) para reducir acoplamiento.
- Consolidar la eliminacion de series en un unico endpoint/servicio orquestado, sin flujos duplicados.

## Estado actual (resumen)
- Routers de FastAPI invocan servicios que acceden directo a Mongo (`core.database`).
- `series.services.delete_series_hard_service` ya borra en cascada la serie y sus juegos/relaciones; `remove_game_from_series` elimina un juego puntual.
- No hay capa de aplicacion explicita ni interfaces de repositorio; hay logica de negocio mezclada con acceso a datos.

## Acciones prioritarias
1) **Capas y estructura**
- Crear estructura `src/{domain}/{domain}_router.py` -> presentacion; `src/{domain}/application/use_cases.py` -> orquestacion; `src/{domain}/domain/models.py` & `schemas.py` -> reglas/DTOs; `src/infrastructure/repositories/{domain}_mongo.py` -> persistencia. Exportar puertos en `src/core/ports/{domain}_repository.py`.
- Mover validaciones y reglas (p.ej. orden de juegos, visibilidad) a casos de uso; routers solo hacen auth y delegan.

2) **Repositorios y puertos**
- Definir interfaces: `SeriesRepository` (crud series, reordenar), `GameRepository` (crud + provisional), `StateRepository` (state_glic/state_game), `CharacterRepository`, `LocationRepository`, `EventRepository`.
- Implementar adaptadores Mongo que reciban `AsyncIOMotorDatabase` y devuelvan dicts/DTOs; evitar usar `db` global.

3) **Comunicacion y contratos**
- REST: versionar rutas (`/api/v1/series`). Estandarizar respuestas con envoltura `{data, meta, errors}`.
- Eventos/Tareas: definir esquemas de eventos (`SeriesDeleted`, `GameDeleted`) en `core/events` y usarlos en Celery/consumidores; publicar tras casos de uso.
- Storage: centralizar uploads en un gateway (GCS) y encapsular en adaptador `StorageService` inyectable.

4) **Borrado en un solo endpoint/servicio**
- Exponer `DELETE /api/v1/series/{id}` que invoque `DeleteSeriesUseCase` (hard o soft segun flag). El caso de uso debe: validar ID, cargar serie, borrar/soft-delete juegos y relaciones (`state_glic/state_game/event/character/location`), borrar `game_provisional`, y remover la serie.
- Deprecar flujos redundantes (`/remove-game/`) o hacer que llamen al mismo caso de uso con un parametro `game_id` opcional; documentar en OpenAPI.

5) **Observabilidad y consistencia**
- Agregar logger estructurado y trazas por request ID; centralizar manejo de errores en middleware.
- Añadir tests de integracion para casos de uso: crear serie, agregar juegos, borrar serie (valida cascada) y borrar juego individual.

## Como hacerlo (hoja de ruta corta)
- Paso 1: Crear puertos en `core/ports` y adaptadores Mongo en `infrastructure/repositories`; inyectarlos en `SeriesService` o nuevos casos de uso.
- Paso 2: Extraer casos de uso a `series/application/use_cases.py` (`CreateSeries`, `UpdateSeries`, `DeleteSeries`, `ReorderGames`, etc.).
- Paso 3: Ajustar routers a llamar casos de uso y normalizar respuestas/errores; versionar rutas.
- Paso 4: Añadir eventos `SeriesDeleted`, `GameDeleted` y publicar en `DeleteSeriesUseCase`.
- Paso 5: Escribir tests de integracion para borrado en cascada y reorden.

## Preguntas abiertas
- ¿Soft-delete (marcar `is_active=False` + TTL) o hard-delete actual? Se recomienda soft + tarea de limpieza diferida.
- ¿Compartir juegos entre series? Si es afirmativo, no borrar juegos compartidos; requeriria tabla de referencias.
- ¿Mantener endpoints actuales y marcar obsoletos o hacer corte limpio con `/api/v1`?

