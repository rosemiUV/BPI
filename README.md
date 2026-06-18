# Motor de Búsqueda Semántica de Sesiones Plenarias de YouTube - MVP

Este repositorio contiene un MVP para procesar enlaces de YouTube de sesiones plenarias del gobierno, transcribir el audio, identificar oradores y proporcionar búsqueda semántica sobre el contenido generado.

## Pipeline de 4 Bloques

1. **Bloque A — Extracción / ASR**
   - Descargar audio de YouTube.
   - Transcribir con marcas de tiempo usando `faster-whisper`.
2. **Bloque B — Diarización**
   - Asignar etiquetas de orador en segmentos de tiempo con `pyannote.audio`.
3. **Bloque C — Motor de Búsqueda RAG**
   - Segmentar texto, almacenar embeddings en ChromaDB y recuperar contexto relevante.
4. **Bloque D — Interfaz Streamlit**
   - Procesar videos y ejecutar búsqueda semántica desde una interfaz web simple.

## Estructura del Proyecto

- `requirements.txt`
- `src/transcriber.py` (Bloque A)
- `src/diarizer.py` (Bloque B)
- `src/search_engine.py` (Bloque C)
- `src/app.py` (Bloque D)

## Instrucciones de Configuración

1. Clonar el repositorio.
2. Crear y activar un entorno virtual.
   - Linux/macOS:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```powershell
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
3. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
4. (Opcional) Crear un archivo `.env` para tokens de proveedores/modelos.
5. Ejecutar la aplicación Streamlit:
   ```bash
   streamlit run src/app.py
   ```

## Notas del MVP

- Las integraciones de ML pesadas están andamiadas con alternativas seguras para que el proyecto funcione inmediatamente.
- Reemplaza la lógica de simulación/alternativa con la configuración del modelo de producción cuando avances más allá de la etapa MVP.
