# IceTrack Edge Service

Servicio local que recibe telemetría del ESP32, la guarda en SQLite y la sincroniza
con el backend de IceTrack cuando está habilitada la conexión cloud.

## Ejecutar en desarrollo

```powershell
cd D:\IoT-Code\icetrack-edge-service
.\.venv\Scripts\python.exe app.py
```

La configuración de desarrollo se encuentra en `.env.development`. El servicio se
inicia, por defecto, en `http://127.0.0.1:5000`.

## Documentación interactiva

Con el servicio ejecutándose, abre:

- Swagger UI: `http://127.0.0.1:5000/docs/swagger`
- Especificación OpenAPI JSON: `http://127.0.0.1:5000/docs/openapi.json`

Para los endpoints protegidos, pulsa **Authorize**, ingresa únicamente el valor de
la API key (en desarrollo: `local-development-only-key`) y confirma. Swagger
enviará el header `X-API-Key` en las solicitudes correspondientes.

## Endpoints principales

| Método | Ruta | Uso |
| --- | --- | --- |
| `GET` | `/api/v1/status` | Verifica que el servicio esté disponible. |
| `POST` | `/api/v1/iam/authentications` | Autentica localmente al ESP32. |
| `POST` | `/api/v1/telemetry/samples` | Guarda una lectura de sensores. |
| `GET` | `/api/v1/synchronization/status` | Consulta el estado de la cola local. |
| `POST` | `/api/v1/synchronization/attempts` | Ejecuta un intento manual de sincronización. |

No uses la clave de desarrollo fuera de tu entorno local. Para producción, define
las variables reales en el entorno de despliegue y conserva `SEED_EDGE_DEVICE=false`.
