import streamlit as st
import pandas as pd
import re
import os
import datetime

st.set_page_config(page_title="Generador de Respuestas", layout="wide")
st.title("Generador de Respuestas (versión web)")

RESPUESTAS_CSV = 'RESPUESTAS.csv'
COLEGIOS_CSV = 'COLEGIOS.csv'
CONTADOR_TXT = 'contador.txt'

# --- Contador persistente ---
if os.path.exists(CONTADOR_TXT):
    try:
        with open(CONTADOR_TXT, 'r') as f:
            contador = int(f.read().strip())
    except:
        contador = 0
else:
    contador = 0

st.subheader(f"Total de respuestas generadas: {contador}")


# --- Cargar CSVs ---
respuestas_dict = {}
casos_dict = {}
colegios_dict = {}
regiones = []
comunas_por_region = {}

# --- Cargar respuestas ---
if os.path.exists(RESPUESTAS_CSV):
    df_respuestas = pd.read_csv(RESPUESTAS_CSV, delimiter=';', encoding='utf-8-sig')
    for _, row in df_respuestas.iterrows():
        caso = str(row.get('Caso', '')).strip()
        desc = str(row.get('Descripcion', '')).strip()
        resp = str(row.get('Respuesta', '')).strip()
        if caso and resp:
            respuestas_dict[caso] = resp
            casos_dict[caso] = desc
else:
    st.error(f"No se encontró {RESPUESTAS_CSV}")

if os.path.exists(COLEGIOS_CSV):
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
            colegios_dict[codigo] = {'nombre': nombre, 'direccion': direccion, 'comuna': comuna, 'region': region}
            regiones_set.add(region)
            comunas_dict.setdefault(region, set()).add(comuna)
    regiones = sorted(list(regiones_set))
    comunas_por_region = {r: sorted(list(c)) for r, c in comunas_dict.items()}
else:
    st.error(f"No se encontró {COLEGIOS_CSV}")

# --- Funciones ---
def limpiar_rut(rut):
    m = re.match(r'^\s*([\d\.]+)-?([\dkK])\s*$', rut)
    if m:
        cuerpo = re.sub(r'\D', '', m.group(1))
        dv = m.group(2)
        return cuerpo, dv
    return '', ''

def generar_respuesta(caso, codigo_local, rut, numero_reclamo, fecha_extra='', origen_extra=''):
    if codigo_local not in colegios_dict or caso not in respuestas_dict:
        return ''
    plantilla = respuestas_dict[caso]
    colegio = colegios_dict[codigo_local]
    texto = plantilla.replace('(nombre del local)', colegio['nombre'])\
                     .replace('(direccion del local)', colegio['direccion'])\
                     .replace('(comuna respectiva)', colegio['comuna'])\
                     .replace('(region respectiva)', colegio['region'])
    if caso == '5':
        if fecha_extra: texto = texto.replace('(fecha)', fecha_extra) if '(fecha)' in texto else texto + f" ({fecha_extra})"
        if origen_extra: texto = texto.replace('(origen)', origen_extra) if '(origen)' in texto else texto + f" ({origen_extra})"
    return texto

def generar_log(numero_reclamo, rut_limpio, dv, caso, codigo_local, fecha_extra='', origen_extra=''):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    campos = [timestamp, numero_reclamo, f"{rut_limpio}-{dv}", caso, codigo_local]
    if caso == '5':
        campos += [fecha_extra, origen_extra]
    return ";".join(str(c) for c in campos)

# --- Inputs ---
col1, col2 = st.columns(2)
with col1:
    numero_reclamo = st.text_input("Número de Reclamo")
    rut_input = st.text_input("RUT (formato 12.345.678-9)")
    rut_limpio, dv = limpiar_rut(rut_input)
    st.text(f"RUT limpio: {rut_limpio} - DV: {dv}")
with col2:
    # Mostrar selectbox con caso + descripción
    opciones_casos = [f"{c} - {desc}" for c, desc in casos_dict.items()]
    seleccion = st.selectbox("Selecciona Caso", opciones_casos)
    caso = seleccion.split(" - ")[0]
    codigo_local = st.text_input("Código del Local")

# --- Inputs caso 5 siempre presentes ---
fecha_extra = st.text_input("Fecha (solo caso 5)", key='fecha_extra')
origen_extra = st.selectbox("Origen (solo caso 5)", ["Clave Única","Oficina Servicio Electoral","ChileAtiende","Registro Civil e Identificación"], key='origen_extra')

if st.button("Generar Respuesta"):
    if not numero_reclamo or not rut_limpio or not caso or not codigo_local:
        st.warning("Complete todos los campos obligatorios.")
    else:
        respuesta_generada = generar_respuesta(caso, codigo_local, rut_limpio, numero_reclamo,
                                              fecha_extra if caso=='5' else '',
                                              origen_extra if caso=='5' else '')
        log_line = generar_log(numero_reclamo, rut_limpio, dv, caso, codigo_local,
                               fecha_extra if caso=='5' else '',
                               origen_extra if caso=='5' else '')

        if respuesta_generada:
            st.subheader("Respuesta Generada")
            st.text_area("", respuesta_generada, height=250)
            st.subheader("Fecha y hora; N° reclamo; RUT; N° Caso; Recinto")
            st.text_area("", log_line, height=50)

            # --- Actualizar contador ---
            contador += 1
            with open(CONTADOR_TXT, 'w') as f:
                f.write(str(contador))
            st.success(f"Total de respuestas generadas: {contador}")

# --- Buscador de colegios ---
st.subheader("Buscar Local por Región y Comuna")
region_sel = st.selectbox("Región", [''] + regiones)
if region_sel:
    comunas_disp = comunas_por_region.get(region_sel, [])
    comuna_sel = st.selectbox("Comuna", [''] + comunas_disp)
    if comuna_sel:
        resultados = [f"{cod}: {d['nombre']}" for cod,d in colegios_dict.items()
                      if d['region']==region_sel and d['comuna']==comuna_sel]
        st.text_area("Resultados", "\n".join(resultados) if resultados else "No se encontraron colegios.", height=200)


