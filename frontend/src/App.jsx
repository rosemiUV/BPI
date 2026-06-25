import { useState, useEffect, useRef } from 'react'
import { Search, PlayCircle, ArrowLeft, Loader2, Video, Clock, ChevronRight, Info, Sparkles, X, Users } from 'lucide-react'

// Las sesiones se cargarán ahora de forma dinámica desde el backend
function App() {

  // ========================================================
  // 1. Definimos los ESTADOS (variables que al cambiar actualizan la pantalla)
  // ========================================================
  // === ESTADOS GENERALES ===
  const [sesionActiva, setSesionActiva] = useState(null) // null = Pantalla de Inicio
  const [sesionesGuardadas, setSesionesGuardadas] = useState([])
  const [cargandoSesiones, setCargandoSesiones] = useState(true)

  // Cargar las sesiones al iniciar la app
  useEffect(() => {
    const fetchSesiones = async () => {
      try {
        const respuesta = await fetch('http://localhost:8000/api/sessions')
        if (respuesta.ok) {
          const datos = await respuesta.json()
          setSesionesGuardadas(datos)
        }
      } catch (error) {
        console.error("Error al cargar las sesiones desde la BBDD:", error)
      } finally {
        setCargandoSesiones(false)
      }
    }
    fetchSesiones()
  }, [])

  // === ESTADOS PANTALLA DE INICIO ===
  const [urlVideo, setUrlVideo] = useState('')
  const [procesandoUrl, setProcesandoUrl] = useState(false)

  // === ESTADOS BUSCADOR ===
  const [pregunta, setPregunta] = useState('')
  const [cargandoBusqueda, setCargandoBusqueda] = useState(false)
  const [historialChat, setHistorialChat] = useState([])
  const [mensajeActivo, setMensajeActivo] = useState(null)
  const [indiceActivo, setIndiceActivo] = useState(0)
  const chatEndRef = useRef(null)

  // === CONTEXTO AMPLIADO ===
  const [contextoAmpliado, setContextoAmpliado] = useState(null)
  const [cargandoContexto, setCargandoContexto] = useState(null) // Guardará el index del botón clickeado

  // === RESUMEN GLOBAL ===
  const [resumenGlobal, setResumenGlobal] = useState(null)
  const [cargandoResumen, setCargandoResumen] = useState(false)
  const [mostrarResumen, setMostrarResumen] = useState(false)

  // === ENTIDADES EXTRAÍDAS ===
  const [entidades, setEntidades] = useState(null)
  const [cargandoEntidades, setCargandoEntidades] = useState(false)
  const [mostrarEntidades, setMostrarEntidades] = useState(false)

  // === TOOLTIP GLOBAL PARA ENTIDADES ===
  const [tooltipGlobal, setTooltipGlobal] = useState({ visible: false, x: 0, y: 0, title: '', desc: '', icon: '' })

  // 1.2. Referencia al contenedor del scroll para poder observarlo
  const feedRef = useRef(null)


  // ========================================================
  // EFECTO DE RESUMEN GLOBAL Y ENTIDADES AL SELECCIONAR SESIÓN
  // ========================================================
  useEffect(() => {
    if (!sesionActiva) {
      setResumenGlobal(null)
      setMostrarResumen(false)
      setEntidades(null)
      setMostrarEntidades(false)
      return
    }

    let isMounted = true;

    const fetchResumen = async () => {
      setCargandoResumen(true)
      try {
        const respuesta = await fetch('http://localhost:8000/api/summary', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ video_id: sesionActiva.id_sesion })
        })
        if (respuesta.ok) {
          const data = await respuesta.json()
          if (isMounted && !data.error && data.resumen) {
            setResumenGlobal(data.resumen)
            setMostrarResumen(true) // Mostramos el resumen al entrar por primera vez
          }
        }
      } catch (error) {
        console.error("Error al obtener el resumen global:", error)
      } finally {
        if (isMounted) setCargandoResumen(false)
      }
    }

    const fetchEntidades = async () => {
      setCargandoEntidades(true)
      try {
        const respuesta = await fetch('http://localhost:8000/api/entities', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ video_id: sesionActiva.id_sesion })
        })
        if (respuesta.ok) {
          const data = await respuesta.json()
          if (isMounted && !data.error && data.entidades) {
            setEntidades(data.entidades)
          }
        }
      } catch (error) {
        console.error("Error al obtener entidades:", error)
      } finally {
        if (isMounted) setCargandoEntidades(false)
      }
    }

    fetchResumen()
    fetchEntidades()

    return () => {
      isMounted = false;
    }
  }, [sesionActiva])

  // ========================================================
  // FUNCIONES Y COMPONENTES AUXILIARES
  // ========================================================

  // Componente que resalta las entidades en un texto
  const TextWithEntities = ({ text, entidadesList }) => {
    if (!text) return null;
    if (!entidadesList || entidadesList.length === 0) return <>{text}</>;

    // Filtrar válidas y ordenar de mayor a menor longitud para regex seguro
    const validEntities = entidadesList.filter(e => e.nombre && e.nombre.length > 2);
    if (validEntities.length === 0) return <>{text}</>;
    
    validEntities.sort((a, b) => b.nombre.length - a.nombre.length);

    // Regex global case-insensitive
    const escapedNames = validEntities.map(e => e.nombre.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
    const regex = new RegExp(`(${escapedNames.join('|')})`, 'gi');

    const parts = text.split(regex);

    return (
      <>
        {parts.map((part, i) => {
          const entityMatch = validEntities.find(e => e.nombre.toLowerCase() === part.toLowerCase());
          
          if (entityMatch) {
            const tipo = entityMatch.tipo;
            let bgColor = 'bg-gray-100 text-gray-800 border-gray-300';
            let icon = '📌';
            
            if (tipo === 'ley') { bgColor = 'bg-amber-100 text-amber-800 border-amber-300'; icon = '⚖️'; }
            else if (tipo === 'persona') { bgColor = 'bg-emerald-100 text-emerald-800 border-emerald-300'; icon = '👤'; }
            else if (tipo === 'lugar') { bgColor = 'bg-blue-100 text-blue-800 border-blue-300'; icon = '📍'; }
            else if (tipo === 'institucion') { bgColor = 'bg-purple-100 text-purple-800 border-purple-300'; icon = '🏛️'; }
            
            return (
              <span 
                key={i}
                onMouseEnter={(e) => {
                  const rect = e.target.getBoundingClientRect();
                  setTooltipGlobal({
                    visible: true,
                    x: rect.left + rect.width / 2,
                    y: rect.top, // lo pondremos encima
                    title: tipo,
                    desc: entityMatch.explicacion,
                    icon: icon
                  });
                }}
                onMouseLeave={() => setTooltipGlobal({ ...tooltipGlobal, visible: false })}
                className={`inline-flex items-center px-1.5 py-0 mx-0.5 rounded-md font-medium border cursor-help transition-all hover:shadow-md hover:-translate-y-0.5 relative ${bgColor}`}
              >
                {part}
              </span>
            );
          }
          return <span key={i}>{part}</span>;
        })}
      </>
    );
  };

  // Componente para renderizar visualmente el resumen parseando el Markdown del LLM
  const ResumenVisual = ({ texto }) => {
    if (!texto) return null;

    // Separamos el índice del resumen usando el encabezado que le exigimos al LLM
    const partes = texto.split(/### 2\. Resumen Global/i);
    
    let indiceStr = partes[0].replace(/### 1\. Índice de Temas/i, '').trim();
    let resumenStr = partes.length > 1 ? partes[1].trim() : '';

    // Si el LLM no usó exactamente esos encabezados, asumimos todo como resumen
    if (partes.length === 1) {
      resumenStr = texto;
      indiceStr = '';
    }

    // Parseamos las viñetas del índice (líneas que empiezan por - o *)
    const temas = indiceStr.split('\n')
      .filter(line => line.trim().startsWith('-') || line.trim().startsWith('*'))
      .map(line => {
        let text = line.replace(/^[-*]\s*/, '').trim();
        // Si tiene formato "**Tema**: Descripción", lo separamos
        const match = text.match(/^\*\*(.*?)\*\*(.*)/);
        if (match) {
          return { titulo: match[1], desc: match[2].replace(/^:/, '').trim() };
        }
        return { titulo: text, desc: '' };
      });

    return (
      <div className="flex flex-col lg:flex-row gap-8 mt-2">
        {/* Índice de Temas */}
        {temas.length > 0 && (
          <div className="w-full lg:w-1/3 flex flex-col gap-3">
            <h4 className="text-xs font-bold tracking-widest text-purple-600 uppercase mb-2">Índice de Temas</h4>
            <div className="flex flex-col gap-3">
              {temas.map((tema, idx) => (
                <div key={idx} className="bg-purple-50/50 p-4 rounded-2xl border border-purple-100/50 transition-all hover:bg-purple-50 hover:shadow-sm">
                  <h5 className="font-semibold text-[#1d1d1f] leading-tight mb-1">{tema.titulo}</h5>
                  {tema.desc && <p className="text-sm text-[#86868b] leading-relaxed">{tema.desc}</p>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Resumen Global */}
        <div className="w-full lg:flex-1 flex flex-col gap-3">
          <h4 className="text-xs font-bold tracking-widest text-blue-600 uppercase mb-2">Análisis Global</h4>
          <div className="prose prose-lg text-[#1d1d1f] leading-relaxed opacity-90 whitespace-pre-wrap">
            <TextWithEntities text={resumenStr} entidadesList={entidades} />
          </div>
        </div>
      </div>
    );
  };

  const procesarNuevoVideo = async () => {

    if (!urlVideo.trim()) return
    setProcesandoUrl(true)

    // Extraer las URLs separadas por coma o salto de línea
    const urlsArray = urlVideo
      .split(/[\n,]+/)
      .map(u => u.trim())
      .filter(u => u !== '');

    if (urlsArray.length === 0) {
      setProcesandoUrl(false);
      return;
    }

    try {
      // Hacemos la peticion POST a nuestro endpoint de FastAPI
      const respuesta = await fetch('http://localhost:8000/api/process', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          url: urlsArray[0], // Compatibilidad hacia atrás
          urls: urlsArray    // Nueva funcionalidad lote
        })
      })

      if (!respuesta.ok) {
        throw new Error('Error en el servidor al procesar el/los vídeo(s)')
      }

      const respuestaData = await respuesta.json()

      // Soporte para array de sesiones (modo lote) o una sola sesión (modo normal)
      if (Array.isArray(respuestaData)) {
        if (respuestaData.length > 0) {
          setSesionActiva(respuestaData[0])
          setSesionesGuardadas(prev => {
            const nuevas = respuestaData.filter(nueva => !prev.find(s => s.id_sesion === nueva.id_sesion));
            return [...nuevas, ...prev];
          });
        }
      } else {
        setSesionActiva(respuestaData)
        setSesionesGuardadas(prev => {
          if (!prev.find(s => s.id_sesion === respuestaData.id_sesion)) {
            return [respuestaData, ...prev]
          }
          return prev
        })
      }
      
      setUrlVideo('')

    } catch (error) {
      console.error('Error al procesar el vídeo:', error)
      alert("Hubo un error al procesar el vídeo. Revisa la terminal donde corre FastAPI para ver los detalles.")
    } finally {
      setProcesandoUrl(false)
    }
  }

  const volverAlInicio = () => {
    setSesionActiva(null)
    setHistorialChat([])
    setMensajeActivo(null)
    setPregunta('')
  }

  const cargarContextoAmpliado = async (fuente, index) => {
    if (!sesionActiva) return;

    let inicio_seg = fuente.inicio_segundos;
    let fin_seg = fuente.fin_segundos;
    
    if (inicio_seg === undefined) {
      if (fuente.enlace_video && fuente.enlace_video.includes('t=')) {
        const match = fuente.enlace_video.match(/t=(\d+)/);
        if (match) {
          inicio_seg = parseInt(match[1]);
          fin_seg = inicio_seg + 10;
        }
      } else {
        inicio_seg = 0;
        fin_seg = 0;
      }
    }

    setCargandoContexto(index);
    setContextoAmpliado(null);
    try {
      const response = await fetch('http://localhost:8000/api/context', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          video_id: sesionActiva.id_sesion,
          ponente: fuente.ponente,
          inicio: inicio_seg,
          fin: fin_seg
        })
      });
      if (response.ok) {
        const data = await response.json();
        if (data.error) {
          alert("Aviso: " + data.error);
        } else {
          setContextoAmpliado(data);
        }
      } else {
        console.error("Error devuelto por la API:", await response.text());
        alert("No se pudo obtener el contexto ampliado.");
      }
    } catch (error) {
      console.error("Error al cargar contexto ampliado:", error);
    } finally {
      setCargandoContexto(null);
    }
  };


  // --- FUNCIONES DEL BUSCADOR ---
  const realizarBusqueda = async () => {
    if (!pregunta.trim()) return;

    setCargandoBusqueda(true);
    const preguntaEnviada = pregunta;
    
    // Añadimos la pregunta al chat
    const nuevoMensajeUsuario = { role: 'user', content: preguntaEnviada, id: Date.now() };
    setHistorialChat(prev => [...prev, nuevoMensajeUsuario]);
    setPregunta('');

    try {
      const respuesta = await fetch('http://localhost:8000/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pregunta: preguntaEnviada,
          id_sesion: sesionActiva.id_sesion
        })
      });

      const datos = await respuesta.json();
      
      const nuevoMensajeBot = { 
        role: 'bot', 
        content: datos.respuesta_llm, 
        fuentes_top_k: datos.fuentes_top_k || [], 
        id: Date.now() + 1 
      };

      setHistorialChat(prev => [...prev, nuevoMensajeBot]);
      setMensajeActivo(nuevoMensajeBot);
      setIndiceActivo(0);

    } catch (error) {
      console.error('Error al conectar con la API:', error);
      setHistorialChat(prev => [...prev, { role: 'bot', content: 'Lo siento, ha ocurrido un error al procesar tu solicitud.', fuentes_top_k: [] }]);
    } finally {
      setCargandoBusqueda(false);
    }
  };

  // Autoscroll del chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [historialChat, cargandoBusqueda]);

  // 2.2. Función que convierte un link normal de YT en un link incrustable para el iframe
  const obtenerEnlaceEmbed = (url) => {
    try {
      let videoId = 'TEST';
      let time = 0;

      // Algunas URLs vienen mal formadas como /live/ID&t=10s
      const cleanUrl = url.replace(/&t=/, '?t='); 
      const urlObj = new URL(cleanUrl);

      if (urlObj.hostname.includes('youtube.com')) {
        if (urlObj.pathname.startsWith('/watch')) {
          videoId = urlObj.searchParams.get('v');
        } else if (urlObj.pathname.startsWith('/live/')) {
          videoId = urlObj.pathname.split('/')[2];
        } else if (urlObj.pathname.startsWith('/embed/')) {
          videoId = urlObj.pathname.split('/')[2];
        }
      } else if (urlObj.hostname === 'youtu.be') {
        videoId = urlObj.pathname.slice(1);
      }

      let timeStr = urlObj.searchParams.get('t');
      if (timeStr) {
        time = parseInt(timeStr.replace('s', '')) || 0;
      }

      return `https://www.youtube.com/embed/${videoId}?start=${time}&enablejsapi=1`;
    } catch {
      return url;
    }
  }

  // 2.3. Función para mover el feed estilo TIKTOK
  const irAVideo = (indice) => {
    setIndiceActivo(indice);

    const elemento = document.getElementById(`video-tiktok-${indice}`);

    if (elemento) {
      elemento.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }

  // 2.4. IntersectionObserver para detectar el SCROLL
  useEffect(() => {
    if (!mensajeActivo || !feedRef.current) return;

    const observador = new IntersectionObserver(
      (entradas) => {
        entradas.forEach((entrada) => {
          if (entrada.isIntersecting) {
            const indexStr = entrada.target.getAttribute('data-index');

            if (indexStr === 'fantasma') {
              irAVideo(0); // Vuelve al inicio suavemente
              return;
            }

            const indiceActual = parseInt(indexStr);
            setIndiceActivo(indiceActual);

            // Pausar todos los demás videos para que no se solape el audio
            const iframes = document.querySelectorAll('.yt-iframe');
            iframes.forEach((iframe, i) => {
              if (i !== indiceActual) {
                iframe.contentWindow.postMessage(
                  '{"event": "command", "func": "pauseVideo", "args":""}',
                  '*'
                );
              }
            });
          }
        });
      },
      {
        root: feedRef.current,
        threshold: 0.6 // Se activa cuando el 60% del vídeo está en la pantalla
      }
    );

    // Observamos todos los contenedores de vídeo y el div fantasma final
    const elementos = feedRef.current.querySelectorAll('.video-container, .fantasma-loop')
    elementos.forEach((el) => observador.observe(el));

    // Limpieza del observador cuando se desmonta o cambian los resultados
    return () => observador.disconnect();
  }, [mensajeActivo]);


  // ========================================================
  // 3. Lo que se pinta en pantalla (JSX)
  // ========================================================
  return (
    /* Fondo Apple clásico (#f5f5f7) y texto casi negro (#1d1d1f) */
    <div className='min-h-screen bg-[#f5f5f7] text-[#1d1d1f] py-12 px-4 sm:px-6 lg:px-8 font-sans selection:bg-blue-200 selection:text-blue-900 relative'>

      {/* Brillos ambientales de fondo */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none z-0">
        <div className="absolute -top-[10%] -left-[10%] w-[50vw] h-[50vw] max-w-[600px] max-h-[600px] bg-blue-500/10 rounded-full blur-[100px]"></div>
        <div className="absolute top-[20%] -right-[10%] w-[40vw] h-[40vw] max-w-[500px] max-h-[500px] bg-purple-500/10 rounded-full blur-[100px]"></div>
      </div>

      {/* --- PANTALLA 1: INICIO --- */}
      {!sesionActiva && (
        <div className='max-w-4xl mx-auto space-y-10 animate-fade-in relative z-10'>

          {/* Cabecera Apple-style */}
          <div className="text-center space-y-5 pt-8 flex flex-col items-center">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-black/5 text-sm font-medium text-gray-600 mb-4">
              <Sparkles size={16} />
              <span>BETA v1.0</span>
            </div>
            <h1 className="text-5xl sm:text-6xl font-bold tracking-tight text-[#1d1d1f]">
              Buscador Plenario<br />
              <span className="text-gray-400">Inteligente</span>
            </h1>
            <p className="text-xl text-[#86868b] max-w-2xl mx-auto text-center font-medium">
              Analiza, transcribe y busca intervenciones políticas con precisión milimétrica usando modelos de lenguaje avanzados.
            </p>
          </div>

          {/* Sección Principal: Input URL */}
          <div className="bg-white p-8 sm:p-10 rounded-[2rem] shadow-[0_4px_24px_rgba(0,0,0,0.04)] border border-black/[0.04] max-w-2xl mx-auto transition-all">
            <h2 className='text-2xl font-semibold tracking-tight mb-3'>Procesar nueva sesión</h2>
            <p className='text-[#86868b] mb-8 text-lg'>Introduce el enlace oficial de YouTube para generar el análisis vectorial.</p>

            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <div className="absolute top-4 left-4 flex items-center pointer-events-none">
                  <Video size={20} className="text-gray-400" />
                </div>
                <textarea
                  className='w-full pl-12 pr-5 py-4 bg-[#f5f5f7] rounded-3xl focus:bg-white focus:ring-4 focus:ring-blue-500/20 focus:border-blue-500 border border-transparent outline-none transition-all placeholder:text-gray-400 font-medium resize-none'
                  placeholder='Pega aquí uno o varios enlaces de YouTube (separados por coma o salto de línea)'
                  rows={3}
                  value={urlVideo}
                  onChange={(e) => setUrlVideo(e.target.value)}
                />
              </div>
              <button
                onClick={procesarNuevoVideo}
                disabled={procesandoUrl || !urlVideo.trim()}
                className='px-8 py-4 bg-[#1d1d1f] text-white font-semibold rounded-3xl hover:bg-black transition-all disabled:opacity-50 flex items-center justify-center min-w-[160px] shadow-sm h-[88px] sm:h-auto'
              >
                {procesandoUrl ? <Loader2 className="animate-spin" size={20} /> : 'Analizar'}
              </button>
            </div>

            {procesandoUrl && (
              <p className='text-sm text-[#86868b] mt-6 flex items-center justify-center gap-2 animate-pulse font-medium'>
                <Info size={16} /> Descargando y ejecutando modelos (Whisper + PyAnnote)...
              </p>
            )}
          </div>

          {/* Sección Secundaria: Tarjetas Precargadas */}
          <div className="pt-4">
            <h3 className="text-xl font-semibold tracking-tight mb-6 flex items-center gap-2 text-[#1d1d1f]">
              Sesiones archivadas
            </h3>
            {cargandoSesiones ? (
              <div className="flex justify-center items-center py-10">
                <Loader2 className="animate-spin text-blue-500" size={32} />
                <span className="ml-3 text-[#86868b] font-medium">Conectando con ChromaDB...</span>
              </div>
            ) : sesionesGuardadas.length === 0 ? (
              <div className="text-center py-12 bg-white rounded-[2rem] border border-black/[0.04]">
                <p className="text-[#86868b] font-medium text-lg">No hay sesiones procesadas todavía. ¡Pega un enlace de YouTube arriba para empezar!</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {sesionesGuardadas.map((sesion) => (
                  <div
                    key={sesion.id_sesion}
                    onClick={() => setSesionActiva(sesion)}
                    className="bg-white p-6 rounded-[2rem] border border-black/[0.04] shadow-[0_4px_20px_rgba(0,0,0,0.03)] hover:shadow-[0_8px_30px_rgba(0,0,0,0.08)] hover:-translate-y-1 cursor-pointer transition-all duration-300 group flex flex-col h-full"
                  >
                    <div className='flex-1'>
                      <span className='text-[11px] font-bold uppercase tracking-widest text-blue-600 mb-3 block'>
                        {sesion.fecha}
                      </span>
                      <h4 className="text-lg font-semibold tracking-tight leading-snug group-hover:text-blue-600 transition-colors line-clamp-2">
                        {sesion.titulo}
                      </h4>
                    </div>
                    <div className="mt-6 flex justify-between items-center text-sm font-medium text-[#86868b]">
                      <span className="flex items-center gap-1.5"><Clock size={16} /> {sesion.duracion}</span>
                      <span className="flex items-center text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity -translate-x-2 group-hover:translate-x-0 duration-300">
                        Explorar <ChevronRight size={16} />
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>
      )}

      {/* --- PANTALLA 2: CHATBOT RAG DUAL-PANE --- */}
      {sesionActiva && (
        <div className="max-w-[1400px] mx-auto animate-fade-in relative z-10 h-[calc(100vh-6rem)] flex flex-col">

          {/* Barra superior */}
          <div className="mb-6 flex items-center justify-between bg-white px-6 py-4 rounded-full shadow-[0_4px_24px_rgba(0,0,0,0.04)] border border-black/[0.04] shrink-0">
            <button
              onClick={volverAlInicio}
              className='text-[#86868b] hover:text-[#1d1d1f] font-medium flex items-center gap-2 transition-colors'
            >
              <ArrowLeft size={18} /> Volver
            </button>
            <div className="text-right flex items-center gap-3">
              <span className="text-sm font-semibold text-[#86868b] uppercase tracking-wider hidden sm:inline-block">Buscando en:</span>
              <h2
                className="font-semibold bg-[#f5f5f7] px-4 py-2 rounded-lg text-[#1d1d1f] truncate max-w-[300px] sm:max-w-[500px]"
                style={{ fontSize: '18px', lineHeight: '14px', margin: 0 }}
              >
                {sesionActiva.titulo}
              </h2>
              {cargandoResumen || cargandoEntidades ? (
                <div className="flex items-center gap-2 px-4 py-2 bg-gray-50 text-gray-500 rounded-lg font-medium text-sm border border-gray-100 shadow-sm">
                  <Loader2 className="animate-spin text-blue-500" size={16} /> 
                  <span className="animate-pulse">Analizando sesión...</span>
                </div>
              ) : resumenGlobal ? (
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setMostrarEntidades(true)}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-colors bg-blue-50 text-blue-700 hover:bg-blue-100"
                  >
                    <Users size={16} /> Entidades
                  </button>
                  <button
                    onClick={() => setMostrarResumen(!mostrarResumen)}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
                      mostrarResumen ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    <Sparkles size={16} /> {mostrarResumen ? 'Ocultar Resumen' : 'Ver Resumen'}
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-2 px-4 py-2 bg-red-50 text-red-500 rounded-lg font-medium text-sm">
                  <Info size={16} /> Análisis no disponible
                </div>
              )}
            </div>
          </div>

          {/* CONTENEDOR DE VISTAS CON TRANSICIÓN CRUZADA */}
          <div className="flex-1 relative min-h-0">

            {/* VISTA 1: Tarjeta de Resumen Global */}
            <div className={`absolute inset-0 transition-all duration-500 ease-out flex flex-col ${
              mostrarResumen && resumenGlobal ? 'opacity-100 z-20 translate-y-0' : 'opacity-0 z-0 pointer-events-none translate-y-8'
            }`}>
              <div className="bg-white rounded-[2rem] shadow-[0_8px_30px_rgba(0,0,0,0.06)] border border-black/[0.04] p-8 relative flex flex-col flex-1 min-h-0 mb-6 overflow-hidden">
                <div className="absolute -top-24 -right-24 w-48 h-48 bg-purple-500/10 rounded-full blur-3xl pointer-events-none"></div>
                
                <div className="flex items-start justify-between mb-6 shrink-0">
                  <h3 className="text-2xl font-semibold tracking-tight flex items-center gap-3 text-[#1d1d1f]">
                    <div className="bg-purple-50 p-2 rounded-2xl border border-purple-100/50 shadow-sm">
                      <Sparkles className="text-purple-500" size={24} />
                    </div>
                    Resumen de la Sesión
                  </h3>
                  <button onClick={() => setMostrarResumen(false)} className="p-2 hover:bg-gray-100 rounded-full transition-colors">
                    <X size={20} className="text-gray-400 hover:text-gray-600" />
                  </button>
                </div>
                
                <div className="flex-1 overflow-y-auto pr-4 [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-thumb]:bg-gray-200 [&::-webkit-scrollbar-thumb]:rounded-full relative z-10">
                  <ResumenVisual texto={resumenGlobal} />
                </div>
              </div>
            </div>

            {/* VISTA 2: Layout Principal Dual-Pane (Chat + Vídeo) */}
            <div className={`absolute inset-0 transition-all duration-500 ease-out flex flex-col lg:flex-row gap-6 pb-6 ${
              !mostrarResumen ? 'opacity-100 z-20 translate-y-0' : 'opacity-0 z-0 pointer-events-none translate-y-8'
            }`}>
            
            {/* PANEL IZQUIERDO: CHAT (40%) */}
            <div className="w-full lg:w-[40%] flex flex-col bg-white rounded-[2.5rem] shadow-[0_8px_30px_rgba(0,0,0,0.06)] border border-black/[0.04] overflow-hidden">
              
              {/* Historial de mensajes */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6 flex flex-col bg-[#fcfcfc] [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-thumb]:bg-gray-200 [&::-webkit-scrollbar-thumb]:rounded-full">
                {historialChat.length === 0 ? (
                  <div className="m-auto text-center flex flex-col items-center justify-center text-gray-400 p-8">
                    <div className="bg-blue-50 p-4 rounded-full mb-4">
                      <Sparkles size={32} className="text-blue-500" />
                    </div>
                    <h3 className="font-semibold text-xl text-gray-800 mb-2">Asistente de Sesión</h3>
                    <p className="text-sm">Escribe tu pregunta abajo para buscar información en el vídeo interactuando con la inteligencia artificial.</p>
                  </div>
                ) : (
                  historialChat.map((msg) => (
                    <div 
                      key={msg.id} 
                      onClick={() => msg.role === 'bot' && msg.fuentes_top_k?.length > 0 && setMensajeActivo(msg)}
                      className={`max-w-[85%] rounded-3xl p-4 shadow-sm transition-all ${
                        msg.role === 'user' 
                          ? 'bg-blue-600 text-white self-end rounded-br-md shadow-blue-500/20' 
                          : `bg-white text-[#1d1d1f] self-start rounded-bl-md border border-gray-100 cursor-pointer hover:border-blue-200 hover:shadow-md ${mensajeActivo?.id === msg.id ? 'ring-2 ring-blue-500/30 bg-blue-50/30' : ''}`
                      }`}
                    >
                      <p className="leading-relaxed whitespace-pre-wrap text-[15px]">
                        <TextWithEntities text={msg.content} entidadesList={entidades} />
                      </p>
                      
                      {msg.role === 'bot' && msg.fuentes_top_k?.length > 0 && (
                        <div className="mt-4 pt-3 border-t border-gray-100 flex items-center gap-2 text-xs font-semibold text-blue-600">
                          <PlayCircle size={14}/> {msg.fuentes_top_k.length} fuentes en vídeo (clic para ver)
                        </div>
                      )}
                      {msg.role === 'bot' && msg.fuentes_top_k?.length === 0 && (
                         <div className="mt-4 pt-3 border-t border-gray-100 text-xs text-gray-400">
                           Sin coincidencias exactas.
                         </div>
                      )}
                    </div>
                  ))
                )}
                {cargandoBusqueda && (
                  <div className="bg-white text-gray-500 rounded-3xl rounded-bl-md p-4 self-start flex items-center gap-3 border border-gray-100 shadow-sm">
                    <Loader2 className="animate-spin text-blue-500" size={18} /> Pensando la respuesta...
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              {/* Input de chat */}
              <div className="p-4 bg-white border-t border-gray-100 shrink-0">
                <div className="relative flex items-center">
                  <input 
                    type="text" 
                    className="w-full pl-6 pr-14 py-4 bg-[#f5f5f7] rounded-full focus:bg-white focus:ring-4 focus:ring-blue-500/20 focus:border-blue-500 border border-transparent outline-none transition-all placeholder:text-gray-400 font-medium"
                    placeholder="Pregunta algo sobre el vídeo..."
                    value={pregunta}
                    onChange={e => setPregunta(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && realizarBusqueda()}
                    disabled={cargandoBusqueda}
                  />
                  <button 
                    onClick={realizarBusqueda}
                    disabled={cargandoBusqueda || !pregunta.trim()}
                    className="absolute right-2 p-3 bg-blue-600 text-white rounded-full hover:bg-blue-700 transition disabled:opacity-50 shadow-md"
                  >
                    <ArrowLeft size={18} className="rotate-180" />
                  </button>
                </div>
              </div>

            </div>

            {/* PANEL DERECHO: TIKTOK FEED (60%) */}
            <div className="w-full lg:w-[60%] flex flex-col bg-white rounded-[2.5rem] shadow-[0_8px_30px_rgba(0,0,0,0.06)] border border-black/[0.04] p-6 overflow-hidden">
              {mensajeActivo && mensajeActivo.fuentes_top_k && mensajeActivo.fuentes_top_k.length > 0 ? (
                <div className="flex flex-col h-full gap-6 md:flex-row min-h-0">
                  
                  {/* Lista de Fuentes */}
                  <div className="w-full md:w-1/3 overflow-y-auto pr-2 flex flex-col gap-3 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
                    <h4 className="text-sm font-bold uppercase tracking-widest text-[#86868b] mb-2 px-2 shrink-0">Evidencias</h4>
                    {mensajeActivo.fuentes_top_k.map((fuente, index) => (
                      <button
                        key={index}
                        onClick={() => irAVideo(index)}
                        className={`text-left p-3 rounded-3xl transition-all duration-300 ${indiceActivo === index
                          ? 'bg-[#f5f5f7] shadow-inner border border-black/[0.04]'
                          : 'bg-transparent scale-[0.98] hover:bg-gray-50 opacity-60 hover:opacity-100'
                          }`}
                      >
                        <span className="flex items-center gap-2 font-semibold text-sm mb-2 text-[#1d1d1f]">
                          <PlayCircle size={16} className={indiceActivo === index ? "text-blue-600" : "text-gray-400"} />
                          {fuente.ponente}
                        </span>
                        <p className="text-sm text-[#86868b] line-clamp-3 leading-relaxed">
                          "{fuente.texto}"
                        </p>

                        <div className="mt-3 flex justify-end">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              cargarContextoAmpliado(fuente, index);
                            }}
                            disabled={cargandoContexto !== null}
                            className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1 bg-blue-50 hover:bg-blue-100 px-3 py-1.5 rounded-full transition-colors disabled:opacity-50"
                          >
                            {cargandoContexto === index ? <Loader2 size={14} className="animate-spin" /> : <Info size={14} />} Ver contexto
                          </button>
                        </div>
                      </button>
                    ))}
                  </div>

                  {/* Reproductor de Video Carrusel */}
                  <div
                    ref={feedRef}
                    className="w-full md:w-2/3 flex-1 bg-black rounded-[2rem] overflow-y-scroll snap-y snap-mandatory relative shadow-inner [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none] scroll-smooth"
                  >
                    {mensajeActivo.fuentes_top_k.map((fuente, index) => (
                      <div
                        key={index}
                        id={`video-tiktok-${index}`}
                        data-index={index}
                        className="video-container w-full h-full snap-start snap-always relative flex flex-col items-center justify-center bg-[#1d1d1f]"
                      >
                        <iframe
                          className="yt-iframe w-full aspect-video shadow-2xl"
                          src={obtenerEnlaceEmbed(fuente.enlace_video)}
                          title={`Video ${index}`}
                          frameBorder="0"
                          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                          allowFullScreen
                        ></iframe>
                        <div className="absolute bottom-8 left-6 right-6 bg-black/40 backdrop-blur-md p-5 rounded-3xl border border-white/10 text-white pointer-events-none">
                          <p className="font-semibold text-lg tracking-tight mb-1">{fuente.ponente}</p>
                          <p className="text-sm opacity-80 line-clamp-2 leading-relaxed">"{fuente.texto}"</p>
                        </div>
                      </div>
                    ))}
                    <div data-index="fantasma" className="fantasma-loop w-full h-2 snap-start opacity-0"></div>
                  </div>
                </div>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center text-center p-10 bg-gray-50/50 rounded-3xl border border-gray-100 border-dashed">
                  <div className="bg-white p-4 rounded-full shadow-sm mb-4">
                    <Video size={48} className="text-gray-300" />
                  </div>
                  <h3 className="text-xl font-semibold text-[#1d1d1f] mb-2">Feed de Vídeo</h3>
                  <p className="text-[#86868b] max-w-sm">Haz una pregunta en el chat para ver aquí las evidencias en vídeo de la respuesta.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      )}

      {/* MODAL CONTEXTO AMPLIADO */}
      {contextoAmpliado && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="bg-white rounded-3xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
              <div>
                <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                  <Info className="text-blue-500" size={24} />
                  Contexto Ampliado
                </h3>
                <p className="text-sm text-gray-500 mt-1">
                  Intervención completa de <span className="font-semibold text-gray-700">{contextoAmpliado.ponente}</span>
                </p>
              </div>
              <button 
                onClick={() => setContextoAmpliado(null)}
                className="p-2 hover:bg-gray-200 rounded-full transition-colors"
              >
                <X size={20} className="text-gray-500" />
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto flex-1">
              {contextoAmpliado.contexto_completo && contextoAmpliado.contexto_completo.length > 0 ? (
                <div className="flex flex-col gap-4">
                  {contextoAmpliado.contexto_completo.map((item, i) => {
                    const isTarget = item.texto === contextoAmpliado.texto_fragmento;
                    return (
                      <div 
                        key={i} 
                        className={`p-4 rounded-2xl transition-colors ${isTarget ? 'bg-blue-50 border border-blue-100 shadow-sm' : 'bg-gray-50 hover:bg-gray-100'}`}
                      >
                        <div className={`text-xs font-medium mb-2 uppercase tracking-wider ${isTarget ? 'text-blue-500' : 'text-gray-400'}`}>
                          {item.inicio} - {item.fin} {isTarget && '(Coincidencia)'}
                        </div>
                        <p className={`text-sm md:text-base leading-relaxed ${isTarget ? 'text-blue-900 font-medium' : 'text-gray-700'}`}>
                          <TextWithEntities text={item.texto} entidadesList={entidades} />
                        </p>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">No se pudo recuperar el contexto.</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* MODAL ENTIDADES */}
      {mostrarEntidades && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="bg-white rounded-3xl w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
            <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50 shrink-0">
              <div>
                <h3 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                  <Users className="text-blue-500" size={28} />
                  Directorio de Entidades
                </h3>
                <p className="text-sm text-gray-500 mt-1">
                  Personas y normativas extraídas de la sesión actual
                </p>
              </div>
              <button 
                onClick={() => setMostrarEntidades(false)}
                className="p-2 hover:bg-gray-200 rounded-full transition-colors"
              >
                <X size={24} className="text-gray-500" />
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto flex-1 bg-gray-50/30">
              {cargandoEntidades ? (
                <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                  <Loader2 className="animate-spin mb-4" size={32} />
                  <p>Analizando entidades y consultando Wikipedia...</p>
                </div>
              ) : !entidades || entidades.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                  <Info size={48} className="mb-4 opacity-50" />
                  <p>No se han detectado entidades relevantes en esta sesión.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  {/* PERSONAS */}
                  <div className="flex flex-col gap-4">
                    <h4 className="font-bold text-sm text-emerald-700 uppercase tracking-widest flex items-center gap-2 border-b border-emerald-100 pb-2">
                      <span className="text-xl">👤</span> Personas Mencionadas
                    </h4>
                    {entidades.filter(e => e.tipo === 'persona').length === 0 && (
                      <p className="text-sm text-gray-400 italic">No se detectaron personas.</p>
                    )}
                    {entidades.filter(e => e.tipo === 'persona').map((entidad, idx) => (
                      <div key={idx} className="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
                        <h5 className="font-bold text-gray-900 mb-2">{entidad.nombre}</h5>
                        <p className="text-sm text-gray-600 leading-relaxed">{entidad.explicacion}</p>
                      </div>
                    ))}
                  </div>
                  
                  {/* LEYES */}
                  <div className="flex flex-col gap-4">
                    <h4 className="font-bold text-sm text-amber-700 uppercase tracking-widest flex items-center gap-2 border-b border-amber-100 pb-2">
                      <span className="text-xl">⚖️</span> Leyes y Normativas
                    </h4>
                    {entidades.filter(e => e.tipo === 'ley').length === 0 && (
                      <p className="text-sm text-gray-400 italic">No se detectaron normativas.</p>
                    )}
                    {entidades.filter(e => e.tipo === 'ley').map((entidad, idx) => (
                      <div key={idx} className="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
                        <h5 className="font-bold text-gray-900 mb-2">{entidad.nombre}</h5>
                        <p className="text-sm text-gray-600 leading-relaxed">{entidad.explicacion}</p>
                      </div>
                    ))}
                  </div>
                  {/* LUGARES */}
                  <div className="flex flex-col gap-4">
                    <h4 className="font-bold text-sm text-blue-700 uppercase tracking-widest flex items-center gap-2 border-b border-blue-100 pb-2">
                      <span className="text-xl">📍</span> Lugares y Zonas
                    </h4>
                    {entidades.filter(e => e.tipo === 'lugar').length === 0 && (
                      <p className="text-sm text-gray-400 italic">No se detectaron lugares.</p>
                    )}
                    {entidades.filter(e => e.tipo === 'lugar').map((entidad, idx) => (
                      <div key={idx} className="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
                        <h5 className="font-bold text-gray-900 mb-2">{entidad.nombre}</h5>
                        <p className="text-sm text-gray-600 leading-relaxed">{entidad.explicacion}</p>
                      </div>
                    ))}
                  </div>

                  {/* INSTITUCIONES */}
                  <div className="flex flex-col gap-4">
                    <h4 className="font-bold text-sm text-purple-700 uppercase tracking-widest flex items-center gap-2 border-b border-purple-100 pb-2">
                      <span className="text-xl">🏛️</span> Instituciones
                    </h4>
                    {entidades.filter(e => e.tipo === 'institucion').length === 0 && (
                      <p className="text-sm text-gray-400 italic">No se detectaron instituciones.</p>
                    )}
                    {entidades.filter(e => e.tipo === 'institucion').map((entidad, idx) => (
                      <div key={idx} className="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
                        <h5 className="font-bold text-gray-900 mb-2">{entidad.nombre}</h5>
                        <p className="text-sm text-gray-600 leading-relaxed">{entidad.explicacion}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* PORTAL TOOLTIP GLOBAL */}
      {tooltipGlobal.visible && (
        <div 
          className="fixed z-[9999] pointer-events-none transition-opacity duration-200"
          style={{ 
            left: `${tooltipGlobal.x}px`, 
            top: `${tooltipGlobal.y - 8}px`, // 8px de margen arriba
            transform: 'translate(-50%, -100%)' // Centrado horizontalmente, justo encima
          }}
        >
          <div className="w-64 p-3 bg-gray-900 text-white text-sm font-normal rounded-xl shadow-2xl leading-tight">
            <div className="font-bold text-gray-200 mb-1 flex items-center gap-1 uppercase text-xs tracking-wider">
              {tooltipGlobal.icon} {tooltipGlobal.title}
            </div>
            {tooltipGlobal.desc}
            <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
          </div>
        </div>
      )}

    </div>
  )
}

export default App