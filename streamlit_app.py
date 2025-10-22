# streamlit_app.py
import streamlit as st
import pandas as pd
import csv
import re
import datetime
import io
import json
from typing import Tuple

st.set_page_config(page_title="Generador SERVEL (web)", layout="wide")

# ---------- Helpers ----------
def limpiar_rut(rut: str) -> str:
    if not isinstance(rut, str):
        return ""
    m = re.match(r'^\s*([\d\.]+)-?([\dkK])\s*$', rut)
    if m:
        cuerpo = m.group(1)
        return re.sub(r'\D', '', cuerpo)
    return ""

def cargar_respuestas_file(uploaded_file) -> dict:
    # asumimos ; como separador (igual que tu app de escritorio)
    try:
        df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8-sig')
    except Exception:
        # intentar con coma
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, sep=',', encoding='utf-8-sig')
    respuestas = {}
    if 'Caso' in df.columns and 'Respuesta' in df.columns:
        for _, row in df.iterrows():
            caso = str(row.get('Caso', '')).strip()
            respuesta = str(row.get('Respuesta', '')).strip()
            if caso and respuesta:
                respuestas[caso] = respuesta
    else:
        # intentar primera columna como caso y segunda como respuesta
        for _, row in df.iterrows():
            cols = list(row.dropna().astype(str))
            if len(cols) >= 2:
                respuestas[cols[0].strip()] = cols[1].strip()
    return respuestas

def cargar_colegios_file(uploaded_file) -> Tuple[dict, list, dict]:
    try:
        df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8-sig', dtype=str)
    except Exception:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, sep=',', encoding='utf-8-sig', dtype=str)

    # Normalizar nombres de columnas (aceptar variantes)
    cols = {c.lower(): c for c in df.columns}
    def col(name_options):
        for o in name_options:
            if o.lower() in cols:
                return cols[o.lower()]
        return None

    codigo_col = col(['codigo_rec', 'codigo', 'codigo_recinto', 'codigo_recinto'])
    region_col = col(['region', 'región'])
    comuna_col = col(['comuna', 'comuna_res'])
    recinto_col = col(['recinto', 'nombre', 'recinto_nombre', 'recinto'])
    direccion_col = col(['direccion', 'dirección', 'direccion_recinto'])

    colegios = {}
    regiones = set()
    comunas_por_region = {}

    for _, row in df.fillna('').iterrows():
        codigo = str(row.get(codigo_col, '')).strip() if codigo_col else ''
        region = str(row.get(region_col, '')).strip() if region_col else ''
        comuna = str(row.get(comuna_col, '')).strip() if comuna_col else ''
        nombre = str(row.get(recinto_col, '')).strip() if recinto_col else ''
        direccion = str(row.get(direccion_col, '')).strip() if direccion_col else ''
        if codigo:
            colegios[codigo] = {
                'nombre': nombre,
                'direccion': direccion,
                'comuna': comuna,
                'region': region
            }
            regiones.add(region)
            comunas_por_region.setdefault(region, set()).add(comuna)

    regiones_ordenadas = sorted([r for r in regiones if r])
    comunas_por_region_ordenadas = {r: sorted(list(c)) for r, c in comunas_por_region.items()}
    return colegios, regiones_ordenadas, comunas_por_region_ordenadas

def generar_texto(respuestas_dict, colegios_dict, caso, codigo, fecha_extra=None, origen_extra=None):
    plantilla = respuestas_dict.get(caso, "")
    colegio = colegios_dict.get(codigo, {})
    texto = plantilla
    texto = texto.replace('(nombre del local)', colegio.get('nombre', ''))
    texto = texto.replace('(direccion del local)', colegio.get('direccion', ''))
    texto = texto.replace('(comuna respectiva)', colegio.get('comuna', ''))
    texto = texto.replace('(region respectiva)', colegio.get('region', ''))
    if caso == '5':
        if '(fecha)' in texto:
            texto = texto.replace('(fecha)', fecha_extra or '')
        else:
            texto = texto + f" {fecha_extra or ''}"
        if '(origen)' in texto:
            texto = texto.replace('(origen)', origen_extra or '')
        else:
            texto = texto + f" {origen_extra or ''}"
    return texto

def df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    bio = io.BytesIO()
    try:
        df.to_excel(bio, index=False, engine='openpyxl')
    except Exception:
        # fallback to csv bytes if excel not available
        bio = io.BytesIO(df.to_csv(index=False, sep=';').encode('utf-8-sig'))
    else:
        bio.seek(0)
    return bio.getvalue()

# ---------- UI ----------
st.title("Generador de Respuestas SERVEL — Web (v3.0 quick)")

col1, col2 = st.columns([1, 2])

with col1:
    st.header("1) Subir datos")
    respuestas_file = st.file_uploader("Sube respuestas (CSV; columnas: Caso,Respuesta)", type=['csv'], key="rfile")
    colegios_file = st.file_uploader("Sube recintos/colegios (CSV con código, región, comuna, recinto, Direccion)", type=['csv'], key="cfile")

    st.markdown("**Opcional:** Si quieres probar sin subir archivos, sube los CSV de ejemplo en tu repositorio y usa la URL vía `raw`.")

with col2:
    st.header("2) Campos de entrada")
    numero_reclamo = st.text_input("Número de Reclamo")
    rut_input = st.text_input("RUT (ej: 12.345.678-9)")
    rut_limpio = limpiar_rut(rut_input)
    st.text_input("RUT sin puntos ni DV (automático)", value=rut_limpio, disabled=True)

    # cargamos datos si están disponibles
    respuestas = {}
    colegios = {}
    regiones = []
    comunas_por_region = {}

    if respuestas_file:
        respuestas = cargar_respuestas_file(respuestas_file)

    if colegios_file:
        colegios, regiones, comunas_por_region = cargar_colegios_file(colegios_file)

    caso = st.selectbox("Caso (tipo de respuesta)", options=sorted(list(respuestas.keys())) if respuestas else ["(sube respuestas)"])
    codigo_manual = st.text_input("Código del local (puede autocompletarse desde buscador)")

    st.markdown("---")

    st.write("**Buscador de recintos**")
    region = st.selectbox("Región", options=[""] + regiones) if regiones else st.selectbox("Región", options=["(sube recintos)"])
    comuna = None
    if region:
        comunas = comunas_por_region.get(region, [])
        comuna = st.selectbox("Comuna", options=[""] + comunas)
    else:
        st.selectbox("Comuna", options=["(elige región primero)"])

    # mostrar list of colegios coincidentes y permitir seleccionar
    codigo_seleccionado = ""
    if region and comuna:
        matches = []
        for cod, d in colegios.items():
            if d.get('region') == region and d.get('comuna') == comuna:
                matches.append((cod, f"{cod}: {d.get('nombre','')} - {d.get('direccion','')}"))
        if matches:
            sel = st.selectbox("Colegios encontrados", options=[m[1] for m in matches])
            if sel:
                codigo_seleccionado = sel.split(':')[0].strip()
                st.write(f"Código seleccionado: **{codigo_seleccionado}**")
                if st.button("Copiar código al campo"):
                    codigo_manual = codigo_seleccionado
                    st.experimental_rerun()
        else:
            st.info("No se encontraron colegios para la región/comuna seleccionada.")

    # si el usuario puso un código manual, priorizarlo
    codigo_final = codigo_manual.strip() if codigo_manual.strip() else codigo_seleccionado

    # campos extra para caso 5
    fecha_caso5 = None
    origen_caso5 = None
    if caso == '5':
        fecha_caso5 = st.text_input("(Caso 5) Fecha")
        origen_caso5 = st.selectbox("(Caso 5) Origen", ["", "Clave Única", "Servicio Electoral", "ChileAtiende", "Registro Civil e Identificación"])

st.markdown("---")
st.header("3) Generar respuesta")

colA, colB = st.columns([3, 1])
with colA:
    generar = st.button("Generar Respuesta")
with colB:
    descargar_registro_disabled = False
    # session registro
    if 'registro_df' not in st.session_state:
        st.session_state['registro_df'] = pd.DataFrame(columns=[
            'Número de Reclamo', 'Fecha y Hora', 'Caso', 'Comuna', 'RUT', 'Dígito Verificador', 'Respuesta Generada'
        ])

# acciones al generar
if generar:
    if not numero_reclamo.strip():
        st.error("Ingrese número de reclamo.")
    elif not rut_limpio:
        st.error("Ingrese un RUT válido.")
    elif not caso or caso == "(sube respuestas)":
        st.error("Seleccione un caso válido (sube CSV de respuestas).")
    elif not codigo_final:
        st.error("Ingrese o seleccione código del local.")
    elif caso == '5' and (not fecha_caso5 or not origen_caso5):
        st.error("Para caso 5 complete Fecha y Origen.")
    else:
        texto_generado = generar_texto(respuestas, colegios, caso, codigo_final, fecha_caso5, origen_caso5)
        st.session_state['ultima_respuesta'] = texto_generado
        # extraer dv
        m = re.match(r'^\s*([\d\.]+)-?([\dkK])\s*$', rut_input)
        dv = m.group(2) if m else ''
        fila = {
            'Número de Reclamo': numero_reclamo,
            'Fecha y Hora': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Caso': int(caso) if caso.replace('.', '', 1).isdigit() else caso,
            'Comuna': colegios.get(codigo_final, {}).get('comuna', ''),
            'RUT': rut_limpio,
            'Dígito Verificador': dv,
            'Respuesta Generada': texto_generado
        }
        st.session_state['registro_df'] = pd.concat([st.session_state['registro_df'], pd.DataFrame([fila])], ignore_index=True)
        st.success("Respuesta generada y añadida al registro (descárgala abajo).")

# mostrar respuesta generada
if 'ultima_respuesta' in st.session_state:
    st.subheader("Respuesta generada")
    st.text_area("Texto", value=st.session_state['ultima_respuesta'], height=180, key="texto_generado")
    # botón copiar al portapapeles usando JS (component)
    safe_text = json.dumps(st.session_state['ultima_respuesta'])
    copy_html = f"""
    <button id="copy-btn">Copiar al portapapeles</button>
    <script>
    const text = {safe_text};
    document.getElementById('copy-btn').addEventListener('click', async () => {{
        try {{
            await navigator.clipboard.writeText(text);
            alert('Copiado al portapapeles');
        }} catch(e) {{
            alert('No se pudo copiar automáticamente. Copie manualmente desde el área de texto.');
        }}
    }});
    </script>
    """
    st.components.v1.html(copy_html, height=50)

# Mostrar y descargar registro acumulado
st.markdown("---")
st.subheader("Registro de respuestas generadas (temporal)")
st.write(f"Registros guardados en esta sesión: {len(st.session_state['registro_df'])}")
st.dataframe(st.session_state['registro_df'].tail(50))

# Botones de descarga: Excel si posible, CSV siempre
buffer_csv = st.session_state['registro_df'].to_csv(index=False, sep=';', encoding='utf-8-sig')
st.download_button("Descargar registro (.csv)", data=buffer_csv, file_name="registro_respuestas.csv", mime="text/csv")

# intentar generar xlsx
try:
    excel_bytes = df_to_excel_bytes(st.session_state['registro_df'])
    # si df_to_excel_bytes devolvió csv bytes porque no había openpyxl, se sirve como csv
    is_xlsx = excel_bytes[:2] != b'\xff\xfe' and (b'PK' in excel_bytes[:4] or b'Relationships' in excel_bytes[:200])
    if is_xlsx:
        st.download_button("Descargar registro (.xlsx)", data=excel_bytes, file_name="registro_respuestas.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        # fallback: serve same as csv but with xlsx name (Excel puede abrir CSV con separador ;)
        st.download_button("Descargar registro (.xlsx) (CSV-based)", data=excel_bytes, file_name="registro_respuestas.xlsx", mime="application/vnd.ms-excel")
except Exception:
    pass

st.caption("Nota: el registro se mantiene solo en la sesión del usuario de Streamlit. Descargue el archivo para conservarlo.")

