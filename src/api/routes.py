'''
Los endpoints (URLs) de la API
'''

import asyncio
from fastapi import APIRouter
from src.api.schemas import SearchRequest, SearchResponse

# Instanciamos el enrutador
router = APIRouter()

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
                'enlace_video': 'https://www.youtube.com/watch?v=fwgOUDzn4M8&t=10'
            },

            {
                'ponente': 'SPEAKER_00',
                'texto': 'Señorías, pasamos a debatir la nueva ley 2...',
                'enlace_video': 'https://www.youtube.com/watch?v=oiv_iJZGVv4&t=10'
            },

            {
                'ponente': 'SPEAKER_00',
                'texto': 'Señorías, pasamos a debatir la nueva ley 3...',
                'enlace_video': 'https://www.youtube.com/watch?v=LZPLBSRnxSY&t=10'
            }
        ]
    }

    return mock_data