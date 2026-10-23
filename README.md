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

## Ejecutar con Docker

Esto permite instalar el Edge Service en otra laptop, mini-PC o Raspberry Pi que
esté en la misma red local que el ESP32.

1. Instala Docker Desktop (Windows/macOS) o Docker Engine (Linux/Raspberry Pi).
2. Copia la plantilla y configura una clave distinta para esa instalación:

   ```powershell
   Copy-Item .env.docker.example .env.docker
   ```

3. Edita `.env.docker` y reemplaza `EDGE_DEVICE_API_KEY` por una clave larga y
   secreta.
4. Construye e inicia el servicio:

   ```powershell
   docker compose up --build -d
   ```

5. Comprueba el estado con `http://localhost:5000/api/v1/status` o abre Swagger
   en `http://localhost:5000/docs/swagger`.

Docker conserva SQLite en el volumen `icetrack_edge_data`; reiniciar o actualizar
el contenedor no elimina la telemetría pendiente. Para detenerlo sin borrar datos:

```powershell
docker compose down
```

Desde el ESP32 no se utiliza `localhost`: configura como destino la dirección IP
local de la computadora/Raspberry Pi que ejecuta Docker, por ejemplo
`http://192.168.1.50:5000`.

La plantilla Docker es una configuración inicial para demostraciones porque crea
el dispositivo indicado en `EDGE_DEVICE_UID`. Antes de producción se deberá usar
un mecanismo de aprovisionamiento seguro y desactivar `SEED_EDGE_DEVICE`.

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
