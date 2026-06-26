'''
Configuración principal de FastAPI y CORS

Aquí configuramos el CORS (Cross-Origin Resource Sharing). 

Como el frontend JS corre en un puerto distinto al de FastAPI, 
si no configuramos esto, el navegador bloqueará las peticiones 
HTTP por seguridad.
'''

# --- PARCHES DE COMPATIBILIDAD DE PYTORCH Y LIBRERÍAS ---
import src.api.compatibilidad
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
