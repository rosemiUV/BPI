import json
from pathlib import Path

def fusionar_datos_para_rag(ruta_transcripcion: Path, ruta_diarizacion: Path, ruta_guardado: Path, video_id: str, url_video: str, titulo_video: str, fecha_publicacion: str, max_palabras=50, solapamiento=15):
    """
    Junta transcripción y diarización añadiendo metadatos completos para Vector DB.
    """
    with open(ruta_transcripcion, 'r', encoding='utf-8') as f:
        transcripcion = json.load(f)
    with open(ruta_diarizacion, 'r', encoding='utf-8') as f:
        diarizacion = json.load(f)

    def encontrar_ponente(tiempo, segmentos_diarizacion):
        for turno in segmentos_diarizacion:
            if turno["inicio"] <= tiempo <= turno["fin"]:
                return turno["ponente"]
        return "DESCONOCIDO"

    todas_las_palabras = []
    for seg in transcripcion:
        punto_medio = (seg["inicio"] + seg["fin"]) / 2.0
        ponente = encontrar_ponente(punto_medio, diarizacion)
        
        palabras = seg["texto"].split()
        if not palabras: continue
            
        duracion_por_palabra = (seg["fin"] - seg["inicio"]) / len(palabras)
        
        for i, palabra in enumerate(palabras):
            t_inicio = seg["inicio"] + (i * duracion_por_palabra)
            t_fin = t_inicio + duracion_por_palabra
            todas_las_palabras.append({
                "texto": palabra,
                "inicio": t_inicio,
                "fin": t_fin,
                "ponente": ponente
            })

    chunks_finales = []
    salto = max_palabras - solapamiento
    if salto <= 0: salto = max_palabras
    
    for i in range(0, len(todas_las_palabras), salto):
        ventana = todas_las_palabras[i:i + max_palabras]
        if not ventana: break
        
        texto_chunk = " ".join([p["texto"] for p in ventana])
        inicio_chunk = ventana[0]["inicio"]
        fin_chunk = ventana[-1]["fin"]
        
        ponentes_en_ventana = [p["ponente"] for p in ventana]
        ponente_dominante = max(set(ponentes_en_ventana), key=ponentes_en_ventana.count)
        
        # --- CAMPOS NUEVOS Y AUTOGENERADOS ---
        # Formateamos el tiempo a entero para la URL de YouTube
        url_tiempo = f"{url_video}&t={int(inicio_chunk)}s"
        # Creamos un ID único combinando el vídeo y el segundo de inicio
        chunk_id = f"{video_id}_{int(inicio_chunk)}_{int(fin_chunk)}"
        
        chunks_finales.append({
            "chunk_id": chunk_id,
            "video_id": video_id,
            "titulo_video": titulo_video,
            "fecha_publicacion": fecha_publicacion,
            "url_video": url_video,
            "url_exacta_tiempo": url_tiempo,
            "ponente": ponente_dominante,
            "inicio": round(inicio_chunk, 3),
            "fin": round(fin_chunk, 3),
            "duracion": round(fin_chunk - inicio_chunk, 3),
            "texto": texto_chunk
        })

    ruta_guardado.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta_guardado, 'w', encoding='utf-8') as f:
        json.dump(chunks_finales, f, indent=2, ensure_ascii=False)
        
    return chunks_finales