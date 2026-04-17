# Refactor por capas (serie y patrones aplicables)

## Objetivo
Separar responsabilidades en capas claras (presentacion, servicios/aplicacion, dominio, infraestructura/datos) para mejorar mantenibilidad, pruebas y control de reglas de negocio.

## Estructura sugerida
```
src/series/
  routers.py              # Capa presentacion (FastAPI)
  schemas.py              # DTOs de entrada/salida HTTP
  services.py             # Casos de uso (aplicacion)
  repositories.py         # Acceso a datos (Mongo/otros)
  domain/
    models.py             # Entidades y valores de dominio
    errors.py             # Excepciones de dominio
  mappers.py              # Conversion dominio <-> DB/DTO (opcional)
```

## Que hacer y como hacerlo
- Presentacion (routers)
  - Dejar solo parsing de DTOs, dependencias de auth/roles y retorno de respuestas.
  - Convertir excepciones de dominio en HTTP (ej. 404, 400, 403) en un manejador comun.
- Servicios/Aplicacion
  - Crear `SeriesService` con metodos `create`, `update`, `publish`, `reorder_games`, `remove_game`, `update_game_visibility`.
  - Aplicar reglas: rating 0-5, no publicar sin juegos, coherencia `publish_type` vs `is_link`, unicidad de juegos en `games_order`.
  - Inyectar repositorio (interfaz) para permitir dobles de prueba.
- Dominio
  - Definir `PublishType` como `Enum` (`public`, `link`, `private`).
  - Entidad `Series` con invariantes: `games_id` sin duplicados, `is_link` solo si `publish_type == link`, `is_published` derivado de `publish_type != private`.
  - Centralizar errores (`SeriesNotFound`, `InvalidPublishState`, `UnauthorizedOwner`).
- Infraestructura/Repositorios
  - Implementar `SeriesRepository` con operaciones CRUD y queries de listado/paginacion.
  - Mapear ObjectId <-> str en mappers; usar proyecciones para listados ligeros y filtros por `is_active`/`is_published`.
- DTOs y validaciones (schemas)
  - Usar `Literal`/`Enum` para `publish_type`; validadores de `ObjectId` en `category_id` y `games_order`.
  - Agregar `min_items` en listas y limites en `rating` (0-5).
- Tests
  - Unitarios de servicios con repo fake: publish sin juegos debe fallar, reorder con duplicados debe fallar, update de owner incorrecto -> 403.
  - Integracion de routers con app test y repo/mongo de prueba: happy-path de create/publish/list.

## Pasos inmediatos sugeridos
1) Crear `src/series/domain/models.py` y `errors.py` con `Series`, `PublishType` y excepciones.
2) Crear interfaz + implementacion inicial de `SeriesRepository` en `src/series/repositories.py` (Mongo actual).
3) Crear `SeriesService` en `src/series/services.py` moviendo reglas desde routers; agregar validaciones de dominio.
4) Ajustar `src/series/routers.py` para usar el servicio y manejar excepciones de dominio.
5) Endurecer DTOs en `src/series/schemas.py` (rating bounds, ObjectId checks, enums) y escribir tests de servicios/routers.

## Recomendaciones de comunicacion/infra
- Considerar cache Redis para listados publicados y vistas agregadas.
- Exponer eventos (ej. `series.published`) hacia Celery/cola si hay workflows posteriores.
- Registrar logs estructurados en servicios (accion, serie_id, user_id) y metricas por endpoint.

