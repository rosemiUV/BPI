'''
Los endpoints (URLs) de la API
'''

import asyncio
from fastapi import APIRouter, HTTPException
from datetime import datetime
from src.api.schemas import SearchRequest, SearchResponse
from src.api.schemas import UrlVideoRequest
from src.transcriptor_diarizador.pipeline_principal import ejecutar_pipeline_lote

# Instanciamos el enrutador
router = APIRouter()

@router.get('/sessions')
def get_sessions():
    """
    Devuelve la lista de sesiones únicas almacenadas en ChromaDB.
    """
    try:
        from src.transcriptor_diarizador.cargador_chroma import conectar_chromadb, obtener_coleccion
        cliente = conectar_chromadb()
        coleccion = obtener_coleccion(cliente)
        
        resultado = coleccion.get(include=["metadatas"])
        metadatos = resultado.get("metadatas", [])
        
        sesiones_vistas = set()
        sesiones_unicas = []
        
        for m in metadatos:
            vid = m.get("video_id")
            if vid and vid not in sesiones_vistas:
                sesiones_vistas.add(vid)
                # Formateamos la duración a un formato legible si es posible
                dur = "Procesada"
                
                sesiones_unicas.append({
                    "id_sesion": vid,
                    "titulo": m.get("titulo_video", "Sesión Parlamentaria"),
                    "fecha": m.get("fecha_publicacion", "Desconocida"),
                    "duracion": dur
                })
                
        return sesiones_unicas
    except Exception as e:
        print(f"Error al obtener sesiones de ChromaDB: {e}")
        # Si falla, devolvemos un array vacío para no romper el frontend
        return []

@router.post('/search', response_model=SearchResponse)
def perform_search(request: SearchRequest):
    """
    Recibe la pregunta del usuario y busca en ChromaDB y llama a Llama-3.
    """
    from src.motor_busqueda.pipeline_rag import buscar_nube
    
    try:
        # Realizamos la búsqueda real en ChromaDB y llamamos a Llama-3 en la nube (Groq)
        resultados = buscar_nube(pregunta=request.pregunta, video_id=request.id_sesion)
        return resultados
    except Exception as e:
        print(f"Error en la búsqueda RAG: {e}")
        raise HTTPException(status_code=500, detail="Error realizando la búsqueda.")


@router.post('/process')
def process_video(request: UrlVideoRequest):
    try:
        urls_to_process = []
        if request.urls:
            urls_to_process.extend(request.urls)
        elif request.url:
            urls_to_process.append(request.url)
            
        if not urls_to_process:
            raise HTTPException(status_code=400, detail="Se requiere al menos una URL.")
            
        print(f"Petición recibida para procesar {len(urls_to_process)} URLs. Delegando a la función de lote...")
        
        sesiones_procesadas = ejecutar_pipeline_lote(urls_to_process)

        return sesiones_procesadas

    except ImportError:
        raise HTTPException(status_code=501, detail="La función de procesamiento en lote aún no está implementada (esperando pull).")
    except Exception as e:
        print(f"Error crítico en el endpoint /api/process: {e}")
        raise HTTPException(status_code=500, detail="Error procesando los vídeos en el backend.")