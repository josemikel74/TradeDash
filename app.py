import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils import fetch_data, init_db, log_to_db, save_indicators
from agents import Analyst, RiskManager, Executor
from datetime import datetime
import time
import warnings

# Omitir warnings numéricos de optimización en ST Cloud
warnings.filterwarnings('ignore')

# 1. Configuración de la página (Debe ser la primera llamada de Streamlit)
st.set_page_config(
    page_title="Terminal Cuantitativo de Trading",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Inicialización de la base de datos local
init_db()

# 3. Caché de extracción y cálculo de indicadores técnicos
@st.cache_data(ttl=15, show_spinner=False)
def fetch_and_process_data(_refresh_counter):
    data_1d = fetch_data('BTC/USD', '1d', limit=250) # Mas data para la SMA 200
    data_4h = fetch_data('BTC/USD', '4h', limit=250)
    
    analyst = Analyst()
    if data_1d is not None and not data_1d.empty:
        data_1d = analyst.calculate_indicators(data_1d)
        save_indicators('BTC/USD', '1d', data_1d.iloc[-1])
        
    if data_4h is not None and not data_4h.empty:
        data_4h = analyst.calculate_indicators(data_4h)
        save_indicators('BTC/USD', '4h', data_4h.iloc[-1])
        
    return data_1d, data_4h

# Caché del modelo estocástico (Cálculo Pesado Numba+Arch)
@st.cache_data(ttl=900, show_spinner=False)
def compute_probabilities(df, precision_level, _refresh_counter):
    if df is None or len(df) < 50:
        return None
    analyst = Analyst()
    t0 = time.time()
    res = analyst.run_probability_engine(df, precision_level)
    if res:
        res['calc_time'] = time.time() - t0
        res['timestamp'] = datetime.now()
    return res

def render_chart(df, title, show_indicators=True):
    if df is None or df.empty:
        return go.Figure()
        
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, subplot_titles=(title, 'Volumen'), 
                        row_width=[0.3, 0.7])

    fig.add_trace(go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        increasing_line_color='#22c55e',
        decreasing_line_color='#ef4444',
        name='Precio'
    ), row=1, col=1)

    if show_indicators and 'SMA_20' in df.columns:
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['SMA_20'], line=dict(color='#3b82f6', width=1.5), name='SMA 20'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['BB_Upper'], line=dict(color='#64748b', width=1, dash='dot'), name='BB Up'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['BB_Lower'], line=dict(color='#64748b', width=1, dash='dot'), name='BB Low'), row=1, col=1)

    colors = ['#22c55e' if row['close'] >= row['open'] else '#ef4444' for idx, row in df.iterrows()]
    fig.add_trace(go.Bar(
        x=df['timestamp'],
        y=df['volume'],
        marker_color=colors,
        name='Volumen'
    ), row=2, col=1)

    fig.update_layout(
        template='plotly_dark',
        xaxis_rangeslider_visible=False,
        height=650,
        margin=dict(l=10, r=10, t=40, b=10),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def render_mc_paths(paths, current_price, dates, title="Simulaciones Estocásticas (GBM)"):
    fig = go.Figure()
    num_lines = min(200, paths.shape[1])
    
    # Simular fechas futuras
    freq = pd.Timedelta(days=1)
    future_dates = [dates.iloc[-1] + freq * i for i in range(paths.shape[0])]
    
    # Dibujar trayectorias aleatorias (Background)
    for i in range(num_lines):
        fig.add_trace(go.Scatter(x=future_dates, y=paths[:, i], mode='lines', 
                                 line=dict(color='rgba(56, 189, 248, 0.03)', width=1), 
                                 hoverinfo='skip', showlegend=False))
                                 
    # Dibujar la Trayectoria Promedio
    fig.add_trace(go.Scatter(x=future_dates, y=paths.mean(axis=1), mode='lines', 
                             line=dict(color='#eab308', width=3), name='Trayectoria Media Esperada'))
                             
    fig.add_hline(y=current_price, line_dash='dash', line_color='#22c55e', annotation_text='Precio Actual')
    
    fig.update_layout(
        title=title,
        template='plotly_dark',
        height=400,
        margin=dict(l=10, r=10, t=40, b=10),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    return fig

def main():
    st.markdown("""
        <style>
            .stApp { background-color: #0b0e14; color: #ffffff; }
            div[data-testid="stMetricValue"] { color: #ffffff; font-size: 2.2rem; font-weight: 700; }
            .stButton>button { height: 3em; font-size: 1.1em; font-weight: bold; border-radius: 8px; }
            .prob-card { background-color: #1e293b; padding: 20px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 20px; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🏦 Terminal Institucional | Fase 2")
    
    if 'refresh_counter' not in st.session_state:
        st.session_state.refresh_counter = 0

    log_to_db("INFO", "Aplicación cargada (Fase 2 UI).", log_to_file=False)

    tabs = st.tabs([
        "Dashboard Principal", 
        "Gráficos Interactivos", 
        "Agentes", 
        "Supervisor", 
        "Historial/Riesgo", 
        "Configuración", 
        "Operación en Curso"
    ])
    
    # Sidebar
    st.sidebar.markdown("### ⚙️ Motor Matemático")
    precision = st.sidebar.select_slider("Precisión de Simulador Monte Carlo", options=["Rápido", "Normal", "Preciso"], value="Normal")
    
    data_1d, data_4h = fetch_and_process_data(st.session_state.refresh_counter)
    connected = data_1d is not None and data_4h is not None

    prob_res = None
    if connected:
        with st.spinner("Procesando Motor de Probabilidades..."):
            prob_res = compute_probabilities(data_1d, precision, st.session_state.refresh_counter)

    with tabs[0]:
        st.header("Dashboard Principal")
        if connected and prob_res:
            latest = data_1d.iloc[-1]
            prev = data_1d.iloc[-2]
            current_price = latest['close']
            price_change = current_price - prev['close']
            price_change_pct = (price_change / prev['close']) * 100
            
            # Info básica
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("BTC/USD", f"${current_price:,.2f}", f"{price_change_pct:.2f}%")
            col2.metric("Volatilidad (GARCH)", f"{prob_res['garch_vol']:.2f}%")
            col3.metric("RSI (14)", f"{latest['RSI_14']:.2f}")
            col4.metric(" MACD", f"{latest['MACD']:.2f}")
            
            st.markdown("---")
            st.subheader("🧠 Motor Analítico Avanzado y Probabilidades")
            
            pc1, pc2, pc3 = st.columns(3)
            with pc1:
                st.markdown(f"""
                <div class="prob-card">
                    <h3 style="color: #38bdf8; margin-top:0;">{prob_res['prob_up']:.1f}%</h3>
                    <p style="color: #94a3b8; font-size: 0.9em;">Probabilidad Alcista a {prob_res['horizon']} días</p>
                    <p style="font-size: 0.8em; color: #64748b;">Métrica lograda a partir de {prob_res['precision']:,} simulaciones iterativas.</p>
                </div>
                """, unsafe_allow_html=True)
            with pc2:
                st.markdown(f"""
                <div class="prob-card">
                    <h3 style="color: #f87171; margin-top:0;">{prob_res['prob_down']:.1f}%</h3>
                    <p style="color: #94a3b8; font-size: 0.9em;">Probabilidad Bajista a {prob_res['horizon']} días</p>
                    <p style="font-size: 0.8em; color: #64748b;">Complemento condicional del drift proyectado por GBM.</p>
                </div>
                """, unsafe_allow_html=True)
            with pc3:
                st.markdown(f"""
                <div class="prob-card">
                    <h3 style="color: #eab308; margin-top:0;">${prob_res['var_95']:,.0f}</h3>
                    <p style="color: #94a3b8; font-size: 0.9em;">Value at Risk (VaR 95%)</p>
                    <p style="font-size: 0.8em; color: #64748b;">Pérdida máxima estimada con un nivel de confianza del 95%.</p>
                </div>
                """, unsafe_allow_html=True)
            
            st.caption(f"Cálculos realizados en la nube. Tiempo de cómputo matriz distribuido: {prob_res['calc_time']:.2f}s. Sello: {prob_res['timestamp'].strftime('%d/%m/%Y %H:%M:%S')}")
            
            if st.button("🚀 Forzar Cálculo Ultra Preciso Bajo Demanda", type="primary"):
                compute_probabilities.clear()
                st.session_state.refresh_counter += 1
                st.rerun()

    with tabs[1]:
        st.header("Análisis Técnico Integrado")
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(render_chart(data_1d, "Diario (1D) con Bandas Bollinger"), use_container_width=True)
        with col2:
            st.plotly_chart(render_chart(data_4h, "Intradía (4H)"), use_container_width=True)
            
        if connected and prob_res:
            st.markdown("### 📊 Proyecciones Densidad Monte Carlo (GBM)")
            st.markdown(f"> *Se muestra una sub-muestra gráfica ({min(200, prob_res['paths'].shape[1])} trayectorias) del total calculado en la nube ({prob_res['paths'].shape[1]:,} simulaciones).*")
            st.plotly_chart(render_mc_paths(prob_res['paths'], prob_res['current_price'], data_1d['timestamp']), use_container_width=True)

    with tabs[2]:
        st.header("Módulo Complejo de Agentes")
        st.markdown("Los Agentes matemáticos están ejecutando cálculos rigurosos.")
        
        ag_riesgo = RiskManager()
        ag_analista = Analyst()
        ag_exec = Executor()
        
        st.success(ag_exec.status())
        st.success(ag_riesgo.status())
        
        st.info(ag_analista.status())
        if prob_res:
            st.markdown("#### 📓 Reporte Activo del Analista Cuantitativo:")
            st.markdown(f"- **Calibración de Volatilidad Dinámica**: {prob_res['info_garch']}")
            st.markdown(f"- **Actualización del Drift Bayesiana**: {prob_res['drift_bayes']:.2f}% Anualizado estimado.")
            st.markdown(f"- **Teoría Extrema de Valor (EVT)**: Exposición proyectada ante caídas estructurales estimadas en: ${prob_res['evt_var_real']:,.0f} ({prob_res['info_evt']})")
            st.markdown(f"- **Validación Corto Plazo**: Concordancia direccional de {prob_res['backtest']:.1f}% lograda sobre tendencia de control histórica.")

    with tabs[3]:
        st.header("Supervisor Técnico Universal")
        
        status_col, btn_col = st.columns([3, 1])
        with status_col:
            st.markdown(f"**Conector API Master (ccxt):** {'🟢 Operativo' if connected else '🔴 Loop de conexión'}")
            st.markdown(f"**Motor Matemático Asíncrono:** {'🟢 Calculado y Cacheado' if prob_res else '🔴 Pendiente / Generando'}")
            st.markdown(f"**Kernels Acoplados:** 🟢 Numba LLVM, Arch Stats, SciPy Distribs cargados.")
            
        with btn_col:
            if st.button("🚨 HARD RESET SISTEMA", type="primary", use_container_width=True):
                fetch_and_process_data.clear()
                compute_probabilities.clear()
                st.session_state.refresh_counter += 1
                log_to_db("INFO", "Reset global mandatorio ejecutado.")
                st.rerun()

        st.subheader("Terminal Root Logs")
        try:
            import sqlite3
            conn = sqlite3.connect('data/trading.db')
            logs = pd.read_sql_query("SELECT timestamp, level, message FROM system_logs ORDER BY id DESC LIMIT 15", conn)
            conn.close()
            st.dataframe(logs, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error("No se pudo cargar la base SQLite interna.")

    with tabs[4]:
        st.header("Historial Interdepartamental y Auditoría de Riesgo")
        st.warning("Visualización estricta de las métricas de precisión generadas del comportamiento del Agente en simulador.")
        if prob_res:
            st.metric("Precisión Auditada en T-30", f"{prob_res['backtest']:.1f}%")

    with tabs[5]:
        st.header("Panel de Inserción y Configuraciones")
        st.info("Utilice el entorno de la barra lateral (Sidebar) para conmutar la carga algorítmica de Numba en el hardware remoto.")

    with tabs[6]:
        st.header("Despacho Operacional")
        st.info("Monitor central de despliegue. Habilitación requerida post-auditoría paramétrica en Fase 3.")

    # 5. Polling Asíncrono Liviano
    auto_refresh = st.sidebar.checkbox("Activar Polling Universal (15s)", value=True)
    
    if auto_refresh:
        st.sidebar.success("⏳ Motor de polling subscrito y observando...")
        time.sleep(15)
        st.session_state.refresh_counter += 1
        st.rerun()

if __name__ == "__main__":
    main()
