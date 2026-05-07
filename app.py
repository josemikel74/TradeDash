import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Configuración de la página
st.set_page_config(
    page_title="TradeDash BTC/USD",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Caché de datos para evitar llamadas excesivas a la API (5 minutos)
@st.cache_data(ttl=300)
def fetch_kraken_data():
    url = "https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=1440" # 1440 min = 1 día
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if data.get('error'):
            st.error(f"Error al obtener datos de Kraken: {data['error']}")
            return None
            
        # Extraer el par de trading dinámicamente (ej. 'XXBTZUSD')
        pair_key = [k for k in data['result'].keys() if k != 'last'][0]
        raw_data = data['result'][pair_key]
        
        # Crear DataFrame
        df = pd.DataFrame(raw_data, columns=['time', 'open', 'high', 'low', 'close', 'vwap', 'volume', 'count'])
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Convertir a numérico
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
            
        return df.tail(100) # Mantener solo los últimos 100 días para el gráfico
        
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

def main():
    st.title("📈 TradeDash - BTC/USD")
    st.markdown("Visualización interactiva de BTC/USD en tiempo real usando datos de Kraken.")
    
    # Botón de refresco manual
    if st.button("🔄 Refrescar Datos"):
        fetch_kraken_data.clear()
        
    # Obtener datos
    with st.spinner("Cargando datos del mercado..."):
        df = fetch_kraken_data()
    
    if df is not None and not df.empty:
        # Cálculos para métricas
        current_price = df['close'].iloc[-1]
        prev_price = df['close'].iloc[-2]
        price_change = current_price - prev_price
        price_change_pct = (price_change / prev_price) * 100
        
        # Mostrar Métricas principales
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Precio Actual (USD)", f"${current_price:,.2f}", f"{price_change_pct:.2f}%")
        col2.metric("Máximo (24h)", f"${df['high'].iloc[-1]:,.2f}")
        col3.metric("Mínimo (24h)", f"${df['low'].iloc[-1]:,.2f}")
        col4.metric("Volumen (24h)", f"{df['volume'].iloc[-1]:,.2f} BTC")
        
        # Gráfico de velas
        st.subheader("Gráfico de Velas (Últimos 100 días)")
        
        fig = go.Figure(data=[go.Candlestick(
            x=df['time'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            increasing_line_color='#22c55e', # Verde Tailwind
            decreasing_line_color='#ef4444', # Rojo Tailwind
            name='BTC/USD'
        )])
        
        # Diseño del gráfico
        fig.update_layout(
            template='plotly_dark',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis_rangeslider_visible=False,
            margin=dict(l=0, r=0, t=30, b=0),
            height=550,
            xaxis_title="Fecha",
            yaxis_title="Precio (USD)"
        )
        
        # Renderizar gráfico en Streamlit
        st.plotly_chart(fig, use_container_width=True)
        
        st.caption(f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (Hora Local)")

if __name__ == "__main__":
    main()
