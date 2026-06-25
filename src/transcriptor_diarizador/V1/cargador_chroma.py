import json
import chromadb
from pathlib import Path

# =============================================================
# CONFIGURACIÓN DE LA BASE DE DATOS
# =============================================================
MODO_LOCAL   = False
CHROMA_HOST  = "chromadb-production-8466.up.railway.app"
CHROMA_PORT  = 443
NOMBRE_COLECCION = "plenario"
# =============================================================

def cargar_json(ruta: Path) -> list:
    print(f"Leyendo JSON desde: {ruta}")
    with open(ruta, "r", encoding="utf-8") as f:
        datos = json.load(f)
    print(f"  {len(datos)} fragmentos cargados.")
    return datos

def conectar_chromadb():
    if MODO_LOCAL:
        print("Conectando a ChromaDB local...")
        return chromadb.PersistentClient(path="./chroma_db_local")
    else:
        print(f"Conectando a ChromaDB servidor: {CHROMA_HOST}:{CHROMA_PORT}")
        return chromadb.HttpClient(
            host=CHROMA_HOST,
            port=CHROMA_PORT,
            ssl=True
        )

def obtener_coleccion(cliente: chromadb.Client):
    coleccion = cliente.get_or_create_collection(name=NOMBRE_COLECCION)
    print(f"Colección '{NOMBRE_COLECCION}' lista. Documentos actuales en total: {coleccion.count()}")
    return coleccion

# --- NUEVA FUNCIÓN DE FILTRADO ---
def video_ya_procesado(coleccion: chromadb.Collection, video_id: str) -> bool:
    """Consulta a ChromaDB si existe al menos un chunk con este video_id"""
    try:
        resultado = coleccion.get(
            where={"video_id": video_id},
            limit=1, # Solo necesitamos encontrar uno para saber que existe
            include=["metadatas"]
        )
        return len(resultado["ids"]) > 0
    except Exception as e:
        print(f"Error al comprobar la existencia del vídeo: {e}")
        return False

def insertar_fragmentos(coleccion, fragmentos: list) -> tuple[int, int]:
    insertados = 0
    saltados = 0

    ids_existentes = set(coleccion.get(include=[])["ids"])

    for fragmento in fragmentos:
        frag_id = fragmento.get("chunk_id", f"{fragmento['video_id']}_{fragmento['inicio']}")

        if frag_id in ids_existentes:
            saltados += 1
            continue

        try:
            coleccion.add(
                ids=[frag_id],
                documents=[fragmento["texto"]],
                metadatas=[{
                    "video_id": fragmento["video_id"],
                    "titulo_video": fragmento.get("titulo_video", "Desconocido"),
                    "fecha_publicacion": fragmento.get("fecha_publicacion", "Desconocida"),
                    "url_video": fragmento["url_video"],
                    "url_exacta_tiempo": fragmento.get("url_exacta_tiempo", ""),
                    "ponente":   fragmento["ponente"],
                    "inicio":    fragmento["inicio"],
                    "fin":       fragmento["fin"],
                    "duracion":  fragmento["duracion"],
                }]
            )
            insertados += 1
        except Exception as e:
            print(f"  [ERROR] Fallo al insertar {frag_id}: {e}")

    return insertados, saltados

def subir_datos_a_chroma(ruta_json: Path):
    """Función principal para ser llamada desde el pipeline"""
    fragmentos = cargar_json(ruta_json)
    
    if not fragmentos:
        print("Error: El JSON está vacío.")
        return

    # Extraemos el ID del vídeo del primer fragmento
    video_id = fragmentos[0].get("video_id")
    
    cliente    = conectar_chromadb()
    coleccion  = obtener_coleccion(cliente)

    # --- NUEVO CORTAFUEGOS ---
    if video_id and video_ya_procesado(coleccion, video_id):
        print(f"\nEl vídeo '{video_id}' ya se encuentra en la Base de Datos.")
        print("Abortando subida para evitar duplicados y ahorrar tiempo.")
        return
    
    print(f"\nSubiendo nuevos fragmentos del vídeo '{video_id}'...")
    insertados, saltados = insertar_fragmentos(coleccion, fragmentos)
    
    print("\n--- RESUMEN CHROMA DB ---")
    print(f"  Nuevos insertados:  {insertados}")
    print(f"  Saltados (ya existían): {saltados}")
    print(f"  Total en BD global: {coleccion.count()}")