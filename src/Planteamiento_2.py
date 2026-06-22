import json
import os
import chromadb
from chromadb.utils import embedding_functions
import ollama


# ─────────────────────────────────────────────────────────────
# CONECTAR A CHROMADB REMOTA
# ─────────────────────────────────────────────────────────────

CHROMA_HOST      = "chromadb-production-8466.up.railway.app"
CHROMA_PORT      = 443
NOMBRE_COLECCION = "plenario"

ef = embedding_functions.DefaultEmbeddingFunction()

client = chromadb.HttpClient(
    host=CHROMA_HOST,
    port=CHROMA_PORT
)

collection = client.get_collection(
    name=NOMBRE_COLECCION,
    embedding_function=ef
)

print(f"Conectado a ChromaDB en {CHROMA_HOST}:{CHROMA_PORT}")
print(f"Coleccion: '{NOMBRE_COLECCION}' — {collection.count()} fragmentos")


# ─────────────────────────────────────────────────────────────
# FUNCIONES
# ─────────────────────────────────────────────────────────────

def _segundos_a_mmss(segundos: float) -> str:
    """Convierte 125.4 → '02:05'"""
    s = int(segundos)
    return f"{s // 60:02d}:{s % 60:02d}"


def buscar(pregunta: str, video_id: str, top_k: int = 5) -> dict:
    """
    Recibe la pregunta del usuario y el video_id del JSON de entrada.
    Busca los fragmentos más relevantes en ChromaDB y genera una respuesta con Llama-3.
    Devuelve el resultado como diccionario para Streamlit.

    Parámetros:
        pregunta  → pregunta que escribe el usuario en la interfaz
        video_id  → viene de los metadatos del JSON de entrada 
        top_k     → número de fragmentos a recuperar (entre 5 y 10)
    """

    # 1. Buscar los top-k fragmentos filtrando por video_id
    resultados = collection.query(
        query_texts=[pregunta],
        n_results=top_k,
        where={"video_id": {"$eq": video_id}},
        include=["documents", "metadatas"]
    )

    documentos = resultados["documents"][0]
    metadatos  = resultados["metadatas"][0]

    if not documentos:
        return {
            "pregunta":      pregunta,
            "prompt":        "",
            "respuesta_llm": f"No se encontraron fragmentos relevantes en el video '{video_id}'.",
            "fuentes_top_k": []
        }

    # 2. Construir el contexto
    lineas_contexto = []
    for i, (doc, meta) in enumerate(zip(documentos, metadatos), start=1):
        t_inicio = _segundos_a_mmss(meta["inicio"])
        t_fin    = _segundos_a_mmss(meta["fin"])
        lineas_contexto.append(
            f"Ponente {i}: ({t_inicio} - {t_fin}): [{doc}]"
        )

    contexto = "\n".join(lineas_contexto)

    # 3. Construir el prompt
    prompt = (
        f"Pregunta del usuario: {pregunta}\n\n"
        f"Contexto:\n{contexto}"
    )

    # 4. Llamar a Llama-3 con Ollama
    respuesta = ollama.chat(
        model="llama3",
        messages=[
            {
                "role": "system",
                "content": (
                    "Eres un asistente especializado en sesiones parlamentarias. "
                    "Responde usando ÚNICAMENTE los fragmentos del contexto que se te dan. "
                    "Si la respuesta no está en los fragmentos, dilo claramente. "
                    "Sé conciso y cita al ponente cuando sea relevante."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    respuesta_llm = respuesta["message"]["content"]

    # 5. Construir las fuentes top-k
    fuentes_top_k = []
    for doc, meta in zip(documentos, metadatos):
        fuentes_top_k.append({
            "ponente":      meta["ponente"],
            "texto":        doc,
            "enlace_video": meta["enlace_video"],
            "inicio":       _segundos_a_mmss(meta["inicio"]),
            "fin":          _segundos_a_mmss(meta["fin"])
        })

    return {
        "pregunta":      pregunta,
        "prompt":        prompt,
        "respuesta_llm": respuesta_llm,
        "fuentes_top_k": fuentes_top_k
    }



