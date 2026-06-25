import os
import json
import urllib.request
import urllib.parse
import spacy
import chromadb
from chromadb.utils import embedding_functions
import ollama
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Inicializar modelo de spaCy una sola vez en el arranque
try:
    nlp = spacy.load("es_core_news_sm")
except Exception as e:
    print(f"Advertencia: No se pudo cargar el modelo spaCy 'es_core_news_sm'. Asegúrate de haber ejecutado 'python -m spacy download es_core_news_sm'. Error: {e}")
    nlp = None

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

collection = client.get_or_create_collection(
    name=NOMBRE_COLECCION,
    embedding_function=ef
)

print(f"Conectado a ChromaDB en {CHROMA_HOST}:{CHROMA_PORT}")
print(f"Coleccion: '{NOMBRE_COLECCION}' — {collection.count()} fragmentos")


# ─────────────────────────────────────────────────────────────
# MEMORIA DEL CHATBOT
# Se guarda en un diccionario: { video_id: [lista de mensajes] }
# Cada mensaje es {"role": "user"/"assistant", "content": "..."}
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


def _llamar_ollama(system: str, messages: list[dict]) -> str:
    """Llama a Llama-3 local con Ollama. Igual que en el código original."""
    respuesta = ollama.chat(
        model="llama3",
        messages=[{"role": "system", "content": system}] + messages
    )
    return respuesta["message"]["content"]


def _llamar_groq(system: str, messages: list[dict]) -> str:
    """
    Llama a Llama-3 en la nube con Groq.
    Solo se usa en extraer_entidades(), para las búsquedas de Wikipedia.
    Requiere GROQ_API_KEY en el archivo .env
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "No se encontró GROQ_API_KEY. "
            "Asegúrate de tenerla en el archivo .env"
        )
    cliente = Groq(api_key=api_key)
    respuesta = cliente.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "system", "content": system}] + messages,
        temperature=0.3
    )
    return respuesta.choices[0].message.content

def _llamar_groq_json(system: str, messages: list[dict]) -> str:
    """Llama a Llama-3 forzando respuesta en JSON"""
    api_key = os.environ.get("GROQ_API_KEY")
    cliente = Groq(api_key=api_key)
    respuesta = cliente.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "system", "content": system}] + messages,
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    return respuesta.choices[0].message.content


# ─────────────────────────────────────────────────────────────
# FUNCIÓN 1: BÚSQUEDA CON MEMORIA
# Añade memoria de conversación por vídeo.
# ─────────────────────────────────────────────────────────────

def buscar(pregunta: str, video_id: str, top_k: int = 5) -> dict:
    """
    Busca fragmentos relevantes y responde usando Llama-3 local (Ollama).
    Recuerda las preguntas anteriores del mismo vídeo (memoria de conversación).

    Parámetros:
      - pregunta  → lo que escribe el usuario
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

    # 6. Llamar a Groq (en la nube) en lugar de Ollama local
    respuesta_llm = _llamar_groq(system, mensajes)

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
            "fin":          _segundos_a_mmss(meta["fin"]),
            "inicio_segundos": meta["inicio"],
            "fin_segundos":    meta["fin"]
        })

    return {
        "pregunta":      pregunta,
        "prompt":        mensaje_usuario,
        "respuesta_llm": respuesta_llm,
        "fuentes_top_k": fuentes_top_k
    }


# ─────────────────────────────────────────────────────────────
# FUNCIÓN 2: RESUMEN GLOBAL DEL VÍDEO
# Se llama una sola vez al cargar el vídeo.
# ─────────────────────────────────────────────────────────────

def generar_resumen(video_id: str, n_fragmentos: int = 40) -> dict:
    """
    Genera un resumen global y un índice de temas de la sesión.
    Aplica 'Muestreo Estratégico Extendido': extrae fragmentos uniformemente a lo largo de todo el vídeo.
    
    Devuelve un diccionario con:
      - video_id  → id del vídeo
      - resumen   → texto del resumen generado por el LLM (incluye Índice y Resumen)
      - error     → mensaje de error si algo falló (None si todo fue bien)
    """

    resultados = collection.get(
        where={"video_id": {"$eq": video_id}},
        include=["documents", "metadatas"]
    )

    documentos = resultados.get("documents", [])
    metadatos  = resultados.get("metadatas", [])

    if not documentos:
        return {
            "video_id": video_id,
            "resumen":  "",
            "error":    f"No se encontraron fragmentos para el video '{video_id}'."
        }

    # Ordenar cronológicamente
    pares = sorted(zip(metadatos, documentos), key=lambda x: x[0].get("inicio", 0))
    total_frag = len(pares)
    
    # Muestreo estratégico distribuido (por defecto 100 fragmentos en toda la sesión)
    if total_frag <= n_fragmentos:
        pares_muestra = pares
    else:
        step = total_frag / n_fragmentos
        pares_muestra = [pares[int(i * step)] for i in range(n_fragmentos)]

    contexto = _construir_contexto(
        [doc for _, doc in pares_muestra],
        [meta for meta, _ in pares_muestra]
    )

    # Límite estricto de seguridad para no superar el límite de contexto (8192 tokens en Llama 3)
    if len(contexto) > 20000:
        contexto = contexto[:20000] + "\n...[texto truncado por longitud]..."

    system = (
        "Eres un analista parlamentario experto. "
        "Tu tarea es analizar una muestra representativa de toda la sesión y generar un reporte global."
    )

    mensaje = (
        f"Aquí tienes {len(pares_muestra)} fragmentos extraídos de manera uniforme a lo largo de toda una sesión parlamentaria.\n\n"
        f"FRAGMENTOS:\n{contexto}\n\n"
        "Basándote exclusivamente en esta muestra global, genera un reporte en español estructurado exactamente en dos partes:\n\n"
        "### 1. Índice de Temas\n"
        "- Lista con viñetas de los 3-5 temas principales o bloques que se debatieron.\n\n"
        "### 2. Resumen Global\n"
        "Un resumen de 2 o 3 párrafos explicando el desarrollo general de la sesión, las posturas de los ponentes principales y si hubo acuerdos o tensiones clave.\n\n"
        "No añadas textos introductorios ni despedidas, ve directo al contenido."
    )

    try:
        resumen = _llamar_groq(system, [{"role": "user", "content": mensaje}])
        return {"video_id": video_id, "resumen": resumen, "error": None}
    except Exception as e:
        return {"video_id": video_id, "resumen": "", "error": str(e)}


# ─────────────────────────────────────────────────────────────
# FUNCIÓN 3: EXTRACCIÓN DE ENTIDADES CON BÚSQUEDA WEB
# Usa Groq para más velocidad porque hace varias llamadas al LLM seguidas
#
# Flujo:
#   1. Groq detecta leyes y personas en los fragmentos
#   2. Por cada entidad, busca información en Wikipedia (gratis, sin API key)
#   3. Groq genera una explicación breve con lo que encontró
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
    Usa Groq para detectar leyes, personas, lugares e instituciones importantes en el texto.
    Devuelve {"leyes": [...], "personas": [...], "lugares": [...], "instituciones": [...]}
    """
    system = (
        "Eres un extractor de entidades de textos parlamentarios españoles. "
        "Responde ÚNICAMENTE con un objeto JSON válido, con las claves 'leyes', 'personas', 'lugares' e 'instituciones', "
        "y que sus valores sean listas de strings. No incluyas nada más. Extrae la máxima cantidad de entidades relevantes posibles."
    )
    mensaje = (
        "Del siguiente texto parlamentario, extrae exhaustivamente:\n"
        "1. Leyes, decretos, artículos o normativas mencionadas (nombre completo si aparece).\n"
        "2. Nombres de personas relevantes mencionadas (políticos, ministros, etc.).\n"
        "3. Lugares o zonas geográficas clave (ciudades, países, comunidades autónomas, barrios).\n"
        "4. Instituciones, organismos, partidos políticos o ministerios mencionados.\n\n"
        f"Texto:\n{texto}\n"
    )
    try:
        respuesta = _llamar_groq_json(system, [{"role": "user", "content": mensaje}])
        return json.loads(respuesta)
    except Exception as e:
        print(f"Error parseando JSON de Groq: {e}")
        return {"leyes": [], "personas": [], "lugares": [], "instituciones": []}


import concurrent.futures

def _detectar_entidades_con_ner(texto: str) -> dict:
    """
    Usa el modelo clásico NER de SpaCy para detectar entidades.
    No requiere API externa ni tiene límite estricto de contexto.
    """
    if not nlp:
        return {"leyes": [], "personas": [], "lugares": [], "instituciones": []}
        
    # El límite de longitud por defecto en spacy es 1000000 caracteres
    if len(texto) > 999999:
        texto = texto[:999999]

    doc = nlp(texto)
    leyes = set()
    personas = set()
    lugares = set()
    instituciones = set()
    
    palabras_ley = ["ley", "decreto", "artículo", "reglamento", "código", "constitución", "estatuto", "directiva"]

    for ent in doc.ents:
        # SpaCy NER labels for es_core_news_sm: PER, LOC, ORG, MISC
        texto_ent = ent.text.strip()
        if len(texto_ent) < 3:
            continue
            
        if ent.label_ == "PER":
            personas.add(texto_ent)
        elif ent.label_ == "LOC":
            lugares.add(texto_ent)
        elif ent.label_ == "ORG":
            instituciones.add(texto_ent)
        elif ent.label_ == "MISC":
            # Si es MISC, intentamos deducir si es una ley
            texto_lower = texto_ent.lower()
            if any(palabra in texto_lower for palabra in palabras_ley):
                leyes.add(texto_ent)

    return {
        "leyes": list(leyes),
        "personas": list(personas),
        "lugares": list(lugares),
        "instituciones": list(instituciones)
    }

def extraer_entidades(video_id: str, pregunta: str = "", top_k: int = 10) -> dict:
    """
    Detecta leyes y personas relevantes en los fragmentos del vídeo,
    y busca información sobre cada una en Wikipedia en paralelo.
    """
    try:
        # Recuperamos TODOS los fragmentos del vídeo, no solo el top_k, ya que el NER local puede procesarlos rápidamente
        resultados = collection.get(
            where={"video_id": {"$eq": video_id}},
            include=["documents"]
        )
        documentos = resultados.get("documents", [])

        if not documentos:
            return {
                "video_id":  video_id,
                "entidades": [],
                "error":     f"No se encontraron fragmentos para el video '{video_id}'."
            }

        texto_completo = " ".join(documentos)
            
        detectadas = _detectar_entidades_con_ner(texto_completo)

        leyes    = detectadas.get("leyes", [])
        personas = detectadas.get("personas", [])
        lugares  = detectadas.get("lugares", [])
        instituciones = detectadas.get("instituciones", [])
        
        candidatos = [{"nombre": l, "tipo": "ley"} for l in leyes if l and len(l) > 3] + \
                     [{"nombre": p, "tipo": "persona"} for p in personas if p and len(p) > 3] + \
                     [{"nombre": lu, "tipo": "lugar"} for lu in lugares if lu and len(lu) > 2] + \
                     [{"nombre": i, "tipo": "institucion"} for i in instituciones if i and len(i) > 2]

        entidades = []
        
        # Buscar en Wikipedia en paralelo para máxima velocidad
        def _procesar_entidad(candidato):
            info = _buscar_wikipedia(candidato["nombre"])
            if info:
                # Usar solo la primera o segunda frase del resumen para no saturar la UI
                explicacion_corta = ". ".join(info.split(". ")[:2]) + "."
                return {
                    "nombre": candidato["nombre"],
                    "tipo": candidato["tipo"],
                    "explicacion": explicacion_corta
                }
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            resultados_wiki = executor.map(_procesar_entidad, candidatos)
            
        for r in resultados_wiki:
            if r is not None:
                entidades.append(r)

        return {"video_id": video_id, "entidades": entidades, "error": None}

    except Exception as e:
        return {"video_id": video_id, "entidades": [], "error": str(e)}


# ─────────────────────────────────────────────────────────────
# FUNCIÓN 4: CHUNKING AMPLIADO
# Devuelve el fragmento exacto + todo el contexto de esa intervención.
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
        # Hacemos una consulta más robusta: traemos todos los del vídeo y filtramos en Python.
        # Esto evita problemas con los operadores $gte y $lte en metadatos numéricos de ChromaDB.
        resultados = collection.get(
            where={"video_id": {"$eq": video_id}},
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

        # Filtrar en Python
        pares_filtrados = []
        for doc, meta in zip(documentos, metadatos):
            if meta.get("ponente") == ponente:
                if meta.get("inicio", 0) >= max(0.0, inicio - MARGEN_SEGUNDOS) and meta.get("fin", 0) <= fin + MARGEN_SEGUNDOS:
                    pares_filtrados.append((meta, doc))

        if not pares_filtrados:
            return {
                "ponente":           ponente,
                "inicio_mmss":       _segundos_a_mmss(inicio),
                "fin_mmss":          _segundos_a_mmss(fin),
                "texto_fragmento":   "",
                "contexto_completo": [],
                "error":             "No se encontraron fragmentos para esa intervención en el margen de tiempo."
            }

        # Ordenar por tiempo
        pares = sorted(pares_filtrados, key=lambda x: x[0].get("inicio", 0))

        # El fragmento exacto: el que más se solapa con [inicio, fin]
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