import streamlit as st
import pandas as pd
from datetime import datetime

# Configuración de la página
st.set_page_config(
    page_title="Control de Mantenimiento - Avangard Labs",
    page_icon="⚙️",
    layout="wide"
)

# Título principal
st.title("⚙️ Sistema de Registro y Control de Mantenimiento")
st.markdown("---")

# Simulación de datos o carga inicial (ajusta esto según tu estructura de DataFrame real)
if "df_ordenes" not in st.session_state:
    st.session_state.df_ordenes = pd.DataFrame([
        {
            "ID": 101,
            "Equipo": "Línea de Envasado 1",
            "Responsable": "Carlos Pérez",
            "Estado": "Completado",
            "Fecha": "2026-07-20"
        },
        {
            "ID": 102,
            "Equipo": "Banda Transportadora B",
            "Responsable": "Ana Gómez",
            "Estado": "En Proceso",
            "Fecha": "2026-07-22"
        },
        {
            "ID": 103,
            "Equipo": "Compresor Principal",
            "Responsable": "Luis Martínez",
            "Estado": "Pendiente",
            "Fecha": "2026-07-23"
        }
    ])

df_filtrado = st.session_state.df_ordenes

# ==========================================
# SECCIÓN: DETALLE DE ÓRDENES Y DESCARGA EN PDF
# ==========================================
st.subheader("📋 Detalle de Órdenes y Descarga Individual en PDF")

# Definición de colores para los estados
colores_estado = {
    "Completado": "#28a745",   # Verde
    "En Proceso": "#ffc107",   # Amarillo / Naranja
    "Pendiente": "#dc3545",    # Rojo
    "Cancelado": "#6c757d"     # Gris
}

if df_filtrado.empty:
    st.info("No hay órdenes registradas para mostrar.")
else:
    for index, row in df_filtrado.iterrows():
        estado_actual = row.get("Estado", "Pendiente")
        color_linea = colores_estado.get(estado_actual, "#007bff")
        
        # Contenedor individual con la línea lateral de color para el estado
        st.markdown(
            f"""
            <div style="
                border-left: 5px solid {color_linea}; 
                padding: 10px 15px; 
                margin-bottom: 10px; 
                background-color: #f8f9fa; 
                border-radius: 4px;
            ">
                <strong>Orden #{row.get('ID', index)}</strong> - <span>Estado: <b>{estado_actual}</b></span><br>
                <small>Equipo: {row.get('Equipo', 'N/A')} | Responsable: {row.get('Responsable', 'N/A')} | Fecha: {row.get('Fecha', 'N/A')}</small>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # Botón para la descarga individual en PDF de esta orden
        col_det1, col_det2 = st.columns([4, 1])
        with col_det2:
            if st.button(f"📥 PDF #{row.get('ID', index)}", key=f"pdf_{index}"):
                # Aquí puedes integrar tu lógica de generación de PDF individual
                st.success(f"Generando PDF de la orden #{row.get('ID', index)}...")

st.markdown("---")
st.caption("Avangard Labs - Sistema de Control de Turnos y Mantenimiento")
