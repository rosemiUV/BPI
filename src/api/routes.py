'''
Los endpoints (URLs) de la API
'''

import asyncio
from fastapi import APIRouter, HTTPException
from datetime import datetime
from src.api.schemas import SearchRequest, SearchResponse
from src.api.schemas import UrlVideoRequest, ContextRequest, SummaryRequest, EntitiesRequest
from src.transcriptor_diarizador.V1.pipeline_principal import ejecutar_pipeline_lote

# Instanciamos el enrutador
router = APIRouter()

@router.get('/sessions')
def get_sessions():
    """
    Devuelve la lista de sesiones únicas almacenadas en ChromaDB.
    """
    try:
        from src.transcriptor_diarizador.V1.cargador_chroma import conectar_chromadb, obtener_coleccion
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
    from src.motor_busqueda.pipeline_rag import buscar
    
    try:
        # Realizamos la búsqueda en ChromaDB y llamamos a Llama-3 local con memoria
        resultados = buscar(pregunta=request.pregunta, video_id=request.id_sesion)
        return resultados
    except Exception as e:
        print(f"Error en la búsqueda RAG: {e}")
        raise HTTPException(status_code=500, detail="Error realizando la búsqueda.")


@router.post('/context')
def get_context(request: ContextRequest):
    """
    Recupera el contexto completo (fragmentos adyacentes) de una intervención.
    """
    from src.motor_busqueda.pipeline_rag import obtener_intervencion_completa
    
    try:
        resultado = obtener_intervencion_completa(
            request.video_id, request.ponente, request.inicio, request.fin
        )
        if resultado.get("error"):
            # Devolvemos el error limpiamente sin lanzarlo como excepción para que no lo atrape el except global
            return {"error": resultado["error"]}
            
        return resultado
    except Exception as e:
        print(f"Error al obtener el contexto completo: {e}")
        raise HTTPException(status_code=500, detail="Error obteniendo el contexto.")


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
            
        # Su función debería encargarse de iterar, subir a ChromaDB y devolver 
        # una lista con el formato exacto que necesita el frontend.
        resultados_exitosos, videos_fallidos = ejecutar_pipeline_lote(urls_to_process)

        # Mapeamos los resultados exitosos al formato exacto que espera nuestro frontend React
        sesiones_procesadas = []
        for res in resultados_exitosos:
            sesiones_procesadas.append({
                "id_sesion": res["video_id"],
                "titulo": res["titulo"],
                "fecha": datetime.now().strftime("%d/%m/%Y"),
                "duracion": "Procesada"
            })

        return sesiones_procesadas

    except ImportError:
        raise HTTPException(status_code=501, detail="La función de procesamiento en lote aún no está implementada (esperando pull).")
    except Exception as e:
        print(f"Error crítico en el endpoint /api/process: {e}")
        raise HTTPException(status_code=500, detail="Error procesando los vídeos en el backend.")

@router.post('/summary')
def get_summary(request: SummaryRequest):
    """
    Devuelve un resumen global y el índice de temas para la sesión especificada.
    """
    from src.motor_busqueda.pipeline_rag import generar_resumen
    
    try:
        resultado = generar_resumen(request.video_id)
        if resultado.get("error"):
            # Devolver el error sin fallar con 500
            return {"error": resultado["error"]}
        return resultado
    except Exception as e:
        print(f"Error al generar resumen: {e}")
        raise HTTPException(status_code=500, detail="Error generando el resumen global.")

@router.post('/entities')
def get_entities(request: EntitiesRequest):
    """
    Devuelve las entidades encontradas (Leyes y Personas) junto a un pequeño resumen de Wikipedia.
    """
    from src.motor_busqueda.pipeline_rag import extraer_entidades
    
    try:
        resultado = extraer_entidades(request.video_id, pregunta=request.pregunta)
        if resultado.get("error"):
            return {"error": resultado["error"]}
        return resultado
    except Exception as e:
        print(f"Error extrayendo entidades: {e}")
        raise HTTPException(status_code=500, detail="Error extrayendo las entidades.")