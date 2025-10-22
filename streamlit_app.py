import streamlit as st
import pandas as pd
import datetime
import re
import os

st.set_page_config(page_title="Generador de Respuestas", layout="wide")

st.title("Generador de Respuestas (versión web)")

# --- Archivos CSV locales ---
RESPUESTAS_CSV = 'RESPUESTAS.csv'
COLEGIOS_CSV = 'COLEGIOS.csv'

respuestas_dict = {}
colegios_dict = {}
regiones = []
comunas_por_region = {}

# --- Cargar respuestas ---
if os.path.exists(RESPUESTAS_CSV):
    try:
        df_respuestas = pd.read_csv(RESPUESTAS_CSV, delimiter=';', encoding='utf-8-sig')
        for _, row in df_respuestas.iterrows():
            caso = str(row.get('Caso', '')).strip()
            resp = str(row.get('Respuesta', '')).strip()
            if caso and resp:
                respuestas_dict[caso] = resp
        st.success("Archivo de respuestas cargado correctamente.")
    except Exception as e:
        st.error(f"No se pudo leer {RESPUESTAS_CSV}: {e}")
else:
    st.error(f"No se encontró {RESPUESTAS_CSV} en el repositorio.")

# --- Cargar colegios ---
if os.path.exists(COLEGIOS_CSV):
    try:
        df_colegios = pd.read_csv(COLEGIOS_CSV, delimiter=';', encoding='utf-8-sig')
        regiones_set = set()
        comunas_dict = {}
        for _, row in df_colegios.iterrows():
            codigo = str(row.get('codigo_rec', '')).strip()
            region = str(row.get('region', '')).strip()
            comuna = str(row.get('comuna', '')).strip()
            nombre = str(row.get('recinto', '')).strip()
            direccion = str(row.get('Direccion', '')).strip()
            if codigo:
                colegios_dict[codigo] = {
                    'nombre': nombre,
                    'direccion': direccion,
                    'comuna': comuna,
                    'region': region
                }
                regiones_set.add(region)
                comunas_dict.setdefault(region, set()).add(comuna)
        regiones = sorted(list(regiones_set))
        comunas_por_region = {r: sorted(list(c)) for r, c in comunas_dict.items()}
        st.success("Archivo de colegios cargado correctamente.")
    except Exception as e:
        st.error(f"No se pudo leer {COLEGIOS_CSV}: {e}")
else:
    st.error(f"No se encontró {COLEGIOS_CSV} en el repositorio.")

# --- Función para limpiar RUT ---
def limpiar_rut(rut):
    m = re.match(r'^\s*([\d\.]+)-?([\dkK])\s*$', rut)
    if m:
        cuerpo = re.sub(r'\D', '', m.group(1))
        dv = m.group(2)
        return cuerpo, dv
    return '', ''

# --- Función para generar respuesta ---
def generar_respuesta(caso, codigo_local, rut, numero_reclamo, fecha_extra=None, origen_extra=None):
    if codigo_local not in colegios_dict:
        st.error("Código de local no encontrado en la base.")
        return ''
    if caso not in respuestas_dict:
        st.error("Caso no válido.")
        return ''

    plantilla = respuestas_dict[caso]
    colegio = colegios_dict[codigo_local]
    texto = plantilla
    texto = texto.replace('(nombre del local)', colegio['nombre'])
    texto = texto.replace('(direccion del local)', colegio['direccion'])
    texto = texto.replace('(comuna respectiva)', colegio['comuna'])
    texto = texto.replace('(region respectiva)', colegio['region'])

    if caso == '5':
        if fecha_extra:
            if '(fecha)' in texto:
                texto = texto.replace('(fecha)', fecha_extra)
            else:
                texto += f" ({fecha_extra})"
        if origen_extra:
            if '(origen)' in texto:
                texto = texto.replace('(origen)', origen_extra)
            else:
                texto += f" ({origen_extra})"
    return texto

# --- Interfaz de inputs ---
if respuestas_dict and colegios_dict:
    st.subheader("Datos del Reclamo")
    col1, col2 = st.columns(2)
    with col1:
        numero_reclamo = st.text_input("Número de Reclamo")
        rut_input = st.text_input("RUT (formato 12.345.678-9)")
        rut_limpio, dv = limpiar_rut(rut_input)
        st.text(f"RUT limpio: {rut_limpio} - DV: {dv}")
    with col2:
        caso = st.selectbox("Selecciona Caso", sorted(respuestas_dict.keys()))
        codigo_local = st.text_input("Código del Local")

    # Inputs extra para caso 5
    fecha_extra, origen_extra = '', ''
    if caso == '5':
        fecha_extra = st.text_input("Fecha")
        origen_extra = st.selectbox("Origen", ["Clave Única", "Servicio Electoral", "ChileAtiende", "Registro Civil e Identificación"])

    if st.button("Generar Respuesta"):
        if not numero_reclamo or not rut_limpio or not caso or not codigo_local:
            st.warning("Complete todos los campos obligatorios.")
        else:
            respuesta_generada = generar_respuesta(caso, codigo_local, rut_limpio, numero_reclamo, fecha_extra, origen_extra)
            if respuesta_generada:
                st.subheader("Respuesta Generada")
                st.text_area("", respuesta_generada, height=200)
                st.success("Respuesta generada correctamente.")
    
    # --- Buscador de colegios ---
    st.subheader("Buscar Colegios por Región y Comuna")
    region_sel = st.selectbox("Región", [''] + regiones)
    if region_sel:
        comunas_disp = comunas_por_region.get(region_sel, [])
        comuna_sel = st.selectbox("Comuna", [''] + comunas_disp)
        if comuna_sel:
            resultados = []
            for cod, datos in colegios_dict.items():
                if datos['region'] == region_sel and datos['comuna'] == comuna_sel:
                    resultados.append(f"{cod}: {datos['nombre']} - {datos['direccion']}")
            if resultados:
                st.text_area("Resultados", "\n".join(resultados), height=200)
            else:
                st.text("No se encontraron colegios para la comuna seleccionada.")

