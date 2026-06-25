import os
import subprocess
from pathlib import Path
import json
import torch
from dotenv import load_dotenv

load_dotenv()
HF_TOKEN = os.getenv("HF_TOKEN")

def configurar_ffmpeg_local() -> str:
    """Obtiene la ruta a la carpeta local tools_transcripcion y la inyecta en el PATH."""
    ruta_script = Path(__file__).parent
    dir_tools = ruta_script / "tools_transcripcion"
    dir_tools.mkdir(parents=True, exist_ok=True)
    
    # Añadimos nuestra carpeta al PATH de Windows de forma temporal (solo en la memoria de Python)
    if str(dir_tools) not in os.environ["PATH"]:
        os.environ["PATH"] = str(dir_tools) + os.pathsep + os.environ["PATH"]  
          
    return str(dir_tools)

def descargar_audio_youtube(url: str, directorio_salida: Path) -> Path:
    """Descarga el audio de YouTube usando yt-dlp."""
    print(f"Descargando audio de: {url}")
    directorio_salida.mkdir(parents=True, exist_ok=True)
    
    archivo_salida = directorio_salida / 'audio_prueba.wav'
    
    if archivo_salida.exists():
        archivo_salida.unlink()
        
    # Le decimos exactamente donde esta la carpeta con los .exe
    directorio_ffmpeg = configurar_ffmpeg_local()
        
    try:
        comando = [
            'yt-dlp',
            '--js-runtimes', 'node',
            '--extractor-args', 'youtube:player_client=android',              
            '-f', 'ba/b',
            '-x', '--audio-format', 'wav',
            '--ffmpeg-location', directorio_ffmpeg,
            '-o', str(archivo_salida),
            url
        ]
        
        subprocess.run(comando, capture_output=True, text=True, check=True)
        print(f"Audio descargado en: {archivo_salida}")
        return archivo_salida
        
    except subprocess.CalledProcessError as e:
        print(f"ERROR REAL DE YT-DLP:\n{e.stderr}")
        return None

def probar_whisperx(ruta_audio: Path, idioma: str = "es"):
    """Transcribe el audio usando WhisperX."""
    # Asegurarnos de que FFmpeg está en el PATH antes de importar whisperx
    configurar_ffmpeg_local()
    import whisperx
    
    dispositivo = "cuda" if torch.cuda.is_available() else "cpu"
    tipo_computo = "float16" if dispositivo == "cuda" else "int8"
    print(f"Usando dispositivo: {dispositivo.upper()}")
    
    try:
        print("Cargando modelo WhisperX (large-v2)...")
        modelo = whisperx.load_model("base", dispositivo, compute_type=tipo_computo)
        
        print("Transcribiendo...")
        resultado = modelo.transcribe(str(ruta_audio), batch_size=16, language=idioma)
        
        print("Alineando tiempos con precision...")
        modelo_alineacion, metadatos_alineacion = whisperx.load_align_model(language_code=idioma, device=dispositivo)
        resultado_alineado = whisperx.align(resultado["segments"], modelo_alineacion, metadatos_alineacion, str(ruta_audio), dispositivo, return_char_alignments=False)
        
        segmentos_finales = []
        for segmento in resultado_alineado["segments"]:
            if "start" in segmento and "end" in segmento:
                segmentos_finales.append({
                    "inicio": round(segmento["start"], 2),
                    "fin": round(segmento["end"], 2),
                    "texto": segmento["text"].strip()
                })
            
        return segmentos_finales

    except Exception as e:
        print(f"Error durante el proceso de WhisperX: {e}")
        return None

if __name__ == "__main__":
    if not HF_TOKEN:
        print("ADVERTENCIA: No se encontro HF_TOKEN en el archivo .env.")
        
    url_test = "https://www.youtube.com/watch?v=RerhvFiQIYI" 
    
    
    ruta_script = Path(__file__).parent
    dir_salida = ruta_script / "data_prueba"
    
    audio_path = descargar_audio_youtube(url_test, dir_salida)
    
    if audio_path:
        resultado_json = probar_whisperx(audio_path)
        
        if resultado_json:
            print("\nResultado Final (JSON):")
            print(json.dumps(resultado_json[:3], indent=2, ensure_ascii=False))
            print(f"... y {len(resultado_json) - 3} segmentos mas.")
            
            dir_resultados = ruta_script / "resultados"
            dir_resultados.mkdir(parents=True, exist_ok=True)
            ruta_guardado = dir_resultados / "resultado_prueba.json"
            
            with open(ruta_guardado, "w", encoding="utf-8") as f:
                json.dump(resultado_json, f, indent=2, ensure_ascii=False)
            print(f"Resultado completo guardado en '{ruta_guardado}'")