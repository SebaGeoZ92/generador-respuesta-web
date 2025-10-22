import streamlit as st
import pandas as pd
import datetime
import re
from openai import OpenAI

# Inicialización del cliente OpenAI
client = OpenAI()

# Función para limpiar RUT y extraer DV
def separar_rut_dv(rut):
    rut = rut.replace(".", "").replace("-", "").strip().upper()
    match = re.match(r"^(\d+)([0-9K])?$", rut)
    if match:
        numero = match.group(1)
        dv = match.group(2) if match.group(2) else ""
        return numero, dv
    return rut, ""

# Cargar datos desde CSV en mayúsculas
@st.cache_data
def cargar_datos():
    respuestas_df = pd.read_csv("RESPUESTAS.csv", dtype=str).fillna("")
    colegios_df = pd.read_csv("COLEGIOS.csv", dtype=str).fillna("")
    return respuestas_df, colegios_df

respuestas_df, colegios_df = cargar_datos()

# Procesar datos de colegios
colegios_dict = {
    row["CODIGO_LOCAL"]: {
        "nombre": row["NOMBRE_LOCAL"],
        "region": row["REGION"],
        "comuna": row["COMUNA"]
    }
    for _, row in colegios_df.iterrows()
}

regiones = sorted(colegios_df["REGION"].unique())
comunas_por_region = {
    region: sorted(colegios_df[colegios_df["REGION"] == region]["COMUNA"].unique())
    for region in regiones
}

# UI de Streamlit
st.title("🗳️ Sistema Automatizado de Respuestas SERVEL 3.1")

# Selector de datos
rut_input = st.text_input("Ingrese RUT (con puntos o guion):")
numero_reclamo = st.text_input("Número de Reclamo:")
caso = st.text_input("Número de Caso (ej: 5, 5.1):")

# Dinámica Región → Comuna → Local
region_sel = st.selectbox("Seleccione Región", [""] + regiones)
comuna_sel = ""
codigo_local = ""

if region_sel:
    comunas_disp = comunas_por_region.get(region_sel, [])
    comuna_sel = st.selectbox("Seleccione Comuna", [""] + comunas_disp)

if comuna_sel:
    codigos_disp = [
        cod for cod, datos in colegios_dict.items()
        if datos["region"] == region_sel and datos["comuna"] == comuna_sel
    ]
    codigo_local = st.selectbox("Seleccione Código de Local", [""] + codigos_disp)

# Botón para procesar
if st.button("Generar Respuesta"):
    if not (rut_input and numero_reclamo and caso and codigo_local):
        st.error("⚠️ Debe completar todos los campos.")
    else:
        rut_limpio, dv = separar_rut_dv(rut_input)
        datos_local = colegios_dict[codigo_local]

        # Buscar plantilla de la respuesta según caso
        respuesta_base = respuestas_df[respuestas_df["CASO"] == caso]
        if respuesta_base.empty:
            st.error("❌ No se encontró una respuesta para ese caso.")
        else:
            plantilla = respuesta_base.iloc[0]["RESPUESTA"]
            respuesta_generada = plantilla.format(
                RUT=rut_limpio,
                DV=dv,
                NUMERO_RECLAMO=numero_reclamo,
                LOCAL=datos_local["nombre"],
                COMUNA=datos_local["comuna"],
                REGION=datos_local["region"]
            )

            # Mostrar respuesta generada
            st.subheader("✉️ Respuesta Generada")
            st.text_area("Copiar y pegar en Sistema:", respuesta_generada, height=200)

            # Generar línea para Excel
            ahora = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            caso_val = caso.replace(",", ".")
            linea_excel = f"{numero_reclamo}\t{ahora}\t{caso_val}\t{datos_local['comuna']}\t{rut_limpio}\t{dv}\t{respuesta_generada}"
            
            st.subheader("📄 Línea lista para pegar en Excel:")
            st.text_area("", linea_excel, height=100)

            st.success("✅ Proceso completado correctamente.")
