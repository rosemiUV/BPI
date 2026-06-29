import sqlite3
import json
from pathlib import Path

DB_DIR = Path(__file__).parent.parent.parent / "data" / "db"
DB_PATH = DB_DIR / "metadatos_videos.db"

def _obtener_conexion():
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def inicializar_db():
    conn = _obtener_conexion()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos_metadata (
            video_id TEXT PRIMARY KEY,
            resumen TEXT,
            entidades_json TEXT
        )
    ''')
    conn.commit()
    conn.close()

def guardar_metadatos_video(video_id: str, resumen: str, entidades: list):
    """
    Guarda el resumen y las entidades de un vídeo en SQLite.
    Las entidades se serializan como un string JSON.
    """
    inicializar_db()
    conn = _obtener_conexion()
    cursor = conn.cursor()
    
    entidades_json = json.dumps(entidades, ensure_ascii=False)
    
    cursor.execute('''
        INSERT INTO videos_metadata (video_id, resumen, entidades_json)
        VALUES (?, ?, ?)
        ON CONFLICT(video_id) DO UPDATE SET
            resumen=excluded.resumen,
            entidades_json=excluded.entidades_json
    ''', (video_id, resumen, entidades_json))
    
    conn.commit()
    conn.close()

def obtener_metadatos_video(video_id: str):
    """
    Recupera los metadatos de un vídeo.
    Devuelve un diccionario con 'resumen' y 'entidades' (lista) o None si no existe.
    """
    inicializar_db()
    conn = _obtener_conexion()
    cursor = conn.cursor()
    
    cursor.execute('SELECT resumen, entidades_json FROM videos_metadata WHERE video_id = ?', (video_id,))
    fila = cursor.fetchone()
    conn.close()
    
    if fila:
        try:
            entidades = json.loads(fila['entidades_json'])
        except Exception:
            entidades = []
            
        return {
            "resumen": fila['resumen'],
            "entidades": entidades
        }
    return None

# Aseguramos que se crea la DB al importar el módulo
inicializar_db()
