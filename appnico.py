import streamlit as st
import pandas as pd
import os
from datetime import datetime
from openpyxl.workbook import Workbook

# --- CONFIGURACIÓN DE ARCHIVO ---
ARCHIVO_DB = "/Users/robaboian/Desktop/Argentinos Juniors/registro_scouting.xlsx"

def cargar_datos():
    if os.path.exists(ARCHIVO_DB):
        return pd.read_excel(ARCHIVO_DB)
    return pd.DataFrame(columns=["Codigo", "Nota", "Fecha"])

def guardar_datos(df):
    df.to_excel(ARCHIVO_DB, index=False)

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
    if len(codigo) == 4 and nota:
        nueva_fila = pd.DataFrame([{
            "Codigo": codigo,
            "Nota": nota,
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
    
    # Filtro dinámico
    df_filtrado = df_actual[df_actual.apply(lambda r: busqueda.upper() in r.astype(str).str.upper().values, axis=1)]
    
    st.dataframe(df_filtrado, use_container_width=True)
    
    # Mostrar cuántas notas hay en total en el archivo
    st.sidebar.metric("Notas Totales", len(df_actual))
    
    # Opción para descargar una copia limpia
    csv_data = df_actual.to_excel(index=False)
    st.sidebar.download_button("📥 Descargar reporte", data=csv_data, file_name="reporte_final.xlsx")
else:
    st.info("El archivo de base de datos está vacío. Empieza a registrar para crear el historial.")
