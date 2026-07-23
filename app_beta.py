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

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Mesa de Ayuda [BETA] - Avangard Labs",
    page_icon="⚙️",
    layout="wide",
)

if "mensaje_alerta" not in st.session_state:
  st.session_state["mensaje_alerta"] = None

if "ordenes_en_atencion" not in st.session_state:
  st.session_state["ordenes_en_atencion"] = {}

# Control de Sesión Global
if "sesion_activa" not in st.session_state:
  st.session_state["sesion_activa"] = False
if "rol_usuario" not in st.session_state:
  st.session_state["rol_usuario"] = None
if "nombre_usuario" not in st.session_state:
  st.session_state["nombre_usuario"] = None

st.title("⚙️ Sistema de Órdenes de Trabajo (Fase Beta) - Avangard Labs")

# --- MENÚ LATERAL Y CONTROL DE SESIÓN ---
st.sidebar.title("Control de Acceso [BETA]")

if not st.session_state["sesion_activa"]:
  st.sidebar.info("Inicia sesión para acceder a tu módulo correspondiente.")
  tipo_login = st.sidebar.selectbox(
      "Selecciona tu Rol",
      [
          "📝 Solicitante (Producción)",
          "👷‍♂️ Técnico de Mantenimiento",
          "📊 Visualizador",
          "🛠️ Administrador",
      ],
  )

  df_deptos_system = cargar_departamentos_df()
  df_tec_system = cargar_tecnicos_df()

  if "📊 Visualizador" in tipo_login:
    if st.sidebar.button(
        "Ingresar como Visualizador", use_container_width=True
    ):
      st.session_state["sesion_activa"] = True
      st.session_state["rol_usuario"] = "Visualizador"
      st.session_state["nombre_usuario"] = "Visualizador"
      st.rerun()
  else:
    with st.sidebar.form("form_login_global"):
      if "Solicitante" in tipo_login:
        usuario_sel = st.selectbox(
            "Departamento", df_deptos_system["Departamento"]
        )
      elif "Técnico" in tipo_login:
        usuario_sel = st.selectbox("Técnico", df_tec_system["Tecnico"])
      else:
        usuario_sel = "Acceso General"

      pass_ingresada = st.text_input("Contraseña", type="password")
      btn_entrar = st.form_submit_button(
          "Iniciar Sesión", use_container_width=True
      )

      if btn_entrar:
        if "Solicitante" in tipo_login:
          match = df_deptos_system[
              df_deptos_system["Departamento"] == usuario_sel
          ]
          if (
              not match.empty
              and str(match["Password"].values[0]).strip()
              == pass_ingresada.strip().replace(".0", "")
          ):
            st.session_state["sesion_activa"] = True
            st.session_state["rol_usuario"] = "Solicitante"
            st.session_state["nombre_usuario"] = usuario_sel
            st.rerun()
          else:
            st.error("Contraseña incorrecta.")

        elif "Técnico" in tipo_login:
          match = df_tec_system[df_tec_system["Tecnico"] == usuario_sel]
          if (
              not match.empty
              and str(match["Password"].values[0]).strip()
              == pass_ingresada.strip().replace(".0", "")
          ):
            st.session_state["sesion_activa"] = True
            st.session_state["rol_usuario"] = "Tecnico"
            st.session_state["nombre_usuario"] = usuario_sel
            st.rerun()
          else:
            st.error("Contraseña incorrecta.")

        elif "Administrador" in tipo_login:
          if pass_ingresada.strip() == "avangardmtto22":
            st.session_state["sesion_activa"] = True
            st.session_state["rol_usuario"] = "Admin"
            st.session_state["nombre_usuario"] = "Administrador"
            st.rerun()
          else:
            st.error("Contraseña de administrador incorrecta.")
else:
  st.sidebar.success(
      f"Sesión activa:\n**{st.session_state['nombre_usuario']}**"
  )
  if st.sidebar.button("Cerrar Sesión", use_container_width=True):
    st.session_state["sesion_activa"] = False
    st.session_state["rol_usuario"] = None
    st.session_state["nombre_usuario"] = None
    st.rerun()

st.sidebar.markdown("---")

# Validar en qué sección estamos según la sesión activa
if not st.session_state["sesion_activa"]:
  st.warning(
      "👈 Por favor, inicia sesión en el menú lateral para usar el sistema."
  )
else:
  rol = st.session_state["rol_usuario"]

  # ---------------------------------------------------------
  # CATEGORÍA 1: SOLICITANTE (PRODUCCIÓN)
  # ---------------------------------------------------------
  if rol == "Solicitante":
    depto_actual = st.session_state["nombre_usuario"]
    st.subheader(
        f"📝 Solicitar Orden de Mantenimiento - Departamento: {depto_actual}"
    )
    st.markdown(
        "Reporta una falla o necesidad de ajuste directamente al área de"
        " mantenimiento."
    )

    lista_areas = ["Selecciona un área..."] + cargar_areas()

    with st.form("form_solicitud_produccion"):
      area_sol = st.selectbox("Área / Nave", lista_areas)
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

      submitted_sol = st.form_submit_button(
          "Enviar Solicitud a Mantenimiento", use_container_width=True
      )

      if submitted_sol:
        if area_sol == "Selecciona un área...":
          st.error("Selecciona el área correspondiente.")
        elif not equipo_sol or not desc_sol:
          st.warning("Completa el equipo y la descripción de la falla.")
        else:
          nueva_ot = {
              "Fecha": datetime.now().strftime("%Y-%m-%d"),
              "Turno": turno_sol,
              "Tecnico": "Pendiente de Asignar",
              "Departamento": depto_actual,
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
          st.success(f"✅ ¡Solicitud {num_ot_generado} enviada con éxito!")

    st.markdown("---")
    st.markdown("### 📋 Mis Órdenes Abiertas / En Seguimiento")
    st.markdown(
        "Aquí puedes visualizar el estatus actual de tus reportes enviados:"
    )

    df_mis_ordenes = cargar_datos_db(
        "SELECT id, Fecha, Turno, Tecnico, Area, Equipo, NumOrden,"
        " TipoMantenimiento, HoraEmision, HoraCierre, HoraConformidad, Estado,"
        " Descripcion FROM ordenes WHERE Departamento = ?",
        params=(depto_actual,),
    )

    if df_mis_ordenes.empty:
      st.info("No tienes órdenes registradas en este momento.")
    else:
      for index, row in df_mis_ordenes.iterrows():
        ot_id = row["id"]
        estado_ot = row["Estado"]
        h_conf = str(row["HoraConformidad"])

        if h_conf != "--:--" and h_conf:
          color_badge = "🟢 **[Visto Bueno Otorgado]**"
          borde_markdown = (
              ":green[**Orden Completada y Validada con Conformidad**]"
          )
        elif estado_ot == "Cerrada":
          color_badge = "🟡 **[Cerrada - Pendiente de Visto Bueno]**"
          borde_markdown = ":orange[**Atendida por Mantenimiento**]"
        else:
          color_badge = f"🔵 **[{estado_ot}]**"
          borde_markdown = f"**Estado:** {estado_ot}"

        with st.expander(
            f"[{row['NumOrden']}] Área: {row['Area']} | Equipo:"
            f" {row['Equipo']} | {color_badge}"
        ):
          st.markdown(borde_markdown)
          st.write(f"**Técnico Atendió:** {row['Tecnico']}")
          st.write(f"**Descripción:** {row['Descripcion']}")
          st.write(f"**Hora de Cierre:** {row['HoraCierre']}")
          st.write(f"**Visto Bueno / Conformidad:** {h_conf}")

          if estado_ot == "Cerrada" and (h_conf == "--:--" or not h_conf):
            if st.button(
                f"Dar Visto Bueno (Conformidad) - {row['NumOrden']}",
                key=f"btn_conf_{ot_id}",
            ):
              hora_actual = datetime.now().strftime("%H:%M")
              actualizar_conformidad_db(ot_id, hora_actual)
              st.success(
                  "✅ Visto bueno registrado correctamente a las"
                  f" {hora_actual}."
              )
              st.rerun()
          elif h_conf != "--:--" and h_conf:
            st.success(f"✔️ Esta orden ya cuenta con visto bueno ({h_conf}).")

  # ---------------------------------------------------------
  # CATEGORÍA 2: TÉCNICO DE MANTENIMIENTO
  # ---------------------------------------------------------
  elif rol == "Tecnico":
    tec_actual = st.session_state["nombre_usuario"]
    st.subheader(f"👷‍♂️ Panel de Trabajo - Técnico: {tec_actual}")
    st.markdown(
        "Atiende solicitudes nuevas o gestiona aquellas en espera asignadas a"
        " ti o disponibles en general."
    )
    st.markdown(
        "💡 **Código de colores:** 🔴 **Rojo** (Abiertas / Sin técnico"
        " asignado), 🔵 **Azul** (En espera / Pausadas)."
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
      for index, row in df_pendientes.iterrows():
        ot_id = row["id"]
        estado_actual_ot = row["Estado"]
        tec_en_bd = str(row["Tecnico"]).strip()

        es_mio = tec_en_bd == tec_actual
        esta_libre = tec_en_bd == "Pendiente de Asignar"

        # Definir color de contenedor según estatus y si requiere técnico
        if estado_actual_ot == "Abierta" or esta_libre:
          # ROJO / ROSA CLARO: Abiertas o sin técnico
          estilo_color = "background-color: #f8d7da; padding: 15px; border-radius: 8px; border-left: 6px solid #dc3545; margin-bottom: 15px;"
          badge_estado = (
              "🔴 **[ESTADO: ABIERTA / SIN TÉCNICO ASIGNADO]**"
          )
        elif estado_actual_ot == "En Espera":
          # AZUL CLARO: En espera (refacción o externo)
          estilo_color = "background-color: #cce5ff; padding: 15px; border-radius: 8px; border-left: 6px solid #004085; margin-bottom: 15px;"
          badge_estado = "🔵 **[ESTADO: EN ESPERA / PAUSADA]**"
        else:
          estilo_color = "background-color: #f1f3f5; padding: 15px; border-radius: 8px; border-left: 6px solid #6c757d; margin-bottom: 15px;"
          badge_estado = f"⚪ **[ESTADO: {estado_actual_ot}]**"

        # Contenedor visual coloreado
        with st.container():
          st.markdown(
              f"""
                    <div style="{estilo_color}">
                        <h4>[{row['NumOrden']}] Área: {row['Area']} | Equipo: {row['Equipo']}</h4>
                        <p>{badge_estado} | <b>Depto:</b> {row.get('Departamento', 'N/D')} | <b>Técnico:</b> {tec_en_bd}</p>
                        <p><b>Descripción:</b> {row['Descripcion']}</p>
                    </div>
                    """,
              unsafe_allow_html=True,
          )

          # Opciones de acción dentro de un expander o directo
          with st.expander(
              f"⚙️ Gestionar Orden [{row['NumOrden']}]", expanded=False
          ):
            if esta_libre:
              if st.button(
                  f"Tomar esta Orden y Atender - {row['NumOrden']}",
                  key=f"tomar_{ot_id}",
              ):
                datos_toma = {
                    "Tecnico": tec_actual,
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
                st.success("✅ ¡Orden tomada con éxito!")
                st.rerun()

            elif es_mio or estado_actual_ot == "En Espera":
              with st.form(f"form_cierre_{ot_id}"):
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                  clasificacion_trabajo = st.selectbox(
                      "Clasificación de Trabajo",
                      [
                          "Correctivo",
                          "Ajuste",
                          "Configuracion de linea",
                          "Mejora",
                      ],
                      key=f"tipo_{ot_id}",
                  )
                with col_t2:
                  accion_orden = st.selectbox(
                      "Acción sobre la Orden",
                      [
                          "Finalizar y Cerrar Orden",
                          "Poner en Espera (Falta Refacción)",
                          "Poner en Espera (Servicio Externo)",
                          "Liberar Orden (Devolver a Pendientes)",
                      ],
                      key=f"accion_{ot_id}",
                  )

                desc_tec = st.text_area(
                    "Diagnóstico o Notas de Avance",
                    value=row["Descripcion"],
                    key=f"desc_{ot_id}",
                )

                btn_ejecutar = st.form_submit_button(
                    "Ejecutar Acción", use_container_width=True
                )

                if btn_ejecutar:
                  if accion_orden == "Liberar Orden (Devolver a Pendientes)":
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
                    st.success("ℹ️ Orden devuelta a pendientes.")
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
                    st.success("⚠️ Orden marcada como En Espera.")
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

                      min_esp = max(0, int((dt_r - dt_e).total_seconds() / 60))
                      min_trab = max(
                          0, int((dt_c - dt_r).total_seconds() / 60)
                      )
                      min_tot = max(
                          0, int((dt_c - dt_e).total_seconds() / 60)
                      )

                      datos_actualizados = {
                          "Tecnico": tec_actual,
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
                      st.success(
                          f"✅ Orden {row['NumOrden']} cerrada con éxito."
                      )
                      st.rerun()
                    except ValueError:
                      st.error("Error al procesar las horas automáticas.")

          st.markdown("<br>", unsafe_allow_html=True)

  # ---------------------------------------------------------
  # CATEGORÍA 3: VISUALIZADOR
  # ---------------------------------------------------------
  elif rol == "Visualizador":
    st.subheader(
        "📊 Panel de Visualización, Seguimiento e Indicadores [BETA]"
    )

    df_all = cargar_datos_db()

    if df_all.empty:
      st.info("Aún no hay registros en la base de datos.")
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
        depto_sel = st.selectbox(
            "Filtrar por Departamento", lista_deptos_filtro
        )

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

        st.markdown("---")
        st.markdown("### 📈 Indicadores y Rendimiento")
        col_ind1, col_ind2 = st.columns(2)

        with col_ind1:
          st.markdown("#### ⚙️ Top de Fallas por Equipo (En Lista)")
          if "Equipo" in df_f.columns and not df_f["Equipo"].empty:
            top_equipos = df_f["Equipo"].value_counts().reset_index()
            top_equipos.columns = ["Equipo", "Total Fallas"]
            st.dataframe(
                top_equipos, use_container_width=True, hide_index=True
            )
          else:
            st.info("No hay datos suficientes de equipos.")

        with col_ind2:
          st.markdown("#### 👷‍♂️ Desglose de Órdenes por Técnico")
          if "Tecnico" in df_f.columns and not df_f["Tecnico"].empty:
            df_tecnicos_resumen = (
                df_f.groupby(["Tecnico", "Estado"])
                .size()
                .unstack(fill_value=0)
                .reset_index()
            )
            st.dataframe(df_tecnicos_resumen, use_container_width=True)
          else:
            st.info("No hay datos suficientes de técnicos.")

        st.markdown("---")
        st.markdown("### 📥 Exportar Reportes")

        csv_data = df_f.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📊 Descargar Reporte Filtrado en CSV (Excel)",
            data=csv_data,
            file_name=f"reporte_mantenimiento_{fecha_sel}.csv",
            mime="text/csv",
            use_container_width=True,
        )

        st.markdown("---")
        st.markdown("### 📋 Detalle de Órdenes (Informativo)")
        st.markdown(
            "A continuación se enlistan las órdenes filtradas. Código de"
            " colores: 🔴 **Rojo** (Abiertas o sin técnico), 🟡 **Amarillo**"
            " (Cerradas pendientes de visto bueno), 🔵 **Azul** (En espera), 🟢"
            " **Verde** (Completadas)."
        )

        # Función para aplicar estilos condicionales y marcar con colores en el visualizador
        def destacar_ordenes_visualizador(row):
          estado = str(row["Estado"])
          tec = str(row["Tecnico"])
          h_conf = str(row["HoraConformidad"])

          # 1. Órdenes Abiertas o sin técnico asignado -> ROJO
          if estado == "Abierta" or tec == "Pendiente de Asignar":
            return [
                "background-color: #f8d7da; color: #721c24;" for _ in row.index
            ]
          # 2. Órdenes Cerradas pendientes de visto bueno -> AMARILLO
          elif estado == "Cerrada" and (
              h_conf == "--:--" or h_conf == "nan" or not h_conf
          ):
            return [
                "background-color: #fff3cd; color: #856404;" for _ in row.index
            ]
          # 3. Órdenes en espera (refacción / externo) -> AZUL
          elif estado == "En Espera":
            return [
                "background-color: #cce5ff; color: #004085;" for _ in row.index
            ]
          # 4. Órdenes con visto bueno completo -> VERDE
          elif h_conf != "--:--" and h_conf != "nan" and h_conf:
            return [
                "background-color: #d4edda; color: #155724;" for _ in row.index
            ]
          else:
            return ["" for _ in row.index]

        try:
          st.dataframe(
              df_f.style.apply(destacar_ordenes_visualizador, axis=1),
              use_container_width=True,
          )
        except Exception:
          st.dataframe(df_f, use_container_width=True)

  # ---------------------------------------------------------
  # CATEGORÍA 4: ADMINISTRADOR (GESTIÓN TOTAL)
  # ---------------------------------------------------------
  elif rol == "Admin":
    st.subheader("🛠️ Panel de Administración del Sistema")
    st.markdown(
        "Gestiona los técnicos autorizados, los departamentos solicitantes y"
        " las áreas de planta."
    )

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
