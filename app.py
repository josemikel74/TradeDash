import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils import fetch_data, init_db, log_to_db, calc_volatility
from datetime import datetime
import time

# 1. Configuración de la página (Debe ser la primera llamada de Streamlit)
st.set_page_config(
    page_title="Terminal de Trading Analítico",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Inicialización de la base de datos (se crea carpeta data/ si no existe)
init_db()

# 3. Caché de datos para limitar llamadas a la API
@st.cache_data(ttl=15, show_spinner=False)
def fetch_market_data(_refresh_counter):
    data_1d = fetch_data('BTC/USD', '1d', limit=100)
    data_4h = fetch_data('BTC/USD', '4h', limit=100)
    return data_1d, data_4h

def render_chart(df, title):
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
        height=600,
        margin=dict(l=10, r=10, t=40, b=10),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    return fig

def main():
    # Estilos CSS tipo Bloomberg
    st.markdown("""
        <style>
            .stApp { background-color: #0b0e14; color: #ffffff; }
            /* Tarjetas de métricas */
            div[data-testid="stMetricValue"] {
                color: #ffffff;
                font-size: 2.2rem;
                font-weight: 700;
            }
            .stButton>button {
                height: 3em;
                font-size: 1.1em;
                font-weight: bold;
                border-radius: 8px;
            }
        </style>
    """, unsafe_allow_html=True)

    st.title("🏦 Terminal de Trading | Fase 1")
    
    if 'refresh_counter' not in st.session_state:
        st.session_state.refresh_counter = 0

    log_to_db("INFO", "Aplicación iniciada o recargada en interfaz.", log_to_file=False)

    # 4. Pestañas Requeridas Exactas
    tabs = st.tabs([
        "Dashboard Principal", 
        "Gráficos Interactivos", 
        "Agentes", 
        "Supervisor", 
        "Historial/Riesgo", 
        "Configuración", 
        "Operación en Curso"
    ])

    data_1d, data_4h = fetch_market_data(st.session_state.refresh_counter)
    connected = data_1d is not None and data_4h is not None

    with tabs[0]:
        st.header("Dashboard Principal")
        if connected:
            latest = data_1d.iloc[-1]
            prev = data_1d.iloc[-2]
            current_price = latest['close']
            price_change = current_price - prev['close']
            price_change_pct = (price_change / prev['close']) * 100
            
            # Aproximar volumen de 24h
            if data_4h is not None and len(data_4h) >= 6:
                vol_24h = data_4h['volume'].tail(6).sum()
            else:
                vol_24h = latest['volume']
                
            volatility = calc_volatility(data_1d)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("BTC/USD", f"${current_price:,.2f}", f"{price_change_pct:.2f}%")
            col2.metric("Volumen (24h)", f"{vol_24h:,.2f} BTC")
            col3.metric("Volatilidad (1D)", f"{volatility:.2f}%")
            col4.metric("Conexión Market Data", "🟢 Estable", "OK", delta_color="off")
            
            st.caption(f"Última actualización de datos: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        else:
            st.error("Error al conectar con la API de precios (Kraken).")
            col1, col2 = st.columns(2)
            col1.metric("Conexión Market Data", "🔴 Caída", "-100%", delta_color="inverse")

    with tabs[1]:
        st.header("Análisis Técnico y Gráficos")
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(render_chart(data_1d, "Diario (1D)"), use_container_width=True)
        with col2:
            st.plotly_chart(render_chart(data_4h, "Intradía (4H)"), use_container_width=True)
            
        if st.button("🔄 Actualizar Gráficos Manualmente"):
            st.session_state.refresh_counter += 1
            log_to_db("INFO", "Actualización manual de gráficos solicitada por usuario.")
            st.rerun()

    with tabs[2]:
        st.header("Módulo de Agentes")
        st.markdown("Los Agentes de inteligencia artificial se activarán en las fases posteriores.")
        import agents
        ag_riesgo = agents.RiskManager()
        ag_analista = agents.Analyst()
        ag_exec = agents.Executor()
        st.success(ag_riesgo.status())
        st.success(ag_analista.status())
        st.success(ag_exec.status())

    with tabs[3]:
        st.header("Supervisor y Estado del Sistema")
        
        status_col, btn_col = st.columns([3, 1])
        with status_col:
            st.markdown(f"**Estado del Exchange (ccxt):** {'🟢 Operativo' if connected else '🔴 Error de Conexión'}")
            st.markdown(f"**Sistema de Base de Datos SQLite:** 🟢 Activo en `data/trading.db`")
            st.markdown(f"**Última verificación interna:** {datetime.now().strftime('%H:%M:%S')}")
            
        with btn_col:
            if st.button("🚨 REFRESH SISTEMA", type="primary", use_container_width=True):
                st.session_state.refresh_counter += 1
                log_to_db("INFO", "Refresh maestro ejecutado desde el Dashboard Supervisor.")
                st.rerun()

        st.subheader("Logs Recientes del Sistema")
        try:
            import sqlite3
            conn = sqlite3.connect('data/trading.db')
            logs = pd.read_sql_query("SELECT timestamp, level, message FROM system_logs ORDER BY id DESC LIMIT 10", conn)
            conn.close()
            st.dataframe(logs, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error("No se pudo cargar la base de datos de logs locales.")

    with tabs[4]:
        st.header("Historial y Gestión de Riesgo")
        st.warning("Pestaña reservada para visualización de operaciones pasadas y cálculo de métricas de riesgo (Drawdown, Sharpe Ratio).")

    with tabs[5]:
        st.header("Configuración de Entorno")
        st.info("Espacio para introducir claves de la API del Exchange, límites de Stop Loss global y variables de entorno.")

    with tabs[6]:
        st.header("Operación en Curso")
        st.info("Monitor en tiempo real de operaciones abiertas administradas por el Agente Executor.")

    # 5. Polling de autoliquidación / refresco (15s)
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Control de Datos")
    auto_refresh = st.sidebar.checkbox("Activar Polling (15s)", value=False)
    
    if auto_refresh:
        st.sidebar.success("⏳ Polling activo. Esperando 15s...")
        # Simula un auto-refresh simple. En producción requiere configuraciones específicas de frontend.
        time.sleep(15)
        st.session_state.refresh_counter += 1
        st.rerun()

if __name__ == "__main__":
    main()
