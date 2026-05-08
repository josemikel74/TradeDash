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
        # Tabla para recomendaciones del AgenteTrading
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                symbol TEXT,
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,
                position_size REAL,
                confidence REAL,
                reason TEXT,
                status TEXT
            )
        ''')
        # Tabla para operaciones en curso e historial
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rec_id INTEGER,
                timestamp TEXT,
                symbol TEXT,
                entry_price REAL,
                current_stop_loss REAL,
                take_profit REAL,
                position_size REAL,
                status TEXT,
                close_price REAL,
                close_time TEXT,
                pnl REAL,
                FOREIGN KEY(rec_id) REFERENCES recommendations(id)
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

def save_recommendation(symbol, entry, sl, tp, size, confidence, reason):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO recommendations (timestamp, symbol, entry_price, stop_loss, take_profit, position_size, confidence, reason, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
    ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), symbol, entry, sl, tp, size, float(confidence), reason))
    rec_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return rec_id

def update_recommendation_status(rec_id, status):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE recommendations SET status = ? WHERE id = ?', (status, rec_id))
    conn.commit()
    conn.close()

def open_operation(rec_id, symbol, entry, sl, tp, size):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO operations (rec_id, timestamp, symbol, entry_price, current_stop_loss, take_profit, position_size, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN')
    ''', (rec_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), symbol, entry, sl, tp, size))
    conn.commit()
    conn.close()

def get_active_operation():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM operations WHERE status = 'OPEN' ORDER BY id DESC LIMIT 1", conn)
    conn.close()
    if not df.empty:
        return df.iloc[0].to_dict()
    return None

def close_operation(op_id, close_price, reason):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT entry_price, position_size FROM operations WHERE id = ?', (op_id,))
    row = cursor.fetchone()
    if row:
        pnl = (close_price - row[0]) * row[1]
        cursor.execute('''
            UPDATE operations 
            SET status = ?, close_price = ?, close_time = ?, pnl = ? 
            WHERE id = ?
        ''', (reason, close_price, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pnl, op_id))
    conn.commit()
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
