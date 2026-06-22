import json
import warnings
import hashlib
from pathlib import Path

# Ocultar los warnings molestos
warnings.filterwarnings("ignore")

# 1. Configurar FFmpeg ANTES de cargar NADA
from transcriber_prueba import configurar_ffmpeg_local
configurar_ffmpeg_local()

# 2. Ahora si, importamos las herramientas pesadas
from transcriber_prueba import descargar_audio_youtube, probar_whisperx
from diarizador_prueba import ejecutar_diarizacion

if __name__ == "__main__":
    url_video = "https://www.youtube.com/watch?v=RerhvFiQIYI"
    
    # --- NUEVO: Generar el VIDEO_ID único al arrancar ---
    video_id = "video_" + hashlib.sha1(url_video.encode("utf-8")).hexdigest()[:8]
    print(f"\n=============================================")
    print(f"INICIANDO PIPELINE PARA: {video_id}")
    print(f"=============================================")
    
    ruta_script = Path(__file__).parent
    dir_salida_audio = ruta_script / "data_prueba"
    
    print("\n--- INICIANDO FASE 1: OBTENCION DE DATOS ---")
    # Para ser más organizados, guardamos el audio con su nuevo ID
    ruta_guardado_audio = dir_salida_audio / f"{video_id}.wav"
    audio_path = descargar_audio_youtube(url_video, dir_salida_audio)
    
    # Renombrar archivo de audio temporal a su nombre único
    if audio_path and audio_path.exists():
        audio_path = audio_path.replace(ruta_guardado_audio)
    else:
        print("Fallo la descarga del audio. Abortando pipeline.")
        exit()

    print("\n--- INICIANDO FASE 2: TRANSCRIPCION (WhisperX) ---")
    # (Todavía no le pasamos el video_id porque actualizaremos el transcriptor en el próximo paso)
    resultado_transcripcion = probar_whisperx(audio_path)
    
    if resultado_transcripcion:
        dir_resultados_transcripcion = ruta_script / "resultados_transcripcion"
        dir_resultados_transcripcion.mkdir(parents=True, exist_ok=True)
        # Nombramos el archivo JSON usando el ID
        ruta_json_trans = dir_resultados_transcripcion / f"transcripcion_{video_id}.json"
        
        with open(ruta_json_trans, "w", encoding="utf-8") as f:
            json.dump(resultado_transcripcion, f, indent=2, ensure_ascii=False)
        print(f"Transcripcion guardada en: {ruta_json_trans}")

    print("\n--- INICIANDO FASE 3: DIARIZACION (Pyannote) ---")
    # Pasamos el video_id a la nueva versión del diarizador
    resultado_diarizacion = ejecutar_diarizacion(audio_path, video_id)
    
    if resultado_diarizacion:
        dir_resultados_diarizacion = ruta_script / "resultados_diarizacion"
        dir_resultados_diarizacion.mkdir(parents=True, exist_ok=True)
        ruta_json_diar = dir_resultados_diarizacion / f"diarizacion_{video_id}.json"
        
        with open(ruta_json_diar, "w", encoding="utf-8") as f:
            json.dump(resultado_diarizacion, f, indent=2, ensure_ascii=False)
        print(f"Diarizacion guardada en: {ruta_json_diar}")
    else:
        print("Pyannote no devolvio resultados.")
    
    import yt_dlp
    
    print("\n--- EXTRAYENDO METADATOS DEL VÍDEO ---")
    ydl_opts = {'quiet': True, 'skip_download': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url_video, download=False)
        titulo_video = info_dict.get('title', 'Titulo_Desconocido')
        
        # yt-dlp devuelve la fecha como YYYYMMDD, la formateamos a YYYY-MM-DD
        fecha_cruda = info_dict.get('upload_date', '19700101')
        fecha_publicacion = f"{fecha_cruda[:4]}-{fecha_cruda[4:6]}-{fecha_cruda[6:]}"
        
    print(f"Título detectado: {titulo_video}")
    print(f"Fecha detectada: {fecha_publicacion}")
        
    print("\n--- INICIANDO FASE 4: FUSION Y CHUNKING SEMANTICO ---")
    from fusionador_prueba import fusionar_datos_para_rag
    
    dir_resultados_final = ruta_script / "resultados_finales"
    ruta_json_final = dir_resultados_final / f"datos_rag_{video_id}.json"
    
    if ruta_json_trans.exists() and ruta_json_diar.exists():
        resultado_final = fusionar_datos_para_rag(
            ruta_transcripcion=ruta_json_trans,
            ruta_diarizacion=ruta_json_diar,
            ruta_guardado=ruta_json_final,
            video_id=video_id,
            url_video=url_video,
            titulo_video=titulo_video,             
            fecha_publicacion=fecha_publicacion,  
            max_palabras=50,     
            solapamiento=15      
        )
        print(f"Documento maestro generado con {len(resultado_final)} bloques.")
        print(f"Guardado en: {ruta_json_final}")
    else:
        print("Error: Faltan archivos de la Fase 2 o 3 para hacer la fusión.")
    
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

    print("\nPIPELINE COMPLETADO AL 100%.")