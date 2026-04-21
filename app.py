import streamlit as st
import pandas as pd
import json
import io
from datetime import datetime
from openpyxl.styles import Font, Alignment, Border, Side
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection
import os

# --- CONFIGURACIÓN DE PARÁMETROS ---
st.set_page_config(page_title="Tesorería Villa Raimapu", page_icon="🌿", layout="wide")

# ==========================================
# 🎨 INYECCIÓN DE CSS (DISEÑO PREMIUM VERDE)
# ==========================================
st.markdown("""
<style>
    div[data-testid="metric-container"] {
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(49, 51, 63, 0.1);
        padding: 15px 20px;
        border-radius: 12px;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.05);
        border-left: 5px solid #2e7d32; /* Verde corporativo del logo */
        transition: transform 0.2s ease-in-out;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-3px);
        box-shadow: 0px 6px 15px rgba(0,0,0,0.1);
    }
    .stButton>button {
        border-radius: 20px !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: scale(1.02);
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    h1, h2, h3 {font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;}
    .streamlit-expanderHeader {
        background-color: var(--secondary-background-color);
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

CUOTA_MENSUAL = 10000 
PASSWORD_ACCESO = "villa2026"

# --- SISTEMA DE LOGIN (Más intuitivo) ---
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    _, col_logo, _ = st.columns([1.5, 1, 1.5])
    with col_logo:
        # Intenta cargar el logo en el inicio si existe
        if os.path.exists("logo_villa.jpg"):
            st.image("logo_villa.jpg", use_container_width=True)
        else:
            st.markdown("<h1 style='text-align: center; font-size: 4em;'>🌿</h1>", unsafe_allow_html=True)

    st.markdown("<h2 style='text-align: center; color: #2e7d32;'>Tesorería Villa Raimapu</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Ingrese la clave de la directiva para comenzar</p><br>", unsafe_allow_html=True)
    
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        with st.container():
            st.markdown("<div style='background-color: var(--secondary-background-color); padding: 30px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);'>", unsafe_allow_html=True)
            with st.form("login_form"):
                pass_input = st.text_input("🔑 Contraseña:", type="password", placeholder="Escriba aquí...")
                submit_login = st.form_submit_button("Entrar al Sistema", use_container_width=True)
                if submit_login:
                    if pass_input == PASSWORD_ACCESO:
                        st.session_state.autenticado = True
                        st.rerun()
                    else:
                        st.error("❌ Contraseña incorrecta. Por favor, intente de nuevo.")
            st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- CONEXIÓN A GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# 🧠 MEMORIAS INDEPENDIENTES (Anti-Bloqueos)
# ==========================================
@st.cache_data(ttl=600, show_spinner=False)
def cargar_pagos():
    try:
        df = conn.read(worksheet="Pagos", ttl=0).dropna(how="all")
        df['numero'] = pd.to_numeric(df['numero']).astype(int)
        return df
    except: return pd.DataFrame(columns=['calle', 'numero', 'propietario', 'monto_pagado', 'fecha', 'mes'])

@st.cache_data(ttl=600, show_spinner=False)
def cargar_gastos():
    try: return conn.read(worksheet="Gastos", ttl=0).dropna(how="all")
    except: return pd.DataFrame(columns=['descripcion', 'monto', 'fecha', 'mes'])

@st.cache_data(ttl=600, show_spinner=False)
def cargar_extra():
    try: return conn.read(worksheet="Ingresos_Extra", ttl=0).dropna(how="all")
    except: return pd.DataFrame(columns=['concepto', 'monto', 'fecha', 'mes'])

@st.cache_data(ttl=600, show_spinner=False)
def cargar_guardias():
    try: return conn.read(worksheet="Guardias", ttl=0).dropna(how="all")
    except: return pd.DataFrame(columns=['nombre', 'tipo', 'sueldo'])

df_pagos_full = cargar_pagos()
df_gastos_full = cargar_gastos()
df_extra_full = cargar_extra()
df_guardias = cargar_guardias()

# --- CARGA DE CASAS (Maestro local) ---
@st.cache_data
def cargar_casas():
    with open('casas.json', 'r', encoding='utf-8') as f:
        df = pd.DataFrame(json.load(f))
        df['numero'] = pd.to_numeric(df['numero']).astype(int)
        df = df.sort_values(by=['calle', 'numero']).reset_index(drop=True)
        return df

df_casas = cargar_casas()

# --- BARRA LATERAL (Con Logo de la Villa) ---
with st.sidebar:
    if os.path.exists("logo_villa.jpg"):
        st.image("logo_villa.jpg", use_container_width=True)
    else:
        st.markdown("<div style='text-align: center; font-size: 60px;'>🌿</div>", unsafe_allow_html=True)
        
    st.markdown("<h3 style='text-align: center; color: #2e7d32;'>Panel de Control</h3>", unsafe_allow_html=True)
    st.markdown("---")
    st.info("👇 Elija el mes que desea revisar o modificar:")
    meses_disponibles = ["Abril 2026", "Mayo 2026", "Junio 2026", "Julio 2026", "Agosto 2026", "Septiembre 2026", "Octubre 2026", "Noviembre 2026", "Diciembre 2026"]
    mes_actual = st.selectbox("📅 Mes Actual:", meses_disponibles)
    st.markdown("---")
    if st.button("🚪 Salir del Sistema", use_container_width=True):
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

# --- GENERADORES DE PDF (Actualizados al Logo) ---
def generar_boleta_pdf(calle, numero, propietario, monto, fecha, mes_texto):
    pdf = FPDF(format='A5') 
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 8, txt="COMPROBANTE DE PAGO", ln=True, align='C')
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 6, txt="VILLA RAIMAPU - TIERRA FLORIDA", ln=True, align='C')
    pdf.set_font("Arial", '', 9)
    pdf.cell(0, 6, txt="PUENTE ALTO", ln=True, align='C')
    pdf.ln(8)
    
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(40, 8, txt="Fecha:", border=0); pdf.set_font("Arial", '', 11); pdf.cell(0, 8, txt=str(fecha), ln=True)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(40, 8, txt="Concepto:", border=0); pdf.set_font("Arial", '', 11); pdf.cell(0, 8, txt=f"Seguridad Mes {mes_texto}", ln=True)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(40, 8, txt="Vecino:", border=0); pdf.set_font("Arial", '', 11); pdf.cell(0, 8, txt=f"{propietario} (#{numero})", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, txt=f"TOTAL PAGADO: $ {monto:,.0f}", border=1, ln=True, align='C')
    return pdf.output(dest='S').encode('latin-1', 'replace')

def generar_pdf_cierre(ing_v, ing_e, egr_g, egr_o, bal, df_gu, df_ga, df_ex, mes_t):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 8, txt="BALANCE MENSUAL DE TESORERÍA", ln=True, align='L')
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 6, txt="VILLA RAIMAPU - TIERRA FLORIDA - PUENTE ALTO", ln=True, align='L')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, txt=f"Mes: {mes_t.upper()} | Generado el: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
    pdf.ln(8)
    
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, txt="1. Resumen de Caja", ln=True, fill=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(110, 8, txt="(+) Recaudación Cuotas Vecinos", border=1); pdf.cell(80, 8, txt=f"$ {ing_v:,.0f}", border=1, ln=True, align='R')
    pdf.cell(110, 8, txt="(+) Ingresos Extra (Rifas, etc.)", border=1); pdf.cell(80, 8, txt=f"$ {ing_e:,.0f}", border=1, ln=True, align='R')
    pdf.cell(110, 8, txt="(-) Pago de Guardias", border=1); pdf.cell(80, 8, txt=f"- $ {egr_g:,.0f}", border=1, ln=True, align='R')
    pdf.cell(110, 8, txt="(-) Gastos Operativos e Insumos", border=1); pdf.cell(80, 8, txt=f"- $ {egr_o:,.0f}", border=1, ln=True, align='R')
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(110, 10, txt="SALDO FINAL EN CAJA", border=1); pdf.cell(80, 10, txt=f"$ {bal:,.0f}", border=1, ln=True, align='R')
    
    if not df_ex.empty:
        pdf.ln(10); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 8, txt="2. Detalle de Ingresos Extra", ln=True, fill=True)
        pdf.set_font("Arial", 'B', 10); pdf.cell(130, 8, txt="Actividad / Concepto", border=1); pdf.cell(60, 8, txt="Monto Recaudado", border=1, ln=True, align='C')
        pdf.set_font("Arial", '', 10)
        for _, r in df_ex.iterrows():
            pdf.cell(130, 8, txt=str(r['concepto']), border=1); pdf.cell(60, 8, txt=f"$ {int(r['monto']):,.0f}", border=1, ln=True, align='R')
            
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- INTERFAZ PRINCIPAL ---
st.markdown(f"<h2>Resumen General <span style='color: #2e7d32;'>| {mes_actual}</span></h2>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# Cuadrícula de Métricas 2x2 responsiva
m1, m2 = st.columns(2)
m3, m4 = st.columns(2)
m1.metric("Ingresos Vecinos", f"${ingresos_vecinos:,.0f}", help="Suma de todas las cuotas pagadas este mes.")
m2.metric("Ingresos de Eventos", f"${ingresos_eventos:,.0f}", help="Dinero de rifas o actividades extra.")
m3.metric("Fondo Real en Caja", f"${balance_final:,.0f}", help="Dinero total disponible tras pagar sueldos y gastos.")
m4.metric("Vecinos Morosos", f"{deudores_count} casas", help="Cantidad de casas que aún no pagan este mes.")
st.markdown("<br>", unsafe_allow_html=True)

# Pestañas Amigables
t1, t2, t3, t4, t5 = st.tabs([
    "📝 1. Registrar Pagos", 
    "🎁 2. Ingresos Extra", 
    "🛒 3. Ingresar Gastos", 
    "📑 4. Reportes y Cierre", 
    "👮‍♂️ 5. Personal"
])

# ==========================================
# PESTAÑA 1: PAGOS
# ==========================================
with t1:
    with st.container():
        st.markdown("#### 💵 Anotar el pago de un vecino")
        c_sel = st.selectbox("Paso 1: Seleccione la calle o pasaje", df_casas['calle'].unique())
        p_ya = df_pagos_mes[df_pagos_mes['calle'] == c_sel]['numero'].tolist()
        pend = df_casas[(df_casas['calle'] == c_sel) & (~df_casas['numero'].isin(p_ya))]
        
        if pend.empty: 
            st.success("🎉 ¡Felicidades! Todas las casas de este pasaje ya pagaron su cuota.")
        else:
            opc = {f"N° {r['numero']} - {r['propietario']}": r['numero'] for _, r in pend.iterrows()}
            n_sel = opc[st.selectbox("Paso 2: Busque la casa que va a pagar", opc.keys())]
            
            st.info(f"Monto a cobrar: **${CUOTA_MENSUAL:,.0f}**")
            if st.button("💳 Confirmar y Guardar Pago", type="primary", use_container_width=True):
                nom = df_casas[(df_casas['calle'] == c_sel) & (df_casas['numero'] == n_sel)]['propietario'].values[0]
                nuevo = pd.DataFrame([{'calle': c_sel, 'numero': int(n_sel), 'propietario': nom, 'monto_pagado': CUOTA_MENSUAL, 'fecha': datetime.now().strftime("%Y-%m-%d %H:%M"), 'mes': mes_actual}])
                conn.update(worksheet="Pagos", data=pd.concat([df_pagos_full, nuevo], ignore_index=True))
                cargar_pagos.clear()
                st.toast(f"Pago de {nom} guardado exitosamente", icon="✅"); st.rerun()

    st.markdown("---")
    st.markdown("#### 📋 Opciones Adicionales")
    if not df_pagos_mes.empty:
        c_bol, c_an = st.columns(2)
        with c_bol:
            with st.expander("📄 Descargar Comprobante / Boleta"):
                st.write("Busque al vecino para generarle su boleta:")
                p_sel = st.selectbox("Seleccionar vecino:", [f"{r['calle']} #{r['numero']} - {r['propietario']}" for _, r in df_pagos_mes.iterrows()])
                if p_sel:
                    ca, nu = p_sel.split(" #")[0], int(p_sel.split(" #")[1].split(" - ")[0])
                    dat = df_pagos_mes[(df_pagos_mes['calle'] == ca) & (df_pagos_mes['numero'] == nu)].iloc[0]
                    st.download_button("📥 Descargar Boleta (PDF)", generar_boleta_pdf(ca, nu, dat['propietario'], dat['monto_pagado'], dat['fecha'], mes_actual), file_name=f"Boleta_{nu}.pdf", use_container_width=True, type="primary")
        with c_an:
            with st.expander("❌ Corregir un error (Borrar pago)"):
                with st.form("form_anular"):
                    st.warning("Use esto solo si anotó un pago por equivocación.")
                    a_sel = st.selectbox("Seleccione el registro a borrar:", [f"{r['calle']} #{r['numero']} - {r['propietario']}" for _, r in df_pagos_mes.iterrows()])
                    if st.form_submit_button("Eliminar Pago Seleccionado", use_container_width=True):
                        c, n = a_sel.split(" #")[0], int(a_sel.split(" #")[1].split(" - ")[0])
                        df_act = df_pagos_full[~((df_pagos_full['calle'] == c) & (df_pagos_full['numero'] == n) & (df_pagos_full['mes'].astype(str).str.lower() == mes_actual.lower()))].reset_index(drop=True)
                        df_act = df_act.reindex(range(len(df_pagos_full)))
                        conn.update(worksheet="Pagos", data=df_act)
                        cargar_pagos.clear()
                        st.toast("El pago ha sido borrado", icon="🗑️"); st.rerun()
    else:
        st.info("Aún no se han registrado pagos en este mes.")

# ==========================================
# PESTAÑA 2: EXTRA
# ==========================================
with t2:
    st.markdown("#### 🎁 Anotar dineros de actividades")
    st.write("Si hicieron una rifa, vendieron completos o alguien hizo una donación, anótelo aquí para sumarlo a la caja de la Villa.")
    with st.form("form_extra"):
        con = st.text_input("¿De dónde vino el dinero?", placeholder="Ejemplo: Rifa del Día de la Madre")
        mon = st.number_input("¿Cuánto dinero en total se juntó? ($)", min_value=0, step=1000)
        if st.form_submit_button("💰 Guardar Dinero en Caja", use_container_width=True):
            if con and mon > 0:
                nuevo_e = pd.DataFrame([{'concepto': con, 'monto': int(mon), 'fecha': datetime.now().strftime("%d/%m/%Y"), 'mes': mes_actual}])
                conn.update(worksheet="Ingresos_Extra", data=pd.concat([df_extra_full, nuevo_e], ignore_index=True))
                cargar_extra.clear()
                st.toast("Dinero extra guardado correctamente", icon="🎉"); st.rerun()
            else:
                st.error("Debe escribir el concepto y un monto mayor a cero.")
    
    if not df_extra_mes.empty:
        st.markdown("---")
        st.markdown("#### 📋 Actividades realizadas este mes")
        st.dataframe(df_extra_mes[['concepto', 'monto', 'fecha']], use_container_width=True, hide_index=True)
        with st.expander("❌ Me equivoqué, quiero borrar una actividad"):
            borrar_e = st.selectbox("Seleccione la actividad a borrar", [f"{r['concepto']} - ${r['monto']}" for _, r in df_extra_mes.iterrows()])
            if st.button("Eliminar Actividad"):
                c_del, m_del = borrar_e.split(" - $")
                monto_a_borrar = float(m_del)
                df_extra_full['monto'] = pd.to_numeric(df_extra_full['monto'])
                df_act = df_extra_full[~((df_extra_full['concepto'] == c_del) & (df_extra_full['monto'] == monto_a_borrar) & (df_extra_full['mes'].astype(str).str.lower() == mes_actual.lower()))].reset_index(drop=True)
                df_act = df_act.reindex(range(len(df_extra_full)))
                conn.update(worksheet="Ingresos_Extra", data=df_act)
                cargar_extra.clear()
                st.rerun()

# ==========================================
# PESTAÑA 3: GASTOS
# ==========================================
with t3:
    st.markdown("#### 🛒 Anotar compras o gastos de la Villa")
    st.write("Todo lo que se compre con plata de la Villa debe anotarse aquí (ej: ampolletas, pilas, etc.)")
    with st.form("form_gastos"):
        des = st.text_input("¿Qué se compró o pagó?", placeholder="Ejemplo: Compra de 2 focos led para pasaje")
        val = st.number_input("Costo Total de la compra ($)", min_value=0, step=1000)
        if st.form_submit_button("🚀 Registrar Gasto", use_container_width=True):
            if des and val > 0:
                nuevo_g = pd.DataFrame([{'descripcion': des, 'monto': int(val), 'fecha': datetime.now().strftime("%d/%m/%Y"), 'mes': mes_actual}])
                conn.update(worksheet="Gastos", data=pd.concat([df_gastos_full, nuevo_g], ignore_index=True))
                cargar_gastos.clear()
                st.toast("Gasto registrado, el dinero se descontó de la caja", icon="💸"); st.rerun()
            else:
                st.error("Debe escribir qué compró y un costo mayor a cero.")
                
    if not df_gastos_mes.empty:
        st.markdown("---")
        st.markdown("#### 🧾 Cosas compradas este mes")
        st.dataframe(df_gastos_mes[['descripcion', 'monto', 'fecha']], use_container_width=True, hide_index=True)
        with st.expander("❌ Me equivoqué, quiero borrar un gasto"):
            borrar_g = st.selectbox("Seleccione el gasto a borrar", [f"{r['descripcion']} - ${r['monto']}" for _, r in df_gastos_mes.iterrows()])
            if st.button("Eliminar Gasto"):
                d_del, m_del = borrar_g.split(" - $")
                monto_a_borrar = float(m_del)
                df_gastos_full['monto'] = pd.to_numeric(df_gastos_full['monto'])
                df_act = df_gastos_full[~((df_gastos_full['descripcion'] == d_del) & (df_gastos_full['monto'] == monto_a_borrar) & (df_gastos_full['mes'].astype(str).str.lower() == mes_actual.lower()))].reset_index(drop=True)
                df_act = df_act.reindex(range(len(df_gastos_full)))
                conn.update(worksheet="Gastos", data=df_act)
                cargar_gastos.clear()
                st.rerun()

# ==========================================
# PESTAÑA 4: CIERRE
# ==========================================
with t4:
    st.markdown("#### 📑 Generar Documentos Oficiales")
    st.write("Use estos botones a fin de mes o antes de una reunión de vecinos. Se descargarán archivos listos para imprimir o mandar por WhatsApp.")
    
    st.markdown("##### 1. El Balance Mensual (Para la Asamblea)")
    doc = generar_pdf_cierre(ingresos_vecinos, ingresos_eventos, egresos_guardias, egresos_otros, balance_final, df_guardias, df_gastos_mes, df_extra_mes, mes_actual)
    st.download_button("📄 Descargar Balance (PDF)", doc, file_name=f"Balance_Villa_Raimapu_{mes_actual}.pdf", type="primary", use_container_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("##### 2. Lista de Vecinos Morosos (Para ir a cobrar)")
    df_deu = df_casas.merge(df_pagos_mes[['calle', 'numero']], on=['calle', 'numero'], how='left', indicator=True)
    df_deu = df_deu[df_deu['_merge'] == 'left_only'].drop(columns=['_merge'])
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as wr:
        df_impresion = df_deu.rename(columns={'calle': 'PASAJE', 'numero': 'N° CASA', 'propietario': 'PROPIETARIO'})
        df_impresion.to_excel(wr, index=False, sheet_name='Morosos', startrow=2)
        ws = wr.sheets['Morosos']
        ws['A1'] = f"VECINOS QUE FALTAN POR PAGAR - {mes_actual.upper()}"
        ws['A1'].font = Font(bold=True, size=14)
        for col in ['A', 'B', 'C']: ws.column_dimensions[col].width = 20
    st.download_button("📥 Descargar Planilla de Morosos (Excel)", buf.getvalue(), file_name=f"Morosos_Raimapu_{mes_actual}.xlsx", use_container_width=True)

# ==========================================
# PESTAÑA 5: GUARDIAS
# ==========================================
with t5:
    st.markdown("#### 👮‍♂️ Personal de Seguridad Actual")
    st.write("Esta es la lista de personas que trabajan cuidando la Villa. Sus sueldos se descuentan solos de la caja a fin de mes.")
    
    if not df_guardias.empty:
        st.dataframe(df_guardias, use_container_width=True, hide_index=True)
    else:
        st.info("Aún no hay guardias registrados en el sistema.")
        
    st.markdown("---")
    with st.expander("➕ Ingresar a un Nuevo Guardia"):
        with st.form("add_gu"):
            n_gu = st.text_input("Nombre y Apellido del trabajador")
            t_gu = st.selectbox("Tipo de Turno", ["Jornada Completa", "Medio Día", "Reemplazo Fin de Semana"])
            s_gu = st.number_input("Sueldo a pagar en el mes ($)", value=400000, step=10000)
            if st.form_submit_button("Guardar Trabajador", use_container_width=True):
                if n_gu:
                    n_reg = pd.DataFrame([{'nombre': n_gu, 'tipo': t_gu, 'sueldo': int(s_gu)}])
                    conn.update(worksheet="Guardias", data=pd.concat([df_guardias, n_reg], ignore_index=True))
                    cargar_guardias.clear()
                    st.toast(f"{n_gu} ha sido contratado", icon="✅"); st.rerun()
                else:
                    st.error("Falta escribir el nombre.")
                    
    if not df_guardias.empty:
        with st.expander("➖ Eliminar a un Guardia (Despido / Renuncia)"):
            with st.form("del_gu"):
                st.warning("Si borra al guardia, su sueldo ya no se descontará a fin de mes.")
                g_borrar = st.selectbox("Seleccione a la persona que ya no trabaja aquí:", df_guardias['nombre'].tolist())
                if st.form_submit_button("Confirmar Eliminación", use_container_width=True):
                    df_act = df_guardias[df_guardias['nombre'] != g_borrar].reset_index(drop=True)
                    df_act = df_act.reindex(range(len(df_guardias)))
                    conn.update(worksheet="Guardias", data=df_act)
                    cargar_guardias.clear()
                    st.toast("Trabajador eliminado del sistema", icon="🗑️"); st.rerun()
