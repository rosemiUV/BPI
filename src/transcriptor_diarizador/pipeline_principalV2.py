import json
import warnings
import hashlib
from pathlib import Path

warnings.filterwarnings("ignore")

from src.transcriptor_diarizador.procesador import configurar_ffmpeg_local, descargar_audio_youtube, transcribir_y_diarizar
from src.transcriptor_diarizador.fusionador_pruebaV2 import fusionar_datos_para_rag
from src.transcriptor_diarizador.cargador_chroma import subir_datos_a_chroma

configurar_ffmpeg_local()


def obtener_metadatos_youtube(url: str):
    """Extrae título y fecha del vídeo usando yt-dlp."""
    try:
        import yt_dlp
        ydl_opts = {"quiet": True, "skip_download": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            titulo = info.get("title", "Sesión Parlamentaria")
            fecha = info.get("upload_date", "19700101")
            fecha_formateada = f"{fecha[:4]}-{fecha[4:6]}-{fecha[6:]}"
            return titulo, fecha_formateada
    except Exception as e:
        print(f"No se pudo obtener metadatos: {e}")
        return "Sesión Parlamentaria", "1970-01-01"


def ejecutar_pipeline_completo(url_video: str):
    """Función principal llamada desde FastAPI o desde __main__."""

    video_id = "video_" + hashlib.sha1(url_video.encode("utf-8")).hexdigest()[:8]
    titulo_real, fecha_publicacion = obtener_metadatos_youtube(url_video)

    print(f"\n{'='*45}")
    print(f"INICIANDO PIPELINE PARA: {video_id}")
    print(f"TÍTULO:  {titulo_real}")
    print(f"FECHA:   {fecha_publicacion}")
    print(f"{'='*45}")

    ruta_script = Path(__file__).parent
    dir_audio = ruta_script / "data_prueba"

    # --- FASE 1: DESCARGA ---
    audio_temporal = descargar_audio_youtube(url_video, dir_audio)
    if not audio_temporal or not audio_temporal.exists():
        raise Exception("Falló la descarga del audio.")

    audio_path = dir_audio / f"{video_id}.wav"
    audio_temporal.replace(audio_path)

    # --- FASE 2+3: TRANSCRIPCIÓN + DIARIZACIÓN INTEGRADA ---
    print("\n--- FASE 2+3: TRANSCRIPCIÓN Y DIARIZACIÓN (WhisperX + PyAnnote) ---")
    segmentos = transcribir_y_diarizar(audio_path)

    # Guardar segmentos crudos (útil para depuración)
    dir_diar = ruta_script / "resultados_diarizacion"
    dir_diar.mkdir(parents=True, exist_ok=True)
    ruta_segmentos_crudos = dir_diar / f"diarizacion_{video_id}.json"
    with open(ruta_segmentos_crudos, "w", encoding="utf-8") as f:
        json.dump(segmentos, f, indent=2, ensure_ascii=False)
    print(f"Segmentos crudos guardados en: {ruta_segmentos_crudos}")

    # --- FASE 4: CHUNKING + METADATOS ---
    print("\n--- FASE 4: GENERANDO CHUNKS PARA RAG ---")
    dir_final = ruta_script / "resultados_finales"
    ruta_json_final = dir_final / f"datos_rag_{video_id}.json"

    chunks = fusionar_datos_para_rag(
        segmentos=segmentos,
        video_id=video_id,
        url_video=url_video,
        titulo_video=titulo_real,
        fecha_publicacion=fecha_publicacion,
        ruta_guardado=ruta_json_final,
        max_palabras=50,
    )
    print(f"Chunks generados: {len(chunks)} — guardados en: {ruta_json_final}")

    # --- FASE 5: SUBIDA A CHROMADB ---
    print("\n--- FASE 5: SUBIDA A CHROMA DB ---")
    if ruta_json_final.exists():
        subir_datos_a_chroma(ruta_json_final)
    else:
        print("Error: no se encontró el JSON final.")

    print("\nPIPELINE COMPLETADO AL 100%.")
    return video_id, str(ruta_json_final), titulo_real


def ejecutar_pipeline_lote(lista_urls: list):
    """Procesa una lista de URLs una a una con cortafuegos por vídeo."""
    print(f"\nINICIANDO PROCESAMIENTO EN LOTE DE {len(lista_urls)} VÍDEOS")

    resultados_exitosos = []
    videos_fallidos = []

    for indice, url in enumerate(lista_urls, start=1):
        print(f"\n[VÍDEO {indice}/{len(lista_urls)}] {url}")
        try:
            video_id, ruta_json, titulo = ejecutar_pipeline_completo(url)
            resultados_exitosos.append({"url": url, "video_id": video_id, "titulo": titulo, "ruta_json": ruta_json})
            print(f"[VÍDEO {indice}/{len(lista_urls)}] Completado.")
        except Exception as e:
            print(f"[VÍDEO {indice}/{len(lista_urls)}] ERROR: {e}. Saltando al siguiente.")
            videos_fallidos.append({"url": url, "error": str(e)})

    print(f"\n{'='*45}")
    print(f"RESUMEN FINAL")
    print(f"  Completados: {len(resultados_exitosos)}")
    print(f"  Fallidos:    {len(videos_fallidos)}")
    for fallo in videos_fallidos:
        print(f"  - {fallo['url']} -> {fallo['error']}")
    print(f"{'='*45}")

    return resultados_exitosos, videos_fallidos


if __name__ == "__main__":
    mis_videos = [
        "https://youtu.be/Yz1OxfXwdr0?si=US3K_HiWMYn9KrCW",
        "https://www.youtube.com/watch?v=RerhvFiQIYI",
    ]
    ejecutar_pipeline_lote(mis_videos)
