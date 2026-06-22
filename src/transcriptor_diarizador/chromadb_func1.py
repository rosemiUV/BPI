
# =============================================================
# CONFIGURACIÓN — edita solo esta sección
# =============================================================
RUTA_JSON       = r"c:\Users\HUGO\Desktop\Proyecto IDAL\datos_rag_video_061b2843.json"
MODO_LOCAL   = False
CHROMA_HOST  = "chromadb-production-8466.up.railway.app"
CHROMA_PORT  = 443
NOMBRE_COLECCION = "plenario"
# =============================================================

import json
import chromadb


def cargar_json(ruta: str) -> list:
    print(f"Leyendo JSON desde: {ruta}")
    with open(ruta, "r", encoding="utf-8") as f:
        datos = json.load(f)
    print(f"  {len(datos)} fragmentos cargados.")
    return datos


def conectar_chromadb():
    if MODO_LOCAL:
        print(f"Conectando a ChromaDB local en: {CHROMA_PATH}")
        return chromadb.PersistentClient(path=CHROMA_PATH)
    else:
        print(f"Conectando a ChromaDB servidor: {CHROMA_HOST}:{CHROMA_PORT}")
        return chromadb.HttpClient(
            host=CHROMA_HOST,
            port=CHROMA_PORT,
            ssl=True
        )


def obtener_coleccion(cliente: chromadb.Client):
    coleccion = cliente.get_or_create_collection(name=NOMBRE_COLECCION)
    print(f"Colección '{NOMBRE_COLECCION}' lista. Documentos actuales: {coleccion.count()}")
    return coleccion


def construir_id(fragmento: dict) -> str:
    return f"{fragmento['video_id']}_{fragmento['inicio']}"


def insertar_fragmentos(coleccion, fragmentos: list) -> tuple[int, int]:
    insertados = 0
    saltados = 0

    ids_existentes = set(coleccion.get(include=[])["ids"])

    for fragmento in fragmentos:
        frag_id = construir_id(fragmento)

        if frag_id in ids_existentes:
            print(f"  [SKIP] Ya existe: {frag_id}")
            saltados += 1
            continue

        try:
            coleccion.add(
                ids=[frag_id],
                documents=[fragmento["texto"]],
                metadatas=[{
                    "video_id": fragmento["video_id"],
                    "url_video": fragmento["url_video"],
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


def imprimir_resumen(coleccion, insertados: int, saltados: int):
    print("\n--- RESUMEN ---")
    print(f"  Insertados:  {insertados}")
    print(f"  Saltados:    {saltados}")
    print(f"  Total en BD: {coleccion.count()}")


if __name__ == "__main__":
    fragmentos = cargar_json(RUTA_JSON)
    cliente    = conectar_chromadb()
    coleccion  = obtener_coleccion(cliente)
    insertados, saltados = insertar_fragmentos(coleccion, fragmentos)
    imprimir_resumen(coleccion, insertados, saltados)