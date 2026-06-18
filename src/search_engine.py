"""
Bloque C — Motor de Búsqueda Semántica RAG

Este módulo proporciona funcionalidades para:
- Dividir transcripciones en fragmentos (chunks)
- Crear embeddings y almacenarlos en ChromaDB
- Recuperar contexto relevante basado en consultas semánticas
"""

from pathlib import Path
from typing import List, Optional
import chromadb
from chromadb.config import Settings


class MotorBusquedaSemantica:
    """Motor de búsqueda basado en embeddings con ChromaDB."""
    
    def __init__(self, directorio_db: Optional[Path] = None, tamaño_fragmento: int = 500):
        """
        Inicializar el motor de búsqueda.
        
        Args:
            directorio_db: Directorio para almacenar la base de datos ChromaDB
            tamaño_fragmento: Número de caracteres por fragmento de texto
        """
        self.tamaño_fragmento = tamaño_fragmento
        self.directorio_db = Path(directorio_db) if directorio_db else Path("./data/chroma")
        self.directorio_db.mkdir(parents=True, exist_ok=True)
        
        # Inicializar cliente de ChromaDB
        self.cliente_chroma = chromadb.Client(
            Settings(
                chroma_db_impl="duckdb+parquet",
                persist_directory=str(self.directorio_db),
                anonymized_telemetry=False
            )
        )
        
        self.coleccion = None
    
    def indexar_transcripcion(self, texto: str, metadatos: Optional[dict] = None):
        """
        Indexar una transcripción completa en la base de datos.
        
        Args:
            texto: Texto completo de la transcripción
            metadatos: Diccionario con metadatos opcionales (ej: {'url': '...', 'fecha': '...'})
        """
        # Fragmentar el texto
        fragmentos = self._fragmentar_texto(texto)
        
        # Crear nombre de colección si no existe
        if self.coleccion is None:
            self.coleccion = self.cliente_chroma.get_or_create_collection(
                name="transcripciones"
            )
        
        # Agregar fragmentos a ChromaDB
        ids = [f"fragmento_{i}" for i in range(len(fragmentos))]
        metadatos_lista = [metadatos or {} for _ in fragmentos]
        
        try:
            self.coleccion.add(
                ids=ids,
                documents=fragmentos,
                metadatas=metadatos_lista
            )
            print(f"✓ Indexados {len(fragmentos)} fragmentos de transcripción")
        except Exception as e:
            print(f"⚠️  Error al indexar: {e}")
    
    def recuperar_contexto(self, consulta: str, top_k: int = 3) -> List[dict]:
        """
        Recuperar fragmentos relevantes basados en una consulta.
        
        Args:
            consulta: Texto de la consulta de búsqueda
            top_k: Número de resultados a devolver
            
        Returns:
            Lista de diccionarios con fragmentos relevantes
        """
        if self.coleccion is None:
            print("⚠️  No hay transcripción indexada. Usando búsqueda simulada.")
            return self._recuperar_simulada(consulta)
        
        try:
            resultados = self.coleccion.query(
                query_texts=[consulta],
                n_results=top_k
            )
            
            # Procesar resultados
            contextos = []
            if resultados and resultados['documents'] and len(resultados['documents']) > 0:
                for i, doc in enumerate(resultados['documents'][0]):
                    contextos.append({
                        'texto': doc,
                        'distancia': resultados['distances'][0][i] if resultados['distances'] else 0,
                        'metadatos': resultados['metadatas'][0][i] if resultados['metadatas'] else {}
                    })
            
            return contextos if contextos else self._recuperar_simulada(consulta)
            
        except Exception as e:
            print(f"⚠️  Error en recuperación: {e}. Usando búsqueda simulada.")
            return self._recuperar_simulada(consulta)
    
    def _fragmentar_texto(self, texto: str) -> List[str]:
        """
        Dividir un texto en fragmentos solapados.
        
        Args:
            texto: Texto a fragmentar
            
        Returns:
            Lista de fragmentos
        """
        fragmentos = []
        solapamiento = self.tamaño_fragmento // 4  # 25% de solapamiento
        
        for i in range(0, len(texto), self.tamaño_fragmento - solapamiento):
            fragmento = texto[i:i + self.tamaño_fragmento]
            if len(fragmento.strip()) > 10:  # Ignorar fragmentos muy pequeños
                fragmentos.append(fragmento)
        
        return fragmentos
    
    def _recuperar_simulada(self, consulta: str) -> List[dict]:
        """Alternativa segura para MVP: búsqueda simulada."""
        return [
            {
                'texto': f'Resultado simulado 1: Información relacionada con "{consulta}"',
                'distancia': 0.2,
                'metadatos': {'tipo': 'simulado'}
            },
            {
                'texto': f'Resultado simulado 2: Otro fragmento relevante sobre "{consulta}"',
                'distancia': 0.3,
                'metadatos': {'tipo': 'simulado'}
            },
        ]
    
    def limpiar_base_datos(self):
        """Limpiar la base de datos de ChromaDB."""
        try:
            if self.coleccion:
                self.cliente_chroma.delete_collection(name="transcripciones")
                self.coleccion = None
            print("✓ Base de datos limpiada")
        except Exception as e:
            print(f"⚠️  Error al limpiar: {e}")
