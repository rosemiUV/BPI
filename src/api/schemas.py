'''
Modelos de datos (Pydantic) para validación estricta
'''

from pydantic import BaseModel
from typing import List, Optional

#1. Lo que recibimos del Frontend (Input)
class SearchRequest(BaseModel):
    pregunta: str
    id_sesion: str

class Fuente(BaseModel):
    ponente: str
    texto: str
    enlace_video: str

class SearchResponse(BaseModel):
    pregunta: str
    respuesta_llm: str
    fuentes_top_k: List[Fuente]

class UrlVideoRequest(BaseModel):
    url: Optional[str] = None
    urls: Optional[List[str]] = None

class ContextRequest(BaseModel):
    video_id: str
    ponente: str
    inicio: float
    fin: float

class SummaryRequest(BaseModel):
    video_id: str

class EntitiesRequest(BaseModel):
    video_id: str
    pregunta: Optional[str] = None
