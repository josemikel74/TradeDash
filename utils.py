import os
import sqlite3
import logging
import ccxt
import pandas as pd
import numpy as np
from datetime import datetime
import time

# Crear directorio de datos si no existe
os.makedirs('data', exist_ok=True)

# Configuración de logs
logging.basicConfig(
    filename='data/system.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_PATH = 'data/trading.db'

def init_db():
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Tabla para logs del sistema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                level TEXT,
                message TEXT
            )
        ''')
        # Tabla para guardar indicadores
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS indicators_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                symbol TEXT,
                timeframe TEXT,
                rsi REAL,
                macd REAL,
                atr REAL
            )
        ''')
        conn.commit()
    except Exception as e:
        logger.error(f"Error inicializando BD: {e}")
    finally:
        if conn:
            conn.close()

def log_to_db(level, message, log_to_file=True):
    if log_to_file:
        lvl = getattr(logging, level.upper(), logging.INFO)
        logger.log(lvl, message)
        
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO system_logs (timestamp, level, message) VALUES (?, ?, ?)',
                       (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), level, message))
        conn.commit()
    except Exception as e:
        logger.error(f"Error escribiendo en BD: {e}")
    finally:
        if conn:
            conn.close()

def save_indicators(symbol, timeframe, row):
    """Guarda valores de indicadores clave en la DB local."""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Limpieza simple para BD
        rsi = row.get('RSI_14', 0)
        macd = row.get('MACD', 0)
        atr = row.get('ATR_14', 0)
        
        rsi = float(rsi) if not pd.isna(rsi) else 0.0
        macd = float(macd) if not pd.isna(macd) else 0.0
        atr = float(atr) if not pd.isna(atr) else 0.0
        
        cursor.execute('''
            INSERT INTO indicators_log (timestamp, symbol, timeframe, rsi, macd, atr)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), symbol, timeframe, rsi, macd, atr))
        conn.commit()
    except Exception as e:
        logger.error(f"Error guardando indicadores: {e}")
    finally:
        if conn:
            conn.close()

def fetch_data(symbol='BTC/USD', timeframe='1d', limit=250, retries=3):
    """
    Obtiene datos OHLCV de Kraken manejando errores y reintentos.
    """
    exchange = ccxt.kraken()
    for attempt in range(retries):
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            msg = f"Intento {attempt + 1} fallido al obtener datos de {symbol} ({timeframe}): {str(e)}"
            log_to_db('WARNING', msg)
            time.sleep(2)
            
    log_to_db('ERROR', f"Fallo definitivo al obtener datos de {symbol} ({timeframe}) tras {retries} intentos.")
    return None

def calc_volatility(df):
    """
    Calcula volatilidad simple (desviación estándar de los retornos).
    """
    if df is None or len(df) < 2:
        return 0.0
    returns = df['close'].pct_change().dropna()
    return returns.std() * 100
