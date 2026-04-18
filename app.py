import streamlit as st
import pandas as pd
import json
import io
from datetime import datetime
from openpyxl.styles import Font, Alignment, Border, Side
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PARÁMETROS ---
st.set_page_config(page_title="Gestión de Seguridad Villa", layout="wide")

CUOTA_MENSUAL = 10000 
PASSWORD_ACCESO = "villa2026"

# --- SISTEMA DE LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.markdown("<h1 style='text-align: center;'>🔒 Acceso Restringido</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Ingrese sus credenciales de administración para continuar.</p>", unsafe_allow_html=True)
    
    col_espacio1, col_login, col_espacio2 = st.columns([1, 1, 1])
    with col_login:
        with st.form("login_form"):
            pass_input = st.text_input("Contraseña de Tesorería", type="password")
            submit_login = st.form_submit_button("Ingresar al Sistema", use_container_width=True)
            if submit_login:
                if pass_input == PASSWORD_ACCESO:
                    st.session_state.autenticado = True
                    st.rerun()
                else:
                    st.error("❌ Contraseña incorrecta.")
    st.stop()

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5) # Refresca los datos cada 5 segundos
def cargar_datos_nube():
    # Leer Pagos
    try:
        df_p = conn.read(worksheet="Pagos").dropna(how="all")
        df_p['numero'] = pd.to_numeric(df_p['numero']).astype(int)
    except:
        df_p = pd.DataFrame(columns=['calle', 'numero', 'propietario', 'monto_pagado', 'fecha', 'mes'])
        
    # Leer Gastos
    try:
        df_g = conn.read(worksheet="Gastos").dropna(how="all")
    except:
        df_g = pd.DataFrame(columns=['descripcion', 'monto', 'fecha', 'mes'])
        
    # Leer Guardias
    try:
        df_gu = conn.read(worksheet="Guardias").dropna(how="all")
    except:
        df_gu = pd.DataFrame(columns=['nombre', 'tipo', 'sueldo'])
        
    return df_p, df_g, df_gu

df_pagos_full, df_gastos_full, df_guardias = cargar_datos_nube()

# --- CARGA DE CASAS (Maestro local) ---
@st.cache_data
def cargar_casas():
    with open('casas.json', 'r', encoding='utf-8') as f:
        df = pd.DataFrame(json.load(f))
        df['numero'] = pd.to_numeric(df['numero']).astype(int)
        df = df.sort_values(by=['calle', 'numero']).reset_index(drop=True)
        return df

df_casas = cargar_casas()

# --- SELECTOR DE MES ---
st.sidebar.title("⚙️ Administración en la Nube")
meses_disponibles = ["Abril 2026", "Mayo 2026", "Junio 2026", "Julio 2026", "Agosto 2026", "Septiembre 2026", "Octubre 2026", "Noviembre 2026", "Diciembre 2026"]
mes_actual = st.sidebar.selectbox("📅 Mes de Trabajo", meses_disponibles)

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

# Filtrar datos por mes actual
df_pagos_mes = df_pagos_full[df_pagos_full['mes'] == mes_actual].reset_index(drop=True)
df_gastos_mes = df_gastos_full[df_gastos_full['mes'] == mes_actual].reset_index(drop=True)

# --- CÁLCULOS GLOBALES ---
COSTO_TOTAL_GUARDIAS = pd.to_numeric(df_guardias['sueldo']).sum() if not df_guardias.empty else 0
TOTAL_OTROS_GASTOS = pd.to_numeric(df_gastos_mes['monto']).sum() if not df_gastos_mes.empty else 0
recaudado_actual = pd.to_numeric(df_pagos_mes['monto_pagado']).sum() if not df_pagos_mes.empty else 0
balance_total = recaudado_actual - (COSTO_TOTAL_GUARDIAS + TOTAL_OTROS_GASTOS)
deudores_count = len(df_casas) - len(df_pagos_mes)

# --- GENERADOR DE PDF ---
def generar_pdf_cierre(recaudado, costo_guardias, costo_otros, balance, df_guardias_lista, df_gastos, mes_texto):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 8, txt="LIQUIDACIÓN DE GASTOS DE SEGURIDAD", ln=True, align='L')
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 6, txt="VILLA PASAJES PIRKUN, TRIWE Y PRIMAVERA", ln=True, align='L')
    pdf.ln(5)
    pdf.cell(50, 6, txt="Mes de cobro: " + mes_texto.upper(), border=0, ln=True)
    pdf.cell(50, 6, txt="Fecha emisión: " + datetime.now().strftime('%d/%m/%Y'), border=0, ln=True)
    pdf.ln(8)
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, txt="1. Resumen Financiero", ln=True, fill=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(110, 8, txt="Total ingresos (Recaudación)", border=1)
    pdf.cell(80, 8, txt=f"$ {recaudado:,.0f}", border=1, ln=True, align='R')
    pdf.cell(110, 8, txt="Total remuneraciones guardias", border=1)
    pdf.cell(80, 8, txt=f"- $ {costo_guardias:,.0f}", border=1, ln=True, align='R')
    pdf.cell(110, 8, txt="Total gastos insumos/equipos", border=1)
    pdf.cell(80, 8, txt=f"- $ {costo_otros:,.0f}", border=1, ln=True, align='R')
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(110, 8, txt="Saldo Final en Caja", border=1)
    pdf.cell(80, 8, txt=f"$ {balance:,.0f}", border=1, ln=True, align='R')
    
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, txt="2. Detalle Egresos: Remuneraciones", ln=True, fill=True)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(80, 8, txt="Nombre Trabajador", border=1, align='C')
    pdf.cell(50, 8, txt="Tipo de Jornada", border=1, align='C')
    pdf.cell(60, 8, txt="Monto a Pagar", border=1, ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    for idx, g in df_guardias_lista.iterrows():
        pdf.cell(80, 8, txt=g['nombre'], border=1)
        pdf.cell(50, 8, txt=g['tipo'], border=1, align='C')
        pdf.cell(60, 8, txt=f"$ {int(g['sueldo']):,.0f}", border=1, ln=True, align='R')
        
    if not df_gastos.empty:
        pdf.ln(10)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, txt="3. Detalle Egresos: Insumos y Equipamiento", ln=True, fill=True)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(130, 8, txt="Descripción del Artículo / Servicio", border=1)
        pdf.cell(60, 8, txt="Monto", border=1, ln=True, align='C')
        pdf.set_font("Arial", '', 10)
        for idx, row in df_gastos.iterrows():
            pdf.cell(130, 8, txt=str(row['descripcion'])[:70], border=1)
            pdf.cell(60, 8, txt=f"$ {int(row['monto']):,.0f}", border=1, ln=True, align='R')
    pdf.ln(15)
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(0, 5, txt="Documento generado automáticamente por el sistema Cloud.", ln=True, align='C')
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- INTERFAZ ---
st.title(f"🛡️ Panel de Control - {mes_actual}")
tab1, tab2, tab3, tab4 = st.tabs(["📝 Pagos Diarios", "🛒 Otros Gastos", "📊 Cierre de Mes", "👮‍♂️ Personal"])

with tab1:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Meta Mensual", f"${len(df_casas)*CUOTA_MENSUAL:,.0f}")
    c2.metric("Recaudado", f"${recaudado_actual:,.0f}")
    c3.metric("Saldo Actual", f"${balance_total:,.0f}", delta=f"{balance_total:,.0f}")
    c4.metric("Casas Pendientes", f"{deudores_count}")

    st.markdown("---")
    st.subheader("Registrar Pago")
    cola, colb = st.columns(2)
    with cola:
        calle_sel = st.selectbox("Calle / Pasaje", df_casas['calle'].unique())
    with colb:
        p_hechos = df_pagos_mes[df_pagos_mes['calle'] == calle_sel]['numero'].tolist()
        pendientes = df_casas[(df_casas['calle'] == calle_sel) & (~df_casas['numero'].isin(p_hechos))]
        if pendientes.empty:
            st.info("✨ Pasaje al día.")
            num_sel = None
        else:
            dict_pend = {f"{r['numero']} - {r['propietario']}": r['numero'] for idx, r in pendientes.iterrows()}
            num_sel = dict_pend[st.selectbox("N° Casa - Propietario", dict_pend.keys())]

    if st.button("Guardar Pago Nube", type="primary", disabled=(num_sel is None)):
        nom = df_casas[(df_casas['calle'] == calle_sel) & (df_casas['numero'] == num_sel)]['propietario'].values[0]
        nuevo = pd.DataFrame([{'calle': calle_sel, 'numero': int(num_sel), 'propietario': nom, 'monto_pagado': CUOTA_MENSUAL, 'fecha': datetime.now().strftime("%Y-%m-%d %H:%M"), 'mes': mes_actual}])
        df_actualizado = pd.concat([df_pagos_full, nuevo], ignore_index=True)
        conn.update(worksheet="Pagos", data=df_actualizado)
        st.cache_data.clear()
        st.success("✅ Guardado en Google Sheets")
        st.rerun()

    st.markdown("---")
    cizq, cder = st.columns(2)
    with cizq:
        st.subheader("🚨 Casas Pendientes")
        deudores = df_casas.merge(df_pagos_mes[['calle', 'numero']], on=['calle', 'numero'], how='left', indicator=True)
        st.dataframe(deudores[deudores['_merge'] == 'left_only'].drop(columns='_merge'), use_container_width=True, hide_index=True)
    with cder:
        st.subheader("💰 Historial del Mes")
        if not df_pagos_mes.empty:
            st.dataframe(df_pagos_mes[['calle', 'numero', 'propietario', 'fecha']], use_container_width=True, hide_index=True)
            with st.form("anular"):
                target = st.selectbox("Anular pago de:", [f"{r['calle']} #{r['numero']} - {r['propietario']}" for i, r in df_pagos_mes.iterrows()])
                if st.form_submit_button("Confirmar Anulación"):
                    c, n = target.split(" #")[0], int(target.split(" #")[1].split(" - ")[0])
                    # Filtramos del dataframe FULL (todos los meses)
                    df_actualizado = df_pagos_full[~((df_pagos_full['calle'] == c) & (df_pagos_full['numero'] == n) & (df_pagos_full['mes'] == mes_actual))]
                    conn.update(worksheet="Pagos", data=df_actualizado)
                    st.cache_data.clear()
                    st.rerun()

with tab2:
    st.header("Otros Gastos")
    with st.form("gastos"):
        d, m = st.text_input("Descripción"), st.number_input("Monto", min_value=0, step=500)
        if st.form_submit_button("Registrar en Nube"):
            if d and m > 0:
                new_g = pd.DataFrame([{'descripcion': d, 'monto': int(m), 'fecha': datetime.now().strftime("%d/%m/%Y"), 'mes': mes_actual}])
                df_actualizado = pd.concat([df_gastos_full, new_g], ignore_index=True)
                conn.update(worksheet="Gastos", data=df_actualizado)
                st.cache_data.clear()
                st.rerun()
    st.dataframe(df_gastos_mes[['descripcion', 'monto', 'fecha']], use_container_width=True, hide_index=True)

with tab3:
    st.header("Cierre de Mes")
    pdf = generar_pdf_cierre(recaudado_actual, COSTO_TOTAL_GUARDIAS, TOTAL_OTROS_GASTOS, balance_total, df_guardias, df_gastos_mes, mes_actual)
    st.download_button("📄 Descargar Reporte PDF", data=pdf, file_name=f"Reporte_{mes_actual}.pdf", mime="application/pdf")
    
    st.write("---")
    df_deudores = df_casas.merge(df_pagos_mes[['calle', 'numero']], on=['calle', 'numero'], how='left', indicator=True)
    df_deudores = df_deudores[df_deudores['_merge'] == 'left_only'].drop(columns=['_merge'])
    buffer = io.BytesIO()
    df_impresion = df_deudores.rename(columns={'calle': 'CALLE / PASAJE', 'numero': 'N° CASA', 'propietario': 'NOMBRE PROPIETARIO'})
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_impresion.to_excel(writer, index=False, sheet_name='Deudores', startrow=2, startcol=1)
        ws = writer.sheets['Deudores']
        ws.column_dimensions['A'].width = 5
        ws.column_dimensions['B'].width = 25
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 35
        ws.merge_cells('B1:D2')
        ws['B1'].value = f"LISTA DE DEUDORES - {mes_actual.upper()}"
        ws['B1'].font = Font(name='Calibri', size=20, bold=True)
        ws['B1'].alignment = Alignment(horizontal='center', vertical='center')
        borde = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        centrado = Alignment(horizontal='center', vertical='center')
        for row in ws.iter_rows(min_row=3, max_row=len(df_impresion)+3, min_col=2, max_col=4):
            for cell in row:
                cell.border, cell.alignment = borde, centrado
                if cell.row == 3: cell.font = Font(bold=True)
    st.download_button("📥 Descargar Deudores (Excel)", data=buffer.getvalue(), file_name=f"Deudores_{mes_actual}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

with tab4:
    st.header("Personal (Sincronizado con Drive)")
    col_add, col_del = st.columns(2)
    with col_add:
        with st.form("add_g"):
            n, t, s = st.text_input("Nombre"), st.selectbox("Tipo", ["Full Time", "Part Time", "Reemplazo"]), st.number_input("Sueldo", value=450000)
            if st.form_submit_button("Contratar"):
                nuevo = pd.DataFrame([{'nombre': n, 'tipo': t, 'sueldo': int(s)}])
                df_actualizado = pd.concat([df_guardias, nuevo], ignore_index=True)
                conn.update(worksheet="Guardias", data=df_actualizado)
                st.cache_data.clear()
                st.rerun()
    with col_del:
        if not df_guardias.empty:
            with st.form("del_g"):
                guardia_a_borrar = st.selectbox("Despedir", df_guardias['nombre'].tolist())
                if st.form_submit_button("Confirmar"):
                    df_actualizado = df_guardias[df_guardias['nombre'] != guardia_a_borrar]
                    conn.update(worksheet="Guardias", data=df_actualizado)
                    st.cache_data.clear()
                    st.rerun()
    st.dataframe(df_guardias, use_container_width=True, hide_index=True)
