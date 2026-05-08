import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import io
from trade_utils import fetch_data, init_db, log_to_db, save_indicators, save_recommendation, update_recommendation_status, open_operation, get_active_operation, close_operation, save_learning_metrics, get_latest_learning_metrics, update_stop_loss
from trade_agents import Analyst, RiskManager, Executor, DevilAdvocate, TradingAgent
from datetime import datetime
import time
import warnings
import sqlite3

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
        
        # Guardar metricas de aprendizaje
        try:
            metrics = analyst.run_learning_cycle(df, res)
            if metrics:
                save_learning_metrics(metrics['brier_score'], metrics['calibration_error'], metrics['optimal_lookback'], metrics['optimal_vol_threshold'])
        except Exception as e:
            pass # Falla silenciosa si DB aun no lista
            
    return res

def get_excel_download(df_dict):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in df_dict.items():
            df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()

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

    st.title("🏦 Terminal Institucional | Fase 3")
    
    if 'refresh_counter' not in st.session_state:
        st.session_state.refresh_counter = 0

    log_to_db("INFO", "Aplicación cargada.", log_to_file=False)

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
        
        analyst = Analyst()
        devil = DevilAdvocate()
        trader = TradingAgent()
        
        if not connected or not prob_res:
            st.warning("⚠️ Esperando datos del mercado y motor de probabilidades para inicializar el análisis heurístico.")
        else:
            analysis = analyst.generate_full_analysis(data_1d, data_4h, prob_res)
            critique = devil.critique(analysis, prob_res)
            recommendation = trader.generate_recommendation(analysis, critique, prob_res)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader(f"🧠 {analyst.name}")
                st.info(f"Tendencia: **{analysis['trend']}** | Momentum: **{analysis['momentum']}**")
                st.markdown(f"- Confianza Base: {analysis['confidence_score']}%")
                st.markdown(f"- Soporte Clave: ${analysis['support_level']:,.2f}")
                st.markdown(f"- Resistencia Clave: ${analysis['resistance_level']:,.2f}")
                st.markdown(f"- Señal MACD: {analysis['macd_indicator']}")
                st.markdown(f"- RSI(1d): {analysis['rsi_1d']:.1f}")

            with col2:
                st.subheader(f"👿 {devil.name}")
                st.error("Riesgos y Contra-argumentos Activos:")
                for c in critique['counter_arguments']:
                    st.markdown(f"- ⚠️ {c}")
                for r in critique['hidden_risks']:
                    st.markdown(f"- ❗ **CRÍTICO:** {r}")

            st.markdown("---")
            st.subheader(f"🎯 {trader.name}")
            
            active_op = get_active_operation()
            
            if active_op:
                st.info(f"Hay una operación en curso actualmente. Finaliza la operación antes de aplicar nuevas recomendaciones. Visite la pestaña de 'Operación en Curso'.")
            elif recommendation['action'] == 'LONG':
                st.success(f"**Recomendación:** {recommendation['action']} | **Confianza Final:** {recommendation['confidence']}%")
                st.markdown(f"**Razón:** {recommendation['reason']}")
                
                # Resumen de orden
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Precio de Entrada", f"${recommendation['entry_price']:,.2f}")
                c2.metric("Stop Loss Recomendado", f"${recommendation['stop_loss']:,.2f}")
                c3.metric("Take Profit", f"${recommendation['take_profit']:,.2f}")
                c4.metric("Tamaño (Riesgo)", f"{recommendation['position_size_pct']:.1f}%")
                
                colA, colB = st.columns(2)
                with colA:
                    if st.button("✅ Aprobar e Iniciar Operación LONG Simulada", type="primary", use_container_width=True):
                        # Guardar rec y operación
                        rec_id = save_recommendation("BTC/USD", recommendation['entry_price'], recommendation['stop_loss'], recommendation['take_profit'], recommendation['position_size_pct'], recommendation['confidence'], recommendation['reason'])
                        update_recommendation_status(rec_id, 'ACCEPTED')
                        open_operation(rec_id, "BTC/USD", recommendation['entry_price'], recommendation['stop_loss'], recommendation['take_profit'], recommendation['position_size_pct'])
                        log_to_db("INFO", f"Operación LONG Aprobada y abierta en DB.")
                        st.session_state.refresh_counter += 1
                        st.rerun()
                with colB:
                    if st.button("❌ Rechazar Sugerencia", type="secondary", use_container_width=True):
                        rec_id = save_recommendation("BTC/USD", recommendation['entry_price'], recommendation['stop_loss'], recommendation['take_profit'], recommendation['position_size_pct'], recommendation['confidence'], recommendation['reason'])
                        update_recommendation_status(rec_id, 'REJECTED')
                        log_to_db("INFO", "Recomendación rechazada por el usuario.")
                        st.warning("Recomendación denegada. Guardada en el historial de entrenamiento.")
            else:
                st.warning(f"**Recomendación:** {recommendation['action']}")
                st.markdown(f"**Razón:** {recommendation['reason']}")

    with tabs[3]:
        st.header("Supervisor Técnico Universal")
        
        status_col, btn_col = st.columns([3, 1])
        with status_col:
            st.markdown(f"**Conector API Master (ccxt):** {'🟢 Operativo' if connected else '🔴 Error Crítico de Conexión'}")
            st.markdown(f"**Motor Matemático Asíncrono:** {'🟢 En Caché' if prob_res else '🔴 Fallido / No Listo'}")
            st.markdown(f"**Enjambre de Agentes:** {'🟢 Activos y Sincronizados' if connected else '🔴 En Espera'}")
            
        with btn_col:
            if st.button("🚨 REFRESH TOTAL SISTEMA", type="primary", use_container_width=True):
                fetch_and_process_data.clear()
                compute_probabilities.clear()
                st.session_state.refresh_counter += 1
                log_to_db("INFO", "Refresh TOTAL mandatorio ejecutado.")
                st.rerun()

        st.subheader("Estado de Auto-Aprendizaje (Laboratorio Vivo)")
        lm = get_latest_learning_metrics()
        if lm:
            m1, m2, m3, m4 = st.columns(4)
            brier_val = lm.get('brier_score')
            cal_err_val = lm.get('calibration_error')
            look_val = lm.get('optimal_lookback')
            vol_val = lm.get('optimal_vol_threshold')
            
            brier_str = f"{brier_val:.4f}" if brier_val is not None else "N/A"
            cal_err_str = f"{cal_err_val:.4f}" if cal_err_val is not None else "N/A"
            look_str = f"{look_val}d" if look_val is not None else "N/A"
            vol_str = f"{vol_val:.1f}%" if vol_val is not None else "N/A"
            
            m1.metric("Brier Score", brier_str, help="0 = Perfecto, 1 = Error Total")
            m2.metric("Error de Calibración", cal_err_str)
            m3.metric("Lookback Óptimo", look_str)
            m4.metric("Umbral GARCH", vol_str)
            
            if brier_val is not None and brier_val > 0.4:
                st.warning("⚠️ Precisión predictiva degradada recientemente. Reconsidera las operaciones algorítmicas.")
        
        st.subheader("Terminal Root Logs")
        
        log_col, clear_col = st.columns([4, 1])
        with clear_col:
            if st.button("Limpiar Logs", use_container_width=True):
                conn = sqlite3.connect('data/trading.db')
                conn.execute("DELETE FROM system_logs")
                conn.commit()
                conn.close()
                st.rerun()
                
        try:
            conn = sqlite3.connect('data/trading.db')
            # Fetch all for filtering
            logs_df = pd.read_sql_query("SELECT timestamp, level, message FROM system_logs ORDER BY id DESC LIMIT 100", conn)
            conn.close()
            
            filter_level = st.selectbox("Filtrar por nivel:", ["TODOS", "INFO", "WARNING", "ERROR"])
            if filter_level != "TODOS":
                logs_df = logs_df[logs_df['level'] == filter_level]
                
            st.dataframe(
                logs_df, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "level": st.column_config.TextColumn(
                        "Nivel",
                        help="Nivel de severidad"
                    )
                }
            )
        except Exception as e:
            st.error("No se pudo cargar la base SQLite interna.")

    with tabs[4]:
        st.header("Historial Interdepartamental y Auditoría de Riesgo")
        
        try:
            conn = sqlite3.connect('data/trading.db')
            ops = pd.read_sql_query("SELECT id, symbol, status, entry_price, close_price, pnl, timestamp, close_time FROM operations WHERE status != 'OPEN' ORDER BY id ASC", conn)
            recs = pd.read_sql_query("SELECT id, timestamp, status, action, confidence, reason FROM recommendations ORDER BY id DESC LIMIT 50", conn)
            all_ops = pd.read_sql_query("SELECT * FROM operations ORDER BY id DESC", conn)
            conn.close()
            
            # Botones de exportación
            colA, colB = st.columns(2)
            with colA:
                excel_data = get_excel_download({"Operaciones": all_ops, "Recomendaciones": recs})
                st.download_button(
                    label="📊 Exportar Historial a Excel (.xlsx)",
                    data=excel_data,
                    file_name="historial_trading.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            # Cálculo de Métricas Clave
            # Solo consideramos ops cerradas para métricas
            if not ops.empty:
                st.subheader("Métricas de Rendimiento (Cerradas)")
                win_trades = ops[ops['pnl'] > 0]
                loss_trades = ops[ops['pnl'] <= 0]
                
                win_rate = len(win_trades) / len(ops) * 100 if len(ops) > 0 else 0
                gross_profit = win_trades['pnl'].sum() if not win_trades.empty else 0
                gross_loss = abs(loss_trades['pnl'].sum()) if not loss_trades.empty else 0
                profit_factor = gross_profit / gross_loss if gross_loss > 0 else (999.0 if gross_profit > 0 else 0)
                
                avg_win = win_trades['pnl'].mean() if not win_trades.empty else 0
                avg_loss = abs(loss_trades['pnl'].mean()) if not loss_trades.empty else 0
                expectancy = (win_rate/100 * avg_win) - ((1 - win_rate/100) * avg_loss)
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Win Rate", f"{win_rate:.1f}%", help="Porcentaje de operaciones rentables")
                c2.metric("Profit Factor", f"{profit_factor:.2f}", help="Ganancia bruta / Pérdida bruta")
                c3.metric("Expectancy", f"${expectancy:.2f}", help="Retorno promedio esperado por operación")
                c4.metric("PnL Total", f"${ops['pnl'].sum():,.2f}")
                
                # Equity Curve
                ops['cum_pnl'] = ops['pnl'].cumsum()
                fig_eq = go.Figure()
                fig_eq.add_trace(go.Scatter(x=ops['close_time'], y=ops['cum_pnl'], mode='lines+markers', line=dict(color='#22c55e' if ops['pnl'].sum()>=0 else '#ef4444', width=2), name='Cumulative PnL'))
                fig_eq.update_layout(title="Equity Curve", template="plotly_dark", height=350, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig_eq, use_container_width=True)
                
            st.subheader("Todas las Operaciones")
            if not all_ops.empty:
                st.dataframe(all_ops, use_container_width=True, hide_index=True)
            else:
                st.info("No hay historial de operaciones registradas aún.")
                
            st.divider()    
            st.subheader("Registro de Decisiones Estocásticas (Aprendizaje)")
            if not recs.empty:
                st.dataframe(recs, use_container_width=True, hide_index=True)
                
        except Exception as e:
            st.error(f"Error procesando historial: {e}")

    with tabs[5]:
        st.header("Panel de Configuración de Sistema")
        st.info("Utilice el entorno de la barra lateral (Sidebar) para conmutar la precisión del Motor Monte Carlo y el polling.")
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Gestión de Riesgo Avanzada")
            st.slider("Riesgo Máximo por Operación (%)", 0.5, 5.0, 2.0, 0.5)
            st.slider("Umbral Mínimo de Confianza GARCH (%)", 50, 95, 70, 5)
            st.checkbox("Activar auto-ajuste de hiperparámetros (Laboratorio Vivo)", value=True)
            
        with c2:
            st.subheader("Mantenimiento de Datos")
            
            with open('data/trading.db', 'rb') as f:
                st.download_button(
                    label="💾 Descargar Backup Completo de Base de Datos (SQLite)",
                    data=f,
                    file_name="trading_backup.db",
                    mime="application/x-sqlite3",
                    use_container_width=True
                )
                
            st.markdown("⚠️ *Advertencia: La restauración debe ser ejecutada vía administrador.*")
            
            if st.button("Limpiar Caché del Motor de Probabilidades", use_container_width=True):
                compute_probabilities.clear()
                fetch_and_process_data.clear()
                st.success("Caché limpiada. Se recalcularán todos los vectores en el próximo ciclo.")

    with tabs[6]:
        st.header("Despacho Operacional")
        
        active_op = get_active_operation()
        if active_op and connected:
            current_price = data_1d.iloc[-1]['close']
            c1, c2, c3 = st.columns(3)
            c1.metric("Precio de Entrada", f"${active_op['entry_price']:,.2f}")
            c2.metric("Precio Actual", f"${current_price:,.2f}", f"{(current_price - active_op['entry_price']) / active_op['entry_price'] * 100:.2f}%")
            
            c3.metric("Take Profit Estático", f"${active_op['take_profit']:,.2f}", f"{(active_op['take_profit'] - current_price) / current_price * 100:.2f}% a la meta", delta_color="off")
            
            st.markdown("---")
            col_a, col_b = st.columns(2)
            with col_a:
                st.warning(f"**Ubicación de Stop Loss Crítico:** ${active_op['current_stop_loss']:,.2f}")
                dist_sl_pct = (current_price - active_op['current_stop_loss']) / current_price * 100
                st.markdown(f"*Distancia hasta el SL: **{dist_sl_pct:.2f}%***")
                
                new_sl = st.number_input("Actualizar Stop Loss (Trailing SL)", value=active_op['current_stop_loss'], step=100.0)
                if st.button("Actualizar SL en BBDD"):
                    update_stop_loss(active_op['id'], new_sl)
                    st.success("Stop Loss actualizado.")
                    st.rerun()
                
                # Manejo simple de SL y TP
                if current_price <= active_op['current_stop_loss']:
                    st.error("🚨 CRÍTICO: El precio cruzó el nivel de Stop Loss. Operación liquidada preventivamente.")
                    close_operation(active_op['id'], current_price, 'STOP_LOSS_HIT')
                    st.rerun()
                elif current_price >= active_op['take_profit']:
                    st.success("🎯 OBJETIVO ALCANZADO: El precio tocó el Take Profit. Operación finalizada exitosamente.")
                    close_operation(active_op['id'], current_price, 'TAKE_PROFIT_HIT')
                    st.rerun()

            with col_b:
                st.info(f"**Probabilidad Estimada de Éxito Actualizada:** {prob_res['prob_up']:.1f}%")
                pnl_actual = (current_price - active_op['entry_price']) / active_op['entry_price'] * 100
                st.metric("PnL Flotante Aprox.", f"{pnl_actual:.2f}%")
                if st.button("Cerrar Operación Manualmente AHORA", type="primary"):
                    close_operation(active_op['id'], current_price, 'MANUAL_CLOSE')
                    log_to_db("INFO", "Operación cerrada manualmente por el usuario desde la terminal.")
                    st.session_state.refresh_counter += 1
                    st.success("Cerrada con éxito, resultados traspasados a métricas de Historial.")
                    st.rerun()
        else:
            st.info("🔴 No existe ninguna posición viva en curso. Dirigirse al Módulo de Agentes para observar señales activas.")

    # 5. Polling Asíncrono Liviano
    auto_refresh = st.sidebar.checkbox("Activar Polling Universal (15s)", value=True)
    
    if auto_refresh:
        st.sidebar.success("⏳ Motor de polling subscrito y observando...")
        time.sleep(15)
        st.session_state.refresh_counter += 1
        st.rerun()

if __name__ == "__main__":
    main()
