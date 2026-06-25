import json
import warnings
import hashlib
import subprocess
from pathlib import Path

# Ocultar los warnings molestos
warnings.filterwarnings("ignore")

# Usamos rutas absolutas del proyecto para evitar errores al llamar desde FastAPI
from src.transcriptor_diarizador.transcriber_prueba import configurar_ffmpeg_local, descargar_audio_youtube, probar_whisperx
from src.transcriptor_diarizador.diarizador_prueba import ejecutar_diarizacion
from src.transcriptor_diarizador.fusionador_prueba import fusionar_datos_para_rag

configurar_ffmpeg_local()

def obtener_metadatos_youtube(url: str):
    """Extrae el titulo real y fecha del video usando yt-dlp de forma rapida."""
    try:
        import yt_dlp
        ydl_opts = {'quiet': True, 'skip_download': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            titulo = info.get('title', 'Sesión Parlamentaria')
            fecha = info.get('upload_date', '19700101')
            fecha_formateada = f"{fecha[:4]}-{fecha[4:6]}-{fecha[6:]}"
            return titulo, fecha_formateada
    except Exception as e:
        print(f"No se pudo obtener metadatos: {e}")
        return "Sesión Parlamentaria", "1970-01-01"

def ejecutar_pipeline_completo(url_video: str):
    """Función que será llamada desde FastAPI."""
    
    # Generar el VIDEO_ID único y sacar el título
    video_id = "video_" + hashlib.sha1(url_video.encode("utf-8")).hexdigest()[:8]
    titulo_real, fecha_publicacion = obtener_metadatos_youtube(url_video)
    
    print(f"\n=============================================")
    print(f"INICIANDO PIPELINE PARA: {video_id}")
    print(f"TÍTULO: {titulo_real}")
    print(f"FECHA: {fecha_publicacion}")
    print(f"=============================================")
    
    ruta_script = Path(__file__).parent
    dir_salida_audio = ruta_script / "data_prueba"
    
    # --- FASE 1: OBTENCION ---
    ruta_guardado_audio = dir_salida_audio / f"{video_id}.wav"
    audio_path_temporal = descargar_audio_youtube(url_video, dir_salida_audio)
    
    if audio_path_temporal and audio_path_temporal.exists():
        audio_path_temporal.replace(ruta_guardado_audio)
        audio_path = ruta_guardado_audio
    else:
        raise Exception("Falló la descarga del audio.")

    # --- FASE 2: TRANSCRIPCION ---
    resultado_transcripcion = probar_whisperx(audio_path)
    if not resultado_transcripcion:
        raise Exception("Falló la transcripción con WhisperX.")
        
    dir_resultados_transcripcion = ruta_script / "resultados_transcripcion"
    dir_resultados_transcripcion.mkdir(parents=True, exist_ok=True)
    ruta_json_trans = dir_resultados_transcripcion / f"transcripcion_{video_id}.json"
    
    with open(ruta_json_trans, "w", encoding="utf-8") as f:
        json.dump(resultado_transcripcion, f, indent=2, ensure_ascii=False)

    # --- FASE 3: DIARIZACION ---
    resultado_diarizacion = ejecutar_diarizacion(audio_path, video_id)
    if not resultado_diarizacion:
        raise Exception("Falló la diarización con Pyannote.")
        
    dir_resultados_diarizacion = ruta_script / "resultados_diarizacion"
    dir_resultados_diarizacion.mkdir(parents=True, exist_ok=True)
    ruta_json_diar = dir_resultados_diarizacion / f"diarizacion_{video_id}.json"
    
    with open(ruta_json_diar, "w", encoding="utf-8") as f:
        json.dump(resultado_diarizacion, f, indent=2, ensure_ascii=False)
        
    # --- FASE 4: FUSION ---
    dir_resultados_final = ruta_script / "resultados_finales"
    ruta_json_final = dir_resultados_final / f"datos_rag_{video_id}.json"
    
    resultado_final = fusionar_datos_para_rag(
        ruta_transcripcion=ruta_json_trans,
        ruta_diarizacion=ruta_json_diar,
        ruta_guardado=ruta_json_final,
        video_id=video_id,
        url_video=url_video,
        titulo_video=titulo_real,             
        fecha_publicacion=fecha_publicacion,  
        max_palabras=50,     
        solapamiento=15      
    )
    
    # FASE 5 (SUBIDA A BASE DE DATOS VECTORIAL)
    print("\n--- INICIANDO FASE 5: SUBIDA A CHROMA DB ---")
    try:
        from cargador_chroma import subir_datos_a_chroma
        if ruta_json_final.exists():
            subir_datos_a_chroma(ruta_json_final) 
        else:
            print("Error: No se encontró el JSON final para subir a la base de datos.")
    except ImportError as e:
        print(f"Aviso: No se pudo importar el módulo ChromaDB. Error: {e}")
    except Exception as e:
        print(f"Error durante la subida a ChromaDB: {e}")

    print("\nPIPELINE COMPLETADO AL 100%.")

    # IMPORTANTE: Ahora devolvemos 3 cosas para el Director de Orquesta
    return video_id, str(ruta_json_final), titulo_real
