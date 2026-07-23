from datetime import datetime, timedelta
import os
import sqlite3
import pandas as pd
import streamlit as st

# Base de datos SQLite unificada exclusiva para la versión BETA
DB_FILE = "bitacora_beta.db"
TECNICOS_FILE = "tecnicos_beta.csv"
AREAS_FILE = "areas_beta.csv"
DEPTOS_FILE = "departamentos_beta.csv"


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
        INSERT INTO ordenes (
            Fecha, Turno, Tecnico, Departamento, Area, Equipo, NumOrden, TipoMantenimiento, 
            HoraEmision, HoraRecepcion, HoraCierre, HoraConformidad, 
            MinutosEspera, MinutosTrabajo, MinutosTotalOT, Descripcion, Estado
        )
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


# Gestión de Departamentos / Solicitantes (CSV auxiliar beta)
def cargar_departamentos_df():
  if os.path.exists(DEPTOS_FILE):
    df_dep = pd.read_csv(DEPTOS_FILE, dtype=str)
    df_dep["Departamento"] = (
        df_dep["Departamento"].fillna("").astype(str).str.strip()
    )
    df_dep["Password"] = (
        df_dep["Password"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )
    return df_dep
  else:
    df_dep = pd.DataFrame({
        "Departamento": ["Acondicionado", "Producción"],
        "Password": ["1111", "2222"],
    })
    df_dep.to_csv(DEPTOS_FILE, index=False)
    return df_dep


def agregar_o_actualizar_departamento(nombre, password):
  df_dep = cargar_departamentos_df()
  nombre = str(nombre).strip()
  password = str(password).strip().replace(".0", "")
  if not nombre or not password:
    return False, "El departamento y la contraseña no pueden estar vacíos."
  if nombre in df_dep["Departamento"].values:
    df_dep.loc[df_dep["Departamento"] == nombre, "Password"] = password
    mensaje = f"Contraseña actualizada para el departamento {nombre}."
  else:
    nuevo_row = pd.DataFrame(
        {"Departamento": [nombre], "Password": [password]}
    )
    df_dep = pd.concat([df_dep, nuevo_row], ignore_index=True)
    mensaje = f"Departamento {nombre} agregado exitosamente."
  df_dep.to_csv(DEPTOS_FILE, index=False)
  return True, mensaje


def eliminar_departamento(nombre_a_borrar):
  df_dep = cargar_departamentos_df()
  if len(df_dep) <= 1:
    return False, "Debes mantener al menos un departamento registrado."
  df_dep = df_dep[df_dep["Departamento"] != str(nombre_a_borrar).strip()]
  df_dep.to_csv(DEPTOS_FILE, index=False)
  return True, "Departamento eliminado correctamente."


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

# --- CONFIGURACIÓN DE PÁGINA Y ESTILO CORPORATIVO ---
st.set_page_config(
    page_title="Mesa de Ayuda [BETA] - Avangard Labs",
    page_icon="⚙️",
    layout="wide",
)

# Inyección de Estilos CSS con la Paleta de Colores Inspirada en el Logotipo (Tonos Azules/Cian de Avangard Labs)
st.markdown(
    """
    <style>
        /* Color de acento general para botones primarios y selección */
        .stButton>button {
            background-color: #2b7bb9;
            color: white;
            border-radius: 6px;
            border: none;
        }
        .stButton>button:hover {
            background-color: #1f5d8e;
            color: white;
        }
        /* Estilos generales de encabezados */
        h1, h2, h3 {
            color: #1f5d8e;
        }
    </style>
""",
    unsafe_allow_html=True,
)

if "mensaje_alerta" not in st.session_state:
  st.session_state["mensaje_alerta"] = None

if "hora_default" not in st.session_state:
  st.session_state["hora_default"] = datetime.now().strftime("%H:%M")

if "ordenes_en_atencion" not in st.session_state:
  st.session_state["ordenes_en_atencion"] = {}

st.title("⚙️ Sistema de Órdenes de Trabajo (Fase Beta) - Avangard Labs")

# --- MENÚ LATERAL CON INTEGRACIÓN DEL LOGOTIPO ---
# Usamos el logo que proporcionaste para la cabecera lateral
st.sidebar.image(
    "https://i.ibb.co/306915j/logo-avangard.png"
)  # O puedes colocar tu imagen local/enlace
st.sidebar.markdown("---")
st.sidebar.title("Selección de Rol [BETA]")

categoria_usuario = st.sidebar.selectbox(
    "¿Quién está ingresando?",
    [
        "📝 Solicitante (Producción)",
        "👷‍♂️ Órdenes de trabajo Abiertas y en Espera",
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
      "Reporta una falla o necesidad de ajuste. Ingresa tu contraseña de"
      " departamento autorizada al enviar."
  )

  df_deptos_system = cargar_departamentos_df()
  lista_departamentos = ["Selecciona un departamento..."] + list(
      df_deptos_system["Departamento"]
  )
  lista_areas = ["Selecciona un área..."] + cargar_areas()

  with st.form("form_solicitud_produccion"):
    col1, col2 = st.columns(2)
    with col1:
      depto_sol = st.selectbox(
          "Departamento que solicita", lista_departamentos
      )
    with col2:
      area_sol = st.selectbox("Área (configurada por admin)", lista_areas)

    turno_sol = st.selectbox(
        "Turno Actual", ["Matutino", "Vespertino", "Nocturno"]
    )
    equipo_sol = st.text_input(
        "Equipo o Máquina", placeholder="Ej. Línea 2 - Envasadora"
    )

    num_ot_generado = f"OT-{datetime.now().strftime('%d%H%M%S')}"
    st.info(f"📌 Folio Asignado Automáticamente: **{num_ot_generado}**")

    desc_sol = st.text_area(
        "Descripción corta de la falla",
        placeholder=(
            "Ej. Se detuvo la banda principal por atasco en sensor..."
        ),
    )

    st.markdown("---")
    st.markdown("🔒 **Validación de Envío**")

    col_env1, col_env2, col_env3 = st.columns([1, 1, 1.5])
    with col_env1:
      pass_depto_input = st.text_input(
          "Contraseña de Departamento", type="password"
      )
    with col_env2:
      st.markdown("<br>", unsafe_allow_html=True)
      submitted_sol = st.form_submit_button(
          "Enviar Solicitud a Mantenimiento", use_container_width=True
      )
    with col_env3:
      st.markdown("<br>", unsafe_allow_html=True)
      if st.session_state["mensaje_alerta"]:
        st.success(st.session_state["mensaje_alerta"])
        st.session_state["mensaje_alerta"] = None

    if submitted_sol:
      if depto_sol == "Selecciona un departamento...":
        st.error("Selecciona el departamento que solicita.")
      elif not pass_depto_input:
        st.error("Ingresa la contraseña de tu departamento.")
      elif area_sol == "Selecciona un área...":
        st.error("Selecciona el área correspondiente.")
      elif not equipo_sol or not desc_sol:
        st.warning("Completa el equipo y la descripción de la falla.")
      else:
        match_dep = df_deptos_system[
            df_deptos_system["Departamento"] == depto_sol.strip()
        ]
        if not match_dep.empty:
          pass_correcta_dep = str(match_dep["Password"].values[0]).strip()
          pass_ingresada_dep = str(pass_depto_input).strip().replace(".0", "")

          if pass_ingresada_dep == pass_correcta_dep:
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
                f"✅ ¡Solicitud {num_ot_generado} enviada con éxito!"
            )
            st.rerun()
          else:
            st.error("Contraseña de departamento incorrecta.")
        else:
          st.error("Departamento no encontrado.")

# ---------------------------------------------------------
# CATEGORÍA 2: ÓRDENES DE TRABAJO ABIERTAS Y EN ESPERA
# ---------------------------------------------------------
elif categoria_usuario == "👷‍♂️ Órdenes de trabajo Abiertas y en Espera":
  st.subheader("👷‍♂️ Panel de Órdenes Abiertas y en Espera")
  st.markdown(
      "Atiende solicitudes nuevas o gestiona aquellas que están detenidas"
      " por falta de refacción o servicio externo."
  )

  if st.session_state["mensaje_alerta"]:
    st.success(st.session_state["mensaje_alerta"])
    st.session_state["mensaje_alerta"] = None

  df_pendientes = cargar_datos_db(
      "SELECT * FROM ordenes WHERE Estado IN ('Abierta', 'En Espera')"
  )

  if df_pendientes.empty:
    st.info("🎉 ¡Excelente trabajo! No hay órdenes pendientes ni en espera.")
  else:
    st.warning(
        f"⚠️ Hay **{len(df_pendientes)}** orden(es) en total (Abiertas o en"
        " Espera)."
    )

    df_tec_system = cargar_tecnicos_df()
    lista_tecs = ["Selecciona tu nombre..."] + list(df_tec_system["Tecnico"])

    for index, row in df_pendientes.iterrows():
      ot_id = row["id"]
      estado_actual_ot = row["Estado"]
      tec_en_bd = str(row["Tecnico"]).strip()

      tec_es_valido = (
          tec_en_bd in df_tec_system["Tecnico"].values
          and tec_en_bd != "Pendiente de Asignar"
      )

      atendiendo_activo = st.session_state["ordenes_en_atencion"].get(
          ot_id, tec_en_bd if tec_es_valido else None
      )

      etiqueta_exp = (
          f"🔔 [{row['NumOrden']}] Depto: {row.get('Departamento', 'N/D')} |"
          f" Área: {row['Area']} | Equipo: {row['Equipo']} | Estado:"
          f" **{estado_actual_ot}**"
      )

      with st.expander(etiqueta_exp):
        st.write(f"**Descripción:** {row['Descripcion']}")
        st.write(f"**Técnico Registrado:** {row['Tecnico']}")

        if estado_actual_ot == "En Espera":
          st.error(
              f"🛑 Esta orden está pausada. Motivo / Diagnóstico parcial:"
              f" {row['Descripcion']}"
          )

        if not tec_es_valido and not atendiendo_activo:
          with st.form(f"form_responsable_{ot_id}"):
            st.markdown("### 🛠️ Asignar Responsable de Atención")
            col_r1, col_r2 = st.columns(2)
            with col_r1:
              tec_elegido = st.selectbox(
                  "Técnico Responsable", lista_tecs, key=f"tec_sel_{ot_id}"
              )
            with col_r2:
              pass_tec_responsable = st.text_input(
                  "Contraseña Personal",
                  type="password",
                  key=f"pass_sel_{ot_id}",
              )

            btn_hacerse_resp = st.form_submit_button(
                "Marcarme como Responsable / Atender esta Orden",
                use_container_width=True,
            )

            if btn_hacerse_resp:
              if tec_elegido == "Selecciona tu nombre...":
                st.error("Selecciona tu nombre de técnico.")
              elif not pass_tec_responsable:
                st.error("Ingresa tu contraseña personal.")
              else:
                match_t = df_tec_system[
                    df_tec_system["Tecnico"] == tec_elegido.strip()
                ]
                if not match_t.empty:
                  p_correcta = str(match_t["Password"].values[0]).strip()
                  p_ingresada = str(pass_tec_responsable).strip().replace(
                      ".0", ""
                  )

                  if p_ingresada == p_correcta:
                    st.session_state["ordenes_en_atencion"][ot_id] = (
                        tec_elegido
                    )
                    datos_toma = {
                        "Tecnico": tec_elegido,
                        "TipoMantenimiento": row["TipoMantenimiento"],
                        "HoraRecepcion": (
                            row["HoraEmision"]
                            if row["HoraEmision"] != "--:--"
                            else datetime.now().strftime("%H:%M")
                        ),
                        "HoraCierre": row["HoraCierre"],
                        "HoraConformidad": row["HoraConformidad"],
                        "MinutosEspera": row["MinutosEspera"],
                        "MinutosTrabajo": row["MinutosTrabajo"],
                        "MinutosTotalOT": row["MinutosTotalOT"],
                        "Descripcion": row["Descripcion"],
                        "Estado": row["Estado"],
                    }
                    actualizar_orden_db(ot_id, datos_toma)
                    st.success("✅ ¡Asignado correctamente! Menú desplegado.")
                    st.rerun()
                  else:
                    st.error("Contraseña incorrecta.")
                else:
                  st.error("Técnico no encontrado.")
        else:
          tec_activo = (
              atendiendo_activo
              if atendiendo_activo and atendiendo_activo != "Pendiente de Asignar"
              else tec_en_bd
          )
          st.success(f"👤 Técnico responsable actual: **{tec_activo}**")

          with st.form(f"form_cierre_{ot_id}"):
            col_t1, col_t2 = st.columns(2)
            with col_t1:
              clasificacion_trabajo = st.selectbox(
                  "Clasificación de Trabajo",
                  ["Correctivo", "Ajuste", "Configuracion de linea", "Mejora"],
                  key=f"tipo_{ot_id}",
              )
            with col_t2:
              accion_orden = st.selectbox(
                  "Acción sobre la Orden",
                  [
                      "Finalizar y Cerrar Orden",
                      "Poner en Espera (Falta Refacción)",
                      "Poner en Espera (Servicio Externo)",
                      "Cancelar / Liberar Atención",
                  ],
                  key=f"accion_{ot_id}",
              )

            desc_tec = st.text_area(
                "Diagnóstico o Notas de Avance",
                value=row["Descripcion"],
                key=f"desc_{ot_id}",
            )

            st.markdown("---")
            pass_cierre_input = st.text_input(
                f"🔒 Ingresa tu contraseña personal ({tec_activo}) para confirmar"
                " la acción y liberarte:",
                type="password",
                key=f"pass_cierre_{ot_id}",
            )

            btn_ejecutar = st.form_submit_button(
                "Ejecutar Acción y Liberar Técnico", use_container_width=True
            )

            if btn_ejecutar:
              if not pass_cierre_input:
                st.error(
                    "Debes ingresar tu contraseña personal para confirmar la"
                    " acción."
                )
              else:
                match_t = df_tec_system[
                    df_tec_system["Tecnico"] == tec_activo.strip()
                ]
                if not match_t.empty:
                  p_correcta = str(match_t["Password"].values[0]).strip()
                  p_ingresada = str(pass_cierre_input).strip().replace(
                      ".0", ""
                  )

                  if p_ingresada == p_correcta:
                    if accion_orden == "Cancelar / Liberar Atención":
                      if ot_id in st.session_state["ordenes_en_atencion"]:
                        del st.session_state["ordenes_en_atencion"][ot_id]
                      datos_liberar = {
                          "Tecnico": "Pendiente de Asignar",
                          "TipoMantenimiento": row["TipoMantenimiento"],
                          "HoraRecepcion": row["HoraRecepcion"],
                          "HoraCierre": row["HoraCierre"],
                          "HoraConformidad": row["HoraConformidad"],
                          "MinutosEspera": row["MinutosEspera"],
                          "MinutosTrabajo": row["MinutosTrabajo"],
                          "MinutosTotalOT": row["MinutosTotalOT"],
                          "Descripcion": row["Descripcion"],
                          "Estado": "Abierta",
                      }
                      actualizar_orden_db(ot_id, datos_liberar)
                      st.session_state["mensaje_alerta"] = (
                          "ℹ️ Atención cancelada. Orden devuelta a pendientes."
                      )
                      st.rerun()

                    elif "Poner en Espera" in accion_orden:
                      motivo_espera = (
                          "EN ESPERA [Falta Refacción]: "
                          if "Refacción" in accion_orden
                          else "EN ESPERA [Servicio Externo]: "
                      )
                      nota_final_espera = motivo_espera + desc_tec

                      datos_espera = {
                          "Tecnico": "Pendiente de Asignar",
                          "TipoMantenimiento": clasificacion_trabajo,
                          "HoraRecepcion": (
                              row["HoraEmision"]
                              if row["HoraEmision"] != "--:--"
                              else datetime.now().strftime("%H:%M")
                          ),
                          "HoraCierre": "--:--",
                          "HoraConformidad": "--:--",
                          "MinutosEspera": 0,
                          "MinutosTrabajo": 0,
                          "MinutosTotalOT": 0,
                          "Descripcion": nota_final_espera,
                          "Estado": "En Espera",
                      }
                      actualizar_orden_db(ot_id, datos_espera)
                      if ot_id in st.session_state["ordenes_en_atencion"]:
                        del st.session_state["ordenes_en_atencion"][ot_id]

                      st.session_state["mensaje_alerta"] = (
                          f"⚠️ Orden {row['NumOrden']} marcada como En"
                          f" Espera. Técnico liberado correctamente."
                      )
                      st.rerun()

                    elif accion_orden == "Finalizar y Cerrar Orden":
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
                        min_tot = max(
                            0, int((dt_c - dt_e).total_seconds() / 60)
                        )

                        datos_actualizados = {
                            "Tecnico": tec_activo,
                            "TipoMantenimiento": clasificacion_trabajo,
                            "HoraRecepcion": h_rec,
                            "HoraCierre": h_cie,
                            "HoraConformidad": h_con,
                            "MinutosEspera": min_esp,
                            "MinutosTrabajo": min_trab,
                            "MinutosTotalOT": min_tot,
                            "Descripcion": desc_tec,
                            "Estado": "Cerrada",
                        }

                        actualizar_orden_db(ot_id, datos_actualizados)
                        if ot_id in st.session_state["ordenes_en_atencion"]:
                          del st.session_state["ordenes_en_atencion"][ot_id]

                        st.session_state["mensaje_alerta"] = (
                            f"✅ Orden {row['NumOrden']} cerrada correctamente"
                            f" y técnico liberado."
                        )
                        st.rerun()
                      except ValueError:
                        st.error("Error al procesar las horas automáticas.")
                  else:
                    st.error(
                        "Contraseña incorrecta. No se pudo validar tu"
                        " identidad."
                    )
                else:
                  st.error("Técnico no encontrado en el sistema.")

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
    df_deptos_system = cargar_departamentos_df()
    lista_deptos_filtro = ["Todos"] + list(
        df_deptos_system["Departamento"].unique()
    )

    col1, col2, col3, col4 = st.columns(4)
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
          "Filtrar por Estado", ["Todos", "Abierta", "En Espera", "Cerrada"]
      )
    with col4:
      depto_sel = st.selectbox("Filtrar por Departamento", lista_deptos_filtro)

    df_f = df_all[df_all["Fecha"].astype(str) == str(fecha_sel)]
    if turno_sel != "Todos":
      df_f = df_f[df_f["Turno"].astype(str) == str(turno_sel)]
    if estado_sel != "Todos":
      df_f = df_f[df_f["Estado"].astype(str) == str(estado_sel)]
    if depto_sel != "Todos":
      df_f = df_f[df_f["Departamento"].astype(str) == str(depto_sel)]

    st.markdown("---")

    if df_f.empty:
      st.warning("No hay órdenes con los filtros seleccionados.")
    else:
      m1, m2, m3, m4 = st.columns(4)
      m1.metric(label="Total de Órdenes", value=len(df_f))
      m2.metric(
          label="En Espera (Pausadas)",
          value=len(df_f[df_f["Estado"] == "En Espera"]),
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

      for index, row in df_f.iterrows():
        estado_con_actual = row["HoraConformidad"]
        ya_conforme = estado_con_actual != "--:--"
        depto_txt = (
            str(row["Departamento"]).strip()
            if "Departamento" in row and pd.notna(row["Departamento"])
            else "N/D"
        )
        estado_ot = str(row["Estado"]).strip()

        # Determinación de color/estilo según el estado y visto bueno
        if ya_conforme:
          icono_estado = "🟢"
          sufijo_estado = "**[Cerrada con Visto Bueno]**"
        elif estado_ot == "Abierta":
          icono_estado = "🔴"
          sufijo_estado = "**[Abierta]**"
        elif estado_ot == "En Espera":
          icono_estado = "🟠"
          sufijo_estado = "**[En Espera]**"
        else:
          icono_estado = "🔵"
          sufijo_estado = f"**[{estado_ot}]**"

        etiqueta_exp = (
            f"{icono_estado} [{row['NumOrden']}] Depto: {depto_txt} | Área:"
            f" {row['Area']} | Equipo: {row['Equipo']} | Estado:"
            f" {sufijo_estado}"
        )

        with st.expander(etiqueta_exp):
          st.write(f"**Técnico / Responsable:** {row['Tecnico']}")
          st.write(f"**Clasificación de Trabajo:** {row['TipoMantenimiento']}")
          st.write(f"**Diagnóstico / Nota:** {row['Descripcion']}")

          if row["Estado"] == "Cerrada":
            if ya_conforme:
              st.success(
                  f"✅ Esta orden ya cuenta con Visto Bueno / Conformidad"
                  f" registrada a las **{estado_con_actual}** por el"
                  f" departamento **{depto_txt}**."
              )
            else:
              with st.form(f"form_conformidad_{row['id']}"):
                st.markdown(
                    "🔒 **Validación de Conformidad por Departamento**"
                )
                pass_depto_conf = st.text_input(
                    f"Contraseña del departamento que lanzó la orden"
                    f" ({depto_txt}):",
                    type="password",
                    key=f"pass_conf_depto_{row['id']}",
                )
                btn_guardar_conf = st.form_submit_button(
                    "Dar Visto Bueno (Conformidad)"
                )

                if btn_guardar_conf:
                  if not pass_depto_conf:
                    st.error("Debes ingresar la contraseña del departamento.")
                  else:
                    match_dep = df_deptos_system[
                        df_deptos_system["Departamento"] == depto_txt
                    ]
                    if match_dep.empty:
                      st.error(
                          f"El departamento '{depto_txt}' no está registrado."
                      )
                    else:
                      pass_correcta_dep = str(
                          match_dep["Password"].values[0]
                      ).strip()
                      pass_ingresada_dep = str(pass_depto_conf).strip().replace(
                          ".0", ""
                      )

                      if pass_ingresada_dep != pass_correcta_dep:
                        st.error(
                            f"Contraseña incorrecta para el departamento"
                            f" '{depto_txt}'."
                        )
                      else:
                        hora_conf_actual = datetime.now().strftime("%H:%M")
                        actualizar_conformidad_db(row["id"], hora_conf_actual)
                        st.session_state["mensaje_alerta"] = (
                            f"✅ Conformidad registrada correctamente por el"
                            f" departamento {depto_txt}."
                        )
                        st.rerun()
          else:
            st.info(
                f"La orden se encuentra en estado: **{row['Estado']}**. La"
                " conformidad se habilitará una vez que sea cerrada."
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
      "Gestiona los técnicos autorizados, los departamentos solicitantes, las"
      " áreas y la base de datos."
  )

  pass_gerencia = st.text_input(
      "Contraseña de Administrador", type="password", key="pass_admin_total"
  )

  if pass_gerencia.strip() == "avangardmtto22":
    st.success("Acceso concedido.")
    tab_g1, tab_g2, tab_g3 = st.tabs(
        [
            "👥 Gestión de Técnicos",
            "🏢 Gestión de Departamentos",
            "🏭 Gestión de Áreas",
        ]
    )

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
      st.markdown("#### Departamentos Solicitantes Registrados")
      df_d = cargar_departamentos_df()
      st.dataframe(df_d, use_container_width=True)

      st.markdown("#### Agregar o Actualizar Departamento")
      n_dep = st.text_input("Nombre del Departamento (ej. Acondicionado)")
      p_dep = st.text_input(
          "Contraseña del Departamento", type="password", key="p_dep_nuevo"
      )
      if st.button("Guardar / Actualizar Departamento"):
        ex, msg = agregar_o_actualizar_departamento(n_dep, p_dep)
        if ex:
          st.success(msg)
          st.rerun()
        else:
          st.error(msg)

      st.markdown("---")
      st.markdown("#### Eliminar Departamento")
      dep_a_borrar = st.selectbox(
          "Selecciona departamento a eliminar",
          ["Selecciona..."] + list(df_d["Departamento"]),
      )
      if st.button("Eliminar Departamento"):
        if dep_a_borrar != "Selecciona...":
          ex, msg = eliminar_departamento(dep_a_borrar)
          if ex:
            st.success(msg)
            st.rerun()
          else:
            st.error(msg)
        else:
          st.warning("Selecciona un departamento válido.")

    with tab_g3:
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
