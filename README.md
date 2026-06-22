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

## Requisitos Previos: Instalación de FFmpeg (Windows)

Este proyecto utiliza **yt-dlp** y **WhisperX**, herramientas que requieren un motor interno llamado **FFmpeg** para procesar, extraer y convertir el audio de los vídeos de forma eficiente. 

Debido a las políticas de seguridad y restricciones de tamaño de GitHub (límite de 100 MB), los ejecutables pesados no se incluyen en este repositorio. Para que el pipeline funcione en tu máquina local, debes descargarlos manualmente siguiendo estos pasos:

### Paso 1: Descargar los binarios
1. Ve a la página oficial de *builds* de FFmpeg para Windows: [gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)
2. Desplázate hasta la sección **"release builds"** y descarga el archivo empaquetado (suele llamarse `ffmpeg-release-essentials.zip` o similar).

### Paso 2: Extraer los archivos clave
1. Descomprime el archivo `.zip` descargado en cualquier lugar de tu ordenador.
2. Navega hasta la subcarpeta `bin/` que encontrarás en su interior.
3. Copia **únicamente** estos dos archivos: 
   * `ffmpeg.exe`
   * `ffprobe.exe`

### Paso 3: Ubicarlos en el proyecto
Pega esos dos archivos `.exe` exactamente en la siguiente ruta de nuestro proyecto. (Si la carpeta `tools_transcripcion` no existe, créala):

`src/transcriptor_diarizador/tools_transcripcion/`

Para asegurarte de que lo has hecho bien, tu árbol de directorios debería verse exactamente así:

```text
📂 BPI
 ┗ 📂 src
   ┗ 📂 transcriptor_diarizador
     ┣ 📜 pipeline_principal.py
     ┣ ...
     ┗ 📂 tools_transcripcion
       ┣ 📜 ffmpeg.exe    <-- ¡Colocar aquí!
       ┗ 📜 ffprobe.exe   <-- ¡Colocar aquí!

## Notas del MVP

- Las integraciones de ML pesadas están andamiadas con alternativas seguras para que el proyecto funcione inmediatamente.
- Reemplaza la lógica de simulación/alternativa con la configuración del modelo de producción cuando avances más allá de la etapa MVP.
