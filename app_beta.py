from datetime import datetime, timedelta
import os
import pandas as pd
import streamlit as st

# Archivos de datos
DATA_FILE = "bitacora_mantenimiento.csv"
TECNICOS_FILE = "tecnicos_activos.csv"
AREAS_FILE = "areas_activas.csv"
DEPARTAMENTOS_FILE = "departamentos_solicitantes.csv"

COLUMNAS_OFICIALES = [
    "Fecha",
    "Turno",
    "Tecnico",
    "Area",
    "DepartamentoSolicitante",
    "Equipo",
    "NumOrden",
    "TipoMantenimiento",
    "HoraEmision",
    "HoraRecepcion",
    "HoraCierre",
    "HoraConformidad",
    "MinutosEspera",
    "MinutosTrabajo",
    "MinutosTotalOT",
    "Descripcion",
]


# --- FUNCIONES DE DATOS ---
def cargar_datos():
  if os.path.exists(DATA_FILE):
    try:
      df = pd.read_csv(DATA_FILE)
      if "Linea" in df.columns and "Area" not in df.columns:
        df = df.rename(columns={"Linea": "Area"})
      if "Minutos" in df.columns and "MinutosTrabajo" not in df.columns:
        df = df.rename(columns={"Minutos": "MinutosTrabajo"})
      for col in COLUMNAS_OFICIALES:
        if col not in df.columns:
          df[col] = ""
      return df[COLUMNAS_OFICIALES]
    except Exception:
      return pd.DataFrame(columns=COLUMNAS_OFICIALES)
  else:
    return pd.DataFrame(columns=COLUMNAS_OFICIALES)


def generar_siguiente_num_orden():
  df = cargar_datos()
  if df.empty or "NumOrden" not in df.columns:
    return "000001"

  numeros = []
  for val in df["NumOrden"].dropna():
    val_str = str(val).strip()
    digitos = "".join(filter(str.isdigit, val_str))
    if digitos.isdigit():
      numeros.append(int(digitos))

  if not numeros:
    return "000001"

  siguiente_num = max(numeros) + 1
  return f"{siguiente_num:06d}"


def guardar_registro(nuevo_dato):
  df = cargar_datos()
  df = pd.concat([df, pd.DataFrame([nuevo_dato])], ignore_index=True)
  df.to_csv(DATA_FILE, index=False)


def eliminar_orden(index_a_borrar):
  df = cargar_datos()
  if 0 <= index_a_borrar < len(df):
    df = df.drop(index_a_borrar).reset_index(drop=True)
    df.to_csv(DATA_FILE, index=False)
    return True, "Orden eliminada exitosamente."
  return False, "Índice de orden inválido."


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


# Gestión de Departamentos Solicitantes
def cargar_departamentos_df():
  if os.path.exists(DEPARTAMENTOS_FILE):
    df_dep = pd.read_csv(DEPARTAMENTOS_FILE, dtype=str)
    df_dep["Departamento"] = (
        df_dep["Departamento"].fillna("").astype(str).str.strip()
    )
    df_dep["Password"] = df_dep["Password"].fillna("").astype(str).str.strip()
    df_dep["Password"] = df_dep["Password"].str.replace(r"\.0$", "", regex=True)
    return df_dep
  else:
    df_dep = pd.DataFrame({
        "Departamento": ["Producción", "Calidad", "Almacén", "Empaques"],
        "Password": ["prod123", "cal123", "alm123", "emp123"],
    })
    df_dep.to_csv(DEPARTAMENTOS_FILE, index=False)
    return df_dep


def agregar_o_actualizar_departamento(nombre_dep, password):
  df_dep = cargar_departamentos_df()
  nombre_dep = str(nombre_dep).strip()
  password = str(password).strip().replace(".0", "")

  if not nombre_dep or not password:
    return False, "El departamento y la contraseña no pueden estar vacíos."

  if nombre_dep in df_dep["Departamento"].values:
    df_dep.loc[df_dep["Departamento"] == nombre_dep, "Password"] = password
    mensaje = f"Contraseña actualizada para el departamento {nombre_dep}."
  else:
    nuevo_row = pd.DataFrame(
        {"Departamento": [nombre_dep], "Password": [password]}
    )
    df_dep = pd.concat([df_dep, nuevo_row], ignore_index=True)
    mensaje = f"Departamento {nombre_dep} agregado exitosamente."

  df_dep.to_csv(DEPARTAMENTOS_FILE, index=False)
  return True, mensaje


def eliminar_departamento(dep_a_borrar):
  df_dep = cargar_departamentos_df()
  if len(df_dep) <= 1:
    return False, "Debes mantener al menos un departamento registrado."
  df_dep = df_dep[df_dep["Departamento"] != str(dep_a_borrar).strip()]
  df_dep.to_csv(DEPARTAMENTOS_FILE, index=False)
  return True, "Departamento eliminado correctamente."


# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Bitácora de Mantenimiento", page_icon="⚙️", layout="wide"
)

if "admin_logueado" not in st.session_state:
  st.session_state["admin_logueado"] = False

if "hora_inicial_default" not in st.session_state:
  st.session_state["hora_inicial_default"] = datetime.now().strftime("%H:%M")

st.title("⚙️ Bitácora Digital de Órdenes de Trabajo")

# --- MENÚ LATERAL ---
st.sidebar.image("https://img.icons8.com/color/96/maintenance.png", width=80)
st.sidebar.title("Navegación")

opciones_menu = ["Registrar Orden (Técnicos)", "📊 Resumen de Turno"]

if st.session_state["admin_logueado"]:
  opciones_menu.append("👥 Gestionar Personal, Áreas y Deptos")

menu = st.sidebar.selectbox("Selecciona una sección", opciones_menu)
st.sidebar.markdown("---")

if not st.session_state["admin_logueado"]:
  with st.sidebar.expander("🔐 Acceso Administrador"):
    pass_ingresada = st.text_input(
        "Contraseña Admin", type="password", key="pass_admin_login"
    )
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

  df_dep_system = cargar_departamentos_df()
  lista_departamentos = ["Selecciona un departamento..."] + list(
      df_dep_system["Departamento"]
  )

  h_ref = st.session_state["hora_inicial_default"]
  siguiente_ot = generar_siguiente_num_orden()
  st.info(f"📌 Se asignará automáticamente el número de orden: **{siguiente_ot}**")

  with st.form("form_orden"):
    col1, col2 = st.columns(2)

    with col1:
      tecnico = st.selectbox("Técnico responsable", lista_tecnicos_activos)
      area = st.selectbox("Área de la Planta", lista_areas_activas)
      departamento_solicitante = st.selectbox(
          "Departamento Solicitante (OT)", lista_departamentos
      )
      equipo = st.text_input(
          "Equipo intervenido", placeholder="Ej. Banda Transportadora 3"
      )
      tipo_mtto = st.selectbox(
          "Clasificación de la OT",
          ["Correctivo", "Ajuste", "Configuración de línea"],
      )

    with col2:
      turno = st.selectbox(
          "Turno", ["Matutino", "Vespertino", "Nocturno", "Mixto"]
      )
      fecha_actual = datetime.now().strftime("%Y-%m-%d")

      st.markdown(
          "⏱️ **Control de Horarios** *(Teclea rápido, formato HH:MM)*"
      )
      t1, t2, t3, t4 = st.columns(4)
      with t1:
        h_emision = st.text_input("Emisión", value=h_ref)
      with t2:
        h_recepcion = st.text_input("Recepción", value=h_ref)
      with t3:
        h_cierre = st.text_input("Cierre", value=h_ref)
      with t4:
        h_conformidad = st.text_input("Conformidad", value=h_ref)

    descripcion = st.text_area(
        "Descripción del trabajo realizado",
        placeholder=(
            "Ej. Reemplazo de sensor fotoeléctrico desalineado y ajuste de"
            " parámetros..."
        ),
    )

    st.markdown("---")
    st.markdown(
        "🔐 **Validación de Identidad y Solicitud:** Ingresa tu contraseña de"
        " técnico y la clave del departamento solicitante."
    )
    f_col1, f_col2 = st.columns(2)

    with f_col1:
      pass_tecnico = st.text_input(
          "Contraseña de Técnico",
          type="password",
          placeholder="Tu clave personal",
          key="pass_tecnico_form",
      )

    with f_col2:
      pass_departamento = st.text_input(
          "Contraseña del Depto. Solicitante",
          type="password",
          placeholder="Clave del departamento",
          key="pass_depto_form",
      )

    submitted = st.form_submit_button("Guardar Orden", use_container_width=True)

    mensaje_form_container = st.empty()

    if submitted:
      num_orden_asignado = generar_siguiente_num_orden()

      if tecnico == "Selecciona un técnico...":
        mensaje_form_container.error(
            "Por favor selecciona tu nombre de la lista."
        )
      elif area == "Selecciona un área...":
        mensaje_form_container.error(
            "Por favor selecciona el área correspondiente."
        )
      elif departamento_solicitante == "Selecciona un departamento...":
        mensaje_form_container.error(
            "Por favor selecciona el departamento solicitante."
        )
      elif not equipo or not descripcion:
        mensaje_form_container.warning(
            "Por favor completa todos los campos obligatorios (Equipo y"
            " Descripción)."
        )
      elif not pass_tecnico or not pass_departamento:
        mensaje_form_container.error(
            "Por favor ingresa ambas contraseñas (Técnico y Departamento)."
        )
      else:

        def limpiar_hora(texto_hora):
          texto_hora = texto_hora.strip()
          try:
            parsed = datetime.strptime(texto_hora, "%H:%M")
            return parsed.strftime("%H:%M"), parsed
          except ValueError:
            return None, None

        emi_str, dt_emi = limpiar_hora(h_emision)
        rec_str, dt_rec = limpiar_hora(h_recepcion)
        cie_str, dt_cie = limpiar_hora(h_cierre)
        con_str, _ = limpiar_hora(h_conformidad)

        if not emi_str or not rec_str or not cie_str or not con_str:
          mensaje_form_container.error(
              "Formato de hora incorrecto. Usa el formato de 24 horas (Ej. 08:30"
              " o 14:15)."
          )
        else:
          match_tec = df_tec_system[
              df_tec_system["Tecnico"] == tecnico.strip()
          ]
          match_dep = df_dep_system[
              df_dep_system["Departamento"] == departamento_solicitante.strip()
          ]

          if match_tec.empty:
            mensaje_form_container.error(
                "Error al identificar al técnico seleccionado."
            )
          elif match_dep.empty:
            mensaje_form_container.error(
                "Error al identificar el departamento solicitante."
            )
          else:
            pass_correcta_tec = str(match_tec["Password"].values[0]).strip()
            pass_ingresada_tec = str(pass_tecnico).strip().replace(".0", "")

            pass_correcta_dep = str(match_dep["Password"].values[0]).strip()
            pass_ingresada_dep = str(pass_departamento).strip().replace(
                ".0", ""
            )

            if pass_ingresada_tec != pass_correcta_tec:
              mensaje_form_container.error(
                  "Contraseña incorrecta para el técnico seleccionado."
              )
            elif pass_ingresada_dep != pass_correcta_dep:
              mensaje_form_container.error(
                  "Contraseña incorrecta para el departamento solicitante."
              )
            else:
              base_date = datetime.today()
              dt_e = datetime.combine(base_date, dt_emi.time())
              dt_r = datetime.combine(base_date, dt_rec.time())
              dt_c = datetime.combine(base_date, dt_cie.time())

              if dt_r < dt_e:
                dt_r += timedelta(days=1)
              if dt_c < dt_r:
                dt_c += timedelta(days=1)

              min_espera = int((dt_r - dt_e).total_seconds() / 60)
              if min_espera < 0:
                min_espera = 0

              min_trabajo = int((dt_c - dt_r).total_seconds() / 60)
              if min_trabajo < 0:
                min_trabajo = 0

              min_total = int((dt_c - dt_e).total_seconds() / 60)
              if min_total < 0:
                min_total = 0

              nuevo_registro = {
                  "Fecha": fecha_actual,
                  "Turno": turno,
                  "Tecnico": tecnico,
                  "Area": area,
                  "DepartamentoSolicitante": departamento_solicitante,
                  "Equipo": equipo,
                  "NumOrden": num_orden_asignado,
                  "TipoMantenimiento": tipo_mtto,
                  "HoraEmision": emi_str,
                  "HoraRecepcion": rec_str,
                  "HoraCierre": cie_str,
                  "HoraConformidad": con_str,
                  "MinutosEspera": min_espera,
                  "MinutosTrabajo": min_trabajo,
                  "MinutosTotalOT": min_total,
                  "Descripcion": descripcion,
              }

              guardar_registro(nuevo_registro)

              st.session_state["hora_inicial_default"] = datetime.now().strftime(
                  "%H:%M"
              )

              mensaje_form_container.success(
                  f"✅ ¡Orden {num_orden_asignado} guardada exitosamente! "
                  f"(T. Espera: {min_espera} min | T. Trabajo: {min_trabajo} min"
                  f" | Total: {min_total} min)"
              )


# ---------------------------------------------------------
# VISTA 2: RESUMEN DE TURNO
# ---------------------------------------------------------
elif menu == "📊 Resumen de Turno":
  st.subheader("📊 Resumen y Cierre de Turno")

  df = cargar_datos()

  if df.empty or "NumOrden" not in df.columns:
    st.info(
        "Aún no hay registros válidos guardados o el archivo está vacío. Realiza"
        " un registro nuevo para inicializar la estructura."
    )
  else:
    col1, col2, col3 = st.columns(3)
    with col1:
      fechas_disponibles = sorted(
          [str(f) for f in df["Fecha"].dropna().unique()], reverse=True
      )
      fecha_filtro = st.selectbox("Filtrar por Fecha", fechas_disponibles)
    with col2:
      turnos_disponibles = ["Todos"] + list(
          df["Turno"].dropna().unique().astype(str)
      )
      turno_filtro = st.selectbox("Filtrar por Turno", turnos_disponibles)
    with col3:
      busqueda_texto = st.text_input(
          "🔍 Búsqueda rápida",
          placeholder="Busca por OT, equipo, depto o técnico...",
      )

    df_filtrado = df[df["Fecha"].astype(str) == str(fecha_filtro)]
    if turno_filtro != "Todos":
      df_filtrado = df_filtrado[
          df_filtrado["Turno"].astype(str) == str(turno_filtro)
      ]

    if busqueda_texto.strip():
      query = busqueda_texto.strip().lower()
      mask = (
          df_filtrado["NumOrden"].astype(str).str.lower().str.contains(query)
          | df_filtrado["Equipo"].astype(str).str.lower().str.contains(query)
          | df_filtrado["Tecnico"].astype(str).str.lower().str.contains(query)
          | df_filtrado["DepartamentoSolicitante"]
          .astype(str)
          .str.lower()
          .str.contains(query)
          | df_filtrado["Descripcion"]
          .astype(str)
          .str.lower()
          .str.contains(query)
      )
      df_filtrado = df_filtrado[mask]

    st.markdown("---")

    if df_filtrado.empty:
      st.warning("No hay registros para los filtros o búsqueda seleccionados.")
    else:
      total_ordenes = len(df_filtrado)

      for col_t in ["MinutosEspera", "MinutosTrabajo", "MinutosTotalOT"]:
        if col_t in df_filtrado.columns:
          df_filtrado[col_t] = pd.to_numeric(
              df_filtrado[col_t], errors="coerce"
          ).fillna(0)
        else:
          df_filtrado[col_t] = 0

      t_espera_tot = df_filtrado["MinutosEspera"].sum()
      t_trabajo_tot = df_filtrado["MinutosTrabajo"].sum()
      t_total_ot = df_filtrado["MinutosTotalOT"].sum()

      m1, m2, m3, m4 = st.columns(4)
      m1.metric(label="Total Órdenes", value=total_ordenes)
      m2.metric(
          label="Tiempo Espera Acumulado", value=f"{t_espera_tot} min"
      )
      m3.metric(
          label="Tiempo Trabajo Acumulado", value=f"{t_trabajo_tot} min"
      )
      m4.metric(label="Tiempo Total OTs", value=f"{t_total_ot} min")

      col_sec1, col_sec2 = st.columns(2)

      with col_sec1:
        st.markdown(
            "🏆 **Top Equipos con más Fallas** *(Distinguido por Área)*"
        )
        top_equipos = (
            df_filtrado.groupby(["Area", "Equipo"])
            .agg(Total_Fallas=("NumOrden", "count"))
            .reset_index()
            .sort_values(by="Total_Fallas", ascending=False)
            .head(5)
        )
        st.dataframe(top_equipos, use_container_width=True, hide_index=True)

      with col_sec2:
        st.markdown("### 👨‍🔧 Desglose por Técnico")
        resumen_tecnicos = (
            df_filtrado.groupby("Tecnico")
            .agg(
                Ordenes_Atendidas=("NumOrden", "count"),
                Espera_Promedio_Min=("MinutosEspera", "mean"),
                Trabajo_Total_Min=("MinutosTrabajo", "sum"),
            )
            .reset_index()
        )
        resumen_tecnicos["Espera_Promedio_Min"] = resumen_tecnicos[
            "Espera_Promedio_Min"
        ].round(1)
        resumen_tecnicos["Trabajo_Total_Horas"] = round(
            resumen_tecnicos["Trabajo_Total_Min"] / 60, 2
        )
        st.dataframe(resumen_tecnicos, use_container_width=True, hide_index=True)

      st.markdown("---")
      st.markdown("### 📋 Detalle Completo de Órdenes del Turno")

      if st.session_state["admin_logueado"]:
        with st.expander("🛠️ Panel de Administrador: Eliminar Orden Errónea"):
          st.warning(
              "Aquí puedes eliminar cualquier orden registrada por error."
          )
          df_global = cargar_datos()
          indices_filtro = df_filtrado.index.tolist()

          if indices_filtro:
            opcion_borrar = st.selectbox(
                "Selecciona la Orden a eliminar (por Número de Orden y Equipo)",
                options=indices_filtro,
                format_func=lambda x: (
                    f"Índice {x} | Fecha: {df_global.loc[x, 'Fecha']} | OT:"
                    f" {df_global.loc[x, 'NumOrden']} | Equipo:"
                    f" {df_global.loc[x, 'Equipo']} | Técnico:"
                    f" {df_global.loc[x, 'Tecnico']}"
                ),
            )
            if st.button("🗑️ Eliminar Orden Seleccionada", type="primary"):
              exito, msg = eliminar_orden(opcion_borrar)
              if exito:
                st.success(msg)
                st.rerun()
              else:
                st.error(msg)
          else:
            st.info("No hay órdenes disponibles para eliminar en este filtro.")

      st.dataframe(df_filtrado, use_container_width=True)

      csv = df_filtrado.to_csv(index=False).encode("utf-8")
      st.download_button(
          label="📥 Descargar reporte de este turno (CSV)",
          data=csv,
          file_name=f"reporte_turno_{fecha_filtro}.csv",
          mime="text/csv",
      )


# ---------------------------------------------------------
# VISTA 3: GESTIÓN DE PERSONAL, ÁREAS Y DEPARTAMENTOS (Admin)
# ---------------------------------------------------------
elif (
    menu == "👥 Gestionar Personal, Áreas y Deptos"
    and st.session_state["admin_logueado"]
):
  st.subheader("👥 Administración General de Personal, Áreas y Departamentos")
  st.markdown(
      "Gestiona los técnicos, las áreas de la planta y los departamentos"
      " autorizados para solicitar OTs."
  )

  tab1, tab2, tab3 = st.tabs(
      [
          "🔧 Gestionar Técnicos",
          "🏭 Gestionar Áreas",
          "🏢 Gestionar Departamentos",
      ]
  )

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
          placeholder="Clave personal",
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

  with tab2:
    col_area_add, col_area_del = st.columns(2)
    with col_area_add:
      st.markdown("#### ➕ Registrar Nueva Área")
      nueva_area_input = st.text_input(
          "Nombre del Área o Nave", placeholder="Ej. Nave 5 - Ensamble"
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

  with tab3:
    col_dep_add, col_dep_del = st.columns(2)
    with col_dep_add:
      st.markdown("#### ➕ Registrar o Actualizar Departamento")
      nombre_dep_input = st.text_input(
          "Nombre del Departamento", placeholder="Ej. Mantenimiento, Calidad..."
      )
      pass_dep_input = st.text_input(
          "Contraseña de Solicitud",
          type="password",
          placeholder="Clave del departamento",
          key="pass_dep_input",
      )
      if st.button("Guardar Departamento"):
        exito, msg = agregar_o_actualizar_departamento(
            nombre_dep_input, pass_dep_input
        )
        if exito:
          st.success(msg)
          st.rerun()
        else:
          st.error(msg)

    with col_dep_del:
      st.markdown("#### 🗑️ Eliminar Departamento")
      df_dep_current = cargar_departamentos_df()
      dep_a_borrar = st.selectbox(
          "Selecciona el departamento a remover", df_dep_current["Departamento"]
      )
      if st.button("Eliminar Departamento"):
        exito, msg = eliminar_departamento(dep_a_borrar)
        if exito:
          st.success(msg)
          st.rerun()
        else:
          st.error(msg)

    st.markdown("---")
    st.markdown("#### 🏢 Departamentos Solicitantes Registrados")
    st.dataframe(df_dep_current, use_container_width=True)
