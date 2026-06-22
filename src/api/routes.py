'''
Los endpoints (URLs) de la API
'''

import asyncio
from fastapi import APIRouter, HTTPException
from datetime import datetime
from src.api.schemas import SearchRequest, SearchResponse
from src.api.schemas import UrlVideoRequest
from src.transcriptor_diarizador.pipeline_principal import ejecutar_pipeline_completo

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
async def perform_search(request: SearchRequest):
    """
    Recibe la pregunta del usuario y devuelve el JSON simulado.
    En la Fase 2, aquí importaremos las funciones de tus compañeros (ChromaDB + LLM).
    """

    # Simulamos el teimpo que tardaría el LLM y ChromaDB en pensar
    await asyncio.sleep(1.5)

    # Construimos el Contrato de Datos (Mock)
    mock_data = {
        'pregunta': request.pregunta,
        'respuesta_llm': 'El PSOE propone debatir una nueva ley de vivienda que incluye poner un tope a los alquileres...',
        'fuentes_top_k': [
            {
                'ponente': 'SPEAKER_00',
                'texto': 'Señorías, pasamos a debatir la nueva ley...',
                'enlace_video': 'https://www.youtube.com/watch?v=kBezQQVs8Ug&t=10'
            },

            {
                'ponente': 'SPEAKER_00',
                'texto': 'Señorías, pasamos a debatir la nueva ley 2...',
                'enlace_video': 'https://www.youtube.com/watch?v=Pihy5At3Q60&t=10'
            },

            {
                'ponente': 'SPEAKER_00',
                'texto': 'Señorías, pasamos a debatir la nueva ley 3...',
                'enlace_video': 'https://www.youtube.com/watch?v=LZPLBSRnxSY&t=10'
            }
        ]
    }

    return mock_data


@router.post('/process')
def process_video(request: UrlVideoRequest):
    try:
        print(f"Recibida petición para procesar URL: {request.url}")

        # 1. FASE DE PROCESAMIENTO (Whisper + PyAnnote + Fusión)
        video_id, ruta_json_final, titulo_real = ejecutar_pipeline_completo(request.url)

        # 2. FASE DE INGESTA VECTORIAL (ChromaDB)
        print(f"Iniciando ingesta en base de datos vectorial del archivo: {ruta_json_final}")
        try:
            from src.transcriptor_diarizador.cargador_chroma import subir_datos_a_chroma
            subir_datos_a_chroma(ruta_json_final)
        except Exception as e:
            print(f"Error al subir a ChromaDB: {e}")

        # 3. RESPUESTA AL FRONTEND
        # Devolvemos exactamente lo que tu React está esperando para pintar la interfaz
        return {
            "id_sesion": video_id,
            "titulo": titulo_real,
            "fecha": datetime.now().strftime("%d/%m/%Y"),
            "duracion": "Procesada" 
        }

    except Exception as e:
        print(f"Error crítico en el endpoint /api/process: {e}")
        raise HTTPException(status_code=500, detail="Error procesando el vídeo en el backend.")