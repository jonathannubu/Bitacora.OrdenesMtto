from datetime import datetime
import os
import pandas as pd
import streamlit as st

# Archivos de datos locales/en la nube
DATA_FILE = "bitacora_mantenimiento.csv"
TECNICOS_FILE = "tecnicos_activos.csv"


# --- FUNCIONES DE DATOS ---
def cargar_datos():
  if os.path.exists(DATA_FILE):
    return pd.read_csv(DATA_FILE)
  else:
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


def guardar_registro(nuevo_dato):
  df = cargar_datos()
  df = pd.concat([df, pd.DataFrame([nuevo_dato])], ignore_index=True)
  df.to_csv(DATA_FILE, index=False)


def cargar_tecnicos():
  if os.path.exists(TECNICOS_FILE):
    df_tec = pd.read_csv(TECNICOS_FILE)
    return df_tec["Tecnico"].tolist()
  else:
    # Técnicos iniciales por defecto si no existe el archivo
    iniciales = ["Técnico 1", "Técnico 2", "Especialista en Automatización"]
    df_tec = pd.DataFrame({"Tecnico": iniciales})
    df_tec.to_csv(TECNICOS_FILE, index=False)
    return iniciales


def agregar_tecnico(nuevo_nombre):
  lista = cargar_tecnicos()
  if nuevo_nombre not in lista and nuevo_nombre.strip() != "":
    lista.append(nuevo_nombre.strip())
    pd.DataFrame({"Tecnico": lista}).to_csv(TECNICOS_FILE, index=False)
    return True
  return False


def eliminar_tecnico(nombre_a_borrar):
  lista = cargar_tecnicos()
  if nombre_a_borrar in lista:
    lista.remove(nombre_a_borrar)
    pd.DataFrame({"Tecnico": lista}).to_csv(TECNICOS_FILE, index=False)
    return True
  return False


# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Bitácora de Mantenimiento", page_icon="⚙️", layout="wide"
)

st.title("⚙️ Bitácora Digital de Órdenes de Trabajo")

# Control de sesión para el Administrador
if "admin_logueado" not in st.session_state:
  st.session_state["admin_logueado"] = False

# --- MENÚ LATERAL ---
st.sidebar.image(
    "https://img.icons8.com/color/96/maintenance.png", width=80
)  # Ícono decorativo
st.sidebar.title("Navegación")

# Opciones base para cualquier usuario
opciones_menu = ["Registrar Orden (Técnicos)"]

# Si el admin está logueado, agregamos sus opciones exclusivas
if st.session_state["admin_logueado"]:
  opciones_menu.append("📊 Resumen de Turno")
  opciones_menu.append("👥 Gestionar Técnicos")

menu = st.sidebar.selectbox("Selecciona una sección", opciones_menu)

st.sidebar.markdown("---")

# --- CONTROL DE ACCESO DE ADMINISTRADOR EN EL SIDEBAR ---
if not st.session_state["admin_logueado"]:
  with st.sidebar.expander("🔐 Acceso Administrador"):
    pass_ingresada = st.text_input("Contraseña", type="password")
    if st.button("Iniciar Sesión"):
      if pass_ingresada == "avangardmtto22":
        st.session_state["admin_logueado"] = True
        st.success("¡Bienvenido, Administrador!")
        st.rerun()
      else:
        st.error("Contraseña incorrecta.")
else:
  st.sidebar.success("Modo Administrador Activo")
  if st.sidebar.button("Cerrar Sesión Admin"):
    st.session_state["admin_logueado"] = False
    st.rerun()

st.sidebar.markdown("---")


# ---------------------------------------------------------
# VISTA 1: REGISTRO DE ÓRDENES (Para técnicos desde cualquier cel)
# ---------------------------------------------------------
if menu == "Registrar Orden (Técnicos)":
  st.subheader("📝 Registro de Orden Atendida")
  st.markdown(
      "Selecciona tu nombre, indica el equipo y detalla el servicio realizado."
  )

  lista_tecnicos_activos = ["Selecciona un técnico..."] + cargar_tecnicos()

  with st.form("form_orden", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
      tecnico = st.selectbox("Técnico responsable", lista_tecnicos_activos)
      turno = st.selectbox(
          "Turno", ["Matutino", "Vespertino", "Nocturno", "Mixto"]
      )
      equipo = st.text_input(
          "Equipo / Máquina / Línea", placeholder="Ej. Línea de Envasado 2"
      )

    with col2:
      minutos = st.number_input(
          "Tiempo invertido (minutos)", min_value=1, max_value=720, value=30
      )
      fecha_actual = datetime.now().strftime("%Y-%m-%d")
      st.info(f"📅 Fecha de registro: {fecha_actual}")

    descripcion = st.text_area(
        "Descripción del trabajo realizado",
        placeholder=(
            "Ej. Ajuste de sensor óptico, revisión de variador y cambio de"
            " banda..."
        ),
    )

    submitted = st.form_submit_button("Guardar Orden")

    if submitted:
      if tecnico == "Selecciona un técnico...":
        st.error("Por favor selecciona tu nombre de la lista.")
      elif not equipo or not descripcion:
        st.warning(
            "Por favor completa los campos de equipo y descripción del"
            " trabajo."
        )
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
        st.success(
            "¡Orden registrada con éxito! Ya quedó guardada en el sistema."
        )


# ---------------------------------------------------------
# VISTA 2: RESUMEN DE TURNO (Exclusivo Administrador)
# ---------------------------------------------------------
elif menu == "📊 Resumen de Turno" and st.session_state["admin_logueado"]:
  st.subheader("📊 Resumen y Cierre de Turno")

  df = cargar_datos()

  if df.empty:
    st.info("Aún no hay registros guardados en la bitácora.")
  else:
    col1, col2 = st.columns(2)
    with col1:
      fechas_disponibles = sorted(df["Fecha"].unique(), reverse=True)
      fecha_filtro = st.selectbox("Filtrar por Fecha", fechas_disponibles)
    with col2:
      turnos_disponibles = ["Todos"] + list(df["Turno"].unique())
      turno_filtro = st.selectbox("Filtrar por Turno", turnos_disponibles)

    df_filtrado = df[df["Fecha"] == fecha_filtro]
    if turno_filtro != "Todos":
      df_filtrado = df_filtrado[df_filtrado["Turno"] == turno_filtro]

    st.markdown("---")

    if df_filtrado.empty:
      st.warning("No hay registros para los filtros seleccionados.")
    else:
      total_ordenes = len(df_filtrado)
      tiempo_total = df_filtrado["Minutos"].sum()
      horas_totales = round(tiempo_total / 60, 2)

      m1, m2, m3 = st.columns(3)
      m1.metric(label="Total Órdenes Atendidas", value=total_ordenes)
      m2.metric(label="Tiempo Total (Min)", value=f"{tiempo_total} min")
      m3.metric(label="Tiempo Total (Horas)", value=f"{horas_totales} hrs")

      st.markdown("### Desglose por Técnico en este Turno")
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

      st.markdown("### Detalle Completo de Órdenes")
      st.dataframe(df_filtrado, use_container_width=True)

      csv = df_filtrado.to_csv(index=False).encode("utf-8")
      st.download_button(
          label="📥 Descargar reporte de este turno (CSV)",
          data=csv,
          file_name=f"reporte_turno_{fecha_filtro}.csv",
          mime="text/csv",
      )


# ---------------------------------------------------------
# VISTA 3: GESTIÓN DE TÉCNICOS (Exclusivo Administrador)
# ---------------------------------------------------------
elif menu == "👥 Gestionar Técnicos" and st.session_state["admin_logueado"]:
  st.subheader("👥 Administración de Personal Técnico")
  st.markdown(
      "Agrega nuevos técnicos o da de baja a personal sin necesidad de tocar"
      " código."
  )

  col_add, col_del = st.columns(2)

  with col_add:
    st.markdown("#### ➕ Agregar Nuevo Técnico")
    nuevo_nombre_tec = st.text_input(
        "Nombre completo del técnico", placeholder="Ej. Carlos Mendoza"
    )
    if st.button("Registrar Técnico"):
      if agregar_tecnico(nuevo_nombre_tec):
        st.success(
            f"¡Técnico '{nuevo_nombre_tec}' agregado a la lista exitosamente!"
        )
        st.rerun()
      else:
        st.warning(
            "Escribe un nombre válido o el técnico ya existe en la lista."
        )

  with col_del:
    st.markdown("#### 🗑️ Eliminar Técnico")
    tecnicos_actuales = cargar_tecnicos()
    tec_a_borrar = st.selectbox(
        "Selecciona el técnico a remover", tecnicos_actuales
    )
    if st.button("Eliminar de la lista"):
      if len(tecnicos_actuales) > 1:
        eliminar_tecnico(tec_a_borrar)
        st.success(f"Técnico '{tec_a_borrar}' eliminado correctamente.")
        st.rerun()
      else:
        st.error("Debes mantener al menos un técnico registrado.")

  st.markdown("---")
  st.markdown("#### 📋 Plantilla Actual de Técnicos Registrados")
  df_tec_view = pd.DataFrame({"Nombre del Técnico": cargar_tecnicos()})
  st.dataframe(df_tec_view, use_container_width=True)
