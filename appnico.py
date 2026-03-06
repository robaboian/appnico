import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
from io import BytesIO
from openai import OpenAI

# =========================================================
# CONFIG
# =========================================================
ARCHIVO_DB = "data/registro_scouting.xlsx"
HOJA_NOTAS = "Notas"
HOJA_REPORTES = "Reportes_IA"

# Elegí el modelo que tengas habilitado en tu cuenta API
# Si querés, después te lo cambio por otro.
OPENAI_MODEL = "gpt-5"

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
                # fallback si el archivo existe pero no tiene hojas con ese nombre
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
        "Código", "Jugador", "Fecha_reporte", "Resumen_profesional",
        "Fortalezas", "Aspectos_a_mejorar", "Tags", "Notas_utilizadas"
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

# =========================================================
# OPENAI
# =========================================================
def get_openai_client():
    api_key = st.secrets.get("OPENAI_API_KEY", None)
    if not api_key:
        return None
    return OpenAI(api_key=api_key)

def construir_bloque_notas(df_jugador):
    df_jugador = df_jugador.copy()
    if "Fecha" in df_jugador.columns:
        try:
            df_jugador["Fecha_dt"] = pd.to_datetime(df_jugador["Fecha"], errors="coerce")
            df_jugador = df_jugador.sort_values("Fecha_dt", na_position="last")
        except Exception:
            pass

    lineas = []
    for _, row in df_jugador.iterrows():
        fecha = str(row.get("Fecha", "")).strip()
        partido = str(row.get("Partido", "")).strip()
        nota = str(row.get("Nota", "")).strip()

        encabezado = []
        if fecha:
            encabezado.append(fecha)
        if partido:
            encabezado.append(f"Partido: {partido}")

        if encabezado:
            lineas.append(f"- [{' | '.join(encabezado)}] {nota}")
        else:
            lineas.append(f"- {nota}")

    return "\n".join(lineas)

def generar_reporte_ia(df_jugador, codigo, jugador):
    client = get_openai_client()
    if client is None:
        raise ValueError("No se encontró OPENAI_API_KEY en st.secrets.")

    bloque_notas = construir_bloque_notas(df_jugador)

    prompt = f"""
Sos un analista de scouting profesional de fútbol sudamericano.
Tu tarea es convertir observaciones cortas y dispersas en un informe interno más profesional.

Reglas:
- Escribí en español rioplatense.
- No inventes datos.
- No afirmes certezas si las notas no alcanzan.
- Si hay contradicciones, marcá que el comportamiento fue variable o irregular.
- Mantené un tono técnico, claro y útil para secretaría técnica.
- Basate solamente en las notas entregadas.

Devolvé EXCLUSIVAMENTE un JSON válido con esta estructura:

{{
  "resumen_profesional": "un párrafo de 90 a 160 palabras",
  "fortalezas": ["fortaleza 1", "fortaleza 2", "fortaleza 3"],
  "aspectos_a_mejorar": ["aspecto 1", "aspecto 2", "aspecto 3"],
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"]
}}

Código: {codigo}
Jugador: {jugador}

Notas:
{bloque_notas}
"""

    response = client.responses.create(
        model=OPENAI_MODEL,
        input=prompt
    )

    texto = response.output_text.strip()

    try:
        data = json.loads(texto)
    except Exception:
        # fallback por si el modelo devuelve texto no-JSON
        data = {
            "resumen_profesional": texto,
            "fortalezas": [],
            "aspectos_a_mejorar": [],
            "tags": []
        }

    return data

# =========================================================
# APP
# =========================================================
st.set_page_config(page_title="ScoutFlow AI", page_icon="⚽", layout="wide")
st.title("⚽ ScoutFlow AI")
st.caption("Carga de observaciones + síntesis profesional asistida por IA")

# Carga inicial
df_notas = cargar_datos_notas()
df_reportes = cargar_datos_reportes()

# Normalización mínima por si venís de una versión anterior
for col in ["Código", "Jugador", "Partido", "Nota", "Fecha"]:
    if col not in df_notas.columns:
        df_notas[col] = ""

for col in [
    "Código", "Jugador", "Fecha_reporte", "Resumen_profesional",
    "Fortalezas", "Aspectos_a_mejorar", "Tags", "Notas_utilizadas"
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
st.sidebar.metric("Reportes IA guardados", len(df_reportes))

excel_data = dataframe_a_excel_bytes(df_notas, df_reportes)
st.sidebar.download_button(
    "📥 Descargar base completa",
    data=excel_data,
    file_name="scoutflow_ai.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# =========================================================
# VISUALIZACIÓN DE NOTAS
# =========================================================
if df_notas.empty:
    st.info("Todavía no hay observaciones cargadas.")
    st.stop()

st.subheader("📚 Historial")

busqueda = st.text_input("🔍 Filtrar historial")

if busqueda.strip():
    term = busqueda.upper()
    df_filtrado = df_notas[
        df_notas.apply(
            lambda r: r.astype(str).str.upper().str.contains(term, na=False).any(),
            axis=1
        )
    ].copy()
else:
    df_filtrado = df_notas.copy()

st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

st.markdown("---")

# =========================================================
# BLOQUE IA
# =========================================================
st.subheader("🧠 Reporte profesional con IA")

codigos_disponibles = sorted(df_notas["Código"].dropna().astype(str).unique().tolist())

if not codigos_disponibles:
    st.info("No hay códigos disponibles todavía.")
    st.stop()

col_sel1, col_sel2 = st.columns([1, 2])

with col_sel1:
    codigo_ia = st.selectbox("Elegí código", codigos_disponibles)

df_codigo = df_notas[df_notas["Código"].astype(str) == codigo_ia].copy()

jugadores_posibles = sorted([
    j for j in df_codigo["Jugador"].dropna().astype(str).unique().tolist() if j.strip()
])

jugador_ia = jugadores_posibles[0] if jugadores_posibles else ""

with col_sel2:
    jugador_manual = st.text_input("Jugador asociado", value=jugador_ia)

st.caption(f"Notas encontradas para {codigo_ia}: {len(df_codigo)}")

with st.expander("Ver notas que usará la IA"):
    for _, row in df_codigo.iterrows():
        fecha = row.get("Fecha", "")
        partido = row.get("Partido", "")
        nota_txt = row.get("Nota", "")
        st.markdown(f"**{fecha}** | *{partido}*")
        st.write(nota_txt)
        st.markdown("---")

col_btn1, col_btn2 = st.columns([1, 1])

if "ultimo_reporte_ia" not in st.session_state:
    st.session_state["ultimo_reporte_ia"] = None

with col_btn1:
    if st.button("Generar reporte IA", use_container_width=True):
        try:
            with st.spinner("Generando síntesis profesional..."):
                reporte = generar_reporte_ia(df_codigo, codigo_ia, jugador_manual)

            st.session_state["ultimo_reporte_ia"] = {
                "Código": codigo_ia,
                "Jugador": jugador_manual,
                "Fecha_reporte": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Resumen_profesional": reporte.get("resumen_profesional", ""),
                "Fortalezas": " | ".join(reporte.get("fortalezas", [])),
                "Aspectos_a_mejorar": " | ".join(reporte.get("aspectos_a_mejorar", [])),
                "Tags": " | ".join(reporte.get("tags", [])),
                "Notas_utilizadas": len(df_codigo)
            }

        except Exception as e:
            st.error(f"No se pudo generar el reporte IA: {e}")

with col_btn2:
    if st.session_state["ultimo_reporte_ia"] is not None:
        if st.button("Guardar reporte IA en Excel", use_container_width=True):
            nuevo_reporte = pd.DataFrame([st.session_state["ultimo_reporte_ia"]])
            df_reportes = pd.concat([df_reportes, nuevo_reporte], ignore_index=True)
            guardar_todo(df_notas, df_reportes)
            st.success("Reporte IA guardado en la hoja 'Reportes_IA'.")

# =========================================================
# MOSTRAR ÚLTIMO REPORTE
# =========================================================
reporte = st.session_state.get("ultimo_reporte_ia", None)

if reporte is not None and reporte.get("Código") == codigo_ia:
    st.markdown("### Resumen profesional")
    st.write(reporte["Resumen_profesional"])

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("### Fortalezas")
        fortalezas = [x.strip() for x in str(reporte["Fortalezas"]).split("|") if x.strip()]
        if fortalezas:
            for f in fortalezas:
                st.markdown(f"- {f}")
        else:
            st.write("Sin ítems.")

    with c2:
        st.markdown("### Aspectos a mejorar")
        mejoras = [x.strip() for x in str(reporte["Aspectos_a_mejorar"]).split("|") if x.strip()]
        if mejoras:
            for m in mejoras:
                st.markdown(f"- {m}")
        else:
            st.write("Sin ítems.")

    st.markdown("### Tags automáticos")
    tags = [x.strip() for x in str(reporte["Tags"]).split("|") if x.strip()]
    if tags:
        st.write(" | ".join(tags))
    else:
        st.write("Sin tags.")

st.markdown("---")

# =========================================================
# HISTORIAL DE REPORTES IA
# =========================================================
st.subheader("🗂 Historial de reportes IA")

if not df_reportes.empty:
    st.dataframe(df_reportes, use_container_width=True, hide_index=True)
else:
    st.info("Todavía no hay reportes IA guardados.")
