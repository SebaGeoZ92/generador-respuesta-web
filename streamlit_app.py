import streamlit as st
import pandas as pd
import re
import datetime

# --- Archivos CSV ---
RESPUESTAS_CSV = "RESPUESTAS.csv"
COLEGIOS_CSV = "COLEGIOS.csv"

# --- Funciones para cargar CSV --- #
def cargar_respuestas(nombre_archivo):
    try:
        df = pd.read_csv(nombre_archivo, delimiter=';', encoding='utf-8-sig')
        respuestas = {}
        for _, fila in df.iterrows():
            caso = str(fila.get('Caso', '')).strip()
            respuesta = str(fila.get('Respuesta', '')).strip()
            if caso and respuesta:
                respuestas[caso] = respuesta
        return respuestas
    except Exception as e:
        st.error(f"No se pudo leer {nombre_archivo}: {e}")
        return {}

def cargar_colegios(nombre_archivo):
    try:
        df = pd.read_csv(nombre_archivo, delimiter=';', encoding='utf-8-sig')
        colegios = {}
        regiones = set()
        comunas_por_region = {}
        for _, fila in df.iterrows():
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
        return colegios, sorted(list(regiones)), {r: sorted(list(c)) for r, c in comunas_por_region.items()}
    except Exception as e:
        st.error(f"No se pudo leer {nombre_archivo}: {e}")
        return {}, [], {}

# --- Cargar datos --- #
respuestas = cargar_respuestas(RESPUESTAS_CSV)
colegios, regiones, comunas_por_region = cargar_colegios(COLEGIOS_CSV)

# --- Interfaz Streamlit --- #
st.title("Generador de Respuestas - Web")

# Número de reclamo
numero_reclamo = st.text_input("Número de Reclamo:")

# RUT
rut_input = st.text_input("RUT (formato 12.345.678-9):")
# Limpiar RUT
rut_limpio = ''
m = re.match(r'^\s*([\d\.]+)-?([\dkK])\s*$', rut_input)
if m:
    rut_limpio = re.sub(r'\D', '', m.group(1))
dv = m.group(2) if m else ''

# Caso
caso = st.selectbox("Caso (tipo de respuesta):", [""] + sorted(respuestas.keys()))

# Selector dinámico de colegios
region_sel = st.selectbox("Región:", [""] + regiones)
comuna_sel = None
codigo_local = ""
if region_sel:
    comuna_sel = st.selectbox("Comuna:", [""] + comunas_por_region.get(region_sel, []))
if comuna_sel:
    # Filtrar colegios
    codigos_encontrados = [c for c,d in colegios.items() if d['region']==region_sel and d['comuna']==comuna_sel]
    codigo_local = st.selectbox("Código del local:", [""] + codigos_encontrados)

# Campos solo caso 5
fecha_caso5 = ""
origen_caso5 = ""
ORIGENES = ["Clave Única", "Servicio Electoral", "ChileAtiende", "Registro Civil e Identificación"]
if caso == "5":
    fecha_caso5 = st.text_input("Fecha (solo caso 5):")
    origen_caso5 = st.selectbox("Origen (solo caso 5):", [""] + ORIGENES)

# Botón generar respuesta
if st.button("Generar Respuesta"):
    # Validaciones
    errores = []
    if not numero_reclamo:
        errores.append("Debe ingresar número de reclamo.")
    if not rut_input or not rut_limpio:
        errores.append("Debe ingresar un RUT válido.")
    if not caso:
        errores.append("Debe seleccionar un caso.")
    if not codigo_local:
        errores.append("Debe seleccionar un código de local.")
    if caso == "5":
        if not fecha_caso5 or not origen_caso5:
            errores.append("Para el caso 5 debe completar Fecha y Origen.")
    if errores:
        for e in errores:
            st.error(e)
    else:
        # Generar texto
        plantilla = respuestas[caso]
        colegio = colegios[codigo_local]
        texto = plantilla
        texto = texto.replace("(nombre del local)", colegio['nombre'])
        texto = texto.replace("(direccion del local)", colegio['direccion'])
        texto = texto.replace("(comuna respectiva)", colegio['comuna'])
        texto = texto.replace("(region respectiva)", colegio['region'])
        if caso == "5":
            texto = texto.replace("(fecha)", fecha_caso5) if "(fecha)" in texto else texto + f" ({fecha_caso5})"
            texto = texto.replace("(origen)", origen_caso5) if "(origen)" in texto else texto + f" ({origen_caso5})"
        
        # Mostrar respuesta
        st.text_area("Respuesta Generada:", texto, height=150)
        
        # Crear línea lista para Excel
        ahora = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        caso_val = int(caso) if caso.replace('.', '', 1).isdigit() else caso
        linea_excel = f"{numero_reclamo}\t{ahora}\t{caso_val}\t{colegio['comuna']}\t{rut_limpio}\t{dv}\t{texto}"
        st.text_area("Línea lista para copiar en Excel:", linea_excel, height=80)
