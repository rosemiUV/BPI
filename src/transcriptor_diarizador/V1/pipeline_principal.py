import json
import warnings
import hashlib
import subprocess
from pathlib import Path

# Ocultar los warnings molestos
warnings.filterwarnings("ignore")

# Usamos rutas absolutas del proyecto para evitar errores al llamar desde FastAPI
from src.transcriptor_diarizador.V1.transcriber_prueba import configurar_ffmpeg_local, descargar_audio_youtube, probar_whisperx
from src.transcriptor_diarizador.V1.diarizador_prueba import ejecutar_diarizacion
from src.transcriptor_diarizador.V1.fusionador_prueba import fusionar_datos_para_rag

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
        
    print(f" Diarización completada. Guardando JSON...")
    dir_resultados_diarizacion = ruta_script / "resultados_diarizacion"
    dir_resultados_diarizacion.mkdir(parents=True, exist_ok=True)
    ruta_json_diar = dir_resultados_diarizacion / f"diarizacion_{video_id}.json"
    
    with open(ruta_json_diar, "w", encoding="utf-8") as f:
        json.dump(resultado_diarizacion, f, indent=2, ensure_ascii=False)
        
    # --- FASE 4: FUSION ---
    print(f" Iniciando fusión de transcripción y diarización...")
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
    print(f" Fusión completada. Documento RAG generado.")
    
    # FASE 5 (SUBIDA A BASE DE DATOS VECTORIAL)
    print("\n--- INICIANDO FASE 5: SUBIDA A CHROMA DB ---")
    try:
        # AQUÍ ESTÁ LA MAGIA: Le ponemos la ruta completa
        from src.transcriptor_diarizador.V1.cargador_chroma import subir_datos_a_chroma
        
        if ruta_json_final.exists():
            subir_datos_a_chroma(ruta_json_final) 
        else:
            print("Error: No se encontró el JSON final para subir a la base de datos.")
    except ImportError as e:
        print(f"Aviso: No se pudo importar el módulo ChromaDB. Error: {e}")
    except Exception as e:
        print(f"Error durante la subida a ChromaDB: {e}")

    print("\nPIPELINE COMPLETADO AL 100%.")

    return video_id, str(ruta_json_final), titulo_real


def ejecutar_pipeline_lote(lista_urls: list):
    """
    Recibe una lista de URLs y las procesa una a una. 
    Diseñado para ejecuciones largas (batch processing).
    """
    print(f"\n INICIANDO PROCESAMIENTO EN LOTE DE {len(lista_urls)} VÍDEOS")
    
    resultados_exitosos = []
    videos_fallidos = []

    for indice, url in enumerate(lista_urls, start=1):
        print(f"\n [VÍDEO {indice}/{len(lista_urls)}] Preparando: {url}")
        
        try:
            # Llamamos a tu función original que procesa un solo vídeo
            video_id, ruta_json, titulo = ejecutar_pipeline_completo(url)
            
            # Si termina bien, lo guardamos en la lista de éxitos
            resultados_exitosos.append({
                "url": url,
                "video_id": video_id,
                "titulo": titulo,
                "ruta_json": ruta_json
            })
            print(f" [VÍDEO {indice}/{len(lista_urls)}] Completado con éxito.")
            
        except Exception as e:
            # CORTAFUEGOS: Si el vídeo falla, lo capturamos y el bucle sigue
            print(f" [VÍDEO {indice}/{len(lista_urls)}] ERROR CRÍTICO. Saltando al siguiente. Motivo: {e}")
            videos_fallidos.append({
                "url": url,
                "error": str(e)
            })

    # Al terminar toda la lista, imprimimos un resumen para cuando te despiertes
    print("\n=============================================")
    print(" RESUMEN FINAL DEL PROCESAMIENTO NOCTURNO")
    print(f" VÍDEOS COMPLETADOS: {len(resultados_exitosos)}")
    print(f" VÍDEOS FALLIDOS: {len(videos_fallidos)}")
    if videos_fallidos:
        print("Detalle de fallos:")
        for fallo in videos_fallidos:
            print(f"  - {fallo['url']} -> {fallo['error']}")
    print("=============================================")

    # Devolvemos ambos diccionarios por si FastAPI necesita mostrarlos en pantalla
    return resultados_exitosos, videos_fallidos


if __name__ == "__main__":
    # Pon aquí los enlaces que quieras procesar esta noche
    mis_videos_nocturnos = [
        "https://youtu.be/Yz1OxfXwdr0?si=US3K_HiWMYn9KrCW",
        "https://www.youtube.com/watch?v=RerhvFiQIYI"
    ]
    
    # Lanzamos el lote
    ejecutar_pipeline_lote(mis_videos_nocturnos)