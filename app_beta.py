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


# --- CONFIGURACIÓN DE BASE DE DATOS (CERO PÉRDIDA DE DATOS) ---
def inicializar_bd():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        
        # Tabla principal de órdenes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ordenes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                Fecha TEXT,
                Turno TEXT,
                Tecnico TEXT,
                Departamento TEXT,
                AreaLinea TEXT,
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
            ("AreaLinea", "TEXT"),
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


def obtener_siguiente_folio():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ultimo_folio FROM contador_folios WHERE id = 1")
        res = cursor.fetchone()
        siguiente = (res[0] if res else 0) + 1
        cursor.execute("UPDATE contador_folios SET ultimo_folio = ? WHERE id = 1", (siguiente,))
        conn.commit()
    return f"{siguiente:06d}"


def cargar_datos_db(query="SELECT * FROM ordenes", params=()):
    with sqlite3.connect(DB_FILE) as conn:
        try:
            df = pd.read_sql(query, conn, params=params)
            return df
        except Exception:
            return pd.DataFrame()


def guardar_nueva_solicitud(datos):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO ordenes (
                Fecha, Turno, Tecnico, Departamento, AreaLinea, Equipo, NumOrden, TipoMantenimiento, 
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
                datos["AreaLinea"],
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


def actualizar_orden_db(id_orden, datos):
    with sqlite3.connect(DB_FILE) as conn:
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


def actualizar_conformidad_con_evaluacion_db(
    id_orden, hora_con, evals, comentario
):
    with sqlite3.connect(DB_FILE) as conn:
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


def eliminar_orden_db(id_orden):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ordenes WHERE id = ?", (id_orden,))
        conn.commit()


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
        f"Fecha de Emisión: {row.get('Fecha', '')} | Folio: OT-{row.get('NumOrden', '')}",
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
        col_w, 6, f"Área / Línea: {row.get('AreaLinea', '')}", new_x="LMARGIN", new_y="NEXT"
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


# Inicializar Base de Datos Beta
inicializar_bd()

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Avangard Labs Control OT [BETA]",
    page_icon="⚙️",
    layout="wide",
)

# --- ESTILOS CSS GLOBAL ---
st.markdown("""
<style>
    .card-espera { border-left: 5px solid #1c83e1; padding-left: 12px; margin-bottom: 12px; }
    .card-abierta { border-left: 5px solid #ff4b4b; padding-left: 12px; margin-bottom: 12px; }
    .card-otro { border-left: 5px solid #808080; padding-left: 12px; margin-bottom: 12px; }
</style>
""", unsafe_allow_html=True)

if "mensaje_alerta" not in st.session_state:
    st.session_state["mensaje_alerta"] = None

if "sesion_activa" not in st.session_state:
    st.session_state["sesion_activa"] = False
if "rol_usuario" not in st.session_state:
    st.session_state["rol_usuario"] = None
if "nombre_usuario" not in st.session_state:
    st.session_state["nombre_usuario"] = None

st.title("⚙️ Avangard Labs Control OT (Fase Beta)")

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

        with st.form("form_solicitud_produccion"):
            area_sol = st.selectbox("Área / Línea", lista_areas)
            turno_sol = st.selectbox(
                "Turno Actual", ["Matutino", "Vespertino", "Nocturno"]
            )
            equipo_sol = st.text_input(
                "Equipo o Máquina", placeholder="Ej. Línea 2 - Envasadora"
            )

            num_ot_generado = obtener_siguiente_folio()
            st.info(f"📌 Folio Asignado Automáticamente: **OT-{num_ot_generado}**")

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
                if area_sol == "Selecciona un área / línea...":
                    st.error("Selecciona el área o línea correspondiente.")
                elif not equipo_sol or not desc_sol:
                    st.warning("Completa el equipo y la descripción de la falla.")
                else:
                    nueva_ot = {
                        "Fecha": datetime.now().strftime("%Y-%m-%d"),
                        "Turno": turno_sol,
                        "Tecnico": "Pendiente de Asignar",
                        "Departamento": depto_actual,
                        "AreaLinea": area_sol,
                        "Equipo": equipo_sol,
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
                    st.success(f"✅ ¡Solicitud OT-{num_ot_generado} enviada con éxito!")

        st.markdown("---")
        st.subheader(f"📋 Mis Solicitudes ({depto_actual})")
        df_mis_ots = cargar_datos_db(
            "SELECT * FROM ordenes WHERE Departamento = ? ORDER BY id DESC",
            (depto_actual,),
        )
        if df_mis_ots.empty:
            st.info("No has generado solicitudes todavía.")
        else:
            st.dataframe(
                df_mis_ots[
                    [
                        "NumOrden",
                        "Fecha",
                        "AreaLinea",
                        "Equipo",
                        "Estado",
                        "Tecnico",
                    ]
                ],
                use_container_width=True,
            )

            ots_pend_conf = df_mis_ots[
                df_mis_ots["Estado"].isin(["Atendida", "Completada"])
            ]
            if not ots_pend_conf.empty:
                st.markdown(
                    "#### ✍️ Dar Conformidad y Evaluar Servicio Técnico"
                )
                folio_conf = st.selectbox(
                    "Selecciona el Folio para Evaluar",
                    ots_pend_conf["NumOrden"].tolist(),
                )
                row_c = ots_pend_conf[
                    ots_pend_conf["NumOrden"] == folio_conf
                ].iloc[0]

                with st.form(f"form_conf_{folio_conf}"):
                    st.write(f"Evaluando orden: **OT-{folio_conf}**")
                    ev_epp = st.selectbox(
                        "¿Utilizó equipo de protección personal (EPP)?",
                        ["Sí", "No"],
                    )
                    ev_limpia = st.selectbox(
                        "¿Entregó el área limpia y ordenada?", ["Sí", "No"]
                    )
                    ev_actitud = st.selectbox(
                        "¿Mostró actitud de servicio y profesionalismo?",
                        ["Sí", "No"],
                    )
                    ev_recom = st.selectbox(
                        "¿Recomendó acciones para su no ocurrencia?",
                        ["Sí", "No"],
                    )
                    ev_causa = st.selectbox(
                        "¿Explicó la causa que originó la falla?", ["Sí", "No"]
                    )
                    comentario_eval = st.text_area(
                        "Comentarios adicionales (Opcional)"
                    )

                    btn_guardar_conf = st.form_submit_button(
                        "Confirmar y Cerrar Orden"
                    )
                    if btn_guardar_conf:
                        evals = {
                            "EPP": ev_epp,
                            "AreaLimpia": ev_limpia,
                            "Actitud": ev_actitud,
                            "Recomendacion": ev_recom,
                            "Causa": ev_causa,
                        }
                        hora_con_actual = datetime.now().strftime("%H:%M")
                        actualizar_conformidad_con_evaluacion_db(
                            row_c["id"],
                            hora_con_actual,
                            evals,
                            comentario_eval,
                        )
                        with sqlite3.connect(DB_FILE) as conn:
                            cursor = conn.cursor()
                            cursor.execute(
                                "UPDATE ordenes SET Estado = 'Cerrada' WHERE id = ?",
                                (row_c["id"],),
                            )
                            conn.commit()
                        st.success(
                            "✅ ¡Conformidad registrada y Orden Cerrada exitosamente!"
                        )
                        st.rerun()

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

        df_pendientes = cargar_datos_db(
            "SELECT * FROM ordenes WHERE Estado IN ('Abierta', 'En Espera')"
        )

        if df_pendientes.empty:
            st.info("🎉 ¡Excelente trabajo! No hay órdenes pendientes ni en espera.")
        else:
            for index, row in df_pendientes.iterrows():
                estado_clase = (
                    "card-espera"
                    if row["Estado"] == "En Espera"
                    else "card-abierta"
                )
                st.markdown(
                    f"""
                    <div class="{estado_clase}">
                        <b>Folio:</b> OT-{row['NumOrden']} | <b>Área/Línea:</b> {row['AreaLinea']} | <b>Equipo:</b> {row['Equipo']}<br>
                        <b>Descripción:</b> {row['DescripcionFalla']}<br>
                        <b>Estado actual:</b> {row['Estado']} | <b>Técnico asignado:</b> {row['Tecnico']}
                    </div>
                """,
                    unsafe_allow_html=True,
                )

                with st.expander(
                    f"Atender / Editar Orden #OT-{row['NumOrden']}"
                ):
                    with st.form(f"form_atender_{row['id']}"):
                        tec_asignado = st.text_input(
                            "Técnico Responsable",
                            value=(
                                tec_actual
                                if row["Tecnico"] == "Pendiente de Asignar"
                                else row["Tecnico"]
                            ),
                        )
                        tipo_mtto = st.selectbox(
                            "Tipo de Mantenimiento",
                            ["Correctivo", "Preventivo", "Predictivo", "Mejora"],
                            index=(
                                0
                                if row["TipoMantenimiento"]
                                not in [
                                    "Preventivo",
                                    "Predictivo",
                                    "Mejora",
                                ]
                                else [
                                    "Correctivo",
                                    "Preventivo",
                                    "Predictivo",
                                    "Mejora",
                                ].index(row["TipoMantenimiento"])
                            ),
                        )

                        col_h1, col_h2, col_h3 = st.columns(3)
                        with col_h1:
                            h_rec = st.text_input(
                                "Hora Recepción (HH:MM)",
                                value=(
                                    datetime.now().strftime("%H:%M")
                                    if row["HoraRecepcion"] == "--:--"
                                    else row["HoraRecepcion"]
                                ),
                            )
                        with col_h2:
                            f_cierre_val = st.text_input(
                                "Fecha Cierre (AAAA-MM-DD)",
                                value=(
                                    datetime.now().strftime("%Y-%m-%d")
                                    if not row["FechaCierre"]
                                    else row["FechaCierre"]
                                ),
                            )
                        with col_h3:
                            h_cie = st.text_input(
                                "Hora Cierre (HH:MM)",
                                value=(
                                    datetime.now().strftime("%H:%M")
                                    if row["HoraCierre"] == "--:--"
                                    else row["HoraCierre"]
                                ),
                            )

                        trabajo_tec = st.text_area(
                            "Trabajo Realizado / Diagnóstico Técnico",
                            value=(
                                ""
                                if row["TrabajoRealizado"]
                                == "Pendiente de atención técnica"
                                else row["TrabajoRealizado"]
                            ),
                        )
                        nuevo_estado = st.selectbox(
                            "Estado de la OT",
                            [
                                "Abierta",
                                "En Espera",
                                "Atendida",
                                "Completada",
                            ],
                            index=2,
                        )

                        btn_guardar_tec = st.form_submit_button(
                            "Guardar Avances Técnicos"
                        )
                        if btn_guardar_tec:
                            min_esp = 15
                            min_trab = 45
                            min_tot = min_esp + min_trab

                            datos_act = {
                                "Tecnico": tec_asignado,
                                "TipoMantenimiento": tipo_mtto,
                                "HoraRecepcion": h_rec,
                                "HoraCierre": h_cie,
                                "FechaCierre": f_cierre_val,
                                "HoraConformidad": row["HoraConformidad"],
                                "MinutosEspera": min_esp,
                                "MinutosTrabajo": min_trab,
                                "MinutosTotalOT": min_tot,
                                "TrabajoRealizado": trabajo_tec,
                                "Estado": nuevo_estado,
                            }
                            actualizar_orden_db(row["id"], datos_act)
                            st.success(
                                f"✅ ¡Orden OT-{row['NumOrden']} actualizada con"
                                " éxito!"
                            )
                            st.rerun()

    # ---------------------------------------------------------
    # CATEGORÍA 3: VISUALIZADOR
    # ---------------------------------------------------------
    elif rol == "Visualizador":
        st.subheader("📊 Panel de Visualización y Monitoreo General")
        st.markdown(
            "Consulta todas las órdenes de trabajo registradas, filtra por"
            " estado o área y descarga reportes en PDF."
        )

        df_todas = cargar_datos_db()

        if df_todas.empty:
            st.info(
                "No hay órdenes de trabajo registradas en la base de datos"
                " todavía."
            )
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label="Total de Órdenes", value=len(df_todas))
            with col2:
                abiertas_count = len(
                    df_todas[df_todas["Estado"].isin(["Abierta", "En Espera"])]
                )
                st.metric(
                    label="Órdenes Activas / Pendientes", value=abiertas_count
                )
            with col3:
                cerradas_count = len(
                    df_todas[
                        df_todas["Estado"].isin(["Cerrada", "Completada"])
                    ]
                )
                st.metric(label="Órdenes Cerradas", value=cerradas_count)

            st.markdown("---")
            st.markdown("### 🔍 Filtros de Búsqueda")

            filtro_estado = st.selectbox(
                "Filtrar por Estado",
                [
                    "Todos",
                    "Abierta",
                    "En Espera",
                    "Atendida",
                    "Cerrada",
                    "Completada",
                ],
            )

            if filtro_estado != "Todos":
                df_filtrado = df_todas[df_todas["Estado"] == filtro_estado]
            else:
                df_filtrado = df_todas

            st.dataframe(df_filtrado, use_container_width=True)

            st.markdown("### 📥 Descarga de Reportes Individuales")
            folio_sel = st.selectbox(
                "Selecciona el Folio de la Orden a Descargar",
                df_todas["NumOrden"].tolist(),
            )
            if folio_sel:
                row_sel = df_todas[df_todas["NumOrden"] == folio_sel].iloc[0]
                pdf_bytes = generar_pdf_orden(row_sel)
                st.download_button(
                    label=f"📥 Descargar PDF de la Orden OT-{folio_sel}",
                    data=pdf_bytes,
                    file_name=f"Orden_OT-{folio_sel}.pdf",
                    mime="application/pdf",
                )

    # ---------------------------------------------------------
    # CATEGORÍA 4: ADMINISTRADOR
    # ---------------------------------------------------------
    elif rol == "Admin":
        st.subheader("🛠️ Panel de Administración General")
        st.markdown(
            "Control total del sistema, catálogos, registros y eliminación de"
            " órdenes de la base de datos."
        )

        df_admin = cargar_datos_db()
        st.metric(
            "Total de registros históricos en la Base de Datos", len(df_admin)
        )
        st.dataframe(df_admin, use_container_width=True)

        st.markdown("---")
        st.markdown("### 🗑️ Gestión y Eliminación de Órdenes")
        st.warning(
            "⚠️ Precaución: Eliminar una orden la borrará de forma permanente de"
            " la base de datos."
        )

        if not df_admin.empty:
            folio_a_borrar = st.selectbox(
                "Selecciona el Folio de la Orden a Eliminar",
                df_admin["NumOrden"].tolist(),
                key="select_borrar_folio",
            )

            if folio_a_borrar:
                row_borrar = df_admin[
                    df_admin["NumOrden"] == folio_a_borrar
                ].iloc[0]
                st.info(
                    f"Información de la Orden seleccionada: **Folio OT-{row_borrar['NumOrden']}** |"
                    f" **Área/Línea:** {row_borrar['AreaLinea']} | **Equipo:**"
                    f" {row_borrar['Equipo']} | **Estado:**"
                    f" {row_borrar['Estado']}"
                )

                if st.button(
                    f"❌ Eliminar Permanentemente la Orden OT-{folio_a_borrar}",
                    type="primary",
                ):
                    eliminar_orden_db(row_borrar["id"])
                    st.success(
                        f"✅ Orden OT-{folio_a_borrar} eliminada correctamente de la"
                        " base de datos."
                    )
                    st.rerun()
        else:
            st.info("No hay registros disponibles para eliminar.")
