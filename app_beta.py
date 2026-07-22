from datetime import datetime, timedelta
import os
import sqlite3
import pandas as pd
import streamlit as st

# Base de datos SQLite unificada exclusiva para la versión BETA
DB_FILE = "bitacora_beta.db"
TECNICOS_FILE = "tecnicos_beta.csv"
AREAS_FILE = "areas_beta.csv"


# --- CONFIGURACIÓN DE BASE DE DATOS (CERO PÉRDIDA DE DATOS) ---
def inicializar_bd():
  conn = sqlite3.connect(DB_FILE)
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS ordenes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Fecha TEXT,
            Turno TEXT,
            Tecnico TEXT,
            Departamento TEXT,
            Area TEXT,
            Equipo TEXT,
            NumOrden TEXT,
            TipoMantenimiento TEXT,
            HoraEmision TEXT,
            HoraRecepcion TEXT,
            HoraCierre TEXT,
            HoraConformidad TEXT,
            MinutosEspera INTEGER,
            MinutosTrabajo INTEGER,
            MinutosTotalOT INTEGER,
            Descripcion TEXT,
            Estado TEXT
        )
    """)
  conn.commit()
  conn.close()


def cargar_datos_db(query="SELECT * FROM ordenes", params=()):
  conn = sqlite3.connect(DB_FILE)
  try:
    df = pd.read_sql(query, conn, params=params)
    return df
  except Exception:
    return pd.DataFrame()
  finally:
    conn.close()


def guardar_nueva_solicitud(datos):
  conn = sqlite3.connect(DB_FILE)
  cursor = conn.cursor()
  cursor.execute(
      """
        INSERT INTO ordenes (Fecha, Turno, Tecnico, Departamento, Area, Equipo, NumOrden, TipoMantenimiento, 
                             HoraEmision, HoraRecepcion, HoraCierre, HoraConformidad, 
                             MinutosEspera, MinutosTrabajo, MinutosTotalOT, Descripcion, Estado)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
      (
          datos["Fecha"],
          datos["Turno"],
          datos["Tecnico"],
          datos["Departamento"],
          datos["Area"],
          datos["Equipo"],
          datos["NumOrden"],
          datos["TipoMantenimiento"],
          datos["HoraEmision"],
          datos["HoraRecepcion"],
          datos["HoraCierre"],
          datos["HoraConformidad"],
          datos["MinutosEspera"],
          datos["MinutosTrabajo"],
          datos["MinutosTotalOT"],
          datos["Descripcion"],
          datos["Estado"],
      ),
  )
  conn.commit()
  conn.close()


def actualizar_orden_db(id_orden, datos):
  conn = sqlite3.connect(DB_FILE)
  cursor = conn.cursor()
  cursor.execute(
      """
        UPDATE ordenes SET Tecnico=?, TipoMantenimiento=?, HoraRecepcion=?, HoraCierre=?, HoraConformidad=?, 
                           MinutosEspera=?, MinutosTrabajo=?, MinutosTotalOT=?, Descripcion=?, Estado=?
        WHERE id=?
    """,
      (
          datos["Tecnico"],
          datos["TipoMantenimiento"],
          datos["HoraRecepcion"],
          datos["HoraCierre"],
          datos["HoraConformidad"],
          datos["MinutosEspera"],
          datos["MinutosTrabajo"],
          datos["MinutosTotalOT"],
          datos["Descripcion"],
          datos["Estado"],
          id_orden,
      ),
  )
  conn.commit()
  conn.close()


def actualizar_conformidad_db(id_orden, hora_con):
  conn = sqlite3.connect(DB_FILE)
  cursor = conn.cursor()
  cursor.execute(
      """
        UPDATE ordenes SET HoraConformidad=? WHERE id=?
    """,
      (hora_con, id_orden),
  )
  conn.commit()
  conn.close()


def eliminar_orden_db(id_orden):
  conn = sqlite3.connect(DB_FILE)
  cursor = conn.cursor()
  cursor.execute("DELETE FROM ordenes WHERE id=?", (id_orden,))
  conn.commit()
  conn.close()


# Gestión de Técnicos (CSV auxiliar beta)
def cargar_tecnicos_df():
  if os.path.exists(TECNICOS_FILE):
    df_tec = pd.read_csv(TECNICOS_FILE, dtype=str)
    df_tec["Tecnico"] = df_tec["Tecnico"].fillna("").astype(str).str.strip()
    df_tec["Password"] = (
        df_tec["Password"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )
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


# Gestión de Áreas (CSV auxiliar beta)
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
    return False, "Esta área ya existe."
  areas.append(nueva_area)
  pd.DataFrame({"Area": areas}).to_csv(AREAS_FILE, index=False)
  return True, f"Área '{nueva_area}' agregada."


def eliminar_area(area_a_borrar):
  areas = cargar_areas()
  if len(areas) <= 1:
    return False, "Debes mantener al menos un área."
  if area_a_borrar in areas:
    areas.remove(area_a_borrar)
    pd.DataFrame({"Area": areas}).to_csv(AREAS_FILE, index=False)
    return True, "Área eliminada."
  return False, "El área no existe."


# Inicializar Base de Datos Beta
inicializar_bd()

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Mesa de Ayuda [BETA] - Avangard Labs",
    page_icon="⚙️",
    layout="wide",
)

if "mensaje_alerta" not in st.session_state:
  st.session_state["mensaje_alerta"] = None

if "hora_default" not in st.session_state:
  st.session_state["hora_default"] = datetime.now().strftime("%H:%M")

st.title("⚙️ Sistema de Órdenes de Trabajo (Fase Beta) - Avangard Labs")

# --- MENÚ LATERAL: 4 CATEGORÍAS DE USUARIOS ---
st.sidebar.image("https://img.icons8.com/color/96/maintenance.png", width=80)
st.sidebar.title("Selección de Rol [BETA]")

categoria_usuario = st.sidebar.selectbox(
    "¿Quién está ingresando?",
    [
        "📝 Solicitante (Producción)",
        "👷‍♂️ Técnico de Mantenimiento",
        "📊 Visualizador / Gerencia",
        "🛠️ Administrador (Gestión Total)",
    ],
)
st.sidebar.markdown("---")

# ---------------------------------------------------------
# CATEGORÍA 1: SOLICITANTE (PRODUCCIÓN)
# ---------------------------------------------------------
if categoria_usuario == "📝 Solicitante (Producción)":
  st.subheader("📝 Solicitar Orden de Mantenimiento (Helpdesk)")
  st.markdown(
      "Reporta una falla o necesidad de ajuste. El equipo técnico será"
      " notificado de inmediato."
  )

  if st.session_state["mensaje_alerta"]:
    st.success(st.session_state["mensaje_alerta"])
    st.session_state["mensaje_alerta"] = None

  lista_departamentos = [
      "Selecciona un departamento...",
      "Acondicionado",
      "Fabricacion",
      "Almacen",
      "Desarrollo",
      "Calidad",
      "EHS",
  ]
  lista_areas = ["Selecciona un área..."] + cargar_areas()

  with st.form("form_solicitud_produccion"):
    col1, col2 = st.columns(2)
    with col1:
      depto_sol = st.selectbox("Departamento que solicita", lista_departamentos)
      area_sol = st.selectbox("Área (configurada por admin)", lista_areas)
    with col2:
      equipo_sol = st.text_input(
          "Equipo o Máquina", placeholder="Ej. Línea 2 - Envasadora"
      )
      turno_sol = st.selectbox(
          "Turno Actual", ["Matutino", "Vespertino", "Nocturno"]
      )

    num_ot_generado = f"OT-{datetime.now().strftime('%d%H%M%S')}"
    st.info(f"📌 Folio Asignado Automáticamente: **{num_ot_generado}**")

    desc_sol = st.text_area(
        "Descripción corta de la falla",
        placeholder=(
            "Ej. Se detuvo la banda principal por atasco en sensor..."
        ),
    )

    submitted_sol = st.form_submit_button(
        "Enviar Solicitud a Mantenimiento", use_container_width=True
    )

    if submitted_sol:
      if depto_sol == "Selecciona un departamento...":
        st.error("Selecciona el departamento que solicita.")
      elif area_sol == "Selecciona un área...":
        st.error("Selecciona el área correspondiente.")
      elif not equipo_sol or not desc_sol:
        st.warning("Completa el equipo y la descripción de la falla.")
      else:
        nueva_ot = {
            "Fecha": datetime.now().strftime("%Y-%m-%d"),
            "Turno": turno_sol,
            "Tecnico": "Pendiente de Asignar",
            "Departamento": depto_sol,
            "Area": area_sol,
            "Equipo": equipo_sol,
            "NumOrden": num_ot_generado,
            "TipoMantenimiento": "Correctivo",
            "HoraEmision": datetime.now().strftime("%H:%M"),
            "HoraRecepcion": "--:--",
            "HoraCierre": "--:--",
            "HoraConformidad": "--:--",
            "MinutosEspera": 0,
            "MinutosTrabajo": 0,
            "MinutosTotalOT": 0,
            "Descripcion": desc_sol,
            "Estado": "Abierta",
        }
        guardar_nueva_solicitud(nueva_ot)
        st.session_state["mensaje_alerta"] = (
            f"✅ ¡Solicitud {num_ot_generado} enviada con éxito! Mantenimiento"
            " ha sido alertado."
        )
        st.rerun()

# ---------------------------------------------------------
# CATEGORÍA 2: TÉCNICO DE MANTENIMIENTO
# ---------------------------------------------------------
elif categoria_usuario == "👷‍♂️ Técnico de Mantenimiento":
  st.subheader("👷‍♂️ Panel de Atención Técnica")
  st.markdown(
      "Revisa las solicitudes abiertas, tómalas y completa los datos de"
      " intervención."
  )

  if st.session_state["mensaje_alerta"]:
    st.success(st.session_state["mensaje_alerta"])
    st.session_state["mensaje_alerta"] = None

  df_pendientes = cargar_datos_db(
      "SELECT * FROM ordenes WHERE Estado = 'Abierta'"
  )

  if df_pendientes.empty:
    st.info("🎉 ¡Excelente trabajo! No hay órdenes pendientes en este momento.")
  else:
    st.warning(
        f"⚠️ Hay **{len(df_pendientes)}** orden(es) esperando atención técnica."
    )

    for index, row in df_pendientes.iterrows():
      with st.expander(
          f"🔔 [{row['NumOrden']}] Depto: {row.get('Departamento', 'N/D')} | Área:"
          f" {row['Area']} | Equipo: {row['Equipo']}"
      ):
        st.write(f"**Descripción del solicitante:** {row['Descripcion']}")
        st.write(
            f"**Fecha y Hora de Emisión:** {row['Fecha']} a las"
            f" {row['HoraEmision']}"
        )

        df_tec_system = cargar_tecnicos_df()
        lista_tecs = ["Selecciona tu nombre..."] + list(
            df_tec_system["Tecnico"]
        )

        with st.form(f"form_atencion_{row['id']}") as f:
          col_t1, col_t2 = st.columns(2)
          with col_t1:
            tec_asignado = st.selectbox(
                "Técnico que Atiende", lista_tecs, key=f"tec_{row['id']}"
            )
            tipo_pto = st.selectbox(
                "Tipo de Mantenimiento",
                ["Correctivo", "Preventivo", "Predictivo", "Ajuste / Mejora"],
                key=f"tipo_{row['id']}",
            )
          with col_t2:
            pass_tec_input = st.text_input(
                "Contraseña Personal de Técnico",
                type="password",
                key=f"pass_t_{row['id']}",
            )

          desc_tec = st.text_area(
              "Diagnóstico y Trabajo Realizado",
              value=row["Descripcion"],
              key=f"desc_{row['id']}",
          )

          st.markdown("---")
          btn_cerrar_ot = st.form_submit_button(
              "Finalizar y Cerrar Orden de Trabajo", use_container_width=True
          )

          if btn_cerrar_ot:
            if tec_asignado == "Selecciona tu nombre...":
              st.error("Selecciona tu nombre de técnico.")
            elif not pass_tec_input:
              st.error("Ingresa tu contraseña.")
            else:
              match = df_tec_system[
                  df_tec_system["Tecnico"] == tec_asignado.strip()
              ]
              if not match.empty:
                pass_correcta = str(match["Password"].values[0]).strip()
                pass_ingresada = str(pass_tec_input).strip().replace(
                    ".0", ""
                )

                if pass_ingresada == pass_correcta:
                  try:
                    hora_actual_str = datetime.now().strftime("%H:%M")
                    h_rec = (
                        row["HoraEmision"]
                        if row["HoraEmision"] != "--:--"
                        else hora_actual_str
                    )
                    h_cie = hora_actual_str
                    h_con = (
                        row["HoraConformidad"]
                        if row["HoraConformidad"] != "--:--"
                        else "--:--"
                    )

                    dt_emi = datetime.strptime(row["HoraEmision"], "%H:%M")
                    dt_rec = datetime.strptime(h_rec, "%H:%M")
                    dt_cie = datetime.strptime(h_cie, "%H:%M")

                    base_date = datetime.today()
                    dt_e = datetime.combine(base_date, dt_emi.time())
                    dt_r = datetime.combine(base_date, dt_rec.time())
                    dt_c = datetime.combine(base_date, dt_cie.time())

                    if dt_r < dt_e:
                      dt_r += timedelta(days=1)
                    if dt_c < dt_r:
                      dt_c += timedelta(days=1)

                    min_esp = max(
                        0, int((dt_r - dt_e).total_seconds() / 60)
                    )
                    min_trab = max(
                        0, int((dt_c - dt_r).total_seconds() / 60)
                    )
                    min_tot = max(0, int((dt_c - dt_e).total_seconds() / 60))

                    datos_actualizados = {
                        "Tecnico": tec_asignado,
                        "TipoMantenimiento": tipo_pto,
                        "HoraRecepcion": h_rec,
                        "HoraCierre": h_cie,
                        "HoraConformidad": h_con,
                        "MinutosEspera": min_esp,
                        "MinutosTrabajo": min_trab,
                        "MinutosTotalOT": min_tot,
                        "Descripcion": desc_tec,
                        "Estado": "Cerrada",
                    }

                    actualizar_orden_db(row["id"], datos_actualizados)
                    st.session_state["mensaje_alerta"] = (
                        f"✅ Orden {row['NumOrden']} cerrada correctamente a las"
                        f" {h_cie}."
                    )
                    st.rerun()
                  except ValueError:
                    st.error("Error al procesar las horas automáticas.")
                else:
                  st.error("Contraseña incorrecta.")
              else:
                st.error("Técnico no encontrado.")

# ---------------------------------------------------------
# CATEGORÍA 3: VISUALIZADOR / GERENCIA
# ---------------------------------------------------------
elif categoria_usuario == "📊 Visualizador / Gerencia":
  st.subheader(
      "📊 Panel de Visualización, Seguimiento y Conformidad [BETA]"
  )

  if st.session_state["mensaje_alerta"]:
    st.success(st.session_state["mensaje_alerta"])
    st.session_state["mensaje_alerta"] = None

  df_all = cargar_datos_db()

  if df_all.empty:
    st.info("Aún no hay registros en la base de datos de pruebas.")
  else:
    col1, col2, col3 = st.columns(3)
    with col1:
      fechas_disp = sorted(
          [str(f) for f in df_all["Fecha"].dropna().unique()], reverse=True
      )
      fecha_sel = st.selectbox("Filtrar por Fecha", fechas_disp)
    with col2:
      turnos_disp = ["Todos"] + list(
          df_all["Turno"].dropna().unique().astype(str)
      )
      turno_sel = st.selectbox("Filtrar por Turno", turnos_disp)
    with col3:
      estado_sel = st.selectbox(
          "Filtrar por Estado", ["Todos", "Abierta", "Cerrada"]
      )

    df_f = df_all[df_all["Fecha"].astype(str) == str(fecha_sel)]
    if turno_sel != "Todos":
      df_f = df_f[df_f["Turno"].astype(str) == str(turno_sel)]
    if estado_sel != "Todos":
      df_f = df_f[df_f["Estado"].astype(str) == str(estado_sel)]

    st.markdown("---")

    if df_f.empty:
      st.warning("No hay órdenes con los filtros seleccionados.")
    else:
      m1, m2, m3, m4 = st.columns(4)
      m1.metric(label="Total de Órdenes", value=len(df_f))
      m2.metric(
          label="T. Espera Acumulado",
          value=f"{df_f['MinutosEspera'].sum()} min",
      )
      m3.metric(
          label="T. Trabajo Acumulado",
          value=f"{df_f['MinutosTrabajo'].sum()} min",
      )
      m4.metric(
          label="Abiertas / Pendientes",
          value=len(df_f[df_f["Estado"] == "Abierta"]),
      )

      st.markdown("### 📋 Detalle de Órdenes y Dar Conformidad")
      st.markdown(
          "*Las órdenes cerradas por mantenimiento aparecen aquí para que el"
            " solicitante pueda dar su visto bueno (conformidad).*  "
      )

      for index, row in df_f.iterrows():
        estado_con_actual = row["HoraConformidad"]
        ya_conforme = estado_con_actual != "--:--"
        depto_txt = (
            row["Departamento"]
            if "Departamento" in row and pd.notna(row["Departamento"])
            else "N/D"
        )

        with st.expander(
            f"[{row['NumOrden']}] Depto: {depto_txt} | Área: {row['Area']} |"
            f" Equipo: {row['Equipo']} | Estado: {row['Estado']} |"
            f" Conformidad: {('✅ ' + estado_con_actual) if ya_conforme else '⏳ Pendiente'}"
        ):
          st.write(f"**Técnico:** {row['Tecnico']}")
          st.write(f"**Tipo de Mantenimiento:** {row['TipoMantenimiento']}")
          st.write(f"**Trabajo Realizado:** {row['Descripcion']}")
          st.write(
              f"**Horarios — Emisión:** {row['HoraEmision']} | Recepción:"
              f" {row['HoraRecepcion']} | Cierre: {row['HoraCierre']}"
          )

          if row["Estado"] == "Cerrada":
            with st.form(f"form_conformidad_{row['id']}"):
              check_conf = st.checkbox(
                  "✅ Dar Visto Bueno / Conformidad al Trabajo Realizado",
                  value=ya_conforme,
              )
              btn_guardar_conf = st.form_submit_button(
                  "Guardar Conformidad del Solicitante"
              )

              if btn_guardar_conf:
                if check_conf:
                  hora_conf_actual = datetime.now().strftime("%H:%M")
                  actualizar_conformidad_db(row["id"], hora_conf_actual)
                  st.session_state["mensaje_alerta"] = (
                      f"✅ Conformidad registrada para la orden"
                      f" {row['NumOrden']} a las {hora_conf_actual}."
                  )
                  st.rerun()
                else:
                  actualizar_conformidad_db(row["id"], "--:--")
                  st.session_state["mensaje_alerta"] = (
                      f"ℹ️ Se ha removido la conformidad de la orden"
                      f" {row['NumOrden']}."
                  )
                  st.rerun()
          else:
            st.info(
                "La orden aún está abierta. La conformidad se habilitará una"
                " vez que el técnico la cierre."
            )

      st.markdown("---")
      st.markdown("### 📊 Tabla General de Registros")
      st.dataframe(df_f, use_container_width=True)

# ---------------------------------------------------------
# CATEGORÍA 4: ADMINISTRADOR (GESTIÓN TOTAL)
# ---------------------------------------------------------
elif categoria_usuario == "🛠️ Administrador (Gestión Total)":
  st.subheader("🛠️ Panel de Administración del Sistema")
  st.markdown(
      "Gestiona los técnicos autorizados, las áreas/naves y la base de"
      " datos."
  )

  pass_gerencia = st.text_input(
      "Contraseña de Administrador", type="password", key="pass_admin_total"
  )

  if pass_gerencia.strip() == "avangardmtto22":
    st.success("Acceso concedido.")
    tab_g1, tab_g2 = st.tabs(["👥 Gestión de Técnicos", "🏭 Gestión de Áreas"])

    with tab_g1:
      st.markdown("#### Técnicos Registrados")
      df_t = cargar_tecnicos_df()
      st.dataframe(df_t, use_container_width=True)

      st.markdown("#### Agregar o Actualizar Técnico")
      n_tec = st.text_input("Nombre del técnico")
      p_tec = st.text_input(
          "Contraseña del técnico", type="password", key="p_tec_nuevo"
      )
      if st.button("Guardar / Actualizar Técnico"):
        ex, msg = agregar_o_actualizar_tecnico(n_tec, p_tec)
        if ex:
          st.success(msg)
          st.rerun()
        else:
          st.error(msg)

      st.markdown("---")
      st.markdown("#### Eliminar Técnico")
      tec_a_borrar = st.selectbox(
          "Selecciona técnico a eliminar",
          ["Selecciona..."] + list(df_t["Tecnico"]),
      )
      if st.button("Eliminar Técnico"):
        if tec_a_borrar != "Selecciona...":
          ex, msg = eliminar_tecnico(tec_a_borrar)
          if ex:
            st.success(msg)
            st.rerun()
          else:
            st.error(msg)
        else:
          st.warning("Selecciona un técnico válido.")

    with tab_g2:
      st.markdown("#### Áreas / Naves Registradas")
      lista_areas_actuales = cargar_areas()

      df_areas_view = pd.DataFrame(
          {"Área / Nave": lista_areas_actuales}
      ).reset_index(drop=True)
      df_areas_view.index = df_areas_view.index + 1
      st.dataframe(df_areas_view, use_container_width=True)

      st.markdown("---")
      st.markdown("#### Agregar Nueva Área")
      n_area = st.text_input("Nombre de la Nueva Área o Nave")
      if st.button("Guardar Nueva Área"):
        ex, msg = agregar_area(n_area)
        if ex:
          st.success(msg)
          st.rerun()
        else:
          st.error(msg)

      st.markdown("---")
      st.markdown("#### Eliminar Área")
      area_a_borrar = st.selectbox(
          "Selecciona área a eliminar", ["Selecciona..."] + lista_areas_actuales
      )
      if st.button("Eliminar Área"):
        if area_a_borrar != "Selecciona...":
          ex, msg = eliminar_area(area_a_borrar)
          if ex:
            st.success(msg)
            st.rerun()
          else:
            st.error(msg)
        else:
          st.warning("Selecciona un área válida.")

  elif pass_gerencia:
    st.error("Contraseña incorrecta.")
