import streamlit as st
import pandas as pd
import datetime
import re
import os

# --- Archivos CSV --- #
RESPUESTAS_CSV = 'respuestas.csv'
COLEGIOS_CSV = 'colegios.csv'

# --- Funciones para cargar CSV --- #
def cargar_respuestas(nombre_archivo):
    respuestas = {}
    try:
        with open(nombre_archivo, encoding='utf-8-sig') as f:
            reader = pd.read_csv(f, delimiter=';')
            for _, fila in reader.iterrows():
                caso = str(fila.get('Caso', '')).strip()
                respuesta = str(fila.get('Respuesta', '')).strip()
                if caso and respuesta:
                    respuestas[caso] = respuesta
    except Exception as e:
        st.error(f"No se pudo leer {nombre_archivo}: {e}")
    return respuestas

def cargar_colegios(nombre_archivo):
    colegios = {}
    regiones = set()
    comunas_por_region = {}
    try:
        with open(nombre_archivo, encoding='utf-8-sig') as f:
            reader = pd.read_csv(f, delimiter=';')
            for _, fila in reader.iterrows():
                codigo = str(fila.get('codigo_rec', '')).strip()
                region = str(fila.get('region', '')).strip()
                comuna = str(fila.get('comuna', '')).strip()
                nombre = str(fila.get('recinto', '')).strip()
                direccion = str(fila.get('Direccion', '')).strip()
                if codigo:
                    colegios[codigo] = {
                        'nombre': nombre,
                        'direccion': direccion,
                        'comuna': comuna,
                        'region': region
                    }
                    regiones.add(region)
                    comunas_por_region.setdefault(region, set()).add(comuna)
    except Exception as e:
        st.error(f"No se pudo leer {nombre_archivo}: {e}")
    regiones_ordenadas = sorted(list(regiones))
    comunas_por_region_ordenadas = {r: sorted(list(c)) for r, c in comunas_por_region.items()}
    return colegios, regiones_ordenadas, comunas_por_region_ordenadas

# --- Cargar datos --- #
respuestas = cargar_respuestas(RESPUESTAS_CSV)
colegios, regiones, comunas_por_region = cargar_colegios(COLEGIOS_CSV)

# --- Streamlit UI --- #
st.title("Generador de Respuestas - Web")
st.write("Genera respuestas y copia línea lista para Excel.")

# --- Entrada de usuario --- #
numero_reclamo = st.text_input("Número de Reclamo")
rut_input = st.text_input("RUT (12.345.678-9)")
caso = st.selectbox("Caso", sorted(respuestas.keys()) if respuestas else [])
codigo_local = st.text_input("Código del Local")

# --- Opciones para caso 5 --- #
fecha_caso5 = st.text_input("Fecha (solo caso 5)")
origen_caso5 = st.selectbox("Origen (solo caso 5)", ["", "Clave Única", "Servicio Electoral", "ChileAtiende", "Registro Civil e Identificación"])

# --- Función de RUT limpio --- #
def limpiar_rut(rut):
    m = re.match(r'^\s*([\d\.]+)-?([\dkK])\s*$', rut)
    if m:
        cuerpo = re.sub(r'\D', '', m.group(1))
        dv = m.group(2)
        return cuerpo, dv
    return '', ''

# --- Generar respuesta --- #
if st.button("Generar Respuesta"):
    if not numero_reclamo:
        st.error("Debe ingresar número de reclamo.")
    elif not rut_input:
        st.error("Debe ingresar un RUT válido.")
    elif not caso:
        st.error("Debe seleccionar un caso.")
    elif not codigo_local:
        st.error("Debe ingresar o seleccionar el código del local.")
    elif caso == '5' and (not fecha_caso5 or not origen_caso5):
        st.error("Para el caso 5 debe completar Fecha y Origen.")
    elif codigo_local not in colegios:
        st.error("Código de local no encontrado en la base.")
    elif caso not in respuestas:
        st.error("Caso no válido.")
    else:
        # Preparar respuesta
        plantilla = respuestas[caso]
        colegio = colegios[codigo_local]
        texto = plantilla
        texto = texto.replace('(nombre del local)', colegio['nombre'])
        texto = texto.replace('(direccion del local)', colegio['direccion'])
        texto = texto.replace('(comuna respectiva)', colegio['comuna'])
        texto = texto.replace('(region respectiva)', colegio['region'])

        if caso == '5':
            if '(fecha)' in texto:
                texto = texto.replace('(fecha)', fecha_caso5)
            else:
                texto += f" ({fecha_caso5})"
            if '(origen)' in texto:
                texto = texto.replace('(origen)', origen_caso5)
            else:
                texto += f" ({origen_caso5})"

        # RUT limpio y DV
        rut_limpio, dv = limpiar_rut(rut_input)

        # --- Construir línea lista para Excel --- #
        fecha_hora = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        linea_para_excel = f"{fecha_hora};{numero_reclamo};{caso};{colegio['comuna']};{rut_limpio};{dv};{texto}"

        # --- Mostrar respuesta y línea para copiar --- #
        st.subheader("Respuesta generada:")
        st.write(texto)

        st.subheader("Línea lista para copiar en Excel:")
        st.text_area("", linea_para_excel, height=100)
