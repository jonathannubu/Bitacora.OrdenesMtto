from datetime import datetime, timedelta
import io
import os
import sqlite3
from fpdf import FPDF
import pandas as pd
import streamlit as st

# Base de datos SQLite unificada exclusiva para la versión BETA
DB_FILE = "bitacora_beta.db"
TECNICOS_FILE = "tecnicos_beta.csv"
AREAS_FILE = "areas_beta.csv"
DEPTOS_FILE = "departamentos_beta.csv"
EQUIPOS_FILE = "equipos_beta.csv"  # <-- NUEVO: Archivo para catálogo de equipos


# --- CONFIGURACIÓN DE BASE DE DATOS (CERO PÉRDIDA DE DATOS) ---
def inicializar_bd():
  conn = sqlite3.connect(DB_FILE)
  cursor = conn.cursor()

  # Tabla principal de órdenes
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
            FechaCierre TEXT,
            HoraConformidad TEXT,
            MinutosEspera INTEGER,
            MinutosTrabajo INTEGER,
            MinutosTotalOT INTEGER,
            DescripcionFalla TEXT,
            TrabajoRealizado TEXT,
            Estado TEXT,
            EvalEPP TEXT,
            EvalAreaLimpia TEXT,
            EvalActitud TEXT,
            EvalRecomendacion TEXT,
            EvalCausa TEXT,
            ComentarioCalificacion TEXT
        )
    """)

  # Tabla para llevar el control del folio consecutivo iniciando en 000001
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS contador_folios (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            ultimo_folio INTEGER
        )
    """)
  cursor.execute("INSERT OR IGNORE INTO contador_folios (id, ultimo_folio) VALUES (1, 0)")

  columnas_requeridas = [
      ("FechaCierre", "TEXT"),
      ("DescripcionFalla", "TEXT"),
      ("TrabajoRealizado", "TEXT"),
      ("EvalEPP", "TEXT"),
      ("EvalAreaLimpia", "TEXT"),
      ("EvalActitud", "TEXT"),
      ("EvalRecomendacion", "TEXT"),
      ("EvalCausa", "TEXT"),
      ("ComentarioCalificacion", "TEXT"),
  ]

  for col_nombre, col_tipo in columnas_requeridas:
    try:
      cursor.execute(f"ALTER TABLE ordenes ADD COLUMN {col_nombre} {col_tipo}")
    except sqlite3.OperationalError:
      pass

  try:
    cursor.execute(
        "UPDATE ordenes SET DescripcionFalla = Descripcion WHERE (DescripcionFalla IS NULL OR DescripcionFalla = '') AND Descripcion IS NOT NULL"
    )
  except sqlite3.OperationalError:
    pass

  conn.commit()
  conn.close()


def obtener_siguiente_folio():
  conn = sqlite3.connect(DB_FILE)
  cursor = conn.cursor()
  cursor.execute("SELECT ultimo_folio FROM contador_folios WHERE id = 1")
  res = cursor.fetchone()
  siguiente = (res[0] if res else 0) + 1
  cursor.execute("UPDATE contador_folios SET ultimo_folio = ? WHERE id = 1", (siguiente,))
  conn.commit()
  conn.close()
  return f"OT-{siguiente:06d}"


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
            HoraEmision, HoraRecepcion, HoraCierre, FechaCierre, HoraConformidad, 
            MinutosEspera, MinutosTrabajo, MinutosTotalOT, DescripcionFalla, TrabajoRealizado, Estado
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
          datos["FechaCierre"],
          datos["HoraConformidad"],
          datos["MinutosEspera"],
          datos["MinutosTrabajo"],
          datos["MinutosTotalOT"],
          datos["DescripcionFalla"],
          datos["TrabajoRealizado"],
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
        UPDATE ordenes SET Tecnico=?, TipoMantenimiento=?, HoraRecepcion=?, HoraCierre=?, FechaCierre=?, HoraConformidad=?, 
                           MinutosEspera=?, MinutosTrabajo=?, MinutosTotalOT=?, TrabajoRealizado=?, Estado=?
        WHERE id=?
    """,
      (
          datos["Tecnico"],
          datos["TipoMantenimiento"],
          datos["HoraRecepcion"],
          datos["HoraCierre"],
          datos["FechaCierre"],
          datos["HoraConformidad"],
          datos["MinutosEspera"],
          datos["MinutosTrabajo"],
          datos["MinutosTotalOT"],
          datos["TrabajoRealizado"],
          datos["Estado"],
          id_orden,
      ),
  )
  conn.commit()
  conn.close()


def actualizar_conformidad_con_evaluacion_db(
    id_orden, hora_con, evals, comentario
):
  conn = sqlite3.connect(DB_FILE)
  cursor = conn.cursor()
  cursor.execute(
      """
        UPDATE ordenes SET HoraConformidad=?, EvalEPP=?, EvalAreaLimpia=?, EvalActitud=?, EvalRecomendacion=?, EvalCausa=?, ComentarioCalificacion=? WHERE id=?
    """,
      (
          hora_con,
          evals["EPP"],
          evals["AreaLimpia"],
          evals["Actitud"],
          evals["Recomendacion"],
          evals["Causa"],
          comentario,
          id_orden,
      ),
  )
  conn.commit()
  conn.close()


def eliminar_orden_db(id_orden):
  conn = sqlite3.connect(DB_FILE)
  cursor = conn.cursor()
  cursor.execute("DELETE FROM ordenes WHERE id = ?", (id_orden,))
  conn.commit()
  conn.close()


# --- GENERADOR DE PDF PROFESIONAL (fpdf2) ---
def generar_pdf_orden(row):
  pdf = FPDF(orientation="P", unit="mm", format="A4")
  pdf.add_page()

  pdf.set_font("helvetica", "B", 16)
  pdf.cell(
      0,
      10,
      "AVANGARD LABS - ORDEN DE TRABAJO DE MANTENIMIENTO",
      new_x="LMARGIN",
      new_y="NEXT",
      align="C",
  )

  pdf.set_font("helvetica", "", 10)
  pdf.cell(
      0,
      6,
      f"Fecha de Emisión: {row.get('Fecha', '')} | Folio: {row.get('NumOrden', '')}",
      new_x="LMARGIN",
      new_y="NEXT",
      align="C",
  )
  pdf.ln(4)

  pdf.set_font("helvetica", "B", 11)
  pdf.set_fill_color(220, 220, 220)
  pdf.cell(0, 7, "  1. DATOS GENERALES", new_x="LMARGIN", new_y="NEXT", fill=True)

  pdf.set_font("helvetica", "", 10)
  col_w = 95
  pdf.cell(
      col_w,
      6,
      f"Departamento Solicitante: {row.get('Departamento', '')}",
      new_x="RIGHT",
      new_y="TOP",
  )
  pdf.cell(
      col_w, 6, f"Área / Línea: {row.get('Area', '')}", new_x="LMARGIN", new_y="NEXT"
  )

  pdf.cell(
      col_w,
      6,
      f"Equipo o Máquina: {row.get('Equipo', '')}",
      new_x="RIGHT",
      new_y="TOP",
  )
  pdf.cell(
      col_w,
      6,
      f"Turno: {row.get('Turno', '')}",
      new_x="LMARGIN",
      new_y="NEXT",
  )

  pdf.cell(
      col_w,
      6,
      f"Técnico Asignado: {row.get('Tecnico', '')}",
      new_x="RIGHT",
      new_y="TOP",
  )
  pdf.cell(
      col_w,
      6,
      f"Estado Actual: {row.get('Estado', '')}",
      new_x="LMARGIN",
      new_y="NEXT",
  )
  pdf.cell(
      0,
      6,
      f"Tipo de Mantenimiento: {row.get('TipoMantenimiento', '')}",
      new_x="LMARGIN",
      new_y="NEXT",
  )
  pdf.ln(3)

  pdf.set_font("helvetica", "B", 11)
  pdf.cell(0, 7, "  2. CONTROL DE TIEMPOS", new_x="LMARGIN", new_y="NEXT", fill=True)

  pdf.set_font("helvetica", "", 10)
  pdf.cell(
      col_w,
      6,
      f"Hora Emisión: {row.get('HoraEmision', '--:--')}",
      new_x="RIGHT",
      new_y="TOP",
  )
  pdf.cell(
      col_w,
      6,
      f"Hora Recepción Técnico: {row.get('HoraRecepcion', '--:--')}",
      new_x="LMARGIN",
      new_y="NEXT",
  )

  f_cierre = (
      row.get("FechaCierre")
      if pd.notna(row.get("FechaCierre"))
      and str(row.get("FechaCierre")).strip() != ""
      else "--/--/--"
  )
  pdf.cell(
      col_w,
      6,
      f"Cierre: {f_cierre} - {row.get('HoraCierre', '--:--')}",
      new_x="RIGHT",
      new_y="TOP",
  )
  pdf.cell(
      col_w,
      6,
      f"Hora Conformidad: {row.get('HoraConformidad', '--:--')}",
      new_x="LMARGIN",
      new_y="NEXT",
  )

  pdf.cell(
      col_w,
      6,
      f"Minutos de Espera: {row.get('MinutosEspera', 0)} min",
      new_x="RIGHT",
      new_y="TOP",
  )
  pdf.cell(
      col_w,
      6,
      f"Minutos de Trabajo: {row.get('MinutosTrabajo', 0)} min",
      new_x="LMARGIN",
      new_y="NEXT",
  )
  pdf.cell(
      0,
      6,
      f"Tiempo Total OT: {row.get('MinutosTotalOT', 0)} min",
      new_x="LMARGIN",
      new_y="NEXT",
  )
  pdf.ln(3)

  pdf.set_font("helvetica", "B", 11)
  pdf.cell(
      0,
      7,
      "  3. DESCRIPCIÓN DE LA FALLA (SOLICITUD)",
      new_x="LMARGIN",
      new_y="NEXT",
      fill=True,
  )
  pdf.set_font("helvetica", "", 10)
  desc_falla = row.get("DescripcionFalla")
  if not desc_falla or str(desc_falla) == "nan":
    desc_falla = row.get("Descripcion", "Sin descripción registrada.")
  pdf.multi_cell(0, 6, str(desc_falla))
  pdf.ln(2)

  pdf.set_font("helvetica", "B", 11)
  pdf.cell(
      0,
      7,
      "  4. TRABAJO REALIZADO / DIAGNÓSTICO (TÉCNICO)",
      new_x="LMARGIN",
      new_y="NEXT",
      fill=True,
  )
  pdf.set_font("helvetica", "", 10)
  trabajo_realizado = row.get("TrabajoRealizado")
  if not trabajo_realizado or str(trabajo_realizado) == "nan":
    trabajo_realizado = "Pendiente o sin notas técnicas registradas."
  pdf.multi_cell(0, 6, str(trabajo_realizado))
  pdf.ln(3)

  pdf.set_font("helvetica", "B", 11)
  pdf.cell(
      0,
      7,
      "  5. EVALUACIÓN DEL SERVICIO (CONFORMIDAD)",
      new_x="LMARGIN",
      new_y="NEXT",
      fill=True,
  )
  pdf.set_font("helvetica", "", 10)

  eval_epp = row.get("EvalEPP")
  if eval_epp is not None and str(eval_epp).strip() != "" and str(eval_epp) != "nan":
    pdf.cell(
        0,
        6,
        f"- Utilizó equipo de protección personal (EPP): {row.get('EvalEPP', 'N/D')}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(
        0,
        6,
        f"- Entregó el área limpia y ordenada: {row.get('EvalAreaLimpia', 'N/D')}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(
        0,
        6,
        f"- Mostró actitud de servicio y profesionalismo: {row.get('EvalActitud', 'N/D')}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(
        0,
        6,
        f"- Recomendó acciones para su no ocurrencia: {row.get('EvalRecomendacion', 'N/D')}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.cell(
        0,
        6,
        f"- Explicó la causa que originó la falla: {row.get('EvalCausa', 'N/D')}",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    comentario = row.get("ComentarioCalificacion")
    if comentario and str(comentario) != "nan":
      pdf.cell(
          0,
          6,
          f"- Comentarios adicionales: {comentario}",
          new_x="LMARGIN",
          new_y="NEXT",
      )
  else:
    pdf.cell(
        0,
        6,
        "Orden pendiente de Conformidad o sin evaluación registrada.",
        new_x="LMARGIN",
        new_y="NEXT",
    )

  return bytes(pdf.output())


# Gestión de Técnicos
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


# Gestión de Departamentos
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


# Gestión de Áreas / Líneas
def cargar_areas():
  if os.path.exists(AREAS_FILE):
    df_area = pd.read_csv(AREAS_FILE, dtype=str)
    return df_area["Area"].fillna("").astype(str).str.strip().tolist()
  else:
    areas_iniciales = [
        "Línea 1 - Envasado",
        "Línea 2 - Producción",
        "Línea 3 - Empaque",
        "Mantenimiento General",
    ]
    df_area = pd.DataFrame({"Area": areas_iniciales})
    df_area.to_csv(AREAS_FILE, index=False)
    return areas_iniciales


def agregar_area(nueva_area):
  areas = cargar_areas()
  nueva_area = str(nueva_area).strip()
  if not nueva_area:
    return False, "El nombre del área o línea no puede estar vacío."
  if nueva_area in areas:
    return False, "Esta área o línea ya existe."
  areas.append(nueva_area)
  pd.DataFrame({"Area": areas}).to_csv(AREAS_FILE, index=False)
  return True, f"Área / Línea '{nueva_area}' agregada."


def eliminar_area(area_a_borrar):
  areas = cargar_areas()
  if len(areas) <= 1:
    return False, "Debes mantener al menos un área o línea."
  if area_a_borrar in areas:
    areas.remove(area_a_borrar)
    pd.DataFrame({"Area": areas}).to_csv(AREAS_FILE, index=False)
    return True, "Área / Línea eliminada."
  return False, "El área o línea no existe."


# --- NUEVO: Gestión de Equipos / Máquinas ---
def cargar_equipos():
  if os.path.exists(EQUIPOS_FILE):
    df_eq = pd.read_csv(EQUIPOS_FILE, dtype=str)
    return df_eq["Equipo"].fillna("").astype(str).str.strip().tolist()
  else:
    equipos_iniciales = [
        "Línea 2 - Envasadora",
        "Banda Transportadora Principal",
        "Selladora Automática",
        "Compresor de Aire 1",
    ]
    df_eq = pd.DataFrame({"Equipo": equipos_iniciales})
    df_eq.to_csv(EQUIPOS_FILE, index=False)
    return equipos_iniciales


def agregar_equipo(nuevo_equipo):
  equipos = cargar_equipos()
  nuevo_equipo = str(nuevo_equipo).strip()
  if not nuevo_equipo:
    return False, "El nombre del equipo no puede estar vacío."
  if nuevo_equipo in equipos:
    return False, "Este equipo o máquina ya existe en el catálogo."
  equipos.append(nuevo_equipo)
  pd.DataFrame({"Equipo": equipos}).to_csv(EQUIPOS_FILE, index=False)
  return True, f"Equipo '{nuevo_equipo}' agregado al catálogo."


def eliminar_equipo(equipo_a_borrar):
  equipos = cargar_equipos()
  if len(equipos) <= 1:
    return False, "Debes mantener al menos un equipo registrado."
  if equipo_a_borrar in equipos:
    equipos.remove(equipo_a_borrar)
    pd.DataFrame({"Equipo": equipos}).to_csv(EQUIPOS_FILE, index=False)
    return True, "Equipo eliminado del catálogo."
  return False, "El equipo no existe."


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

    lista_areas = ["Selecciona un área / línea..."] + cargar_areas()
    
    # Catálogo unificado de equipos para evitar errores de dedo
    lista_equipos_catalogo = cargar_equipos()
    opciones_equipo_form = ["Selecciona un equipo o máquina..."] + lista_equipos_catalogo + ["➕ Otro (Especificar manualmente)"]

    with st.form("form_solicitud_produccion"):
      area_sol = st.selectbox("Área / Línea", lista_areas)
      turno_sol = st.selectbox(
          "Turno Actual", ["Matutino", "Vespertino", "Nocturno"]
      )
      
      # Selección unificada de equipo
      tipo_sel_equipo = st.selectbox("Equipo o Máquina", opciones_equipo_form)
      
      equipo_manual = ""
      if tipo_sel_equipo == "➕ Otro (Especificar manualmente)":
        equipo_manual = st.text_input(
            "Especificar nombre del equipo o máquina", placeholder="Ej. Etiquetadora Línea 3"
        )

      # Folio consecutivo automático con prefijo OT- y formato OT-000001
      num_ot_generado = obtener_siguiente_folio()
      st.info(f"📌 Folio Asignado Automáticamente: **{num_ot_generado}**")

      desc_sol = st.text_area(
          "Descripción de la Falla",
          placeholder=(
              "Ej. Se detuvo la banda principal por atasco en sensor..."
          ),
      )

      submitted_sol = st.form_submit_button(
          "Enviar Solicitud a Mantenimiento", use_container_width=True
      )

      if submitted_sol:
        # Determinar el equipo final seleccionado
        if tipo_sel_equipo == "➕ Otro (Especificar manualmente)":
          equipo_final = equipo_manual.strip()
        else:
          equipo_final = tipo_sel_equipo

        if area_sol == "Selecciona un área / línea...":
          st.error("Selecciona el área o línea correspondiente.")
        elif tipo_sel_equipo == "Selecciona un equipo o máquina...":
          st.warning("Selecciona un equipo o máquina del catálogo.")
        elif tipo_sel_equipo == "➕ Otro (Especificar manualmente)" and not equipo_final:
          st.warning("Escribe el nombre del equipo o máquina personalizado.")
        elif not desc_sol:
          st.warning("Completa la descripción de la falla.")
        else:
          nueva_ot = {
              "Fecha": datetime.now().strftime("%Y-%m-%d"),
              "Turno": turno_sol,
              "Tecnico": "Pendiente de Asignar",
              "Departamento": depto_actual,
              "Area": area_sol,
              "Equipo": equipo_final,
              "NumOrden": num_ot_generado,
              "TipoMantenimiento": "Correctivo",
              "HoraEmision": datetime.now().strftime("%H:%M"),
              "HoraRecepcion": "--:--",
              "HoraCierre": "--:--",
              "FechaCierre": "",
              "HoraConformidad": "--:--",
              "MinutosEspera": 0,
              "MinutosTrabajo": 0,
              "MinutosTotalOT": 0,
              "DescripcionFalla": desc_sol,
              "TrabajoRealizado": "Pendiente de atención técnica",
              "Estado": "Abierta",
          }
          guardar_nueva_solicitud(nueva_ot)
          st.success(f"✅ ¡Solicitud {num_ot_generado} enviada con éxito!")

    st.markdown("---")
    st.markdown("### 📋 Mis Órdenes Abiertas / En Seguimiento")

    df_mis_ordenes = cargar_datos_db(
        "SELECT id, Fecha, Turno, Tecnico, Departamento, Area, Equipo, NumOrden,"
        " TipoMantenimiento, HoraEmision, HoraRecepcion, HoraCierre,"
        " FechaCierre, HoraConformidad, MinutosEspera, MinutosTrabajo,"
        " MinutosTotalOT, Estado, DescripcionFalla, TrabajoRealizado, EvalEPP,"
        " EvalAreaLimpia, EvalActitud, EvalRecomendacion, EvalCausa,"
        " ComentarioCalificacion FROM ordenes WHERE Departamento = ?",
        params=(depto_actual,),
    )

    if df_mis_ordenes.empty:
      st.info("No tienes órdenes registradas en este momento.")
    else:
      fecha_hoy_str = datetime.now().strftime("%Y-%m-%d")
      ordenes_a_mostrar = []

      for index, row in df_mis_ordenes.iterrows():
        h_conf = str(row["HoraConformidad"])
        fecha_emision = str(row["Fecha"])
        tiene_conf = h_conf != "--:--" and h_conf != ""

        if tiene_conf and fecha_emision != fecha_hoy_str:
          continue
        ordenes_a_mostrar.append(row)

      if not ordenes_a_mostrar:
        st.info("No hay órdenes pendientes ni recientes para mostrar hoy.")
      else:
        for row in ordenes_a_mostrar:
          ot_id = row["id"]
          estado_ot = row["Estado"]
          h_conf = str(row["HoraConformidad"])
          eval_epp = row.get("EvalEPP")

          desc_falla_txt = row.get("DescripcionFalla")
          if not desc_falla_txt or str(desc_falla_txt) == "nan":
            desc_falla_txt = row.get("Descripcion", "Sin descripción")

          trabajo_txt = row.get("TrabajoRealizado")
          if not trabajo_txt or str(trabajo_txt) == "nan":
            trabajo_txt = "Pendiente"

          if h_conf != "--:--" and h_conf:
            color_badge = "🟢 **[Conformidad Otorgada]**"
            borde_markdown = (
                ":green[**Orden Completada y Validada con Conformidad**]"
            )
          elif estado_ot == "Cerrada":
            color_badge = "🟡 **[Cerrada - Pendiente de Conformidad]**"
            borde_markdown = ":orange[**Atendida por Mantenimiento**]"
          else:
            color_badge = f"🔵 **[{estado_ot}]**"
            borde_markdown = f"**Estado:** {estado_ot}"

          with st.expander(
              f"[{row['NumOrden']}] Área/Línea: {row['Area']} | Equipo:"
              f" {row['Equipo']} | {color_badge}"
          ):
            st.markdown(borde_markdown)
            st.write(f"**Técnico Atendió:** {row['Tecnico']}")
            st.write(f"**Descripción de la Falla:** {desc_falla_txt}")
            st.write(f"**Trabajo Realizado:** {trabajo_txt}")
            st.write(
                f"**Cierre:** {row.get('FechaCierre', '')} -"
                f" {row['HoraCierre']}"
            )
            st.write(f"**Conformidad:** {h_conf}")

            pdf_bytes = generar_pdf_orden(row)
            st.download_button(
                label=f"📥 Descargar Orden {row['NumOrden']} en PDF",
                data=pdf_bytes,
                file_name=f"Orden_{row['NumOrden']}.pdf",
                mime="application/pdf",
                key=f"pdf_sol_{ot_id}",
            )

            if (
                eval_epp is not None
                and str(eval_epp).strip() != ""
                and str(eval_epp) != "nan"
            ):
              st.markdown("#### 📋 Evaluación del Servicio Registrada")
              st.write(f"- **Utilizó EPP:** {row.get('EvalEPP')}")
              st.write(
                  f"- **Entregó el área limpia:** {row.get('EvalAreaLimpia')}"
              )
              st.write(
                  f"- **Mostró actitud de servicio:** {row.get('EvalActitud')}"
              )
              st.write(
                  f"- **Recomendó acciones para no ocurrencia:**"
                  f" {row.get('EvalRecomendacion')}"
              )
              st.write(
                  f"- **Explicó la causa que originó la falla:**"
                  f" {row.get('EvalCausa')}"
              )
              if (
                  row.get("ComentarioCalificacion")
                  and str(row.get("ComentarioCalificacion")) != "nan"
              ):
                st.write(
                    f"- **Comentarios:** {row.get('ComentarioCalificacion')}"
                )

            if estado_ot == "Cerrada" and (h_conf == "--:--" or not h_conf):
              with st.form(f"form_conf_{ot_id}"):
                st.markdown("#### 🌟 Evaluación del Servicio de Mantenimiento")
                st.markdown("Valida los siguientes puntos del servicio brindado:")

                chk_epp = st.checkbox(
                    "👷‍♂️ Utilizó equipo de protección personal (EPP)",
                    value=True,
                    key=f"epp_{ot_id}",
                )
                chk_area = st.checkbox(
                    "🧹 Entregó el área limpia y ordenada",
                    value=True,
                    key=f"area_{ot_id}",
                )
                chk_act = st.checkbox(
                    "🤝 Mostró actitud de servicio y profesionalismo",
                    value=True,
                    key=f"act_{ot_id}",
                )
                chk_rec = st.checkbox(
                    "💡 Recomendó acciones para su no ocurrencia",
                    value=True,
                    key=f"rec_{ot_id}",
                )
                chk_causa = st.checkbox(
                    "🔍 Explicó la causa que originó la falla del equipo",
                    value=True,
                    key=f"causa_{ot_id}",
                )

                comentario_ev = st.text_input(
                    "Comentarios u observaciones adicionales",
                    placeholder="Ej. Todo excelente, muy buena atención...",
                    key=f"input_com_{ot_id}",
                )

                btn_enviar_conf = st.form_submit_button(
                    "Confirmar Conformidad y Enviar Evaluación",
                    use_container_width=True,
                )

                if btn_enviar_conf:
                  hora_actual = datetime.now().strftime("%H:%M")
                  evals_dict = {
                      "EPP": "Sí" if chk_epp else "No",
                      "AreaLimpia": "Sí" if chk_area else "No",
                      "Actitud": "Sí" if chk_act else "No",
                      "Recomendacion": "Sí" if chk_rec else "No",
                      "Causa": "Sí" if chk_causa else "No",
                  }
                  actualizar_conformidad_con_evaluacion_db(
                      ot_id, hora_actual, evals_dict, comentario_ev
                  )
                  st.success(
                      "✅ Conformidad y evaluación registradas correctamente a"
                      f" las {hora_actual}."
                  )
                  st.rerun()
            elif h_conf != "--:--" and h_conf:
              st.success(
                  f"✔️ Esta orden ya cuenta con Conformidad ({h_conf})."
              )

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

        desc_falla_txt = row.get("DescripcionFalla")
        if not desc_falla_txt or str(desc_falla_txt) == "nan":
          desc_falla_txt = row.get("Descripcion", "Sin descripción")

        if estado_actual_ot == "En Espera":
          estilo_tarjeta = "border-left: 5px solid #1c83e1; padding-left: 12px; margin-bottom: 12px;"
          badge_estado = "🔵 **En Espera**"
        elif estado_actual_ot == "Abierta" or esta_libre:
          estilo_tarjeta = "border-left: 5px solid #ff4b4b; padding-left: 12px; margin-bottom: 12px;"
          badge_estado = "🔴 **Abierta / Sin Técnico**"
        else:
          estilo_tarjeta = "border-left: 5px solid #808080; padding-left: 12px; margin-bottom: 12px;"
          badge_estado = f"⚪ **{estado_actual_ot}**"

        with st.container():
          st.markdown(
              f"""
                    <div style="{estilo_tarjeta}">
                        <p style="margin-bottom: 4px;"><b>[{row['NumOrden']}]</b> &nbsp;|&nbsp; Área/Línea: <b>{row['Area']}</b> &nbsp;|&nbsp; Equipo: <b>{row['Equipo']}</b> &nbsp;|&nbsp; {badge_estado}</p>
                        <p style="margin-bottom: 4px; color: #555;"><b>Depto:</b> {row.get('Departamento', 'N/D')} &nbsp;|&nbsp; <b>Técnico:</b> {tec_en_bd}</p>
                        <p style="margin-bottom: 0;"><b>Descripción de la Falla:</b> {desc_falla_txt}</p>
                    </div>
                    """,
              unsafe_allow_html=True,
          )

          with st.expander(
              f"⚙️ Gestionar Orden [{row['NumOrden']}]", expanded=False
          ):
            pdf_bytes = generar_pdf_orden(row)
            st.download_button(
                label=f"📥 Descargar Orden {row['NumOrden']} en PDF",
                data=pdf_bytes,
                file_name=f"Orden_{row['NumOrden']}.pdf",
                mime="application/pdf",
                key=f"pdf_tec_{ot_id}",
            )
            st.markdown("---")

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
                    "FechaCierre": row.get("FechaCierre", ""),
                    "HoraConformidad": row["HoraConformidad"],
                    "MinutosEspera": row["MinutosEspera"],
                    "MinutosTrabajo": row["MinutosTrabajo"],
                    "MinutosTotalOT": row["MinutosTotalOT"],
                    "TrabajoRealizado": row.get(
                        "TrabajoRealizado", "En atención..."
                    ),
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

                trabajo_actual_val = row.get("TrabajoRealizado", "")
                if (
                    not trabajo_actual_val
                    or str(trabajo_actual_val) == "nan"
                    or trabajo_actual_val == "Pendiente de atención técnica"
                ):
                  trabajo_actual_val = ""

                desc_tec = st.text_area(
                    "Trabajo Realizado / Diagnóstico Técnico",
                    value=trabajo_actual_val,
                    placeholder=(
                        "Ej. Se reemplazó el sensor dañado, se calibró la"
                        " banda y se probó el equipo exitosamente..."
                    ),
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
                        "FechaCierre": "",
                        "HoraConformidad": row["HoraConformidad"],
                        "MinutosEspera": row["MinutosEspera"],
                        "MinutosTrabajo": row["MinutosTrabajo"],
                        "MinutosTotalOT": row["MinutosTotalOT"],
                        "TrabajoRealizado": desc_tec,
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
                        "FechaCierre": "",
                        "HoraConformidad": "--:--",
                        "MinutosEspera": 0,
                        "MinutosTrabajo": 0,
                        "MinutosTotalOT": 0,
                        "TrabajoRealizado": nota_final_espera,
                        "Estado": "En Espera",
                    }
                    actualizar_orden_db(ot_id, datos_espera)
                    st.success("⚠️ Orden marcada como En Espera.")
                    st.rerun()

                  elif accion_orden == "Finalizar y Cerrar Orden":
                    try:
                      ahora_dt = datetime.now()
                      hora_actual_str = ahora_dt.strftime("%H:%M")
                      fecha_actual_str = ahora_dt.strftime("%Y-%m-%d")

                      h_rec = (
                          row["HoraRecepcion"]
                          if row["HoraRecepcion"] != "--:--"
                          and pd.notna(row["HoraRecepcion"])
                          else (
                              row["HoraEmision"]
                              if row["HoraEmision"] != "--:--"
                              else hora_actual_str
                          )
                      )
                      h_cie = hora_actual_str
                      f_cie = fecha_actual_str
                      h_con = (
                          row["HoraConformidad"]
                          if row["HoraConformidad"] != "--:--"
                          else "--:--"
                      )

                      fecha_emision_str = str(row["Fecha"])
                      dt_emi_time = datetime.strptime(
                          row["HoraEmision"], "%H:%M"
                      ).time()
                      dt_rec_time = datetime.strptime(h_rec, "%H:%M").time()
                      dt_cie_time = datetime.strptime(h_cie, "%H:%M").time()

                      fecha_base = datetime.strptime(
                          fecha_emision_str, "%Y-%m-%d"
                      ).date()
                      fecha_cierre_dt = datetime.strptime(f_cie, "%Y-%m-%d").date()

                      dt_e = datetime.combine(fecha_base, dt_emi_time)
                      dt_r = datetime.combine(fecha_base, dt_rec_time)
                      if dt_r < dt_e:
                        dt_r += timedelta(days=1)

                      dt_c = datetime.combine(fecha_cierre_dt, dt_cie_time)
                      if dt_c < dt_r:
                        dt_c = dt_r

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
                          "FechaCierre": f_cie,
                          "HoraConformidad": h_con,
                          "MinutosEspera": min_esp,
                          "MinutosTrabajo": min_trab,
                          "MinutosTotalOT": min_tot,
                          "TrabajoRealizado": desc_tec,
                          "Estado": "Cerrada",
                      }
                      actualizar_orden_db(ot_id, datos_actualizados)
                      st.success(
                          f"✅ Orden {row['NumOrden']} cerrada con éxito."
                      )
                      st.rerun()
                    except ValueError:
                      st.error("Error al procesar las horas automáticas.")

          st.markdown("---")

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
        st.markdown("### 📋 Detalle de Órdenes y Descarga Individual en PDF")

        for index, row in df_f.iterrows():
          desc_falla_txt = row.get("DescripcionFalla")
          if not desc_falla_txt or str(desc_falla_txt) == "nan":
            desc_falla_txt = row.get("Descripcion", "Sin descripción")

          trabajo_txt = row.get("TrabajoRealizado")
          if not trabajo_txt or str(trabajo_txt) == "nan":
            trabajo_txt = "Pendiente"

          with st.expander(
              f"[{row['NumOrden']}] Área/Línea: {row['Area']} | Equipo:"
              f" {row['Equipo']} | Estado: {row['Estado']}"
          ):
            st.write(f"**Departamento:** {row.get('Departamento', 'N/D')}")
            st.write(f"**Técnico:** {row['Tecnico']}")
            st.write(f"**Descripción de la Falla:** {desc_falla_txt}")
            st.write(f"**Trabajo Realizado:** {trabajo_txt}")

            pdf_bytes = generar_pdf_orden(row)
            st.download_button(
                label=f"📥 Descargar Orden {row['NumOrden']} en PDF",
                data=pdf_bytes,
                file_name=f"Orden_{row['NumOrden']}.pdf",
                mime="application/pdf",
                key=f"pdf_vis_{row['id']}",
            )

  # ---------------------------------------------------------
  # CATEGORÍA 4: ADMINISTRADOR (GESTIÓN TOTAL Y BORRADO DE ÓRDENES)
  # ---------------------------------------------------------
  elif rol == "Admin":
    st.subheader("🛠️ Panel de Administración del Sistema")
    st.markdown(
        "Gestiona los técnicos autorizados, los departamentos solicitantes,"
        " las áreas/líneas de planta, el catálogo de equipos y el control de registros."
    )

    tab_g1, tab_g2, tab_g3, tab_g5, tab_g4 = st.tabs(
        [
            "👥 Gestión de Técnicos",
            "🏢 Gestión de Departamentos",
            "🏭 Gestión de Áreas / Líneas",
            "⚙️ Gestión de Equipos",
            "🗑️ Borrado y Control de Órdenes",
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
      st.markdown("#### Áreas / Líneas Registradas")
      lista_areas_actuales = cargar_areas()

      df_areas_view = pd.DataFrame(
          {"Área / Línea": lista_areas_actuales}
      ).reset_index(drop=True)
      df_areas_view.index = df_areas_view.index + 1
      st.dataframe(df_areas_view, use_container_width=True)

      st.markdown("---")
      st.markdown("#### Agregar Nueva Área o Línea")
      n_area = st.text_input("Nombre de la Nueva Área o Línea")
      if st.button("Guardar Nueva Área / Línea"):
        ex, msg = agregar_area(n_area)
        if ex:
          st.success(msg)
          st.rerun()
        else:
          st.error(msg)

      st.markdown("---")
      st.markdown("#### Eliminar Área / Línea")
      area_a_borrar = st.selectbox(
          "Selecciona área o línea a eliminar", ["Selecciona..."] + lista_areas_actuales
      )
      if st.button("Eliminar Área / Línea"):
        if area_a_borrar != "Selecciona...":
          ex, msg = eliminar_area(area_a_borrar)
          if ex:
            st.success(msg)
            st.rerun()
          else:
            st.error(msg)
        else:
          st.warning("Selecciona un área o línea válida.")

    with tab_g5:
      st.markdown("#### ⚙️ Catálogo Oficial de Equipos / Máquinas")
      lista_equipos_actuales = cargar_equipos()

      df_equipos_view = pd.DataFrame(
          {"Equipo / Máquina": lista_equipos_actuales}
      ).reset_index(drop=True)
      df_equipos_view.index = df_equipos_view.index + 1
      st.dataframe(df_equipos_view, use_container_width=True)

      st.markdown("---")
      st.markdown("#### Agregar Nuevo Equipo o Máquina al Catálogo")
      n_equipo = st.text_input("Nombre del Equipo o Máquina")
      if st.button("Guardar Nuevo Equipo"):
        ex, msg = agregar_equipo(n_equipo)
        if ex:
          st.success(msg)
          st.rerun()
        else:
          st.error(msg)

      st.markdown("---")
      st.markdown("#### Eliminar Equipo del Catálogo")
      equipo_a_borrar = st.selectbox(
          "Selecciona equipo a eliminar", ["Selecciona..."] + lista_equipos_actuales, key="del_eq_sel"
      )
      if st.button("Eliminar Equipo"):
        if equipo_a_borrar != "Selecciona...":
          ex, msg = eliminar_equipo(equipo_a_borrar)
          if ex:
            st.success(msg)
            st.rerun()
          else:
            st.error(msg)
        else:
          st.warning("Selecciona un equipo válido.")

    with tab_g4:
      st.markdown("#### 🗑️ Gestión y Borrado de Órdenes de Trabajo")
      st.markdown(
          "Selecciona una orden por su número de folio (NumOrden) para"
          " eliminarla de la base de datos permanentemente si es necesario."
      )

      df_todas_ots = cargar_datos_db(
          "SELECT id, NumOrden, Fecha, Area, Equipo, Estado, Departamento FROM"
          " ordenes ORDER BY id DESC"
      )

      if df_todas_ots.empty:
        st.info("No hay órdenes registradas en el sistema.")
      else:
        opciones_ots = {
            f"[{row['NumOrden']}] Fecha: {row['Fecha']} | Área/Línea: {row['Area']} | Equipo: {row['Equipo']} ({row['Estado']})": row[
                "id"
            ]
            for index, row in df_todas_ots.iterrows()
        }

        ot_seleccionada_label = st.selectbox(
            "Selecciona la Orden de Trabajo a Borrar",
            ["Selecciona una orden..."] + list(opciones_ots.keys()),
        )

        if ot_seleccionada_label != "Selecciona una orden...":
          id_ot_a_borrar = opciones_ots[ot_seleccionada_label]

          st.warning(
              "⚠️ **Advertencia:** Estás a punto de eliminar permanentemente"
              " esta orden de trabajo de la base de datos."
          )

          confirmar_borrado = st.checkbox(
              "Confirmo que deseo eliminar definitivamente este registro"
          )

          if st.button(
              "🗑️ Eliminar Orden Seleccionada", type="primary"
          ):
            if confirmar_borrado:
              eliminar_orden_db(id_ot_a_borrar)
              st.success(
                  "✅ La orden de trabajo ha sido eliminada exitosamente."
              )
              st.rerun()
            else:
              st.error(
                  "Debes marcar la casilla de confirmación para autorizar el"
                  " borrado."
              )
