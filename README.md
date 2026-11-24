# Seguimiento DAT v2.2

Integra la pestaña **Responsables** del Excel y asigna automáticamente el responsable de cada caso según Norte, Centro o Sur.

## Actualizar GitHub
Reemplace `app_dashboard.py` y `requirements.txt`; agregue `.streamlit/config.toml`. Streamlit Cloud redesplegará automáticamente.

## Excel requerido
Hojas: `Report`, `Zonas`, `Responsables`. La aplicación detecta automáticamente la fila de encabezados. Responsables debe contener `Zona` y `Responsable`.

## Regla de semáforo
New/Open sin asignación: verde 0–4, amarillo 5–6, rojo desde 7 días. Waiting queda pendiente hasta disponer de fecha de respuesta de fábrica.
