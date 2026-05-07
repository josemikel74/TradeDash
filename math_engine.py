import numpy as np
from numba import njit, prange
import logging

logger = logging.getLogger(__name__)

@njit(parallel=True)
def run_gbm_monte_carlo(S0, mu, sigma, T, N, M):
    """
    Simulación Monte Carlo ultra rápida usando Geometric Brownian Motion y Numba.
    """
    dt = T / N
    paths = np.zeros((N + 1, M))
    paths[0] = S0
    for t in range(1, N + 1):
        Z = np.random.standard_normal(M)
        for i in prange(M):
            paths[t, i] = paths[t - 1, i] * np.exp((mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * Z[i])
    return paths

def calculate_garch_volatility(returns):
    try:
        import arch
        rescaled_returns = returns * 100
        am = arch.arch_model(rescaled_returns, vol='Garch', p=1, q=1, rescale=False)
        res = am.fit(disp='off')
        forecasts = res.forecast(horizon=1)
        next_vol_daily = np.sqrt(forecasts.variance.iloc[-1, 0]) / 100
        return next_vol_daily, "Modelo GARCH(1,1) ajustado"
    except Exception as e:
        logger.error(f"GARCH Error: {e}")
        return returns.std(), "GARCH Fallback (Desviación Típica)"

def bayesian_update(prior_mu, prior_sigma2, data):
    n = len(data)
    data_mean = np.mean(data)
    data_var = np.var(data) if n > 1 else prior_sigma2
    if prior_sigma2 + data_var/n == 0:
        return data_mean
    post_mu = (prior_sigma2 * data_mean + data_var * prior_mu) / (prior_sigma2 + data_var/n)
    return post_mu

def extreme_value_theory(returns):
    try:
        from scipy.stats import genextreme
        neg_returns = -returns[returns < 0]
        if len(neg_returns) < 10:
            return 0.0, "Muestra insuficiente"
        c, loc, scale = genextreme.fit(neg_returns)
        var_99 = genextreme.ppf(0.99, c, loc=loc, scale=scale)
        return var_99, "Modelado EVT de Colas (99%)"
    except Exception as e:
        logger.error(f"EVT Error: {e}")
        return returns.quantile(0.01) if not returns.empty else 0, "EVT Fallback"
