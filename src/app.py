"""
Bloque D — Interfaz Streamlit

Aplicación web para:
- Procesar videos de YouTube (Bloques A y B)
- Realizar búsquedas semánticas (Bloque C)
"""

import streamlit as st
from pathlib import Path
import os
from dotenv import load_dotenv

from src.transcriber import descargar_audio_youtube, TranscriptorFasterWhisper
from src.diarizer import diarizar_audio, fusionar_transcripcion_con_diarizacion
from src.search_engine import MotorBusquedaSemantica


# Cargar variables de entorno
load_dotenv()

# Configurar página de Streamlit
st.set_page_config(
    page_title="Motor de Búsqueda de Sesiones Plenarias",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados
st.markdown("""
    <style>
        .header {
            text-align: center;
            color: #1f77b4;
            margin-bottom: 2rem;
        }
        .tab-content {
            padding: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# Título principal
st.markdown(
    "<h1 class='header'>🎥 Motor de Búsqueda de Sesiones Plenarias</h1>",
    unsafe_allow_html=True
)

# Crear directorios necesarios
Path("data/audio").mkdir(parents=True, exist_ok=True)
Path("data/chroma").mkdir(parents=True, exist_ok=True)

# Inicializar estado de sesión
if 'motor_busqueda' not in st.session_state:
    st.session_state.motor_busqueda = MotorBusquedaSemantica()

if 'transcripcion_actual' not in st.session_state:
    st.session_state.transcripcion_actual = None

if 'segmentos_orador' not in st.session_state:
    st.session_state.segmentos_orador = None

# Crear tabs
tab1, tab2 = st.tabs(["📹 Procesar Video", "🔍 Motor de Búsqueda"])

# ============================================================================
# TAB 1: PROCESAR VIDEO
# ============================================================================
with tab1:
    st.header("Procesar Video de YouTube")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        url_youtube = st.text_input(
            "Ingresa la URL de YouTube",
            placeholder="https://www.youtube.com/watch?v=...",
            help="URL válida de un video de YouTube"
        )
    
    with col2:
        procesar_boton = st.button(
            "▶️ Procesar",
            use_container_width=True,
            type="primary"
        )
    
    # Procesar video si se presionó el botón
    if procesar_boton:
        if not url_youtube:
            st.error("⚠️  Por favor ingresa una URL de YouTube válida")
        else:
            try:
                # Crear contenedor de progreso
                progreso = st.container()
                
                with progreso:
                    st.info("⏳ Procesando... esto puede tardar varios minutos")
                    
                    # Paso 1: Descargar audio
                    st.write("**Paso 1:** Descargando audio...")
                    try:
                        ruta_audio = descargar_audio_youtube(url_youtube, Path("data/audio"))
                        st.success(f"✓ Audio descargado: {ruta_audio.name}")
                    except Exception as e:
                        st.error(f"❌ Error al descargar: {str(e)}")
                        ruta_audio = None
                    
                    # Paso 2: Transcribir
                    if ruta_audio:
                        st.write("**Paso 2:** Transcribiendo audio...")
                        try:
                            transcriptor = TranscriptorFasterWhisper(tamaño_modelo="small", idioma="es")
                            resultado_transcripcion = transcriptor.transcribir(ruta_audio)
                            st.session_state.transcripcion_actual = resultado_transcripcion
                            st.success(f"✓ Transcripción completada ({len(resultado_transcripcion.segmentos)} segmentos)")
                        except Exception as e:
                            st.error(f"❌ Error en transcripción: {str(e)}")
                    
                    # Paso 3: Diarizar
                    if st.session_state.transcripcion_actual:
                        st.write("**Paso 3:** Identificando oradores...")
                        try:
                            segmentos_orador = diarizar_audio(ruta_audio)
                            st.session_state.segmentos_orador = segmentos_orador
                            st.success(f"✓ Diarización completada")
                        except Exception as e:
                            st.error(f"❌ Error en diarización: {str(e)}")
                    
                    # Paso 4: Indexar en motor de búsqueda
                    if st.session_state.transcripcion_actual:
                        st.write("**Paso 4:** Indexando en motor de búsqueda...")
                        try:
                            metadatos = {
                                'url': url_youtube,
                                'idioma': st.session_state.transcripcion_actual.idioma
                            }
                            st.session_state.motor_busqueda.indexar_transcripcion(
                                st.session_state.transcripcion_actual.texto_completo,
                                metadatos=metadatos
                            )
                            st.success("✓ Transcripción indexada en el motor de búsqueda")
                        except Exception as e:
                            st.error(f"❌ Error al indexar: {str(e)}")
                
                # Mostrar resultados
                st.divider()
                st.subheader("📊 Resultados")
                
                if st.session_state.transcripcion_actual:
                    # Mostrar transcripción
                    with st.expander("📝 Ver Transcripción Completa"):
                        st.text_area(
                            "Texto transcrito:",
                            value=st.session_state.transcripcion_actual.texto_completo,
                            height=200,
                            disabled=True
                        )
                    
                    # Mostrar segmentos con oradores si disponibles
                    if st.session_state.segmentos_orador:
                        with st.expander("🗣️ Ver Segmentos con Oradores"):
                            segmentos_fusionados = fusionar_transcripcion_con_diarizacion(
                                st.session_state.transcripcion_actual.segmentos,
                                st.session_state.segmentos_orador
                            )
                            for i, seg in enumerate(segmentos_fusionados[:10]):  # Mostrar primeros 10
                                col1, col2, col3 = st.columns([1, 2, 3])
                                with col1:
                                    st.caption(f"{seg['inicio']:.1f}s - {seg['fin']:.1f}s")
                                with col2:
                                    st.caption(f"**{seg['orador']}**")
                                with col3:
                                    st.caption(seg['texto'][:60] + "...")
            
            except Exception as e:
                st.error(f"❌ Error inesperado: {str(e)}")

# ============================================================================
# TAB 2: MOTOR DE BÚSQUEDA
# ============================================================================
with tab2:
    st.header("🔍 Búsqueda Semántica")
    
    if st.session_state.transcripcion_actual is None:
        st.info("⚠️  Primero debes procesar un video en la pestaña 'Procesar Video'")
    else:
        # Entrada de búsqueda
        col1, col2 = st.columns([4, 1])
        
        with col1:
            consulta = st.text_input(
                "¿Qué deseas buscar?",
                placeholder="ej: ¿Qué se dijo sobre educación?",
                help="Escribe una pregunta o tema de búsqueda"
            )
        
        with col2:
            top_k = st.slider("Resultados:", min_value=1, max_value=10, value=3)
        
        # Realizar búsqueda
        if consulta:
            with st.spinner("⏳ Buscando..."):
                resultados = st.session_state.motor_busqueda.recuperar_contexto(
                    consulta,
                    top_k=top_k
                )
            
            # Mostrar resultados
            st.subheader("📌 Resultados")
            
            if resultados:
                for i, resultado in enumerate(resultados, 1):
                    with st.container(border=True):
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.write(f"**Resultado {i}**")
                        with col2:
                            st.caption(f"Relevancia: {1 - resultado['distancia']:.2%}")
                        st.write(resultado['texto'])
            else:
                st.warning("❌ No se encontraron resultados para tu búsqueda")
        else:
            st.info("💡 Escribe una consulta para buscar en la transcripción")
        
        # Panel de información
        st.divider()
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Transcripción indexada",
                "✓" if st.session_state.transcripcion_actual else "✗"
            )
        
        with col2:
            st.metric(
                "Caracteres",
                f"{len(st.session_state.transcripcion_actual.texto_completo):,}"
            )
        
        with col3:
            st.metric(
                "Segmentos",
                len(st.session_state.transcripcion_actual.segmentos)
            )


# Sidebar con información
with st.sidebar:
    st.header("ℹ️ Información")
    st.markdown("""
    ### Motor de Búsqueda de Sesiones Plenarias
    
    **Pipeline de 4 bloques:**
    1. **Extracción/ASR**: Descarga y transcripción
    2. **Diarización**: Identificación de oradores
    3. **Búsqueda RAG**: Indexación semántica
    4. **Interfaz**: Búsqueda web
    
    **Características:**
    - ✓ Descarga de YouTube
    - ✓ Transcripción con marcas de tiempo
    - ✓ Identificación de oradores
    - ✓ Búsqueda semántica
    
    **Requisitos:**
    - Python 3.8+
    - Ver README para setup completo
    """)
    
    st.divider()
    
    # Botón de reset (en secreto)
    if st.button("🔄 Limpiar Base de Datos", use_container_width=True):
        st.session_state.motor_busqueda.limpiar_base_datos()
        st.session_state.transcripcion_actual = None
        st.session_state.segmentos_orador = None
        st.success("✓ Base de datos limpiada")
        st.rerun()
