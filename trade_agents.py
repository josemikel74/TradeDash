import pandas as pd
import numpy as np
from math_engine import run_gbm_monte_carlo, calculate_garch_volatility, bayesian_update, extreme_value_theory

class AgentPlaceholder:
    def __init__(self, name):
        self.name = name

    def status(self):
        return f"✅ El agente '{self.name}' se encuentra inicializado y operando con normalidad."

class Analyst(AgentPlaceholder):
    def __init__(self):
        super().__init__("Agente Analista Cuantitativo")
        
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
    
    def generate_full_analysis(self, df_1d, df_4h, prob_res):
        """Genera un análisis completo estructurado."""
        if df_1d is None or df_1d.empty or prob_res is None:
            return None
        
        latest_1d = df_1d.iloc[-1]
        latest_4h = df_4h.iloc[-1] if (df_4h is not None and not df_4h.empty) else latest_1d
        
        trend = "Alcista" if latest_1d['SMA_20'] > latest_1d['SMA_50'] else "Bajista"
        rsi = latest_1d.get('RSI_14', 50)
        momentum = "Sobrecomprado" if rsi > 70 else ("Sobrevendido" if rsi < 30 else "Neutral")
        
        analysis = {
            "trend": trend,
            "momentum": momentum,
            "rsi_1d": rsi,
            "macd_indicator": "Positivo" if latest_1d.get('MACD', 0) > latest_1d.get('MACD_Signal', 0) else "Negativo",
            "support_level": latest_1d.get('BB_Lower', prob_res['current_price'] * 0.95),
            "resistance_level": latest_1d.get('BB_Upper', prob_res['current_price'] * 1.05),
            "volatility": prob_res['garch_vol'],
            "prob_up": prob_res['prob_up'],
            "confidence_score": 75 if prob_res['backtest'] > 60 else 50
        }
        return analysis

class DevilAdvocate(AgentPlaceholder):
    def __init__(self):
        super().__init__("Abogado del Diablo")

    def critique(self, analysis, prob_res):
        """Genera contra-argumentos estructurados al análisis principal."""
        if not analysis or not prob_res:
            return None
            
        counter_points = []
        risks = []
        
        if analysis['trend'] == "Alcista":
            counter_points.append("Riesgo de agotamiento de tendencia: La reversión a la media podría forzar una fuerte corrección bajista.")
            if analysis['momentum'] == "Sobrecomprado":
                risks.append("Extrema sobrecompra en RSI indica alta probabilidad de corrección inminente.")
        else:
            counter_points.append("Posible trampa bajista (Bear Trap): Volúmenes bajos pueden preceder un rally repentino.")
            if analysis['momentum'] == "Sobrevendido":
                risks.append("Sobrevendido, un short tardío conlleva riesgo asimétrico desfavorable.")
                
        if prob_res['garch_vol'] > 80:
            risks.append(f"Volatilidad GARCH extrema ({prob_res['garch_vol']:.1f}%). Stop losses pueden ser barridos fácilmente.")
            
        if prob_res['prob_up'] > 60:
            counter_points.append(f"Sesgo de overconfidence en Monte Carlo: La probabilidad del {prob_res['prob_up']:.1f}% asume distribuciones continuas que ignoran eventos cisne negro.")
            
        return {
            "counter_arguments": counter_points if counter_points else ["No hay contra-argumentos estructurales fuertes detectados en datos de precio, vigilar fundamentales."],
            "hidden_risks": risks if risks else ["Riesgos matemáticos bajo medias móviles estándar."],
            "confidence_penalty": len(risks) * 5
        }

class TradingAgent(AgentPlaceholder):
    def __init__(self):
        super().__init__("Agente Trading (Especialista LONG)")
        
    def generate_recommendation(self, analysis, critique, prob_res):
        """Genera recomendación EXCLUSIVAMENTE LONG basada en análisis y críticas."""
        if not analysis or not prob_res:
            return None
            
        current_price = prob_res['current_price']
        
        # Ajustar confianza
        final_confidence = max(0, analysis['confidence_score'] - critique.get('confidence_penalty', 0))
        
        # Solo LONG
        if analysis['trend'] == 'Alcista' or (analysis['trend'] == 'Bajista' and analysis['momentum'] == 'Sobrevendido'):
            if prob_res['prob_up'] > 50:
                # Sugerir LONG
                entry = current_price
                sl_distance = (current_price - analysis['support_level']) * 1.2 # Añadir buffer al soporte
                sl = current_price - sl_distance
                
                # Relación Riesgo:Recompensa 1:2
                tp = current_price + (sl_distance * 2)
                
                # Position Sizing (Max 2% riesgo asumiendo cuenta standard)
                risk_per_coin = current_price - sl
                # Asumiendo cuenta hipotética de 10k para sugerencia (simplificado)
                # En la realidad se usaría el balance real
                size_pct = 1.0 if prob_res['garch_vol'] > 60 else 2.0
                
                reason = "Convergencia de probabilidades a favor de LONG. "
                if critique['hidden_risks']:
                    reason += "Requiere precaución por riesgos detectados: " + " / ".join(critique['hidden_risks'])
                
                return {
                    "action": "LONG",
                    "entry_price": entry,
                    "stop_loss": sl,
                    "take_profit": tp,
                    "position_size_pct": size_pct,
                    "confidence": final_confidence,
                    "reason": reason
                }
                
        return {
            "action": "HOLD",
            "reason": "Condiciones insuficientes o demasiado arriesgadas para buscar entradas LONG en este momento.",
            "confidence": final_confidence
        }

class RiskManager(AgentPlaceholder):
    def __init__(self):
        super().__init__("Agente de Gestor de Riesgos")

class Executor(AgentPlaceholder):
    def __init__(self):
        super().__init__("Agente de Terminal de Ejecución")
