from datetime import datetime
import os
import pandas as pd
import streamlit as st

# Archivos de datos
DATA_FILE = "bitacora_mantenimiento.csv"
TECNICOS_FILE = "tecnicos_activos.csv"
AREAS_FILE = "areas_activas.csv"


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
            "Area",
            "Equipo",
            "NumOrden",
            "TipoMantenimiento",
            "HoraRecepcion",
            "HoraCierre",
            "Minutos",
            "Descripcion",
        ]
    )


def guardar_registro(nuevo_dato):
  df = cargar_datos()
  df = pd.concat([df, pd.DataFrame([nuevo_dato])], ignore_index=True)
  df.to_csv(DATA_FILE, index=False)


# Gestión de Técnicos
def cargar_tecnicos_df():
  if os.path.exists(TECNICOS_FILE):
    df_tec = pd.read_csv(TECNICOS_FILE, dtype=str)
    df_tec["Tecnico"] = df_tec["Tecnico"].fillna("").astype(str).str.strip()
    df_tec["Password"] = df_tec["Password"].fillna("").astype(str).str.strip()
    df_tec["Password"] = df_tec["Password"].str.replace(r"\.0$", "", regex=True)
    return df_tec
  else:
    df_tec = pd.DataFrame({
        "Tecnico": [
            "Técnico 1",
            "Técnico 2",
            "Especialista en Automatización",
        ],
        "Password": ["1234", "5678", "9999"],
    })
    df_tec.to_csv(TECNICOS_FILE, index=False)
    return df_tec


def agregar_o_actualizar_tecnico(nombre, password):
  df_tec = cargar_tecnicos_df()
  nombre = str(nombre).strip()
  password = str(password).strip().replace(".0", "")

  if not nombre or not password:
    return False, "El nombre y la contraseña no pueden estar vacíos."

  if nombre in df_tec["Tecnico"].values:
    df_tec.loc[df_tec["Tecnico"] == nombre, "Password"] = password
    mensaje = f"Contraseña actualizada para {nombre}."
  else:
    nuevo_row = pd.DataFrame({"Tecnico": [nombre], "Password": [password]})
    df_tec = pd.concat([df_tec, nuevo_row], ignore_index=True)
    mensaje = f"Técnico {nombre} agregado exitosamente."

  df_tec.to_csv(TECNICOS_FILE, index=False)
  return True, mensaje


def eliminar_tecnico(nombre_a_borrar):
  df_tec = cargar_tecnicos_df()
  if len(df_tec) <= 1:
    return False, "Debes mantener al menos un técnico registrado."
  df_tec = df_tec[df_tec["Tecnico"] != str(nombre_a_borrar).strip()]
  df_tec.to_csv(TECNICOS_FILE, index=False)
  return True, "Técnico eliminado correctamente."


# Gestión de Áreas
def cargar_areas():
  if os.path.exists(AREAS_FILE):
    df_area = pd.read_csv(AREAS_FILE, dtype=str)
    return df_area["Area"].fillna("").astype(str).str.strip().tolist()
  else:
    # Áreas iniciales por defecto
    areas_iniciales = [
        "Nave 1 - Envasado",
        "Nave 2 - Producción",
        "Nave 3 - Empaque",
        "Nave 4 - Mantenimiento General",
    ]
    df_area = pd.DataFrame({"Area": areas_iniciales})
    df_area.to_csv(AREAS_FILE, index=False)
    return areas_iniciales


def agregar_area(nueva_area):
  areas = cargar_areas()
  nueva_area = str(nueva_area).strip()
  if not nueva_area:
    return False, "El nombre del área no puede estar vacío."
  if nueva_area in areas:
    return False, "Esta área ya existe en el sistema."

  areas.append(nueva_area)
  pd.DataFrame({"Area": areas}).to_csv(AREAS_FILE, index=False)
  return True, f"Área '{nueva_area}' agregada exitosamente."


def eliminar_area(area_a_borrar):
  areas = cargar_areas()
  if len(areas) <= 1:
    return False, "Debes mantener al menos un área registrada."
  if area_a_borrar in areas:
    areas.remove(area_a_borrar)
    pd.DataFrame({"Area": areas}).to_csv(AREAS_FILE, index=False)
    return True, "Área eliminada correctamente."
  return False, "El área seleccionada no existe."


# --- VENTANA EMERGENTE (MODAL) PARA CONTRASEÑA DE TÉCNICO ---
@st.dialog("🔒 Validación de Identidad del Técnico")
def modal_password_tecnico(datos_orden):
  st.write(f"Técnico seleccionado: **{datos_orden['Tecnico']}**")
  st.write(
      "Ingresa tu contraseña personal para confirmar y guardar la orden de"
      " trabajo:"
  )

  pass_ingresada = st.text_input(
      "Contraseña de técnico", type="password", key="modal_pass_input"
  )

  col1, col2 = st.columns(2)
  with col1:
    if st.button("Confirmar y Guardar", use_container_width=True):
      df_tec_system = cargar_tecnicos_df()
      match = df_tec_system[
          df_tec_system["Tecnico"] == str(datos_orden["Tecnico"]).strip()
      ]

      if not match.empty:
        pass_correcta = str(match["Password"].values[0]).strip()
        pass_ingresada_clean = str(pass_ingresada).strip().replace(".0", "")

        if pass_ingresada_clean == pass_correcta:
          guardar_registro(datos_orden)
          st.success("¡Orden registrada y validada con éxito!")
          del st.session_state["temp_orden"]
          st.rerun()
        else:
          st.error("Contraseña incorrecta.")
      else:
        st.error("Error en el técnico seleccionado.")

  with col2:
    if st.button("Cancelar", use_container_width=True):
      st.rerun()


# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Bitácora de Mantenimiento", page_icon="⚙️", layout="wide"
)

st.title("⚙️ Bitácora Digital de Órdenes de Trabajo")

if "admin_logueado" not in st.session_state:
  st.session_state["admin_logueado"] = False

# --- MENÚ LATERAL ---
st.sidebar.image("https://img.icons8.com/color/96/maintenance.png", width=80)
st.sidebar.title("Navegación")

opciones_menu = ["Registrar Orden (Técnicos)"]
if st.session_state["admin_logueado"]:
  opciones_menu.append("📊 Resumen de Turno")
  opciones_menu.append("👥 Gestionar Personal y Áreas")

menu = st.sidebar.selectbox("Selecciona una sección", opciones_menu)
st.sidebar.markdown("---")

if not st.session_state["admin_logueado"]:
  with st.sidebar.expander("🔐 Acceso Administrador"):
    pass_ingresada = st.text_input("Contraseña", type="password")
    if st.button("Iniciar Sesión"):
      if str(pass_ingresada).strip() == "avangardmtto22":
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
# VISTA 1: REGISTRO DE ÓRDENES
# ---------------------------------------------------------
if menu == "Registrar Orden (Técnicos)":
  st.subheader("📝 Registro de Orden de Trabajo")
  st.markdown("Completa los datos de la intervención realizada.")

  df_tec_system = cargar_tecnicos_df()
  lista_tecnicos_activos = ["Selecciona un técnico..."] + list(
      df_tec_system["Tecnico"]
  )
  lista_areas_activas = ["Selecciona un área..."] + cargar_areas()

  with st.form("form_orden"):
    col1, col2 = st.columns(2)

    with col1:
      tecnico = st.selectbox("Técnico responsable", lista_tecnicos_activos)
      area = st.selectbox("Área", lista_areas_activas)
      equipo = st.text_input(
          "Equipo intervenido", placeholder="Ej. Banda Transportadora 3"
      )
      num_orden = st.text_input("Número de Orden (OT)", placeholder="Ej. OT-8492")

    with col2:
      tipo_mtto = st.selectbox(
          "Clasificación de la OT",
          ["Correctivo", "Ajuste", "Configuración de línea"],
      )
      turno = st.selectbox(
          "Turno", ["Matutino", "Vespertino", "Nocturno", "Mixto"]
      )

      h_col1, h_col2 = st.columns(2)
      with h_col1:
        hora_recepcion = st.time_input(
            "Hora Recepción OT", value=datetime.now().time()
        )
      with h_col2:
        hora_cierre = st.time_input(
            "Hora Cierre OT", value=datetime.now().time()
        )

      fecha_actual = datetime.now().strftime("%Y-%m-%d")

    descripcion = st.text_area(
        "Descripción del trabajo realizado",
        placeholder=(
            "Ej. Reemplazo de sensor fotoeléctrico desalineado y ajuste de"
            " parámetros..."
        ),
    )

    submitted = st.form_submit_button("Guardar Orden")

    if submitted:
      if tecnico == "Selecciona un técnico...":
        st.error("Por favor selecciona tu nombre de la lista.")
      elif area == "Selecciona un área...":
        st.error("Por favor selecciona el área correspondiente.")
      elif not equipo or not num_orden or not descripcion:
        st.warning(
            "Por favor completa todos los campos obligatorios (Equipo, Núm. de"
            " Orden y Descripción)."
        )
      else:
        dt_recepcion = datetime.combine(datetime.today(), hora_recepcion)
        dt_cierre = datetime.combine(datetime.today(), hora_cierre)

        if dt_cierre < dt_recepcion:
          from datetime import timedelta

          dt_cierre += timedelta(days=1)

        diferencia_minutos = int(
            (dt_cierre - dt_recepcion).total_seconds() / 60
        )
        if diferencia_minutos < 0:
          diferencia_minutos = 0

        st.session_state["temp_orden"] = {
            "Fecha": fecha_actual,
            "Turno": turno,
            "Tecnico": tecnico,
            "Area": area,
            "Equipo": equipo,
            "NumOrden": num_orden,
            "TipoMantenimiento": tipo_mtto,
            "HoraRecepcion": hora_recepcion.strftime("%H:%M"),
            "HoraCierre": hora_cierre.strftime("%H:%M"),
            "Minutos": diferencia_minutos,
            "Descripcion": descripcion,
        }
        st.rerun()

  if "temp_orden" in st.session_state:
    modal_password_tecnico(st.session_state["temp_orden"])


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
      m2.metric(label="Tiempo Total Invertido (Min)", value=f"{tiempo_total} min")
      m3.metric(
          label="Tiempo Total Invertido (Horas)", value=f"{horas_totales} hrs"
      )

      st.markdown("### Desglose por Técnico en este Turno")
      resumen_tecnicos = (
          df_filtrado.groupby("Tecnico")
          .agg(
              Ordenes_Atendidas=("NumOrden", "count"),
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

      csv = df_filtrado.to_csv(index=False).encode("utf-8")
      st.download_button(
          label="📥 Descargar reporte de este turno (CSV)",
          data=csv,
          file_name=f"reporte_turno_{fecha_filtro}.csv",
          mime="text/csv",
      )


# ---------------------------------------------------------
# VISTA 3: GESTIÓN DE PERSONAL Y ÁREAS (Exclusivo Administrador)
# ---------------------------------------------------------
elif menu == "👥 Gestionar Personal y Áreas" and st.session_state["admin_logueado"]:
  st.subheader("👥 Administración de Personal y Áreas de Planta")
  st.markdown(
      "Gestiona los técnicos con sus contraseñas y las áreas o naves de la"
      " planta."
  )

  tab1, tab2 = st.tabs(["🔧 Gestionar Técnicos", "🏭 Gestionar Áreas"])

  # --- TAB 1: TÉCNICOS ---
  with tab1:
    col_add, col_del = st.columns(2)

    with col_add:
      st.markdown("#### ➕ Registrar o Actualizar Técnico")
      nombre_tec = st.text_input(
          "Nombre del técnico", placeholder="Ej. Carlos Mendoza"
      )
      pass_tec = st.text_input(
          "Contraseña asignada",
          type="password",
          placeholder="Clave de 4 dígitos o texto",
          key="pass_tec_input",
      )
      if st.button("Guardar Técnico"):
        exito, msg = agregar_o_actualizar_tecnico(nombre_tec, pass_tec)
        if exito:
          st.success(msg)
          st.rerun()
        else:
          st.error(msg)

    with col_del:
      st.markdown("#### 🗑️ Eliminar Técnico")
      df_tec_current = cargar_tecnicos_df()
      tec_a_borrar = st.selectbox(
          "Selecciona el técnico a remover", df_tec_current["Tecnico"]
      )
      if st.button("Eliminar Técnico"):
        exito, msg = eliminar_tecnico(tec_a_borrar)
        if exito:
          st.success(msg)
          st.rerun()
        else:
          st.error(msg)

    st.markdown("---")
    st.markdown("#### 📋 Plantilla Actual de Personal")
    st.dataframe(df_tec_current, use_container_width=True)

  # --- TAB 2: ÁREAS ---
  with tab2:
    col_area_add, col_area_del = st.columns(2)

    with col_area_add:
      st.markdown("#### ➕ Registrar Nueva Área")
      nueva_area_input = st.text_input(
          "Nombre del Área o Nave",
          placeholder="Ej. Nave 5 - Ensamble o Línea de Pintura",
      )
      if st.button("Guardar Área"):
        exito, msg = agregar_area(nueva_area_input)
        if exito:
          st.success(msg)
          st.rerun()
        else:
          st.error(msg)

    with col_area_del:
      st.markdown("#### 🗑️ Eliminar Área")
      areas_current = cargar_areas()
      area_a_borrar = st.selectbox(
          "Selecciona el área a remover", areas_current
      )
      if st.button("Eliminar Área"):
        exito, msg = eliminar_area(area_a_borrar)
        if exito:
          st.success(msg)
          st.rerun()
        else:
          st.error(msg)

    st.markdown("---")
    st.markdown("#### 🏭 Áreas Registradas Actualmente")
    df_areas_view = pd.DataFrame({"Áreas / Naves": cargar_areas()})
    st.dataframe(df_areas_view, use_container_width=True)
