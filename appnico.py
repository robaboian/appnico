import streamlit as st
import pandas as pd
import os
from datetime import datetime
from io import BytesIO

# --- CONFIGURACIÓN DE ARCHIVO ---
ARCHIVO_DB = "data/registro_scouting.xlsx"

def cargar_datos():
    if os.path.exists(ARCHIVO_DB):
        return pd.read_excel(ARCHIVO_DB)
    return pd.DataFrame(columns=["Codigo", "Nota", "Fecha"])

def guardar_datos(df):
    os.makedirs(os.path.dirname(ARCHIVO_DB), exist_ok=True)
    df.to_excel(ARCHIVO_DB, index=False)

def dataframe_a_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Reporte")
    return output.getvalue()

# --- INTERFAZ ---
st.set_page_config(page_title="ScoutFlow Permanente", page_icon="💾")
st.title("💾 ScoutFlow: Almacenamiento Local")

# Cargar base de datos al iniciar
df_actual = cargar_datos()

with st.form("formulario_nota", clear_on_submit=True):
    col1, col2 = st.columns([1, 3])

    with col1:
        codigo = st.text_input("CÓDIGO (4 Caracteres)").upper()

    with col2:
        nota = st.text_area("OBSERVACIÓN")

    submit = st.form_submit_button("💾 GUARDAR DE FORMA PERMANENTE")

if submit:
    if len(codigo) == 4 and nota.strip():
        nueva_fila = pd.DataFrame([{
            "Codigo": codigo,
            "Nota": nota.strip(),
            "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])

        # Concatenar y guardar en el disco duro
        df_actual = pd.concat([df_actual, nueva_fila], ignore_index=True)
        guardar_datos(df_actual)
        st.success(f"Nota de {codigo} escrita en el archivo local.")
    else:
        st.error("Error: El código debe tener 4 letras y la nota no puede estar vacía.")

# --- VISUALIZACIÓN Y FILTROS ---
st.markdown("---")

if not df_actual.empty:
    busqueda = st.text_input("🔍 Filtrar historial acumulado")

    if busqueda.strip():
        busqueda_upper = busqueda.upper()
        df_filtrado = df_actual[
            df_actual.apply(
                lambda r: r.astype(str).str.upper().str.contains(busqueda_upper, na=False).any(),
                axis=1
            )
        ]
    else:
        df_filtrado = df_actual.copy()

    st.dataframe(df_filtrado, use_container_width=True)

    # Mostrar cuántas notas hay en total en el archivo
    st.sidebar.metric("Notas Totales", len(df_actual))

    # Opción para descargar una copia limpia en Excel
    excel_data = dataframe_a_excel_bytes(df_actual)

    st.sidebar.download_button(
        "📥 Descargar reporte",
        data=excel_data,
        file_name="reporte_final.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("El archivo de base de datos está vacío. Empieza a registrar para crear el historial.")
