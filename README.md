# TradeDash - BTC/USD

Esta es una versión en **Python (Streamlit)** del proyecto TradeDash original en React. 
Te permite visualizar el histórico reciente (100 días) y precio actual en tiempo real de Bitcoin usando la API oficial de Kraken.

## Instrucciones para GitHub y Ejecución Local

Para ejecutar esta aplicación como un dashboard de Streamlit en tu máquina local o hacer deploy (por ejemplo, en Streamlit Community Cloud), sigue estos pasos:

### 1. Clonar el repositorio
Si ya lo exportaste a Github, haz clone en tu máquina:
```bash
git clone <URL_DE_TU_REPOSITORIO>
cd <DIRECTORIO_DEL_REPOSITORIO>
```

### 2. Configurar el entorno virtual (Recomendado)
```bash
python -m venv venv
# Activar en Windows
venv\Scripts\activate
# Activar en macOS/Linux
source venv/bin/activate
```

### 3. Instalar las dependencias
Instala los paquetes de `requirements.txt`:
```bash
pip install -r requirements.txt
```

### 4. Ejecutar la aplicación
Ejecuta el script de Streamlit para arrancar tu servidor local:
```bash
streamlit run app.py
```

Se abrirá automáticamente una pestaña en tu navegador con la dirección `http://localhost:8501`.
