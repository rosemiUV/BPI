'''
Configuración principal de FastAPI y CORS

Aquí configuramos el CORS (Cross-Origin Resource Sharing). 

Como el frontend JS corre en un puerto distinto al de FastAPI, 
si no configuramos esto, el navegador bloqueará las peticiones 
HTTP por seguridad.
'''

# --- PARCHES DE COMPATIBILIDAD DE PYTORCH Y LIBRERÍAS ---
import torch
import torchaudio
import omegaconf

# 1. Parche para torchaudio >= 2.1 con pyannote
if not hasattr(torchaudio, "AudioMetaData"):
    torchaudio.AudioMetaData = type('AudioMetaData', (object,), {})
if not hasattr(torchaudio, "list_audio_backends"):
    torchaudio.list_audio_backends = lambda: ["soundfile"]

# 2. Parche definitivo para PyTorch >= 2.6 (Weights only load failed)
_original_load = torch.load
def safe_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_load(*args, **kwargs)
torch.load = safe_load

# --------------------------------------------------------
# 3. Parche para huggingface_hub (Pyannote usa use_auth_token pero hf pide token)
import huggingface_hub
_old_hf_hub_download = huggingface_hub.hf_hub_download
def _safe_hf_hub_download(*args, **kwargs):
    if "use_auth_token" in kwargs:
        kwargs["token"] = kwargs.pop("use_auth_token")
    return _old_hf_hub_download(*args, **kwargs)
huggingface_hub.hf_hub_download = _safe_hf_hub_download
# --------------------------------------------------------

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router as search_router

# Inicialización de la App con metadatos para la documentación automática
app = FastAPI(
    title = 'API - BPI: Buscador Plenario Inteligente',
    description = 'Motor RAG para la búsqueda semántica en sesiones plenarias',
    version = '1.0.0'
)

# Configuración de CORS para permitir peticiones desde tu Frontend JS
app.add_middleware(
    CORSMiddleware,
    allow_origins = ['*'], # En producción cambiaremos "*" por "http://localhost:5173" (ej. Vite/React)
    allow_credentials = True,
    allow_methods = ['*'],
    allow_headers = ['*']
)

# Acoplamos nuestras rutas bajo el prefijo "/api"
app.include_router(search_router, prefix = '/api')

# Ruta raíz para verificar que la API está funcionando
@app.get('/')
async def root():
    return {
        'mensaje': 'Bienvenido a la API del Buscador Plenario Inteligente (BPI)',
        'documentacion': 'Visita /docs para probar la API'
    }
