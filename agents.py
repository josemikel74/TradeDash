import pandas as pd
import numpy as np
from math_engine import run_gbm_monte_carlo, calculate_garch_volatility, bayesian_update, extreme_value_theory

class AgentPlaceholder:
    def __init__(self, name):
        self.name = name

    def status(self):
        return f"✅ El agente '{self.name}' se encuentra inicializado y a la espera de instrucciones."

class Analyst(AgentPlaceholder):
    def __init__(self):
        super().__init__("Analista Cuantitativo de Mercado")
        
    def calculate_indicators(self, df):
        """Calcula una suite rigurosa de indicadores técnicos y los añade al dataframe."""
        if df is None or df.empty:
            return df
        
        # Copiamos para evitar SettingWithCopyWarning
        df = df.copy()
        
        # SMA (Simple Moving Average)
        df['SMA_20'] = df['close'].rolling(window=20).mean()
        df['SMA_50'] = df['close'].rolling(window=50).mean()
        df['SMA_200'] = df['close'].rolling(window=200).mean()
        
        # EMA (Exponential Moving Average)
        df['EMA_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['EMA_26'] = df['close'].ewm(span=26, adjust=False).mean()
        
        # MACD
        df['MACD'] = df['EMA_12'] - df['EMA_26']
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI_14'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        df['BB_Middle'] = df['SMA_20']
        std = df['close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + 2 * std
        df['BB_Lower'] = df['BB_Middle'] - 2 * std
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['ATR_14'] = true_range.rolling(14).mean()
        
        # OBV (On Balance Volume)
        df['OBV'] = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()
        
        return df

    def run_probability_engine(self, df, precision_level="Normal"):
        """Inicia el motor de probabilidades matemáticas estocásticas."""
        if df is None or len(df) < 50:
            return None
            
        config = {
            "Rápido": {"paths": 5000, "horizon": 7},
            "Normal": {"paths": 15000, "horizon": 14},
            "Preciso": {"paths": 30000, "horizon": 30}
        }
        cfg = config.get(precision_level, config["Normal"])
        
        returns = df['close'].pct_change().dropna()
        current_price = df['close'].iloc[-1]
        
        # 1. Ajuste Volatilidad GARCH(1,1)
        garch_vol, garch_info = calculate_garch_volatility(returns)
        annual_vol = garch_vol * np.sqrt(365)
        
        # 2. Inferencia Bayesiana para el Drift
        historical_mu = returns.mean()
        posterior_mu = bayesian_update(historical_mu, returns.std()**2, returns[-30:])
        annual_mu = posterior_mu * 365
        
        # 3. Monte Carlo GBM
        paths = run_gbm_monte_carlo(current_price, posterior_mu, garch_vol, cfg['horizon'], cfg['horizon'], cfg['paths'])
        
        # 4. Métricas de Riesgo Predictivas
        final_prices = paths[-1, :]
        prob_up = np.mean(final_prices > current_price) * 100
        prob_down = 100.0 - prob_up
        
        var_95 = np.percentile(final_prices, 5)
        cvar_95 = np.mean(final_prices[final_prices <= var_95])
        
        # 5. Modelado EVT (Extreme Value Theory)
        evt_var, evt_info = extreme_value_theory(returns)
        
        # Backtest Básico: Match direccional en los últimos 30 días
        trend_match = (returns[-30:] > 0).mean() * 100
        backtest_accuracy = trend_match if trend_match > 45 else 100 - trend_match
        
        return {
            "paths": paths,
            "prob_up": prob_up,
            "prob_down": prob_down,
            "var_95": current_price - var_95,
            "cvar_95": current_price - cvar_95,
            "evt_var_real": current_price * evt_var,
            "garch_vol": annual_vol * 100,
            "drift_bayes": annual_mu * 100,
            "horizon": cfg['horizon'],
            "precision": cfg['paths'],
            "current_price": current_price,
            "info_garch": garch_info,
            "info_evt": evt_info,
            "backtest": backtest_accuracy
        }

class RiskManager(AgentPlaceholder):
    def __init__(self):
        super().__init__("Gestor de Riesgo y Capital")

class Executor(AgentPlaceholder):
    def __init__(self):
        super().__init__("Ejecutor de Órdenes")
