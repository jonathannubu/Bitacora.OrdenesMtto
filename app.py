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


def cargar_tecnicos_df():
  if os.path.exists(TECNICOS_FILE):
    df_tec = pd.read_csv(TECNICOS_FILE)
    # Asegurar que las columnas sean string puro para evitar errores de tipo
    df_tec["Tecnico"] = df_tec["Tecnico"].astype(str).str.strip()
    df_tec["Password"] = df_tec["Password"].astype(str).str.strip()
    return df_tec
  else:
    # Técnicos iniciales por defecto con sus contraseñas
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
  password = str(password).strip()

  if not nombre or not password:
    return False, "El nombre y la contraseña no pueden estar vacíos."

  if nombre in df_tec["Tecnico"].values:
    # Actualizar contraseña si ya existe
    df_tec.loc[df_tec["Tecnico"] == nombre, "Password"] = password
    mensaje = f"Contraseña actualizada para {nombre}."
  else:
    # Agregar nuevo
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


# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Bitácora de Mantenimiento", page_icon="⚙️", layout="wide"
)

st.title("⚙️ Bitácora Digital de Órdenes de Trabajo")

# Control de sesión para el Administrador
if "admin_logueado" not in st.session_state:
  st.session_state["admin_logueado"] = False

# --- MENÚ LATERAL ---
st.sidebar.image("https://img.icons8.com/color/96/maintenance.png", width=80)
st.sidebar.title("Navegación")

opciones_menu = ["Registrar Orden (Técnicos)"]

if st.session_state["admin_logueado"]:
  opciones_menu.append("📊 Resumen de Turno")
  opciones_menu.append("👥 Gestionar Técnicos")

menu = st.sidebar.selectbox("Selecciona una sección", opciones_menu)

st.sidebar.markdown("---")

# --- CONTROL DE ACCESO DE ADMINISTRADOR ---
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
  st.subheader("📝 Registro de Orden Atendida")
  st.markdown(
      "Selecciona tu nombre, ingresa tu contraseña asignada, detalla el"
      " servicio y guarda."
  )

  df_tec_system = cargar_tecnicos_df()
  lista_tecnicos_activos = ["Selecciona un técnico..."] + list(
      df_tec_system["Tecnico"]
  )

  with st.form("form_orden", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
      tecnico = st.selectbox("Técnico responsable", lista_tecnicos_activos)
      password_tecnico = st.text_input(
          "Contraseña de técnico",
          type="password",
          placeholder="Tu clave personal",
      )
      turno = st.selectbox(
          "Turno", ["Matutino", "Vespertino", "Nocturno", "Mixto"]
      )

    with col2:
      equipo = st.text_input(
          "Equipo / Máquina / Línea", placeholder="Ej. Línea de Envasado 2"
      )
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
      elif not password_tecnico:
        st.error("Debes ingresar tu contraseña de técnico para guardar.")
      elif not equipo or not descripcion:
        st.warning("Por favor completa los campos de equipo y descripción.")
      else:
        # Buscar la contraseña correcta asegurando formato string y sin espacios extra
        match = df_tec_system[df_tec_system["Tecnico"] == str(tecnico).strip()]

        if not match.empty:
          pass_correcta = str(match["Password"].values[0]).strip()
          pass_ingresada = str(password_tecnico).strip()

          if pass_ingresada == pass_correcta:
            nuevo_registro = {
                "Fecha": fecha_actual,
                "Turno": turno,
                "Tecnico": tecnico,
                "Equipo": equipo,
                "Descripcion": descripcion,
                "Minutos": minutos,
            }
            guardar_registro(nuevo_registro)
            st.success("¡Orden registrada y validada con éxito!")
          else:
            st.error(
                "Contraseña de técnico incorrecta. Verifica tu clave o"
                " contacta al administrador."
            )
        else:
          st.error("El técnico seleccionado no es válido en el sistema.")


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
  st.subheader("👥 Administración de Personal Técnico y Claves")
  st.markdown(
      "Asigna o cambia la contraseña personal de cada técnico para sus"
      " registros."
  )

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
    if st.button("Eliminar de la lista"):
      exito, msg = eliminar_tecnico(tec_a_borrar)
      if exito:
        st.success(msg)
        st.rerun()
      else:
        st.error(msg)

  st.markdown("---")
  st.markdown("#### 📋 Plantilla Actual de Personal (Vista Admin)")
  st.dataframe(df_tec_current, use_container_width=True)
