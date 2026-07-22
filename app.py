from datetime import datetime
import os
import pandas as pd
import streamlit as st

# Archivo local donde se guardarán los datos de forma persistente
DATA_FILE = "bitacora_mantenimiento.csv"


# Función para cargar datos
def cargar_datos():
  if os.path.exists(DATA_FILE):
    return pd.read_csv(DATA_FILE)
  else:
    # Si no existe, creamos la estructura base
    return pd.DataFrame(
        columns=[
            "Fecha",
            "Turno",
            "Tecnico",
            "Equipo",
            "Descripcion",
            "Minutos",
        ]
    )


# Guardar datos
def guardar_registro(nuevo_dato):
  df = cargar_datos()
  df = pd.concat([df, pd.DataFrame([nuevo_dato])], ignore_index=True)
  df.to_csv(DATA_FILE, index=False)


# Configuración de la página
st.set_page_config(
    page_title="Bitácora de Mantenimiento", page_icon="⚙️", layout="wide"
)

st.title("⚙️ Bitácora Digital de Órdenes de Trabajo")
st.markdown("---")

# Menú lateral para navegar entre vistas
menu = st.sidebar.selectbox(
    "Selecciona una vista", ["Registrar Orden (Técnicos)", "Resumen de Turno"]
)

# ---------------------------------------------------------
# VISTA 1: REGISTRO DE ÓRDENES
# ---------------------------------------------------------
if menu == "Registrar Orden (Técnicos)":
  st.subheader("📝 Registro de Orden Atendida")

  # Lista de técnicos de tu equipo (puedes modificarla o cargarla dinámicamente)
  lista_tecnicos = [
      "Selecciona un técnico...",
      "Técnico 1",
      "Técnico 2",
      "Técnico 3",
      "Especialista en Automatización",
  ]

  with st.form("form_orden", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
      tecnico = st.selectbox("Técnico responsable", lista_tecnicos)
      turno = st.selectbox(
          "Turno", ["Matutino", "Vespertino", "Nocturno"]
      )
      equipo = st.text_input(
          "Equipo / Máquina / Línea", placeholder="Ej. Línea de Envasado 2"
      )

    with col2:
      minutos = st.number_input(
          "Tiempo invertido (minutos)", min_value=1, max_value=480, value=30
      )
      fecha_actual = datetime.now().strftime("%Y-%m-%d")
      st.info(f"Fecha de registro: {fecha_actual}")

    descripcion = st.text_area(
        "Descripción del trabajo realizado",
        placeholder="Ej. Ajuste de sensor óptico y cambio de banda...",
    )

    submitted = st.form_submit_button("Guardar Orden")

    if submitted:
      if tecnico == "Selecciona un técnico...":
        st.error("Por favor selecciona el nombre del técnico.")
      elif not equipo or not descripcion:
        st.warning("Por favor completa los campos de equipo y descripción.")
      else:
        nuevo_registro = {
            "Fecha": fecha_actual,
            "Turno": turno,
            "Tecnico": tecnico,
            "Equipo": equipo,
            "Descripcion": descripcion,
            "Minutos": minutos,
        }
        guardar_registro(nuevo_registro)
        st.success("¡Orden registrada correctamente!")

# ---------------------------------------------------------
# VISTA 2: RESUMEN DE TURNO (COORDINACIÓN)
# ---------------------------------------------------------
elif menu == "Resumen de Turno":
  st.subheader("📊 Resumen y Cierre de Turno")

  df = cargar_datos()

  if df.empty:
    st.info("Aún no hay registros guardados en la bitácora.")
  else:
    # Filtros de búsqueda
    col1, col2 = st.columns(2)
    with col1:
      fechas_disponibles = df["Fecha"].unique()
      fecha_filtro = st.selectbox("Filtrar por Fecha", fechas_disponibles)
    with col2:
      turnos_disponibles = ["Todos"] + list(df["Turno"].unique())
      turno_filtro = st.selectbox("Filtrar por Turno", turnos_disponibles)

    # Aplicar filtros
    df_filtrado = df[df["Fecha"] == fecha_filtro]
    if turno_filtro != "Todos":
      df_filtrado = df_filtrado[df_filtrado["Turno"] == turno_filtro]

    st.markdown("---")

    if df_filtrado.empty:
      st.warning("No hay registros para los filtros seleccionados.")
    else:
      # Métricas principales
      total_ordenes = len(df_filtrado)
      tiempo_total = df_filtrado["Minutos"].sum()
      horas_totales = round(tiempo_total / 60, 2)

      m1, m2, m3 = st.metrics = st.columns(3)
      st.metric(label="Total Órdenes Atendidas", value=total_ordenes)
      st.metric(label="Tiempo Total Invertido (Min)", value=f"{tiempo_total} min")
      st.metric(
          label="Tiempo Total Invertido (Horas)", value=f"{horas_totales} hrs"
      )

      st.markdown("### Desglose por Técnico")
      # Agrupar por técnico para ver qué atendió cada uno y cuánto tardó
      resumen_tecnicos = (
          df_filtrado.groupby("Tecnico")
          .agg(
              Ordenes_Atendidas=("Equipo", "count"),
              Minutos_Totales=("Minutos", "sum"),
          )
          .reset_index()
      )
      resumen_tecnicos["Horas_Invertidas"] = round(
          resumen_tecnicos["Minutos_Totales"] / 60, 2
      )
      st.dataframe(resumen_tecnicos, use_container_width=True)

      st.markdown("### Detalle Completo de Órdenes del Turno")
      st.dataframe(df_filtrado, use_container_width=True)

      # Botón para descargar el reporte en CSV
      csv = df_filtrado.to_csv(index=False).encode("utf-8")
      st.download_button(
          label="Descargar reporte de este turno (CSV)",
          data=csv,
          file_name=f"reporte_turno_{fecha_filtro}.csv",
          mime="text/csv",
      )