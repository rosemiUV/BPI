"""
Bloque A — Extracción de Audio y Reconocimiento de Voz (ASR)

Este módulo proporciona funcionalidades para:
- Descargar audio de videos de YouTube usando yt-dlp
- Transcribir audio usando faster-whisper con marcas de tiempo
"""

from pathlib import Path
from dataclasses import dataclass
from typing import List
import subprocess
import json


@dataclass
class SegmentoTranscripcion:
    """Segmento individual de transcripción con marca de tiempo."""
    inicio: float  # segundos
    fin: float     # segundos
    texto: str


@dataclass
class ResultadoTranscripcion:
    """Resultado completo de la transcripción."""
    texto_completo: str
    segmentos: List[SegmentoTranscripcion]
    idioma: str


def descargar_audio_youtube(url: str, directorio_salida: Path) -> Path:
    """
    Descargar el mejor audio disponible de un video de YouTube y convertirlo a WAV.
    
    Args:
        url: URL del video de YouTube
        directorio_salida: Directorio donde guardar el archivo de audio
        
    Returns:
        Path al archivo de audio descargado (formato WAV)
        
    Raises:
        RuntimeError: Si la descarga falla
    """
    directorio_salida = Path(directorio_salida)
    directorio_salida.mkdir(parents=True, exist_ok=True)
    
    try:
        # Descargar mejor audio disponible con yt-dlp
        comando = [
            'yt-dlp',
            '-f', 'bestaudio[ext=m4a]/bestaudio',
            '-x', '--audio-format', 'wav',
            '-o', str(directorio_salida / '%(id)s.%(ext)s'),
            url
        ]
        
        resultado = subprocess.run(comando, capture_output=True, text=True, check=True)
        
        # Encontrar el archivo descargado
        archivos_wav = list(directorio_salida.glob('*.wav'))
        if not archivos_wav:
            raise RuntimeError("No se encontró archivo WAV después de la descarga")
            
        return archivos_wav[0]
        
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error al descargar de YouTube: {e.stderr}")


class TranscriptorFasterWhisper:
    """Transcriptor de audio usando faster-whisper con soporte para marcas de tiempo."""
    
    def __init__(self, tamaño_modelo: str = "small", idioma: str = "es"):
        """
        Inicializar el transcriptor.
        
        Args:
            tamaño_modelo: Tamaño del modelo ('tiny', 'small', 'medium', 'large')
            idioma: Código de idioma (ej: 'es' para español, 'en' para inglés)
        """
        self.tamaño_modelo = tamaño_modelo
        self.idioma = idioma
        # En un MVP, la instancia real del modelo se carga bajo demanda
        self._modelo = None
    
    def transcribir(self, ruta_audio: Path) -> ResultadoTranscripcion:
        """
        Transcribir un archivo de audio.
        
        Args:
            ruta_audio: Path al archivo de audio
            
        Returns:
            ResultadoTranscripcion con texto completo y segmentos con marcas de tiempo
        """
        ruta_audio = Path(ruta_audio)
        
        try:
            # Importar faster_whisper solo cuando sea necesario
            from faster_whisper import WhisperModel
            
            # Cargar modelo si no está cargado
            if self._modelo is None:
                self._modelo = WhisperModel(self.tamaño_modelo, device="cpu")
            
            # Transcribir
            segmentos, info = self._modelo.transcribe(str(ruta_audio), language=self.idioma)
            
            # Procesar segmentos
            segmentos_procesados = []
            texto_completo = []
            
            for segmento in segmentos:
                seg = SegmentoTranscripcion(
                    inicio=segmento.start,
                    fin=segmento.end,
                    texto=segmento.text.strip()
                )
                segmentos_procesados.append(seg)
                texto_completo.append(seg.texto)
            
            return ResultadoTranscripcion(
                texto_completo=" ".join(texto_completo),
                segmentos=segmentos_procesados,
                idioma=info.language
            )
            
        except ImportError:
            # Alternativa segura para MVP: retornar transcripción simulada
            print("⚠️  faster-whisper no disponible. Usando transcripción simulada.")
            return self._transcribir_simulada(ruta_audio)
    
    def _transcribir_simulada(self, ruta_audio: Path) -> ResultadoTranscripcion:
        """Alternativa segura para MVP cuando los modelos no están disponibles."""
        return ResultadoTranscripcion(
            texto_completo="[Transcripción simulada] Este es un ejemplo de texto transcrito.",
            segmentos=[
                SegmentoTranscripcion(0.0, 2.5, "[Transcripción simulada]"),
                SegmentoTranscripcion(2.5, 5.0, "Este es un ejemplo de texto transcrito.")
            ],
            idioma="es"
        )
