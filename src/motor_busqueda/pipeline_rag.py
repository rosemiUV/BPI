import os
import json
import urllib.request
import urllib.parse
import chromadb
from chromadb.utils import embedding_functions
from mistralai import Mistral
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────
# CONECTAR A CHROMADB REMOTA
# ─────────────────────────────────────────────────────────────

CHROMA_HOST      = "chromadb-production-8466.up.railway.app"
CHROMA_PORT      = 443
NOMBRE_COLECCION = "plenario"

ef = embedding_functions.DefaultEmbeddingFunction()

client = chromadb.HttpClient(
    host=CHROMA_HOST,
    port=CHROMA_PORT,
    ssl=True
)

collection = client.get_collection(
    name=NOMBRE_COLECCION,
    embedding_function=ef
)

print(f"Conectado a ChromaDB en {CHROMA_HOST}:{CHROMA_PORT}")
print(f"Coleccion: '{NOMBRE_COLECCION}' — {collection.count()} fragmentos")


# ─────────────────────────────────────────────────────────────
# MEMORIA DEL CHATBOT
# Se guarda en un diccionario: { video_id: [lista de mensajes] }
# ─────────────────────────────────────────────────────────────

_historial: dict[str, list[dict]] = {}

def obtener_historial(video_id: str) -> list[dict]:
    """Devuelve el historial de conversación de un vídeo. Lista vacía si no hay."""
    return _historial.get(video_id, [])

def limpiar_historial(video_id: str) -> None:
    """Borra el historial de un vídeo (para empezar conversación nueva)."""
    if video_id in _historial:
        del _historial[video_id]


# ─────────────────────────────────────────────────────────────
# FUNCIONES AUXILIARES
# ─────────────────────────────────────────────────────────────

def _segundos_a_mmss(segundos: float) -> str:
    """Convierte 125.4 → '02:05'"""
    s = int(segundos)
    return f"{s // 60:02d}:{s % 60:02d}"


def _construir_contexto(documentos: list, metadatos: list) -> str:
    """
    Construye el bloque de contexto que se mete al LLM.
    Incluye ponente, tiempo y texto de cada fragmento.
    """
    lineas = []
    for i, (doc, meta) in enumerate(zip(documentos, metadatos), start=1):
        t_inicio = _segundos_a_mmss(meta["inicio"])
        t_fin    = _segundos_a_mmss(meta["fin"])
        lineas.append(f"Ponente {i}: ({t_inicio} - {t_fin}): [{doc}]")
    return "\n".join(lineas)


def _muestrear_video_completo(video_id: str, n_fragmentos: int = 40) -> tuple[list, list]:
    """
    Coge fragmentos REPARTIDOS por todo el vídeo (principio, medio y final),
    en vez de solo los primeros n_fragmentos por tiempo.

    Esto es clave para que los "temas" generados reflejen todo el pleno,
    no solo los primeros minutos.

    Devuelve (documentos, metadatos) ya ordenados por tiempo.
    """
    resultados = collection.get(
        where={"video_id": {"$eq": video_id}},
        include=["documents", "metadatas"]
    )

    documentos = resultados.get("documents", [])
    metadatos  = resultados.get("metadatas", [])

    if not documentos:
        return [], []

    # Ordenar todo el vídeo por tiempo de inicio
    pares = sorted(zip(metadatos, documentos), key=lambda x: x[0].get("inicio", 0))

    total = len(pares)

    # Si hay menos fragmentos que los que pedimos, los devolvemos todos
    if total <= n_fragmentos:
        seleccionados = pares
    else:
        # Elegimos índices repartidos uniformemente a lo largo de TODO el vídeo
        # (ej: si hay 400 fragmentos y queremos 40, cogemos 1 de cada 10)
        paso = total / n_fragmentos
        indices = [int(i * paso) for i in range(n_fragmentos)]
        seleccionados = [pares[i] for i in indices]

    metadatos_sel  = [m for m, _ in seleccionados]
    documentos_sel = [d for _, d in seleccionados]
    return documentos_sel, metadatos_sel


def _llamar_mistral(system: str, messages: list[dict]) -> str:
    """
    Llama a Mistral en la nube.
    Se usa en: buscar() y generar_resumen()
    Requiere MISTRAL_API_KEY en el archivo .env
    """
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError(
            "No se encontró MISTRAL_API_KEY. "
            "Asegúrate de tenerla en el archivo .env"
        )
    cliente = Mistral(api_key=api_key)
    respuesta = cliente.chat.complete(
        model="mistral-small-latest",
        messages=[{"role": "system", "content": system}] + messages,
        temperature=0.3
    )
    return respuesta.choices[0].message.content




def _llamar_groq(system: str, messages: list[dict]) -> str:
    """
    Llama a Llama-3 en la nube con Groq.
    Se usa SOLO en extraer_entidades(), porque hace muchas llamadas seguidas
    y Groq tiene un limite gratuito mas generoso que Mistral (30 rpm vs 2 rpm).
    Requiere GROQ_API_KEY en el archivo .env
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "No se encontro GROQ_API_KEY. "
            "Asegurate de tenerla en el archivo .env"
        )
    cliente = Groq(api_key=api_key)
    respuesta = cliente.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "system", "content": system}] + messages,
        temperature=0.3
    )
    return respuesta.choices[0].message.content

# ─────────────────────────────────────────────────────────────
# FUNCIÓN 1: BÚSQUEDA CON MEMORIA
# ─────────────────────────────────────────────────────────────

def buscar(pregunta: str, video_id: str, top_k: int = 5) -> dict:
    """
    Busca fragmentos relevantes y responde usando Mistral en la nube.
    Recuerda las preguntas anteriores del mismo vídeo (memoria de conversación).

    Parámetros:
      - pregunta  → lo que escribe el usuario en Streamlit
      - video_id  → viene de los metadatos del JSON de entrada
      - top_k     → número de fragmentos a recuperar (entre 5 y 10)

    Devuelve un diccionario con:
      - pregunta       → lo que preguntó el usuario
      - prompt         → el contexto que se mandó al LLM
      - respuesta_llm  → la respuesta generada
      - fuentes_top_k  → lista de fragmentos usados (ponente, texto, enlace, tiempos)
    """

    # 1. Buscar fragmentos en ChromaDB
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

    # 2. Construir contexto
    contexto = _construir_contexto(documentos, metadatos)

    # 3. Recuperar historial previo de este vídeo
    historial_previo = obtener_historial(video_id)

    # 4. Construir el mensaje del usuario (pregunta + contexto nuevo)
    mensaje_usuario = (
        f"Pregunta del usuario: {pregunta}\n\n"
        f"Fragmentos relevantes del vídeo:\n{contexto}"
    )

    # 5. Armar la lista de mensajes (historial + pregunta nueva)
    mensajes = historial_previo + [{"role": "user", "content": mensaje_usuario}]

    system = (
        "Eres un asistente especializado en sesiones parlamentarias españolas. "
        "Responde usando ÚNICAMENTE los fragmentos del contexto que se te dan. "
        "Si la respuesta no está en los fragmentos, dilo claramente. "
        "Sé conciso y cita al ponente cuando sea relevante. "
        "Puedes usar el historial de la conversación para dar respuestas de seguimiento."
    )

    # 6. Llamar a Mistral
    respuesta_llm = _llamar_mistral(system, mensajes)

    # 7. Guardar en historial (pregunta + respuesta)
    if video_id not in _historial:
        _historial[video_id] = []
    _historial[video_id].append({"role": "user",      "content": mensaje_usuario})
    _historial[video_id].append({"role": "assistant", "content": respuesta_llm})

    # 8. Construir fuentes
    fuentes_top_k = []
    for doc, meta in zip(documentos, metadatos):
        fuentes_top_k.append({
            "ponente":      meta.get("ponente", "Desconocido"),
            "texto":        doc,
            "enlace_video": meta.get("url_exacta_tiempo", ""),
            "inicio":       _segundos_a_mmss(meta["inicio"]),
            "fin":          _segundos_a_mmss(meta["fin"])
        })

    return {
        "pregunta":      pregunta,
        "prompt":        mensaje_usuario,
        "respuesta_llm": respuesta_llm,
        "fuentes_top_k": fuentes_top_k
    }


# ─────────────────────────────────────────────────────────────
# FUNCIÓN 2: RESUMEN GLOBAL DEL VÍDEO
# ─────────────────────────────────────────────────────────────

def generar_resumen(video_id: str, n_fragmentos: int = 40) -> dict:
    """
    Genera un resumen de los temas principales debatidos en el vídeo.
    Se recomienda llamar esta función al cargar el vídeo en el frontend.

    IMPORTANTE: usa _muestrear_video_completo() para coger fragmentos
    repartidos por TODO el vídeo (no solo el principio), y le pide al LLM
    que use las palabras literales del texto al nombrar los temas, para que
    luego la búsqueda semántica (buscar()) encuentre fragmentos reales
    cuando el usuario pregunte sobre esos temas.

    Devuelve un diccionario con:
      - video_id  → id del vídeo
      - resumen   → texto del resumen generado por el LLM
      - error     → mensaje de error si algo falló (None si todo fue bien)
    """

    documentos, metadatos = _muestrear_video_completo(video_id, n_fragmentos)

    if not documentos:
        return {
            "video_id": video_id,
            "resumen":  "",
            "error":    f"No se encontraron fragmentos para el video '{video_id}'."
        }

    contexto = _construir_contexto(documentos, metadatos)

    system = (
        "Eres un asistente especializado en sesiones parlamentarias españolas. "
        "Tu tarea es hacer un resumen claro, organizado y FIEL AL TEXTO ORIGINAL. "
        "DEBES estructurar tu respuesta EXACTAMENTE con los siguientes dos encabezados:\n"
        "### 1. Índice de Temas\n"
        "### 2. Resumen Global"
    )

    mensaje = (
        f"A continuación tienes fragmentos de una sesión parlamentaria, "
        f"repartidos a lo largo de TODO el vídeo (no solo el principio).\n\n"
        f"{contexto}\n\n"
        "Por favor, genera tu respuesta siguiendo esta estructura estricta:\n\n"
        "### 1. Índice de Temas\n"
        "- Escribe una lista de viñetas con los temas principales que se debatieron.\n"
        "- Usa el formato: '**Tema**: Breve descripción'.\n"
        "- MUY IMPORTANTE: nombra cada tema usando las MISMAS PALABRAS o expresiones "
        "que aparecen literalmente en los fragmentos de arriba (por ejemplo, si en el "
        "texto se habla de 'la subida del salario mínimo', el tema debe llamarse "
        "'Subida del salario mínimo', NO uses sinónimos rebuscados ni lo generalices "
        "como 'Política económica'). Esto es porque luego un usuario va a preguntar "
        "usando ese mismo nombre de tema y necesitamos que las palabras coincidan "
        "con lo que realmente se dijo.\n"
        "- No inventes ni incluyas temas que no aparezcan en los fragmentos.\n\n"
        "### 2. Resumen Global\n"
        "Escribe un resumen en párrafos continuos que explique:\n"
        "- Las posturas más destacadas de los ponentes.\n"
        "- Cualquier acuerdo o desacuerdo relevante.\n"
        "Sé claro y directo. Máximo 300 palabras en el resumen global."
    )

    try:
        resumen = _llamar_mistral(system, [{"role": "user", "content": mensaje}])
        return {"video_id": video_id, "resumen": resumen, "error": None}
    except Exception as e:
        return {"video_id": video_id, "resumen": "", "error": str(e)}


# ─────────────────────────────────────────────────────────────
# FUNCIÓN 3: EXTRACCIÓN DE ENTIDADES CON BÚSQUEDA WEB
# ─────────────────────────────────────────────────────────────

def _buscar_wikipedia(termino: str) -> str:
    """
    Busca un término en Wikipedia en español y devuelve el primer párrafo.
    No necesita API key, usa la API pública gratuita de Wikipedia.
    Devuelve cadena vacía si no encuentra nada.
    """
    try:
        termino_codificado = urllib.parse.quote(termino)
        url = f"https://es.wikipedia.org/api/rest_v1/page/summary/{termino_codificado}"
        req = urllib.request.Request(url, headers={"User-Agent": "ParlamentoChatbot/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            datos = json.loads(resp.read().decode("utf-8"))
            return datos.get("extract", "")
    except Exception:
        return ""


def _detectar_entidades_con_llm(texto: str) -> dict:
    """
    Usa Groq para detectar leyes, personas, lugares e instituciones en el texto parlamentario,
    ya que es más rápido y tiene un límite de llamadas más alto que Mistral.
    Devuelve {"leyes": [...], "personas": [...], "lugares": [...], "instituciones": [...]}
    """
    system = (
        "Eres un extractor de entidades de textos parlamentarios españoles. "
        "Responde ÚNICAMENTE con un JSON válido, sin texto adicional ni backticks."
    )
    mensaje = (
        "El siguiente texto proviene de una sesión plenaria del Congreso de los Diputados de España.\n\n"
        f"Texto:\n{texto}\n\n"
        "Extrae todas las entidades relevantes que aparezcan:\n"
        "1. LEYES: leyes, decretos, normativas o reglamentos mencionados. "
        "Incluye el nombre completo si aparece (ej: 'Ley Orgánica 3/2007').\n"
        "2. PERSONAS: políticos, ministros, presidentes u otras figuras públicas mencionadas. "
        "MUY IMPORTANTE: si solo aparece el apellido (ej: 'Sánchez', 'Feijóo'), "
        "deduce el nombre completo usando tu conocimiento de la política española actual "
        "(ej: 'Pedro Sánchez', 'Alberto Núñez Feijóo'). "
        "Si hay ambigüedad, usa el cargo mencionado en el texto para decidir.\n"
        "3. LUGARES: países, comunidades autónomas, ciudades o pueblos mencionados "
        "(ej: 'Cataluña', 'Francia', 'Sevilla', 'Vitoria-Gasteiz').\n"
        "4. INSTITUCIONES: organismos, ministerios, partidos políticos, tribunales u "
        "otras instituciones mencionadas "
        "(ej: 'Tribunal Constitucional', 'Ministerio de Hacienda', 'Partido Popular').\n\n"
        "Devuelve SOLO este JSON (sin nada más):\n"
        '{"leyes": ["nombre completo ley 1", "..."], '
        '"personas": ["Nombre Completo Persona 1", "..."], '
        '"lugares": ["Lugar 1", "..."], '
        '"instituciones": ["Institución 1", "..."]}'
    )
    try:
        respuesta = _llamar_groq(system, [{"role": "user", "content": mensaje}])
        respuesta_limpia = respuesta.strip().strip("```json").strip("```").strip()
        return json.loads(respuesta_limpia)
    except Exception:
        return {"leyes": [], "personas": [], "lugares": [], "instituciones": []}


def _resolver_nombre_wikipedia(nombre: str, tipo: str) -> str:
    """
    Intenta encontrar el término exacto que Wikipedia reconoce.
    Primero prueba el nombre tal cual. Si no funciona, prueba variantes.
    Devuelve el texto de Wikipedia o cadena vacía.
    """
    # Intento 1: nombre tal cual
    resultado = _buscar_wikipedia(nombre)
    if resultado and len(resultado) > 50:
        return resultado

    # Intento 2: si es persona, probar "Nombre Apellido (político)"
    if tipo == "persona":
        resultado = _buscar_wikipedia(f"{nombre} (político)")
        if resultado and len(resultado) > 50:
            return resultado

    # Intento 3: preguntar a Mistral cuál es el título exacto del artículo de Wikipedia
    system = (
        "Eres un asistente que conoce la Wikipedia en español. "
        "Responde ÚNICAMENTE con el título exacto del artículo, sin explicaciones."
    )
    if tipo == "persona":
        mensaje = (
            f"¿Cuál es el título exacto del artículo de Wikipedia en español "
            f"sobre '{nombre}', político español? "
            "Responde solo con el título, nada más."
        )
    else:
        mensaje = (
            f"¿Cuál es el título exacto del artículo de Wikipedia en español "
            f"sobre la ley o normativa '{nombre}'? "
            "Responde solo con el título, nada más."
        )
    try:
        titulo_wikipedia = _llamar_groq(system, [{"role": "user", "content": mensaje}])
        titulo_limpio = titulo_wikipedia.strip().strip('"').strip("'")
        resultado = _buscar_wikipedia(titulo_limpio)
        if resultado and len(resultado) > 50:
            return resultado
    except Exception:
        pass

    return ""


def _explicar_entidad(nombre: str, tipo: str) -> str:
    """
    Busca información en Wikipedia y usa Mistral para generar una explicación breve.
    tipo puede ser "ley" o "persona".
    """
    info_wikipedia = _resolver_nombre_wikipedia(nombre, tipo)

    if info_wikipedia:
        fuente = f"Información de Wikipedia:\n{info_wikipedia[:1500]}"
    else:
        fuente = "No se encontró información en Wikipedia."

    if tipo == "ley":
        instruccion = (
            f"Explica en 2-3 frases qué es '{nombre}', "
            "para qué sirve y cuándo entró en vigor. "
            "Sé directo y claro, como si se lo explicaras a alguien sin conocimientos jurídicos."
        )
    elif tipo == "lugar":
        instruccion = (
            f"Explica en 2-3 frases qué es o dónde está '{nombre}' "
            "y por qué es relevante en el contexto de la política española. "
            "Sé directo y claro."
        )
    elif tipo == "institucion":
        instruccion = (
            f"Explica en 2-3 frases qué es '{nombre}': "
            "qué función tiene y por qué aparece en debates parlamentarios. "
            "Sé directo y claro."
        )
    else:
        instruccion = (
            f"Explica en 2-3 frases quién es '{nombre}' en el contexto "
            "de la política española actual: qué cargo ocupa o ha ocupado "
            "y por qué aparece en debates parlamentarios. "
            "Sé directo y objetivo."
        )

    system = "Eres un asistente que explica términos políticos y jurídicos de forma sencilla."
    mensaje = f"{instruccion}\n\n{fuente}"

    try:
        return _llamar_groq(system, [{"role": "user", "content": mensaje}])
    except Exception:
        return info_wikipedia[:300] if info_wikipedia else "No se pudo obtener información."


def extraer_entidades(video_id: str, pregunta: str = "", top_k: int = 10) -> dict:
    """
    Detecta leyes y personas relevantes en los fragmentos del vídeo,
    busca información sobre cada una en Wikipedia y genera una explicación breve.

    Devuelve un diccionario con:
      - video_id   → id del vídeo
      - entidades  → lista de entidades, cada una con:
                       · nombre      → nombre de la entidad
                       · tipo        → "ley" o "persona"
                       · explicacion → 2-3 frases explicando qué es / quién es
      - error      → mensaje de error si algo falló (None si todo fue bien)
    """
    try:
        if pregunta:
            resultados = collection.query(
                query_texts=[pregunta],
                n_results=top_k,
                where={"video_id": {"$eq": video_id}},
                include=["documents"]
            )
            documentos = resultados["documents"][0]
        else:
            documentos, _ = _muestrear_video_completo(video_id, top_k)

        if not documentos:
            return {
                "video_id":  video_id,
                "entidades": [],
                "error":     f"No se encontraron fragmentos para el video '{video_id}'."
            }

        texto_completo = " ".join(documentos)
        detectadas = _detectar_entidades_con_llm(texto_completo)

        leyes         = detectadas.get("leyes", [])
        personas      = detectadas.get("personas", [])
        lugares       = detectadas.get("lugares", [])
        instituciones = detectadas.get("instituciones", [])

        entidades = []

        for ley in leyes:
            if not ley or len(ley) < 3:
                continue
            entidades.append({
                "nombre":      ley,
                "tipo":        "ley",
                "explicacion": _explicar_entidad(ley, "ley")
            })

        for persona in personas:
            if not persona or len(persona) < 3:
                continue
            entidades.append({
                "nombre":      persona,
                "tipo":        "persona",
                "explicacion": _explicar_entidad(persona, "persona")
            })

        for lugar in lugares:
            if not lugar or len(lugar) < 3:
                continue
            entidades.append({
                "nombre":      lugar,
                "tipo":        "lugar",
                "explicacion": _explicar_entidad(lugar, "lugar")
            })

        for institucion in instituciones:
            if not institucion or len(institucion) < 3:
                continue
            entidades.append({
                "nombre":      institucion,
                "tipo":        "institucion",
                "explicacion": _explicar_entidad(institucion, "institucion")
            })

        return {"video_id": video_id, "entidades": entidades, "error": None}

    except Exception as e:
        return {"video_id": video_id, "entidades": [], "error": str(e)}


# ─────────────────────────────────────────────────────────────
# FUNCIÓN 4: CHUNKING AMPLIADO
# ─────────────────────────────────────────────────────────────

def obtener_intervencion_completa(video_id: str, ponente: str, inicio: float, fin: float) -> dict:
    """
    Dado un ponente y un intervalo de tiempo, recupera todos los fragmentos
    de ese ponente que estén cerca en el tiempo (±60 segundos de margen).

    Devuelve un diccionario con:
      - ponente           → nombre del ponente
      - inicio_mmss       → tiempo de inicio formateado
      - fin_mmss          → tiempo de fin formateado
      - texto_fragmento   → el fragmento exacto solicitado
      - contexto_completo → todos los fragmentos del ponente en ese bloque de tiempo
      - error             → mensaje de error si algo falló (None si todo fue bien)
    """

    MARGEN_SEGUNDOS = 60

    try:
        resultados = collection.get(
            where={
                "$and": [
                    {"video_id": {"$eq": video_id}},
                    {"ponente":  {"$eq": ponente}},
                    {"inicio":   {"$gte": max(0.0, inicio - MARGEN_SEGUNDOS)}},
                    {"fin":      {"$lte": fin + MARGEN_SEGUNDOS}}
                ]
            },
            include=["documents", "metadatas"]
        )

        documentos = resultados.get("documents", [])
        metadatos  = resultados.get("metadatas", [])

        if not documentos:
            return {
                "ponente":           ponente,
                "inicio_mmss":       _segundos_a_mmss(inicio),
                "fin_mmss":          _segundos_a_mmss(fin),
                "texto_fragmento":   "",
                "contexto_completo": [],
                "error":             "No se encontraron fragmentos para esa intervención."
            }

        pares = sorted(zip(metadatos, documentos), key=lambda x: x[0].get("inicio", 0))

        texto_exacto = ""
        for meta, doc in pares:
            if meta["inicio"] <= fin and meta["fin"] >= inicio:
                texto_exacto = doc
                break

        contexto_completo = [
            {
                "inicio": _segundos_a_mmss(meta["inicio"]),
                "fin":    _segundos_a_mmss(meta["fin"]),
                "texto":  doc
            }
            for meta, doc in pares
        ]

        return {
            "ponente":           ponente,
            "inicio_mmss":       _segundos_a_mmss(inicio),
            "fin_mmss":          _segundos_a_mmss(fin),
            "texto_fragmento":   texto_exacto,
            "contexto_completo": contexto_completo,
            "error":             None
        }

    except Exception as e:
        return {
            "ponente":           ponente,
            "inicio_mmss":       _segundos_a_mmss(inicio),
            "fin_mmss":          _segundos_a_mmss(fin),
            "texto_fragmento":   "",
            "contexto_completo": [],
            "error":             str(e)
        }