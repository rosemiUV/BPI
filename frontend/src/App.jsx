import { useState, useEffect, useRef } from 'react'
import { Search, PlayCircle, ArrowLeft, Loader2, Video, Clock, ChevronRight, Info, Sparkles } from 'lucide-react'

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
  const [resultados, setResultados] = useState(null)
  const [indiceActivo, setIndiceActivo] = useState(0)

  // 1.2. Referencia al contenedor del scroll para poder observarlo
  const feedRef = useRef(null)


  // ========================================================
  // FUNCIONES
  // ========================================================
  // --- FUNCIONES PANTALLA DE INICIO ---
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
    setResultados(null)
    setPregunta('')
  }


  // --- FUNCIONES DEL BUSCADOR ---
  // 2.1. Función que se ejecuta al pulsar BUSCAR
  const realizarBusqueda = async () => {

    if (!pregunta.trim()) return // Si está vacío no hacemos nada

    setCargandoBusqueda(true)
    setResultados(null)
    setIndiceActivo(0)

    try {
      // Hacemos la petición POST a nuestra API en Python (FastAPI)
      const respuesta = await fetch('http://localhost:8000/api/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          pregunta: pregunta,
          id_sesion: sesionActiva.id_sesion // Para saber en que video buscar
        })
      })

      const datos = await respuesta.json()
      setResultados(datos) // Guardamos el JSON que nos devuelve Python

    } catch (error) {
      console.error('Error al conectar con la API:', error)

    } finally {
      setCargandoBusqueda(false)

    }
  }

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
    if (!resultados || !feedRef.current) return;

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
  }, [resultados]);


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

      {/* --- PANTALLA 2: BUSCADOR RAG --- */}
      {sesionActiva && (
        <div className="max-w-6xl mx-auto animate-fade-in relative z-10">

          {/* Barra superior */}
          <div className="mb-10 flex items-center justify-between bg-white px-6 py-4 rounded-full shadow-[0_4px_24px_rgba(0,0,0,0.04)] border border-black/[0.04]">
            <button
              onClick={volverAlInicio}
              className='text-[#86868b] hover:text-[#1d1d1f] font-medium flex items-center gap-2 transition-colors'
            >
              <ArrowLeft size={18} /> Volver
            </button>
            <div className="text-right flex items-center gap-3">
              <span className="text-sm font-semibold text-[#86868b] uppercase tracking-wider hidden sm:inline-block">Buscando en:</span>
              <h2
                className="font-semibold bg-[#f5f5f7] px-4 py-2 rounded-lg text-[#1d1d1f] truncate max-w-[500px] sm:max-w-[500px]"
                style={{ fontSize: '20px', lineHeight: '14px', margin: 0 }}
              >
                {sesionActiva.titulo}
              </h2>
            </div>
          </div>

          {/* Barra de Búsqueda */}
          <div className='max-w-3xl mx-auto flex flex-col sm:flex-row gap-3'>
            <div className="relative flex-1">
              <div className="absolute inset-y-0 left-5 flex items-center pointer-events-none">
                <Search size={20} className="text-gray-400" />
              </div>
              <input
                type="text"
                className='w-full pl-12 pr-5 py-4 bg-white rounded-full shadow-[0_4px_20px_rgba(0,0,0,0.03)] border border-black/[0.04] focus:ring-4 focus:ring-blue-500/20 focus:border-blue-500 outline-none transition-all placeholder:text-gray-400 font-medium text-lg'
                placeholder='¿Qué se dijo sobre este tema?'
                value={pregunta}
                onChange={(e) => setPregunta(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && realizarBusqueda()}
              />
            </div>
            <button
              onClick={realizarBusqueda}
              disabled={cargandoBusqueda || !pregunta.trim()}
              className='px-8 py-4 bg-blue-600 text-white font-semibold rounded-full shadow-md hover:bg-blue-700 disabled:opacity-50 transition-all flex items-center justify-center min-w-[140px]'
            >
              {cargandoBusqueda ? <Loader2 className="animate-spin" size={20} /> : 'Buscar'}
            </button>
          </div>

          {/* Resultados */}
          {resultados && (
            <div className='max-w-5xl mx-auto mt-12 flex flex-col gap-8'>
              {resultados.fuentes_top_k && resultados.fuentes_top_k.length > 0 ? (
                <div className="flex flex-col gap-8">

                  {/* Tarjeta de Respuesta del LLM Apple-style */}
                  <div className='bg-white p-8 rounded-[2rem] shadow-[0_4px_24px_rgba(0,0,0,0.04)] border border-black/[0.04] relative overflow-hidden'>
                    {/* Brillo sutil de fondo (efecto Apple Intelligence/Siri) */}
                    <div className="absolute -top-24 -left-24 w-48 h-48 bg-blue-500/10 rounded-full blur-3xl pointer-events-none"></div>

                    <h3 className="relative text-xl font-semibold tracking-tight flex items-center gap-3 mb-4 text-[#1d1d1f]">
                      <div className="bg-blue-50 p-2 rounded-2xl border border-blue-100/50 shadow-sm">
                        <Sparkles className="text-blue-500" size={22} />
                      </div>
                      Respuesta sintetizada
                    </h3>
                    <p className='text-[#1d1d1f] leading-relaxed text-lg opacity-90'>{resultados.respuesta_llm}</p>
                  </div>

                  {/* Feed TikTok */}
                  <div className='flex flex-col md:flex-row gap-6 bg-white p-6 rounded-[2.5rem] shadow-[0_8px_30px_rgba(0,0,0,0.06)] border border-black/[0.04]'>

                    <div className='w-full md:w-1/3 overflow-y-auto flex flex-col gap-3 max-h-[600px] pr-2 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]'>
                      <h4 className='text-sm font-bold uppercase tracking-widest text-[#86868b] mb-2 px-2'>Fuentes originales</h4>
                      {resultados.fuentes_top_k.map((fuente, index) => (
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
                        </button>
                      ))}
                    </div>

                    <div
                      ref={feedRef}
                      className='w-full md:w-2/3 h-[600px] bg-black rounded-[2rem] overflow-y-scroll snap-y snap-mandatory relative shadow-inner [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none] scroll-smooth'
                    >
                      {resultados.fuentes_top_k.map((fuente, index) => (
                        <div
                          key={index}
                          id={`video-tiktok-${index}`}
                          data-index={index}
                          className='video-container w-full h-full snap-start snap-always relative flex flex-col items-center justify-center bg-[#1d1d1f]'
                        >
                          <iframe
                            className='yt-iframe w-full aspect-video shadow-2xl'
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
                </div>
              ) : (
                <div className="text-center py-20 bg-white rounded-[2rem] shadow-[0_4px_24px_rgba(0,0,0,0.04)] border border-black/[0.04]">
                  <Search className="mx-auto text-gray-300 mb-5" size={48} />
                  <h3 className="text-2xl font-semibold tracking-tight text-[#1d1d1f] mb-2">Sin coincidencias</h3>
                  <p className="text-[#86868b] max-w-md mx-auto font-medium">
                    No hemos encontrado fragmentos en esta sesión parlamentaria que respondan a tu búsqueda.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default App