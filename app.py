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

# ==========================================
# 🎨 INYECCIÓN DE CSS (DISEÑO PREMIUM)
# ==========================================
st.markdown("""
<style>
    /* Estilo para las métricas (Tarjetas flotantes) */
    div[data-testid="metric-container"] {
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(49, 51, 63, 0.1);
        padding: 15px 20px;
        border-radius: 12px;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.05);
        border-left: 5px solid #2980b9;
        transition: transform 0.2s ease-in-out;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-3px);
        box-shadow: 0px 6px 15px rgba(0,0,0,0.1);
    }
    
    /* Botones más modernos y redondeados */
    .stButton>button {
        border-radius: 20px !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: scale(1.02);
    }

    /* Ocultar elementos innecesarios de Streamlit para un look más "App" */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Ajustes para el texto de los títulos */
    h1, h2, h3 {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Acordeones más limpios */
    .streamlit-expanderHeader {
        background-color: var(--secondary-background-color);
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

CUOTA_MENSUAL = 10000 
PASSWORD_ACCESO = "villa2026"

# --- SISTEMA DE LOGIN ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: #2980b9; font-size: 3em;'>🛡️ Tesorería Villa</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray; font-size: 1.2em;'>Plataforma Inteligente de Gestión Financiera</p><br>", unsafe_allow_html=True)
    
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        with st.container():
            st.markdown("<div style='background-color: var(--secondary-background-color); padding: 30px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);'>", unsafe_allow_html=True)
            with st.form("login_form"):
                pass_input = st.text_input("🔑 Contraseña de Acceso", type="password", placeholder="Ingresa tu clave aquí...")
                submit_login = st.form_submit_button("Ingresar al Sistema", use_container_width=True)
                if submit_login:
                    if pass_input == PASSWORD_ACCESO:
                        st.session_state.autenticado = True
                        st.rerun()
                    else:
                        st.error("❌ Contraseña incorrecta. Intente nuevamente.")
            st.markdown("</div>", unsafe_allow_html=True)
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
        df_ie = conn.read(worksheet="Ingresos_Extra", ttl=0).dropna(how="all")
    except:
        df_ie = pd.DataFrame(columns=['concepto', 'monto', 'fecha', 'mes'])
        
    try:
        df_gu = conn.read(worksheet="Guardias", ttl=0).dropna(how="all")
    except:
        df_gu = pd.DataFrame(columns=['nombre', 'tipo', 'sueldo'])
        
    return df_p, df_g, df_ie, df_gu

df_pagos_full, df_gastos_full, df_extra_full, df_guardias = cargar_datos_nube()

# --- CARGA DE CASAS (Maestro local) ---
@st.cache_data
def cargar_casas():
    with open('casas.json', 'r', encoding='utf-8') as f:
        df = pd.DataFrame(json.load(f))
        df['numero'] = pd.to_numeric(df['numero']).astype(int)
        df = df.sort_values(by=['calle', 'numero']).reset_index(drop=True)
        return df

df_casas = cargar_casas()

# --- BARRA LATERAL ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2622/2622240.png", width=100) # Un icono bonito decorativo
    st.title("Panel de Control")
    st.markdown("---")
    meses_disponibles = ["Abril 2026", "Mayo 2026", "Junio 2026", "Julio 2026", "Agosto 2026", "Septiembre 2026", "Octubre 2026", "Noviembre 2026", "Diciembre 2026"]
    mes_actual = st.selectbox("📅 Mes de Trabajo", meses_disponibles)
    st.markdown("---")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()

# --- FILTROS DE DATOS ---
def filtrar_por_mes(df, mes):
    if not df.empty and 'mes' in df.columns:
        return df[df['mes'].astype(str).str.lower() == mes.lower()].reset_index(drop=True)
    return pd.DataFrame(columns=df.columns)

df_pagos_mes = filtrar_por_mes(df_pagos_full, mes_actual)
df_gastos_mes = filtrar_por_mes(df_gastos_full, mes_actual)
df_extra_mes = filtrar_por_mes(df_extra_full, mes_actual)

# --- MATEMÁTICA FINANCIERA ---
ingresos_vecinos = pd.to_numeric(df_pagos_mes['monto_pagado']).sum() if not df_pagos_mes.empty else 0
ingresos_eventos = pd.to_numeric(df_extra_mes['monto']).sum() if not df_extra_mes.empty else 0
total_ingresos_mes = ingresos_vecinos + ingresos_eventos

egresos_guardias = pd.to_numeric(df_guardias['sueldo']).sum() if not df_guardias.empty else 0
egresos_otros = pd.to_numeric(df_gastos_mes['monto']).sum() if not df_gastos_mes.empty else 0
total_egresos_mes = egresos_guardias + egresos_otros

balance_final = total_ingresos_mes - total_egresos_mes
deudores_count = len(df_casas) - len(df_pagos_mes)

# --- GENERADORES DE PDF ---
def generar_boleta_pdf(calle, numero, propietario, monto, fecha, mes_texto):
    pdf = FPDF(format='A5') 
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 8, txt="COMPROBANTE DE PAGO", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, txt="VILLA PIRKUN, TRIWE Y PRIMAVERA", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(40, 8, txt="Fecha:", border=0); pdf.set_font("Arial", '', 11); pdf.cell(0, 8, txt=str(fecha), ln=True)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(40, 8, txt="Concepto:", border=0); pdf.set_font("Arial", '', 11); pdf.cell(0, 8, txt=f"Seguridad Mes {mes_texto}", ln=True)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(40, 8, txt="Vecino:", border=0); pdf.set_font("Arial", '', 11); pdf.cell(0, 8, txt=f"{propietario} (#{numero})", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, txt=f"TOTAL: $ {monto:,.0f}", border=1, ln=True, align='C')
    return pdf.output(dest='S').encode('latin-1', 'replace')

def generar_pdf_cierre(ing_v, ing_e, egr_g, egr_o, bal, df_gu, df_ga, df_ex, mes_t):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 8, txt="BALANCE MENSUAL DE TESORERÍA", ln=True, align='L')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, txt=f"Mes: {mes_t.upper()} | Generado: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
    pdf.ln(10)
    
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, txt="1. Resumen de Caja", ln=True, fill=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(110, 8, txt="(+) Recaudación de Vecinos", border=1); pdf.cell(80, 8, txt=f"$ {ing_v:,.0f}", border=1, ln=True, align='R')
    pdf.cell(110, 8, txt="(+) Ingresos Extra (Rifas/Completadas)", border=1); pdf.cell(80, 8, txt=f"$ {ing_e:,.0f}", border=1, ln=True, align='R')
    pdf.cell(110, 8, txt="(-) Sueldos Guardias", border=1); pdf.cell(80, 8, txt=f"- $ {egr_g:,.0f}", border=1, ln=True, align='R')
    pdf.cell(110, 8, txt="(-) Otros Gastos e Insumos", border=1); pdf.cell(80, 8, txt=f"- $ {egr_o:,.0f}", border=1, ln=True, align='R')
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(110, 10, txt="SALDO FINAL DISPONIBLE", border=1); pdf.cell(80, 10, txt=f"$ {bal:,.0f}", border=1, ln=True, align='R')
    
    if not df_ex.empty:
        pdf.ln(10); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 8, txt="2. Detalle de Ingresos Extra", ln=True, fill=True)
        pdf.set_font("Arial", 'B', 10); pdf.cell(130, 8, txt="Concepto / Evento", border=1); pdf.cell(60, 8, txt="Monto", border=1, ln=True, align='C')
        pdf.set_font("Arial", '', 10)
        for _, r in df_ex.iterrows():
            pdf.cell(130, 8, txt=str(r['concepto']), border=1); pdf.cell(60, 8, txt=f"$ {int(r['monto']):,.0f}", border=1, ln=True, align='R')
            
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- INTERFAZ PRINCIPAL ---
st.markdown(f"<h2>🏢 Dashboard Financiero <span style='color: #2980b9;'>| {mes_actual}</span></h2>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# Cuadrícula de Métricas 2x2 responsiva
m1, m2 = st.columns(2)
m3, m4 = st.columns(2)
m1.metric("Ingresos Vecinos", f"${ingresos_vecinos:,.0f}")
m2.metric("Ingresos Extra", f"${ingresos_eventos:,.0f}")
m3.metric("Fondo Real en Caja", f"${balance_final:,.0f}")
m4.metric("Casas Morosas", f"{deudores_count} pendientes")
st.markdown("<br>", unsafe_allow_html=True)

# Pestañas
t1, t2, t3, t4, t5 = st.tabs(["📝 Pagos Vecinos", "🎁 Ingresos Extra", "🛒 Gastos", "📑 Cierre de Mes", "👮‍♂️ Guardias"])

with t1:
    with st.container():
        st.markdown("#### 💵 Registrar Nuevo Pago")
        c_sel = st.selectbox("1. Seleccione Pasaje", df_casas['calle'].unique())
        p_ya = df_pagos_mes[df_pagos_mes['calle'] == c_sel]['numero'].tolist()
        pend = df_casas[(df_casas['calle'] == c_sel) & (~df_casas['numero'].isin(p_ya))]
        
        if pend.empty: 
            st.success("🎉 ¡Todas las casas de este pasaje están al día!")
        else:
            opc = {f"N° {r['numero']} - {r['propietario']}": r['numero'] for _, r in pend.iterrows()}
            n_sel = opc[st.selectbox("2. Casa a pagar", opc.keys())]
            if st.button("💳 Registrar Pago", type="primary", use_container_width=True):
                nom = df_casas[(df_casas['calle'] == c_sel) & (df_casas['numero'] == n_sel)]['propietario'].values[0]
                nuevo = pd.DataFrame([{'calle': c_sel, 'numero': int(n_sel), 'propietario': nom, 'monto_pagado': CUOTA_MENSUAL, 'fecha': datetime.now().strftime("%Y-%m-%d %H:%M"), 'mes': mes_actual}])
                conn.update(worksheet="Pagos", data=pd.concat([df_pagos_full, nuevo], ignore_index=True))
                st.cache_data.clear(); st.toast(f"Pago de {nom} guardado", icon="✅"); st.rerun()

    st.markdown("---")
    st.markdown("#### 📋 Historial del Mes")
    if not df_pagos_mes.empty:
        st.dataframe(df_pagos_mes[['calle', 'numero', 'propietario', 'fecha']], use_container_width=True, hide_index=True)
        
        c_bol, c_an = st.columns(2)
        with c_bol:
            with st.expander("📄 Generar Comprobante"):
                p_sel = st.selectbox("Elegir vecino", [f"{r['calle']} #{r['numero']} - {r['propietario']}" for _, r in df_pagos_mes.iterrows()])
                if p_sel:
                    ca, nu = p_sel.split(" #")[0], int(p_sel.split(" #")[1].split(" - ")[0])
                    dat = df_pagos_mes[(df_pagos_mes['calle'] == ca) & (df_pagos_mes['numero'] == nu)].iloc[0]
                    st.download_button("📥 Descargar Boleta PDF", generar_boleta_pdf(ca, nu, dat['propietario'], dat['monto_pagado'], dat['fecha'], mes_actual), file_name=f"Boleta_{nu}.pdf", use_container_width=True, type="primary")
        with c_an:
            with st.expander("⚙️ Anular Pago"):
                with st.form("form_anular"):
                    a_sel = st.selectbox("Borrar registro de:", [f"{r['calle']} #{r['numero']} - {r['propietario']}" for _, r in df_pagos_mes.iterrows()])
                    if st.form_submit_button("Eliminar Pago", use_container_width=True):
                        c, n = a_sel.split(" #")[0], int(a_sel.split(" #")[1].split(" - ")[0])
                        df_act = df_pagos_full[~((df_pagos_full['calle'] == c) & (df_pagos_full['numero'] == n) & (df_pagos_full['mes'].astype(str).str.lower() == mes_actual.lower()))]
                        conn.update(worksheet="Pagos", data=df_act); st.cache_data.clear(); st.toast("Pago Anulado", icon="🗑️"); st.rerun()

with t2:
    st.markdown("#### 🎁 Registrar Ingresos Extra")
    st.info("💡 Usa esta sección para registrar el dinero recaudado en rifas, completadas o aportes voluntarios de los vecinos.")
    with st.form("form_extra"):
        con = st.text_input("Concepto (Ej: Rifa Fiestas Patrias, Completada...)")
        mon = st.number_input("Monto Recaudado Total ($)", min_value=0, step=1000)
        if st.form_submit_button("💰 Guardar Ingreso a la Caja", use_container_width=True):
            if con and mon > 0:
                nuevo_e = pd.DataFrame([{'concepto': con, 'monto': int(mon), 'fecha': datetime.now().strftime("%d/%m/%Y"), 'mes': mes_actual}])
                conn.update(worksheet="Ingresos_Extra", data=pd.concat([df_extra_full, nuevo_e], ignore_index=True))
                st.cache_data.clear(); st.toast("Ingreso guardado correctamente", icon="🎉"); st.rerun()
    
    if not df_extra_mes.empty:
        st.markdown("#### 📋 Eventos del Mes")
        st.dataframe(df_extra_mes[['concepto', 'monto', 'fecha']], use_container_width=True, hide_index=True)
        with st.expander("🗑️ Anular Ingreso Extra"):
            borrar_e = st.selectbox("Seleccione evento a borrar", [f"{r['concepto']} - ${r['monto']}" for _, r in df_extra_mes.iterrows()])
            if st.button("Eliminar Permanentemente"):
                c_del, m_del = borrar_e.split(" - $")
                monto_a_borrar = float(m_del)
                df_extra_full['monto'] = pd.to_numeric(df_extra_full['monto'])
                df_act = df_extra_full[~((df_extra_full['concepto'] == c_del) & (df_extra_full['monto'] == monto_a_borrar) & (df_extra_full['mes'].astype(str).str.lower() == mes_actual.lower()))]
                conn.update(worksheet="Ingresos_Extra", data=df_act); st.cache_data.clear(); st.rerun()

with t3:
    st.markdown("#### 🛒 Ingresar Nuevo Gasto")
    with st.form("form_gastos"):
        des = st.text_input("Descripción del insumo o servicio")
        val = st.number_input("Costo Total ($)", min_value=0, step=1000)
        if st.form_submit_button("🚀 Registrar Gasto", use_container_width=True):
            if des and val > 0:
                nuevo_g = pd.DataFrame([{'descripcion': des, 'monto': int(val), 'fecha': datetime.now().strftime("%d/%m/%Y"), 'mes': mes_actual}])
                conn.update(worksheet="Gastos", data=pd.concat([df_gastos_full, nuevo_g], ignore_index=True))
                st.cache_data.clear(); st.toast("Gasto registrado", icon="💸"); st.rerun()
                
    if not df_gastos_mes.empty:
        st.markdown("#### 🧾 Historial de Compras")
        st.dataframe(df_gastos_mes[['descripcion', 'monto', 'fecha']], use_container_width=True, hide_index=True)
        with st.expander("🗑️ Eliminar Gasto"):
            borrar_g = st.selectbox("Seleccione gasto a borrar", [f"{r['descripcion']} - ${r['monto']}" for _, r in df_gastos_mes.iterrows()])
            if st.button("Confirmar Eliminación"):
                d_del, m_del = borrar_g.split(" - $")
                monto_a_borrar = float(m_del)
                df_gastos_full['monto'] = pd.to_numeric(df_gastos_full['monto'])
                df_act = df_gastos_full[~((df_gastos_full['descripcion'] == d_del) & (df_gastos_full['monto'] == monto_a_borrar) & (df_gastos_full['mes'].astype(str).str.lower() == mes_actual.lower()))]
                conn.update(worksheet="Gastos", data=df_act); st.cache_data.clear(); st.rerun()

with t4:
    st.markdown("#### 📑 Cierre de Tesorería")
    st.write("Genera los documentos oficiales para presentar a la directiva o vecinos.")
    
    doc = generar_pdf_cierre(ingresos_vecinos, ingresos_eventos, egresos_guardias, egresos_otros, balance_final, df_guardias, df_gastos_mes, df_extra_mes, mes_actual)
    st.download_button("📄 Descargar Balance Mensual (PDF)", doc, file_name=f"Balance_{mes_actual}.pdf", type="primary", use_container_width=True)
    
    st.markdown("---")
    df_deu = df_casas.merge(df_pagos_mes[['calle', 'numero']], on=['calle', 'numero'], how='left', indicator=True)
    df_deu = df_deu[df_deu['_merge'] == 'left_only'].drop(columns='_merge')
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as wr:
        df_impresion = df_deu.rename(columns={'calle': 'PASAJE', 'numero': 'N° CASA', 'propietario': 'PROPIETARIO'})
        df_impresion.to_excel(wr, index=False, sheet_name='Morosos', startrow=2)
        ws = wr.sheets['Morosos']
        ws['A1'] = f"VECINOS MOROSOS - {mes_actual.upper()}"
        ws['A1'].font = Font(bold=True, size=14)
        for col in ['A', 'B', 'C']: ws.column_dimensions[col].width = 20
    st.download_button("📥 Descargar Planilla de Morosos (Excel)", buf.getvalue(), file_name=f"Morosos_{mes_actual}.xlsx", use_container_width=True)

with t5:
    st.markdown("#### 👮‍♂️ Nómina de Guardias Activos")
    if not df_guardias.empty:
        st.dataframe(df_guardias, use_container_width=True, hide_index=True)
    else:
        st.info("Sin personal registrado.")
        
    with st.expander("➕ Contratar Nuevo Personal"):
        with st.form("add_gu"):
            n_gu = st.text_input("Nombre Completo")
            t_gu = st.selectbox("Tipo de Contrato", ["Full Time", "Part Time", "Reemplazo Domingos"])
            s_gu = st.number_input("Sueldo Mensual ($)", value=450000, step=10000)
            if st.form_submit_button("Guardar Empleado", use_container_width=True):
                if n_gu:
                    n_reg = pd.DataFrame([{'nombre': n_gu, 'tipo': t_gu, 'sueldo': int(s_gu)}])
                    conn.update(worksheet="Guardias", data=pd.concat([df_guardias, n_reg], ignore_index=True))
                    st.cache_data.clear(); st.toast("Guardia contratado", icon="✅"); st.rerun()
                    
    if not df_guardias.empty:
        with st.expander("➖ Desvincular Guardia"):
            with st.form("del_gu"):
                g_borrar = st.selectbox("Seleccione empleado a eliminar", df_guardias['nombre'].tolist())
                if st.form_submit_button("Confirmar Despido", use_container_width=True):
                    df_act = df_guardias[df_guardias['nombre'] != g_borrar]
                    conn.update(worksheet="Guardias", data=df_act); st.cache_data.clear(); st.rerun()
