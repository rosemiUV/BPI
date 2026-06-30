import os
import subprocess
from pathlib import Path
import torch
from dotenv import load_dotenv

# --- INYECTAR FFMPEG (Windows) — NO TOCAR ---
def inyectar_ffmpeg():
    ruta_script = Path(__file__).parent
    dir_tools = ruta_script / "tools_transcripcion"
    if str(dir_tools) not in os.environ.get("PATH", ""):
        os.environ["PATH"] = str(dir_tools) + os.pathsep + os.environ.get("PATH", "")
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(str(dir_tools))
        except Exception:
            pass

inyectar_ffmpeg()
# ---------------------------------------------

import whisperx

load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")


def configurar_ffmpeg_local() -> str:
    ruta_script = Path(__file__).parent
    dir_tools = ruta_script / "tools_transcripcion"
    dir_tools.mkdir(parents=True, exist_ok=True)
    if str(dir_tools) not in os.environ["PATH"]:
        os.environ["PATH"] = str(dir_tools) + os.pathsep + os.environ["PATH"]
    return str(dir_tools)


def descargar_audio_youtube(url: str, directorio_salida: Path) -> Path:
    print(f"Descargando audio de: {url}")
    directorio_salida.mkdir(parents=True, exist_ok=True)
    archivo_salida = directorio_salida / "audio_prueba.wav"
    if archivo_salida.exists():
        archivo_salida.unlink()
    directorio_ffmpeg = configurar_ffmpeg_local()
    try:
        comando = [
            "yt-dlp",
            "--extractor-args", "youtube:player_client=ios", # Workaround para evitar bloqueos
            "--force-overwrites", # Evitar que pregunte si queremos sobreescribir el archivo .webm
            "-f", "ba/b",
            "-x", "--audio-format", "wav",
            "--ffmpeg-location", directorio_ffmpeg,
            "-o", str(archivo_salida),
            url,
        ]
        subprocess.run(comando, capture_output=True, text=True, check=True, stdin=subprocess.DEVNULL)
        print(f"Audio descargado en: {archivo_salida}")
        return archivo_salida
    except subprocess.CalledProcessError as e:
        print(f"ERROR YT-DLP:\n{e.stderr}")
        return None


def transcribir_y_diarizar(ruta_audio: Path, idioma: str = "es") -> list:
    """
    Transcribe con WhisperX y asigna speakers a nivel de palabra usando PyAnnote integrado.
    Devuelve los segmentos de WhisperX, cada uno con campo 'speaker'.
    """
    if not HF_TOKEN:
        raise ValueError("HF_TOKEN no encontrado en .env")

    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    tipo_computo = "float16" if dispositivo == "cuda" else "int8"
    print(f"Dispositivo: {dispositivo.upper()}")

    # 1. Transcribir
    print("Cargando modelo WhisperX (large-v2)...")
    modelo = whisperx.load_model("large-v2", dispositivo, compute_type=tipo_computo)
    
    try:
        resultado = modelo.transcribe(str(ruta_audio), batch_size=16, language=idioma)
    except IndexError as e:
        print("AVISO: WhisperX lanzó IndexError durante la transcripción. Es probable que no haya voz activa en el audio.")
        del modelo
        if dispositivo == "cuda":
            torch.cuda.empty_cache()
        return []
        
    del modelo
    if dispositivo == "cuda":
        torch.cuda.empty_cache()

    if not resultado.get("segments"):
        print("AVISO: No se detectaron segmentos de voz en la transcripción.")
        return []

    # 2. Alinear timestamps a nivel de palabra
    print("Alineando timestamps por palabra...")
    modelo_align, metadata = whisperx.load_align_model(
        language_code=idioma, device=dispositivo
    )
    resultado_alineado = whisperx.align(
        resultado["segments"],
        modelo_align,
        metadata,
        str(ruta_audio),
        dispositivo,
        return_char_alignments=False,
    )
    del modelo_align
    if dispositivo == "cuda":
        torch.cuda.empty_cache()

    # 3. Diarizar con PyAnnote a través de WhisperX
    print("Ejecutando diarización integrada (PyAnnote via WhisperX)...")
    try:
        pipeline_diar = whisperx.diarize.DiarizationPipeline(
            token=HF_TOKEN,
            device=torch.device(dispositivo),
        )
    except TypeError:
        pipeline_diar = whisperx.diarize.DiarizationPipeline(
            use_auth_token=HF_TOKEN,
            device=torch.device(dispositivo),
        )
    
    try:
        segmentos_diar = pipeline_diar(str(ruta_audio))
    except Exception as e:
        print(f"AVISO: PyAnnote falló en la diarización ({e}). Retornando sin speakers.")
        return resultado_alineado["segments"]

    # 4. Asignar speakers a nivel de palabra
    print("Asignando speakers a cada palabra...")
    try:
        resultado_final = whisperx.assign_word_speakers(segmentos_diar, resultado_alineado)
    except Exception as e:
        print(f"AVISO: Fallo al asignar speakers ({e}). Retornando transcripción sin asignar.")
        return resultado_alineado["segments"]

    return resultado_final["segments"]
