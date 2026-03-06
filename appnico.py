import streamlit as st
import pandas as pd
import os
from datetime import datetime
from io import BytesIO

# =========================================================
# CONFIG
# =========================================================
ARCHIVO_DB = "data/registro_scouting.xlsx"
HOJA_NOTAS = "Notas"
HOJA_REPORTES = "Reportes"

# =========================================================
# FUNCIONES BASE
# =========================================================
def asegurar_carpeta_archivo():
    os.makedirs(os.path.dirname(ARCHIVO_DB), exist_ok=True)

def cargar_datos_notas():
    if os.path.exists(ARCHIVO_DB):
        try:
            return pd.read_excel(ARCHIVO_DB, sheet_name=HOJA_NOTAS)
        except Exception:
            try:
                return pd.read_excel(ARCHIVO_DB)
            except Exception:
                pass

    return pd.DataFrame(columns=["Código", "Jugador", "Partido", "Nota", "Fecha"])

def cargar_datos_reportes():
    if os.path.exists(ARCHIVO_DB):
        try:
            return pd.read_excel(ARCHIVO_DB, sheet_name=HOJA_REPORTES)
        except Exception:
            pass

    return pd.DataFrame(columns=[
        "Código",
        "Jugador",
        "Fecha_reporte",
        "Resumen",
        "Fortalezas",
        "Aspectos_a_mejorar",
        "Conclusión",
        "Notas_utilizadas"
    ])

def guardar_todo(df_notas, df_reportes):
    asegurar_carpeta_archivo()

    with pd.ExcelWriter(ARCHIVO_DB, engine="openpyxl") as writer:
        df_notas.to_excel(writer, index=False, sheet_name=HOJA_NOTAS)
        df_reportes.to_excel(writer, index=False, sheet_name=HOJA_REPORTES)

def dataframe_a_excel_bytes(df_notas, df_reportes):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_notas.to_excel(writer, index=False, sheet_name=HOJA_NOTAS)
        df_reportes.to_excel(writer, index=False, sheet_name=HOJA_REPORTES)
    return output.getvalue()

def ordenar_por_fecha_si_existe(df):
    df = df.copy()
    if "Fecha" in df.columns:
        try:
            df["Fecha_dt"] = pd.to_datetime(df["Fecha"], errors="coerce")
            df = df.sort_values("Fecha_dt", ascending=False, na_position="last")
            df = df.drop(columns=["Fecha_dt"], errors="ignore")
        except Exception:
            pass
    return df

# =========================================================
# APP
# =========================================================
st.set_page_config(page_title="ScoutFlow", page_icon="⚽", layout="wide")
st.title("⚽ ScoutFlow")
st.caption("Carga de observaciones y reportes manuales")

# Carga inicial
df_notas = cargar_datos_notas()
df_reportes = cargar_datos_reportes()

# Normalización mínima por si venís de una versión anterior
for col in ["Código", "Jugador", "Partido", "Nota", "Fecha"]:
    if col not in df_notas.columns:
        df_notas[col] = ""

for col in [
    "Código",
    "Jugador",
    "Fecha_reporte",
    "Resumen",
    "Fortalezas",
    "Aspectos_a_mejorar",
    "Conclusión",
    "Notas_utilizadas"
]:
    if col not in df_reportes.columns:
        df_reportes[col] = ""

# =========================================================
# FORMULARIO DE CARGA
# =========================================================
st.subheader("➕ Nueva observación")

with st.form("formulario_nota", clear_on_submit=True):
    c1, c2 = st.columns([1, 2])

    with c1:
        codigo = st.text_input("CÓDIGO (4 caracteres)").upper().strip()
        jugador = st.text_input("Jugador").strip()

    with c2:
        partido = st.text_input("Partido / contexto").strip()
        nota = st.text_area("Observación", height=120)

    submit = st.form_submit_button("💾 Guardar observación")

if submit:
    if len(codigo) == 4 and nota.strip():
        nueva_fila = pd.DataFrame([{
            "Código": codigo,
            "Jugador": jugador,
            "Partido": partido,
            "Nota": nota.strip(),
            "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])

        df_notas = pd.concat([df_notas, nueva_fila], ignore_index=True)
        guardar_todo(df_notas, df_reportes)
        st.success(f"Observación guardada para {codigo}.")
    else:
        st.error("El código debe tener 4 caracteres y la observación no puede estar vacía.")

st.markdown("---")

# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.metric("Notas totales", len(df_notas))
st.sidebar.metric("Reportes guardados", len(df_reportes))

excel_data = dataframe_a_excel_bytes(df_notas, df_reportes)
st.sidebar.download_button(
    "📥 Descargar base completa",
    data=excel_data,
    file_name="scoutflow.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# =========================================================
# VISUALIZACIÓN DE NOTAS
# =========================================================
if df_notas.empty:
    st.info("Todavía no hay observaciones cargadas.")
    st.stop()

st.subheader("📚 Historial de observaciones")

busqueda = st.text_input("🔍 Filtrar historial")

df_notas_ordenado = ordenar_por_fecha_si_existe(df_notas)

if busqueda.strip():
    term = busqueda.upper()
    df_filtrado = df_notas_ordenado[
        df_notas_ordenado.apply(
            lambda r: r.astype(str).str.upper().str.contains(term, na=False).any(),
            axis=1
        )
    ].copy()
else:
    df_filtrado = df_notas_ordenado.copy()

st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

st.markdown("---")

# =========================================================
# BLOQUE DE ANÁLISIS MANUAL
# =========================================================
st.subheader("📝 Reporte manual")

codigos_disponibles = sorted(df_notas["Código"].dropna().astype(str).unique().tolist())

if not codigos_disponibles:
    st.info("No hay códigos disponibles todavía.")
    st.stop()

col_sel1, col_sel2 = st.columns([1, 2])

with col_sel1:
    codigo_sel = st.selectbox("Elegí código", codigos_disponibles)

df_codigo = df_notas[df_notas["Código"].astype(str) == codigo_sel].copy()
df_codigo = ordenar_por_fecha_si_existe(df_codigo)

jugadores_posibles = sorted([
    j for j in df_codigo["Jugador"].dropna().astype(str).unique().tolist() if j.strip()
])

jugador_default = jugadores_posibles[0] if jugadores_posibles else ""

with col_sel2:
    jugador_sel = st.text_input("Jugador asociado", value=jugador_default)

st.caption(f"Notas encontradas para {codigo_sel}: {len(df_codigo)}")

with st.expander("Ver observaciones del código seleccionado", expanded=True):
    if df_codigo.empty:
        st.info("No hay observaciones para este código.")
    else:
        for _, row in df_codigo.iterrows():
            fecha = str(row.get("Fecha", "")).strip()
            partido = str(row.get("Partido", "")).strip()
            nota_txt = str(row.get("Nota", "")).strip()

            encabezado = f"**{fecha}**"
            if partido:
                encabezado += f" | *{partido}*"

            st.markdown(encabezado)
            st.write(nota_txt)
            st.markdown("---")

# =========================================================
# FORMULARIO DE REPORTE MANUAL
# =========================================================
st.markdown("### Cargar reporte manual")

with st.form("formulario_reporte_manual", clear_on_submit=True):
    resumen = st.text_area("Resumen", height=140)
    col_r1, col_r2 = st.columns(2)

    with col_r1:
        fortalezas = st.text_area("Fortalezas", height=120, placeholder="Una por línea o separadas por |")
    with col_r2:
        aspectos_a_mejorar = st.text_area("Aspectos a mejorar", height=120, placeholder="Uno por línea o separados por |")

    conclusion = st.text_area("Conclusión", height=100)

    guardar_reporte = st.form_submit_button("💾 Guardar reporte manual")

if guardar_reporte:
    if jugador_sel.strip() == "":
        st.error("Completá el nombre del jugador asociado antes de guardar el reporte.")
    elif resumen.strip() == "" and fortalezas.strip() == "" and aspectos_a_mejorar.strip() == "" and conclusion.strip() == "":
        st.error("Completá al menos uno de los campos del reporte.")
    else:
        nuevo_reporte = pd.DataFrame([{
            "Código": codigo_sel,
            "Jugador": jugador_sel.strip(),
            "Fecha_reporte": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Resumen": resumen.strip(),
            "Fortalezas": fortalezas.strip(),
            "Aspectos_a_mejorar": aspectos_a_mejorar.strip(),
            "Conclusión": conclusion.strip(),
            "Notas_utilizadas": len(df_codigo)
        }])

        df_reportes = pd.concat([df_reportes, nuevo_reporte], ignore_index=True)
        guardar_todo(df_notas, df_reportes)
        st.success("Reporte manual guardado correctamente.")

st.markdown("---")

# =========================================================
# HISTORIAL DE REPORTES
# =========================================================
st.subheader("🗂 Historial de reportes")

if not df_reportes.empty:
    df_reportes_mostrar = df_reportes.copy()

    if "Fecha_reporte" in df_reportes_mostrar.columns:
        try:
            df_reportes_mostrar["Fecha_reporte_dt"] = pd.to_datetime(df_reportes_mostrar["Fecha_reporte"], errors="coerce")
            df_reportes_mostrar = df_reportes_mostrar.sort_values("Fecha_reporte_dt", ascending=False, na_position="last")
            df_reportes_mostrar = df_reportes_mostrar.drop(columns=["Fecha_reporte_dt"], errors="ignore")
        except Exception:
            pass

    st.dataframe(df_reportes_mostrar, use_container_width=True, hide_index=True)
else:
    st.info("Todavía no hay reportes guardados.")
