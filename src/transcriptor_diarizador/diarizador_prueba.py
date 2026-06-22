import os
from pathlib import Path
import json
import torch
import torchaudio
from dotenv import load_dotenv

# --- INYECTAR FFMPEG ---
def inyectar_ffmpeg():
    ruta_script = Path(__file__).parent
    dir_tools = ruta_script / "tools_transcripcion"
    if str(dir_tools) not in os.environ.get("PATH", ""):
        os.environ["PATH"] = str(dir_tools) + os.pathsep + os.environ.get("PATH", "")
    if hasattr(os, 'add_dll_directory'):
        try:
            os.add_dll_directory(str(dir_tools))
        except Exception:
            pass
inyectar_ffmpeg()
# -----------------------

from pyannote.audio import Pipeline

# Cargar variables de entorno
load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")

def fusionar_turnos(segmentos, gap_max=1.0):
    """
    Fusiona turnos consecutivos del MISMO ponente separados por <= gap_max segundos.
    """
    if not segmentos:
        return []
    fusionados = [dict(segmentos[0])]
    for s in segmentos[1:]:
        prev = fusionados[-1]
        if s["ponente"] == prev["ponente"] and (s["inicio"] - prev["fin"]) <= gap_max:
            prev["fin"] = s["fin"]
        else:
            fusionados.append(dict(s))
    return fusionados

def ejecutar_diarizacion(ruta_audio: Path, video_id: str) -> list:
    """Ejecuta Pyannote sobre el audio dado, fusiona turnos y devuelve la lista de segmentos."""
    if not HF_TOKEN:
        print("ERROR: No se encontro HF_TOKEN en el archivo .env.")
        return None

    print("Cargando pipeline de diarizacion (Pyannote 3.1)...")
    try:
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=HF_TOKEN
        )
        
        dispositivo = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Moviendo Pyannote al dispositivo: {dispositivo}")
        pipeline = pipeline.to(dispositivo)
        
        # Bypass de Windows: Cargar en memoria usando soundfile directamente en vez de torchaudio
        print("Decodificando audio en memoria RAM con soundfile...")
        import soundfile as sf
        data, sample_rate = sf.read(str(ruta_audio), dtype='float32')
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        waveform = torch.from_numpy(data).T # (channels, frames)
        
        audio_in_memory = {"waveform": waveform, "sample_rate": sample_rate}
        
        print("Ejecutando diarizacion (esto puede tardar)...")
        diarization = pipeline(audio_in_memory)
        
        segmentos_crudos = []
        for segmento, _, ponente in diarization.itertracks(yield_label=True):
            segmentos_crudos.append({
                "video_id": video_id,
                "inicio": round(segmento.start, 3),
                "fin": round(segmento.end, 3),
                "ponente": ponente
            })
            
        # Aplicar la fusión de turnos
        segmentos_fusionados = fusionar_turnos(segmentos_crudos, gap_max=1.0)
        
        # Calcular duracion final de cada bloque
        for s in segmentos_fusionados:
            s["duracion"] = round(s["fin"] - s["inicio"], 3)
            
        return segmentos_fusionados
        
    except Exception as e:
        print(f"Error durante el proceso de Pyannote: {e}")
        return None