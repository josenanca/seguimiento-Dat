# Dashboard de seguimiento DAT

Aplicación Streamlit con el diseño del prototipo visual.

## Ejecutar
1. Descomprimir el ZIP.
2. Abrir una terminal en la carpeta.
3. Ejecutar `pip install -r requirements.txt`.
4. Ejecutar `streamlit run app_dashboard.py`.

La aplicación abre `Base.xlsx` incluido y permite cargar el nuevo archivo cada lunes.

## Regla implementada
- New/Open sin responsable: verde 0–4 días, amarillo 5–6, rojo desde 7.
- Waiting queda pendiente de validar hasta disponer de una columna inequívoca de fecha de respuesta de fábrica.
- Solo zonas Norte, Centro y Sur.
