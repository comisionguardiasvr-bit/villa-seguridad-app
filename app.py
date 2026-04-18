import streamlit as st
import pandas as pd
import json
import io
from datetime import datetime
from openpyxl.styles import Font, Alignment, Border, Side
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURACIÓN DE PARÁMETROS ---
st.set_page_config(page_title="Seguridad Villa", page_icon="🛡️", layout="wide")

CUOTA_MENSUAL = 10000 
PASSWORD_ACCESO = "villa2026"

# --- SISTEMA DE LOGIN (Optimizado para móvil) ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center;'>🛡️ Tesorería Villa</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Sistema de control de accesos y pagos</p>", unsafe_allow_html=True)
    
    _, col_login, _ = st.columns([1, 2, 1])
    with col_login:
        with st.form("login_form"):
            pass_input = st.text_input("Contraseña de acceso", type="password", placeholder="Ingrese su clave...")
            submit_login = st.form_submit_button("Ingresar", use_container_width=True)
            if submit_login:
                if pass_input == PASSWORD_ACCESO:
                    st.session_state.autenticado = True
                    st.rerun()
                else:
                    st.error("❌ Contraseña incorrecta.")
    st.stop()

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos_nube():
    try:
        df_p = conn.read(worksheet="Pagos", ttl=0).dropna(how="all")
        df_p['numero'] = pd.to_numeric(df_p['numero']).astype(int)
    except:
        df_p = pd.DataFrame(columns=['calle', 'numero', 'propietario', 'monto_pagado', 'fecha', 'mes'])
        
    try:
        df_g = conn.read(worksheet="Gastos", ttl=0).dropna(how="all")
    except:
        df_g = pd.DataFrame(columns=['descripcion', 'monto', 'fecha', 'mes'])
        
    try:
        df_gu = conn.read(worksheet="Guardias", ttl=0).dropna(how="all")
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

# --- BARRA LATERAL (Menú) ---
with st.sidebar:
    st.title("⚙️ Menú Principal")
    meses_disponibles = ["Abril 2026", "Mayo 2026", "Junio 2026", "Julio 2026", "Agosto 2026", "Septiembre 2026", "Octubre 2026", "Noviembre 2026", "Diciembre 2026"]
    mes_actual = st.selectbox("📅 Seleccione el Mes", meses_disponibles)
    st.markdown("---")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()

# --- FILTROS SEGUROS DE MES ---
if not df_pagos_full.empty and 'mes' in df_pagos_full.columns:
    df_pagos_mes = df_pagos_full[df_pagos_full['mes'].astype(str).str.lower() == mes_actual.lower()].reset_index(drop=True)
else:
    df_pagos_mes = pd.DataFrame(columns=df_pagos_full.columns)

if not df_gastos_full.empty and 'mes' in df_gastos_full.columns:
    df_gastos_mes = df_gastos_full[df_gastos_full['mes'].astype(str).str.lower() == mes_actual.lower()].reset_index(drop=True)
else:
    df_gastos_mes = pd.DataFrame(columns=df_gastos_full.columns)

# --- CÁLCULOS GLOBALES ---
COSTO_TOTAL_GUARDIAS = pd.to_numeric(df_guardias['sueldo']).sum() if not df_guardias.empty else 0
TOTAL_OTROS_GASTOS = pd.to_numeric(df_gastos_mes['monto']).sum() if not df_gastos_mes.empty else 0
recaudado_actual = pd.to_numeric(df_pagos_mes['monto_pagado']).sum() if not df_pagos_mes.empty else 0
balance_total = recaudado_actual - (COSTO_TOTAL_GUARDIAS + TOTAL_OTROS_GASTOS)
deudores_count = len(df_casas) - len(df_pagos_mes)

# --- GENERADORES DE PDF ---
def generar_boleta_pdf(calle, numero, propietario, monto, fecha, mes_texto):
    pdf = FPDF(format='A5') 
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 8, txt="COMPROBANTE DE PAGO - SEGURIDAD", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, txt="VILLA PASAJES PIRKUN, TRIWE Y PRIMAVERA", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(40, 8, txt="Fecha de Pago:", border=0)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, txt=str(fecha), border=0, ln=True)
    
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(40, 8, txt="Mes Cancelado:", border=0)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, txt=str(mes_texto).upper(), border=0, ln=True)
    
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(40, 8, txt="Recibido de:", border=0)
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 8, txt=f"{propietario} (Calle {calle} #{numero})", border=0, ln=True)
    
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(40, 10, txt="Monto Pagado:", border=0)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, txt=f"$ {monto:,.0f}", border=0, ln=True)
    
    pdf.ln(15)
    pdf.set_font("Arial", 'I', 9)
    pdf.cell(0, 5, txt="Documento emitido digitalmente. Válido como comprobante de tesorería.", ln=True, align='C')
    
    return pdf.output(dest='S').encode('latin-1', 'replace')

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

# --- INTERFAZ PRINCIPAL ---
st.title(f"📊 Dashboard - {mes_actual}")

tab1, tab2, tab3, tab4 = st.tabs(["📝 Pagos", "🛒 Gastos", "📑 Cierre", "👮‍♂️ Personal"])

# ==========================================
# PESTAÑA 1: PAGOS
# ==========================================
with tab1:
    col_m1, col_m2 = st.columns(2)
    col_m3, col_m4 = st.columns(2)
    col_m1.metric("Meta Mensual", f"${len(df_casas)*CUOTA_MENSUAL:,.0f}")
    col_m2.metric("Recaudado", f"${recaudado_actual:,.0f}")
    col_m3.metric("Saldo Caja", f"${balance_total:,.0f}", delta=f"{balance_total:,.0f}")
    col_m4.metric("Morosos", f"{deudores_count} casas")

    st.markdown("---")
    st.subheader("💵 Registrar Nuevo Pago")
    
    with st.container():
        calle_sel = st.selectbox("1. Seleccione Calle / Pasaje", df_casas['calle'].unique())
        
        p_hechos = df_pagos_mes[df_pagos_mes['calle'] == calle_sel]['numero'].tolist()
        pendientes = df_casas[(df_casas['calle'] == calle_sel) & (~df_casas['numero'].isin(p_hechos))]
        
        if pendientes.empty:
            st.success("✨ ¡Todas las casas de este pasaje están al día!")
            num_sel = None
        else:
            dict_pend = {f"N° {r['numero']} - {r['propietario']}": r['numero'] for idx, r in pendientes.iterrows()}
            num_sel = dict_pend[st.selectbox("2. Seleccione Casa Pendiente", dict_pend.keys())]

        if st.button("💳 Guardar Pago", type="primary", use_container_width=True, disabled=(num_sel is None)):
            nom = df_casas[(df_casas['calle'] == calle_sel) & (df_casas['numero'] == num_sel)]['propietario'].values[0]
            nuevo = pd.DataFrame([{'calle': calle_sel, 'numero': int(num_sel), 'propietario': nom, 'monto_pagado': CUOTA_MENSUAL, 'fecha': datetime.now().strftime("%Y-%m-%d %H:%M"), 'mes': mes_actual}])
            df_actualizado = pd.concat([df_pagos_full, nuevo], ignore_index=True)
            conn.update(worksheet="Pagos", data=df_actualizado)
            st.cache_data.clear()
            st.toast(f"✅ Pago de {nom} guardado con éxito.", icon="☁️")
            st.rerun()

    st.markdown("---")
    st.subheader("📋 Estado del Mes")
    
    view_morosos, view_pagos = st.tabs(["🔴 Casas Pendientes", "🟢 Pagos Realizados"])
    
    with view_morosos:
        deudores = df_casas.merge(df_pagos_mes[['calle', 'numero']], on=['calle', 'numero'], how='left', indicator=True)
        st.dataframe(deudores[deudores['_merge'] == 'left_only'].drop(columns='_merge'), use_container_width=True, hide_index=True)
        
    with view_pagos:
        if not df_pagos_mes.empty:
            st.dataframe(df_pagos_mes[['calle', 'numero', 'propietario', 'fecha']], use_container_width=True, hide_index=True)
            
            st.markdown("##### 🧾 Comprobantes y Anulaciones")
            c_bol, c_anular = st.columns(2)
            
            with c_bol:
                with st.expander("📄 Descargar Comprobante"):
                    pago_sel = st.selectbox("Seleccione el vecino:", [f"{r['calle']} #{r['numero']} - {r['propietario']}" for i, r in df_pagos_mes.iterrows()])
                    if pago_sel:
                        c, n = pago_sel.split(" #")[0], int(pago_sel.split(" #")[1].split(" - ")[0])
                        datos_pago = df_pagos_mes[(df_pagos_mes['calle'] == c) & (df_pagos_mes['numero'] == n)].iloc[0]
                        
                        pdf_boleta = generar_boleta_pdf(c, n, datos_pago['propietario'], datos_pago['monto_pagado'], datos_pago['fecha'], mes_actual)
                        
                        st.download_button(
                            label="📥 Descargar Boleta (PDF)",
                            data=pdf_boleta,
                            file_name=f"Comprobante_{c}_{n}_{mes_actual.replace(' ', '_')}.pdf",
                            mime="application/pdf",
                            type="primary",
                            use_container_width=True
                        )
            
            with c_anular:
                with st.expander("⚙️ Anular un pago (Borrar)"):
                    with st.form("anular_pago"):
                        target = st.selectbox("Seleccione pago a eliminar:", [f"{r['calle']} #{r['numero']} - {r['propietario']}" for i, r in df_pagos_mes.iterrows()])
                        if st.form_submit_button("Confirmar Anulación", use_container_width=True):
                            c, n = target.split(" #")[0], int(target.split(" #")[1].split(" - ")[0])
                            df_actualizado = df_pagos_full[~((df_pagos_full['calle'] == c) & (df_pagos_full['numero'] == n) & (df_pagos_full['mes'].astype(str).str.lower() == mes_actual.lower()))]
                            conn.update(worksheet="Pagos", data=df_actualizado)
                            st.cache_data.clear()
                            st.toast("🗑️ Pago anulado correctamente.", icon="✅")
                            st.rerun()
        else:
            st.info("Aún no hay pagos registrados en este mes.")

# ==========================================
# PESTAÑA 2: GASTOS
# ==========================================
with tab2:
    st.subheader("🛒 Ingresar Nuevo Gasto")
    with st.container():
        d = st.text_input("Descripción del insumo/servicio", placeholder="Ej: Pilas, linterna, arreglos...")
        m = st.number_input("Costo Total ($)", min_value=0, step=1000)
        
        if st.button("➕ Registrar Gasto", type="primary", use_container_width=True):
            if d and m > 0:
                new_g = pd.DataFrame([{'descripcion': d, 'monto': int(m), 'fecha': datetime.now().strftime("%d/%m/%Y"), 'mes': mes_actual}])
                df_actualizado = pd.concat([df_gastos_full, new_g], ignore_index=True)
                conn.update(worksheet="Gastos", data=df_actualizado)
                st.cache_data.clear()
                st.toast("✅ Gasto registrado en la nube.", icon="💸")
                st.rerun()
            else:
                st.error("Ingrese una descripción y monto válido.")
                
    st.markdown("---")
    st.subheader("🧾 Historial de Compras")
    if not df_gastos_mes.empty:
        st.dataframe(df_gastos_mes[['descripcion', 'monto', 'fecha']], use_container_width=True, hide_index=True)
        
        with st.expander("⚙️ Anular un Gasto"):
            with st.form("borrar_gasto"):
                target_g = st.selectbox("Seleccione gasto:", [f"{r['descripcion']} - ${r['monto']}" for i, r in df_gastos_mes.iterrows()])
                if st.form_submit_button("Eliminar Gasto", use_container_width=True):
                    desc_del, monto_del = target_g.split(" - $")
                    
                    # Fix de los decimales de Google Sheets
                    monto_a_borrar = float(monto_del)
                    df_gastos_full['monto'] = pd.to_numeric(df_gastos_full['monto'])
                    
                    df_actualizado = df_gastos_full[~((df_gastos_full['descripcion'] == desc_del) & (df_gastos_full['monto'] == monto_a_borrar) & (df_gastos_full['mes'].astype(str).str.lower() == mes_actual.lower()))]
                    conn.update(worksheet="Gastos", data=df_actualizado)
                    st.cache_data.clear()
                    st.toast("🗑️ Gasto eliminado.", icon="✅")
                    st.rerun()
    else:
        st.info("Sin gastos registrados este mes.")

# ==========================================
# PESTAÑA 3: CIERRE
# ==========================================
with tab3:
    st.subheader("📑 Reportes Oficiales")
    st.write("Descarga los documentos de tesorería listos para imprimir o enviar por WhatsApp.")
    
    st.markdown("##### 1. Liquidación de Gastos (Balance)")
    pdf = generar_pdf_cierre(recaudado_actual, COSTO_TOTAL_GUARDIAS, TOTAL_OTROS_GASTOS, balance_total, df_guardias, df_gastos_mes, mes_actual)
    st.download_button("📄 Descargar PDF Final", data=pdf, file_name=f"Reporte_{mes_actual}.pdf", mime="application/pdf", use_container_width=True, type="primary")
    
    st.markdown("---")
    st.markdown("##### 2. Lista de Vecinos Morosos")
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
    st.download_button("📥 Descargar Excel de Morosos", data=buffer.getvalue(), file_name=f"Deudores_{mes_actual}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

# ==========================================
# PESTAÑA 4: PERSONAL
# ==========================================
with tab4:
    st.subheader("👮‍♂️ Nómina de Guardias")
    if not df_guardias.empty:
        st.dataframe(df_guardias, use_container_width=True, hide_index=True)
    else:
        st.info("No hay guardias registrados.")
        
    st.markdown("---")
    
    with st.expander("➕ Contratar Nuevo Guardia"):
        with st.form("add_g"):
            n = st.text_input("Nombre Completo")
            t = st.selectbox("Tipo de Contrato", ["Full Time", "Part Time", "Reemplazo"])
            s = st.number_input("Sueldo Acordado ($)", value=400000, step=10000)
            if st.form_submit_button("Registrar Contrato", use_container_width=True):
                if n:
                    nuevo = pd.DataFrame([{'nombre': n, 'tipo': t, 'sueldo': int(s)}])
                    df_actualizado = pd.concat([df_guardias, nuevo], ignore_index=True)
                    conn.update(worksheet="Guardias", data=df_actualizado)
                    st.cache_data.clear()
                    st.toast(f"✅ Guardia {n} registrado.", icon="👮")
                    st.rerun()

    if not df_guardias.empty:
        with st.expander("➖ Despedir / Eliminar Guardia"):
            with st.form("del_g"):
                guardia_a_borrar = st.selectbox("Seleccione al trabajador", df_guardias['nombre'].tolist())
                if st.form_submit_button("Confirmar Despido", use_container_width=True):
                    df_actualizado = df_guardias[df_guardias['nombre'] != guardia_a_borrar]
                    conn.update(worksheet="Guardias", data=df_actualizado)
                    st.cache_data.clear()
                    st.toast("🗑️ Registro de guardia eliminado.", icon="✅")
                    st.rerun()
