import json
import chromadb
from chromadb.utils import embedding_functions
from anthropic import Anthropic


# ─────────────────────────────────────────────────────────────
# CHUNK 3 - CONECTAR A CHROMADB REMOTA
# ─────────────────────────────────────────────────────────────
# Cambia estos valores con lo que te diga tu compañero

CHROMA_HOST      = "localhost"   # IP o dominio del servidor de tu compañero
CHROMA_PORT      = 8000          # puerto (8000 es el de ChromaDB por defecto)
NOMBRE_COLECCION = "plenario"    # cambiar cuando lo tengáis acordado

ef = embedding_functions.DefaultEmbeddingFunction()

client = chromadb.HttpClient(
    host=CHROMA_HOST,
    port=CHROMA_PORT
)

collection = client.get_collection(
    name=NOMBRE_COLECCION,
    embedding_function=ef
)

print(f"✅ Conectado a ChromaDB en {CHROMA_HOST}:{CHROMA_PORT}")
print(f"   Colección: '{NOMBRE_COLECCION}' — {collection.count()} fragmentos")


# ─────────────────────────────────────────────────────────────
# CHUNK 4 - FUNCIÓN DE BÚSQUEDA
# ─────────────────────────────────────────────────────────────

def _segundos_a_mmss(segundos: float) -> str:
    """Convierte 125.4 → '02:05'"""
    s = int(segundos)
    return f"{s // 60:02d}:{s % 60:02d}"


def buscar(pregunta: str, top_k: int = 5) -> dict:
    """
    Recibe la pregunta que escribe el usuario en la interfaz y devuelve
    el JSON de salida completo del proyecto:
    {
        "pregunta"      : lo que escribió el usuario
        "prompt"        : el prompt completo que se mandó al LLM
        "respuesta_llm" : la respuesta de Claude
        "fuentes_top_k" : los K fragmentos más similares
    }
    """

    # ── 1. Buscar los top-k fragmentos más similares en ChromaDB ────────
    resultados = collection.query(
        query_texts=[pregunta],
        n_results=top_k,
        include=["documents", "metadatas"]
    )

    documentos = resultados["documents"][0]
    metadatos  = resultados["metadatas"][0]

    if not documentos:
        return {
            "pregunta":      pregunta,
            "prompt":        "",
            "respuesta_llm": "No se encontraron fragmentos relevantes.",
            "fuentes_top_k": []
        }

    # ── 2. Construir el contexto con el formato de la imagen ────────────
    # Formato: "Ponente K: (mm:ss - mm:ss): [Texto]"
    lineas_contexto = []
    for i, (doc, meta) in enumerate(zip(documentos, metadatos), start=1):
        t_inicio = _segundos_a_mmss(meta["inicio"])
        t_fin    = _segundos_a_mmss(meta["fin"])
        lineas_contexto.append(
            f"Ponente {i}: ({t_inicio} - {t_fin}): [{doc}]"
        )

    contexto = "\n".join(lineas_contexto)

    # ── 3. Construir el prompt completo ─────────────────────────────────
    prompt = (
        f"Pregunta del usuario: {pregunta}\n\n"
        f"Contexto:\n{contexto}"
    )

    # ── 4. Llamar a Claude ──────────────────────────────────────────────
    client_llm = Anthropic()

    mensaje = client_llm.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=(
            "Eres un asistente especializado en sesiones parlamentarias. "
            "Responde usando ÚNICAMENTE los fragmentos del contexto que se te dan. "
            "Si la respuesta no está en los fragmentos, dilo claramente. "
            "Sé conciso y cita al ponente cuando sea relevante."
        ),
        messages=[{"role": "user", "content": prompt}]
    )

    respuesta_llm = mensaje.content[0].text

    # ── 5. Construir las fuentes top-k ──────────────────────────────────
    fuentes_top_k = []
    for doc, meta in zip(documentos, metadatos):
        fuentes_top_k.append({
            "ponente":      meta["ponente"],
            "texto":        doc,
            "enlace_video": meta["enlace_video"]
        })

    return {
        "pregunta":      pregunta,
        "prompt":        prompt,
        "respuesta_llm": respuesta_llm,
        "fuentes_top_k": fuentes_top_k
    }


# ESTE BLOQUE ES SOLO PARA PROBAR, CUANDO SE JUNTE HAY QUE ELIMINARLO
# ─────────────────────────────────────────────────────────────
# CHUNK 5 - PRUEBA
# ─────────────────────────────────────────────────────────────
# Cambia la pregunta por lo que quieras buscar

resultado = buscar("¿Qué propone el PSOE sobre los alquileres?", top_k=3)

print("PROMPT ENVIADO AL LLM:")
print(resultado["prompt"])
print("\n" + "=" * 60)
print("RESPUESTA:")
print(resultado["respuesta_llm"])
print("=" * 60)
print(f"\nFUENTES ({len(resultado['fuentes_top_k'])} fragmentos):")
for i, f in enumerate(resultado["fuentes_top_k"], start=1):
    print(f"\n  [{i}] {f['ponente']}")
    print(f"       📺 {f['enlace_video']}")
    print(f"       \"{f['texto'][:80]}...\"")

# Guardar el resultado en JSON
with open("resultado_busqueda.json", "w", encoding="utf-8") as f:
    json.dump(resultado, f, ensure_ascii=False, indent=2)

print("\n💾 Guardado en resultado_busqueda.json")