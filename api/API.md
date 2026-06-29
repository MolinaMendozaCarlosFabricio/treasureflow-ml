# TreasureFlow ML API

Microservicio de clustering geográfico para TreasureFlow. Agrupa publicaciones de residuos en
zonas de densidad usando DBSCAN con métrica haversine.

- **Versión:** 1.0.0
- **Servidor local:** `http://localhost:8000`
- **Especificación fuente:** [`openapi_swagger/openapi.yaml`](openapi_swagger/openapi.yaml)
- **Swagger UI interactivo (local):** [`figures/api/swagger.html`](figures/api/swagger.html)
- **Swagger UI servido por FastAPI:** `http://localhost:8000/docs` (Redoc en `/redoc`)

---

## Inferencia

### `POST /inference/assign-zone`

Recibe las coordenadas de una publicación de residuos y retorna la zona DBSCAN más cercana.
Si la publicación está fuera del radio de cualquier zona (`eps_meters`) retorna `zone_id: null`
y `assigned: false`. En cold start (sin modelo activo todavía) retorna `mode: "no_model"`.

**Request body**

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `publication_id` | string (UUID) | No | Identificador de la publicación |
| `lat` | number | Sí | Latitud en grados decimales (-90 a 90) |
| `lng` | number | Sí | Longitud en grados decimales (-180 a 180) |

```json
{
  "publication_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "lat": 19.432608,
  "lng": -99.133209
}
```

**Response `200`**

| Campo | Tipo | Descripción |
|---|---|---|
| `zone_id` | int \| null | Zona asignada, o `null` si es outlier o no hay modelo |
| `distance_meters` | float \| null | Distancia haversine al centroide más cercano |
| `model_version` | string \| null | Versión del modelo activo usado |
| `assigned` | bool | `true` si quedó dentro de `eps_meters` de alguna zona |
| `mode` | `"normal"` \| `"no_model"` | `"no_model"` en cold start |

```json
{
  "zone_id": 2,
  "distance_meters": 184.32,
  "model_version": "v1.0",
  "assigned": true,
  "mode": "normal"
}
```

**Response `422`** — validación fallida (`lat`/`lng` fuera de rango).

---

## Historial

### `GET /inference/history`

Consulta paginada del log de inferencias almacenado en BD Almacén. Soporta filtros por
`zone_id`, `assigned` y `from_date`.

**Query params**

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `limit` | int | 50 | Máximo de resultados por página (1–500) |
| `offset` | int | 0 | Registros a omitir |
| `zone_id` | int | — | Filtrar por zona específica |
| `assigned` | bool | — | Filtrar por asignación exitosa |
| `from_date` | string (`YYYY-MM-DD`) | — | Fecha mínima |

**Response `200`**

```json
{
  "total": 132,
  "results": [
    {
      "id": 17,
      "publication_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "lat": 19.432608,
      "lng": -99.133209,
      "zone_id": 2,
      "distance_meters": 184.32,
      "assigned": true,
      "model_version": "v1.0",
      "inferred_at": "2026-06-20T14:35:02"
    }
  ]
}
```

---

## Modelo

### `POST /reload-model`

Uso interno — llamado por el servidor de entrenamiento tras registrar una nueva versión
aprobada. Recarga los centroides desde BD Almacén sin reiniciar el servicio.

**Response `200`**

```json
{
  "status": "ok",
  "version_loaded": "v1.1",
  "n_zones": 5
}
```

---

## Health

### `GET /health`

Verifica que el servicio esté activo e indica el modelo cargado en memoria.

**Response `200`**

```json
{
  "status": "ok",
  "active_model": "v1.1",
  "n_zones_in_memory": 5,
  "mode": "normal"
}
```

`mode: "no_model"` y `active_model: null` indican que el servicio aún no tiene centroides
cargados (cold start, antes del primer entrenamiento aprobado).
