# 🚀 Comandos de Arranque del Proyecto (BPI)

Para que la aplicación funcione completa, necesitas tener **dos terminales** abiertas simultáneamente: una para el Backend (Python/FastAPI) y otra para el Frontend (Vite/React).

---

## 1️⃣ Terminal 1: Backend (FastAPI / Python)

Esta terminal ejecuta el servidor que procesa las búsquedas y devuelve los datos.

**Pasos:**
1. Abre una terminal en la raíz de tu proyecto (`C:\Users\Usuario\Documents\Proyectos\practicas Emilio\BPI`).
2. Activa el entorno virtual de Python (si no lo tienes activo ya):
   ```powershell
   .venv\Scripts\activate
   ```
3. Arranca el servidor FastAPI:
   ```powershell
   uvicorn src.api.main:app --reload
   ```

*(El servidor de backend estará corriendo en `http://127.0.0.1:8000`)*

---

## 2️⃣ Terminal 2: Frontend (Vite / React)

Esta terminal ejecuta la interfaz visual (la web) con la que interactúa el usuario final.

**Pasos:**
1. Abre **otra** terminal nueva.
2. Navega hacia la carpeta del frontend:
   ```powershell
   cd frontend
   ```
3. *(Opcional)* Si es la primera vez que abres el proyecto o alguien ha añadido librerías nuevas, instala las dependencias:
   ```powershell
   npm install
   ```
4. Arranca el servidor de React con Vite:
   ```powershell
   npm run dev
   ```

*(La página web estará disponible normalmente en `http://localhost:5173`)*

---

### 💡 Resumen rápido (Para copiar y pegar)

**Terminal 1 (Backend - en carpeta `BPI`):**
```powershell
.venv\Scripts\activate
uvicorn src.api.main:app --reload
```

**Terminal 2 (Frontend - en carpeta `BPI\frontend`):**
```powershell
npm run dev
```
