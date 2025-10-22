# streamlit_app.py
import streamlit as st
import pandas as pd
import re
import datetime
import os

# --- Archivos --- #
RESPUESTAS_CSV = 'respuestas.csv'
COLEGIOS_CSV = 'colegios.csv'
REGISTRO_XLSX = 'registro_respuestas.xlsx'

# --- Funciones utilitarias --- #
def convertir_a_int(valor):
    try:
        return int(valor)
    except (ValueError, TypeError):
        return valor

def cargar_respuestas(nombre_archivo):
    try:
        df = pd.read_csv(nombre_archivo, delimiter=';', encoding='utf-8-sig')
        respuestas = {str(row['Caso']).strip(): row['Respuesta'].strip() for _, row in df.iterrows()}
        return respuestas
    except Exception as e:
        st.warning(f"No se pudo leer {nombre_archivo}: {e}")
        return {}

def cargar_colegios(nombre_archivo):
    try:
        df = pd.read_csv(nombre_archivo, delimiter=';', encoding='utf-8-sig')
        colegios = {}
        regiones = set()
        comunas_por_region = {}
        for _, row in df.iterrows():
            codigo = str(row.get('codigo_rec', '')).strip()
            region = str(row.get('region', '')).strip()
            comuna = str(row.get('comuna', '')).strip()
            nombre = str(row.get('recinto', '')).strip()
            direccion = str(row.get('Direccion', '')).strip()
            if codigo:
                colegios[codigo] = {
                    'nombre': nombre,
                    'direccion': direccion,
                    'comuna': comuna,
                    'region': region
                }
                regiones.add(region)
                comunas_por_region.setdefault(region, set()).add(comuna)
        regiones_ordenadas = sorted(list(regiones))
        comunas_por_region_ordenadas = {r: sorted(list(c)) for r, c in comunas_por_region.items()}
        return colegios, regiones_ordenadas, comunas_por_region_ordenadas
    except Exception as e:
        st.warning(f"No se pudo leer {nombre_archivo}: {e}")
        return {}, [], {}

def registrar_respuesta(numero_reclamo, fecha_hora, caso, respuesta, comuna, rut_limpio, dv):
    fila = {
        'Número de Reclamo': numero_reclamo,
        'Fecha y Hora': fecha_hora.strftime('%Y-%m-%d %H:%M:%S'),
        'Caso': convertir_a_int(caso),
        'Comuna': comuna,
        'RUT': rut_limpio,
        'Dígito Verificador': dv,
        'Respuesta Generada': respuesta
    }
    if os.path.exists(REGISTRO_XLSX):
        df_existente = pd.read_excel(REGISTRO_XLSX)
        df_final = pd.concat([df_existente, pd.DataFrame([fila])], ignore_index=True)
    else:
        df_final = pd.DataFrame([fila])
    df_final.to_excel(REGISTRO_XLSX, index=False)

def limpiar_rut(rut_input):
    m = re.match(r'^\s*([\d\.]+)-?([\dkK])\s*$', rut_input)
    if m:
        cuerpo = m.group(1)
        dv = m.group(2)
        cuerpo_limpio = re.sub(r'\D', '', cuerpo)
        return cuerpo_limpio, dv
    return '', ''

# --- Carga de datos --- #
respuestas = cargar_respuestas(RESPUESTAS_CSV)
colegios, regiones, comunas_por_region = cargar_colegios(COLEGIOS_CSV)
ORIGENES = ["Clave Única", "Servicio Electoral", "ChileAtiende", "Registro Civil e Identificación"]

# --- Interfaz Streamlit --- #
st.set_page_config(page_title="Generador de Respuestas", layout="wide")

st.title("Generador de Respuestas - Web")

# --- Datos de entrada --- #
col1, col2 = st.columns(2)

with col1:
    numero_reclamo = st.text_input("Número de Reclamo:")
    rut = st.text_input("RUT (formato 12.345.678-9):")
    caso = st.selectbox("Caso (tipo de respuesta):", options=sorted(respuestas.keys()))
    codigo_local = st.text_input("Código del local:")

with col2:
    region_seleccionada = st.selectbox("Región:", options=regiones)
    comuna_seleccionada = st.selectbox("Comuna:", options=comunas_por_region.get(region_seleccionada, []))

# Caso 5
fecha_caso5 = ''
origen_caso5 = ''
if caso == '5':
    fecha_caso5 = st.text_input("(Caso 5) Fecha:")
    origen_caso5 = st.selectbox("(Caso 5) Origen:", options=ORIGENES)

# --- Funcionalidad --- #
if st.button("Generar Respuesta"):
    # Validaciones
    if not numero_reclamo or not rut or not caso or not codigo_local:
        st.warning("Complete todos los campos obligatorios")
    elif caso == '5' and (not fecha_caso5 or not origen_caso5):
        st.warning("Para el caso 5 debe completar Fecha y Origen")
    elif codigo_local not in colegios:
        st.warning("Código de local no encontrado")
    elif caso not in respuestas:
        st.warning("Caso no válido")
    else:
        plantilla = respuestas[caso]
        colegio = colegios[codigo_local]
        texto = plantilla.replace("(nombre del local)", colegio['nombre'])
        texto = texto.replace("(direccion del local)", colegio['direccion'])
        texto = texto.replace("(comuna respectiva)", colegio['comuna'])
        texto = texto.replace("(region respectiva)", colegio['region'])
        if caso == '5':
            texto = texto.replace("(fecha)", fecha_caso5) if "(fecha)" in texto else texto + f" ({fecha_caso5})"
            texto = texto.replace("(origen)", origen_caso5) if "(origen)" in texto else texto + f" ({origen_caso5})"

        rut_limpio, dv = limpiar_rut(rut)
        registrar_respuesta(numero_reclamo, datetime.datetime.now(), caso, texto, colegio['comuna'], rut_limpio, dv)
        st.text_area("Respuesta generada:", value=texto, height=200)
        st.success("Respuesta generada y registrada correctamente.")

# --- Buscador de colegios --- #
st.subheader("Buscar colegios por Región y Comuna")
region_busq = st.selectbox("Región (buscador):", options=regiones, key='busq_region')
comuna_busq = st.selectbox("Comuna (buscador):", options=comunas_por_region.get(region_busq, []), key='busq_comuna')

if st.button("Mostrar colegios"):
    encontrados = []
    for codigo, datos in colegios.items():
        if datos['region'] == region_busq and datos['comuna'] == comuna_busq:
            encontrados.append(f"{codigo}: {datos['nombre']} - {datos['direccion']}")
    if not encontrados:
        st.info("No se encontraron colegios para la comuna seleccionada.")
    else:
        st.text_area("Resultados:", value="\n".join(encontrados), height=200)
