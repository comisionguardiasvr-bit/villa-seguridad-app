import streamlit as st
import pandas as pd
import json
import io
from datetime import datetime
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection
import os

st.set_page_config(page_title="Tesorería Villa Raimapu", page_icon="🌿", layout="wide")

# ==========================================
# 🎨 DISEÑO PROFESIONAL (ADAPTABLE A MODO CLARO/OSCURO)
# ==========================================
st.markdown("""
<style>
    /* Uso de variables nativas de Streamlit para asegurar lectura perfecta */
    h1, h2, h3, h4, h5 { font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #5a7d65 !important; }
    
    div[data-testid="metric-container"] {
        background-color: var(--secondary-background-color); 
        border: 1px solid rgba(90, 125, 101, 0.2);
        padding: 15px 20px; border-radius: 12px; 
        border-left: 5px solid #5a7d65; transition: all 0.3s ease;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    div[data-testid="metric-container"]:hover { transform: translateY(-3px); box-shadow: 0 6px 12px rgba(0,0,0,0.1); }
    
    .stButton>button {
        border-radius: 8px !important; font-weight: 600 !important;
        background-color: #6c8d76 !important; color: white !important; 
        border: none !important; transition: all 0.3s;
    }
    .stButton>button:hover { background-color: #4a6652 !important; transform: scale(1.02); }
    
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { border-radius: 8px 8px 0px 0px; padding: 10px 16px; }
    .stTabs [aria-selected="true"] { border-bottom: 3px solid #5a7d65 !important; color: #5a7d65 !important; }
    
    div[data-testid="stForm"] { 
        background-color: var(--secondary-background-color); 
        padding: 25px; border-radius: 12px; 
        border: 1px solid rgba(90, 125, 101, 0.2); 
    }
    
    #MainMenu, footer {visibility: hidden;}
    [data-testid="stImage"] img { border-radius: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.08); }
</style>
""", unsafe_allow_html=True)

CUOTA_MENSUAL = 10000 
MESES_DISPONIBLES = ["Abril 2026", "Mayo 2026", "Junio 2026", "Julio 2026", "Agosto 2026", "Septiembre 2026", "Octubre 2026", "Noviembre 2026", "Diciembre 2026"]

# --- HELPER: Formato de Moneda Chilena ---
def fmt_dinero(monto):
    return f"$ {int(monto):,.0f}".replace(",", ".")

# ==========================================
# 🔐 SISTEMA DE LOGIN EJECUTIVO
# ==========================================
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.rol = ""
    st.session_state.usuario = ""

if not st.session_state.autenticado:
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, col_logo, _ = st.columns([2.5, 1.5, 2.5])
    with col_logo:
        if os.path.exists("logo_villa.jpg"): st.image("logo_villa.jpg", use_container_width=True)
        else: st.markdown("<h1 style='text-align: center; font-size: 4em;'>🌿</h1>", unsafe_allow_html=True)
    
    st.markdown("<h2 style='text-align: center;'>Plataforma Financiera Raimapu</h2>", unsafe_allow_html=True)
    
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        with st.form("login_form"):
            tipo_usuario = st.selectbox("Perfil de Acceso:", ["Tesorera / Administradora", "Recaudadora en Terreno"])
            pass_input = st.text_input("🔑 Contraseña:", type="password")
            if st.form_submit_button("Ingresar al Sistema", use_container_width=True):
                if tipo_usuario == "Tesorera / Administradora" and pass_input == "villa2026":
                    st.session_state.autenticado = True; st.session_state.rol = "Admin"; st.session_state.usuario = "Tesorera Principal"; st.rerun()
                elif tipo_usuario == "Recaudadora en Terreno" and pass_input == "recauda2026":
                    st.session_state.autenticado = True; st.session_state.rol = "Recaudadora"; st.session_state.usuario = "Recaudadora Móvil"; st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas. Verifique su contraseña.")
    st.stop()

conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# 🧠 NÚCLEO DE DATOS BLINDADO
# ==========================================
def cargar_hoja_robusta(nombre_hoja, columnas_esperadas):
    try:
        df = conn.read(worksheet=nombre_hoja, ttl=0).dropna(how="all")
        if df.empty: return pd.DataFrame(columns=columnas_esperadas)
        for col in columnas_esperadas:
            if col not in df.columns: df[col] = None
        return df
    except: return pd.DataFrame(columns=columnas_esperadas)

@st.cache_data(ttl=600, show_spinner=False)
def cargar_pagos():
    df = cargar_hoja_robusta("Pagos", ['calle', 'numero', 'propietario', 'monto_pagado', 'fecha', 'mes', 'registrado_por'])
    if not df.empty: df['numero'] = pd.to_numeric(df['numero'], errors='coerce').fillna(0).astype(int)
    return df

@st.cache_data(ttl=600, show_spinner=False)
def cargar_gastos(): return cargar_hoja_robusta("Gastos", ['descripcion', 'monto', 'fecha', 'mes'])

@st.cache_data(ttl=600, show_spinner=False)
def cargar_extra(): return cargar_hoja_robusta("Ingresos_Extra", ['concepto', 'monto', 'fecha', 'mes'])

@st.cache_data(ttl=600, show_spinner=False)
def cargar_guardias(): return cargar_hoja_robusta("Guardias", ['nombre', 'tipo', 'sueldo'])

@st.cache_data(ttl=600, show_spinner=False)
def cargar_logs(): return cargar_hoja_robusta("Logs", ['fecha_hora', 'usuario', 'accion', 'detalle'])

@st.cache_data(ttl=600, show_spinner=False)
def cargar_ajustes(): return cargar_hoja_robusta("Ajustes_Guardias", ['mes', 'guardia', 'tipo', 'monto', 'detalle'])

@st.cache_data
def cargar_casas():
    with open('casas.json', 'r', encoding='utf-8') as f:
        df = pd.DataFrame(json.load(f))
        df['numero'] = pd.to_numeric(df['numero']).astype(int)
        return df.sort_values(by=['calle', 'numero']).reset_index(drop=True)

df_pagos_full = cargar_pagos()
df_gastos_full = cargar_gastos()
df_extra_full = cargar_extra()
df_guardias = cargar_guardias()
df_logs_full = cargar_logs()
df_ajustes_full = cargar_ajustes()
df_casas = cargar_casas()

def registrar_log(accion, detalle):
    df_l = cargar_logs()
    nuevo_log = pd.DataFrame([{'fecha_hora': datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'usuario': st.session_state.usuario, 'accion': accion, 'detalle': detalle}])
    conn.update(worksheet="Logs", data=pd.concat([df_l, nuevo_log], ignore_index=True))
    cargar_logs.clear() 

# --- MENÚ LATERAL ---
with st.sidebar:
    if os.path.exists("logo_villa.jpg"): st.image("logo_villa.jpg", use_container_width=True)
    st.markdown(f"<h3 style='text-align: center; color: #5a7d65;'>{st.session_state.rol}</h3>", unsafe_allow_html=True)
    st.markdown("---")
    mes_actual = st.selectbox("📅 Período de Trabajo:", MESES_DISPONIBLES)
    st.markdown("---")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.clear(); st.rerun()

def filtrar_por_mes(df, mes):
    if not df.empty and 'mes' in df.columns: return df[df['mes'].astype(str).str.lower() == mes.lower()].reset_index(drop=True)
    return pd.DataFrame(columns=df.columns)

df_pagos_mes = filtrar_por_mes(df_pagos_full, mes_actual)
df_gastos_mes = filtrar_por_mes(df_gastos_full, mes_actual)
df_extra_mes = filtrar_por_mes(df_extra_full, mes_actual)
df_ajustes_mes = filtrar_por_mes(df_ajustes_full, mes_actual)

# ==========================================
# 💰 MATEMÁTICA Y ARRASTRE DE CAJA
# ==========================================
idx_mes = MESES_DISPONIBLES.index(mes_actual)
meses_anteriores = MESES_DISPONIBLES[:idx_mes]

ingresos_ant = pd.to_numeric(df_pagos_full[df_pagos_full['mes'].isin(meses_anteriores)]['monto_pagado'], errors='coerce').fillna(0).sum() + \
               pd.to_numeric(df_extra_full[df_extra_full['mes'].isin(meses_anteriores)]['monto'], errors='coerce').fillna(0).sum() if idx_mes > 0 else 0

egresos_ant = pd.to_numeric(df_gastos_full[df_gastos_full['mes'].isin(meses_anteriores)]['monto'], errors='coerce').fillna(0).sum() if idx_mes > 0 else 0

if idx_mes > 0:
    for m_ant in meses_anteriores:
        sueldos_base = pd.to_numeric(df_guardias['sueldo'], errors='coerce').fillna(0).sum() if not df_guardias.empty else 0
        bonos = pd.to_numeric(df_ajustes_full[(df_ajustes_full['mes'] == m_ant) & (df_ajustes_full['tipo'] == 'Bono Turno Extra')]['monto'], errors='coerce').fillna(0).sum()
        descuentos = pd.to_numeric(df_ajustes_full[(df_ajustes_full['mes'] == m_ant) & (df_ajustes_full['tipo'] == 'Descuento Falta')]['monto'], errors='coerce').fillna(0).sum()
        egresos_ant += (sueldos_base + bonos - descuentos)

caja_chica_anterior = ingresos_ant - egresos_ant

ingresos_vecinos = pd.to_numeric(df_pagos_mes['monto_pagado'], errors='coerce').fillna(0).sum()
ingresos_eventos = pd.to_numeric(df_extra_mes['monto'], errors='coerce').fillna(0).sum()
total_ingresos_mes = ingresos_vecinos + ingresos_eventos

sueldos_base_actual = pd.to_numeric(df_guardias['sueldo'], errors='coerce').fillna(0).sum()
bonos_actual = pd.to_numeric(df_ajustes_mes[df_ajustes_mes['tipo'] == 'Bono Turno Extra']['monto'], errors='coerce').fillna(0).sum()
descuentos_actual = pd.to_numeric(df_ajustes_mes[df_ajustes_mes['tipo'] == 'Descuento Falta']['monto'], errors='coerce').fillna(0).sum()
egresos_guardias = sueldos_base_actual + bonos_actual - descuentos_actual

egresos_otros = pd.to_numeric(df_gastos_mes['monto'], errors='coerce').fillna(0).sum()
total_egresos_mes = egresos_guardias + egresos_otros

balance_final = caja_chica_anterior + total_ingresos_mes - total_egresos_mes
deudores_count = len(df_casas) - len(df_pagos_mes)

# ==========================================
# 📄 GENERADORES DE DOCUMENTOS FORMALES
# ==========================================
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
    pdf.cell(0, 10, txt=f"TOTAL PAGADO: {fmt_dinero(monto)}", border=1, ln=True, align='C')
    return pdf.output(dest='S').encode('latin-1', 'replace')

def generar_pdf_cierre(ing_v, ing_e, egr_g, egr_o, bal, arrastre, df_ex, mes_t):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 8, txt="BALANCE MENSUAL DE TESORERÍA", ln=True, align='L')
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 6, txt="VILLA RAIMAPU - TIERRA FLORIDA - PUENTE ALTO", ln=True, align='L')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, txt=f"Mes: {mes_t.upper()} | Generado el: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
    pdf.ln(8)
    
    pdf.set_fill_color(235, 240, 235)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, txt="1. Resumen de Caja", ln=True, fill=True)
    pdf.set_font("Arial", '', 11)
    if arrastre != 0:
        pdf.cell(120, 8, txt="(+) Saldo a favor mes anterior (Caja Chica)", border=1); pdf.cell(70, 8, txt=fmt_dinero(arrastre), border=1, ln=True, align='R')
    pdf.cell(120, 8, txt="(+) Recaudación Cuotas Vecinos", border=1); pdf.cell(70, 8, txt=fmt_dinero(ing_v), border=1, ln=True, align='R')
    pdf.cell(120, 8, txt="(+) Ingresos Extra (Eventos/Rifas)", border=1); pdf.cell(70, 8, txt=fmt_dinero(ing_e), border=1, ln=True, align='R')
    pdf.cell(120, 8, txt="(-) Liquidaciones Guardias (Base + Ajustes)", border=1); pdf.cell(70, 8, txt=f"- {fmt_dinero(egr_g)}", border=1, ln=True, align='R')
    pdf.cell(120, 8, txt="(-) Gastos Operativos e Insumos", border=1); pdf.cell(70, 8, txt=f"- {fmt_dinero(egr_o)}", border=1, ln=True, align='R')
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(120, 10, txt="SALDO FINAL DISPONIBLE EN CAJA", border=1); pdf.cell(70, 10, txt=fmt_dinero(bal), border=1, ln=True, align='R')
    
    if not df_ex.empty:
        pdf.ln(10); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 8, txt="2. Detalle de Ingresos Extra", ln=True, fill=True)
        pdf.set_font("Arial", 'B', 10); pdf.cell(120, 8, txt="Actividad / Concepto", border=1); pdf.cell(70, 8, txt="Monto Recaudado", border=1, ln=True, align='C')
        pdf.set_font("Arial", '', 10)
        for _, r in df_ex.iterrows():
            m_val = pd.to_numeric(r['monto'], errors='coerce')
            pdf.cell(120, 8, txt=str(r['concepto']), border=1); pdf.cell(70, 8, txt=fmt_dinero(m_val) if not pd.isna(m_val) else "$ 0", border=1, ln=True, align='R')
            
    return pdf.output(dest='S').encode('latin-1', 'replace')

def generar_liquidacion_guardia(nombre, tipo, base, bonos, descuentos, total, mes_texto):
    pdf = FPDF(format='A5')
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, txt="LIQUIDACIÓN DE PAGO - SERVICIO DE SEGURIDAD", ln=True, align='C')
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(0, 5, txt="VILLA RAIMAPU - TIERRA FLORIDA", ln=True, align='C')
    pdf.ln(8)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(40, 6, txt="Nombre Trabajador:", border=0); pdf.set_font("Arial", '', 10); pdf.cell(0, 6, txt=nombre, ln=True)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(40, 6, txt="Período / Mes:", border=0); pdf.set_font("Arial", '', 10); pdf.cell(0, 6, txt=mes_texto.upper(), ln=True)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(40, 6, txt="Tipo de Turno:", border=0); pdf.set_font("Arial", '', 10); pdf.cell(0, 6, txt=tipo, ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(90, 8, txt="Detalle de Remuneración", border=1); pdf.cell(40, 8, txt="Monto", border=1, ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(90, 8, txt="Sueldo Base Acordado", border=1); pdf.cell(40, 8, txt=fmt_dinero(base), border=1, ln=True, align='R')
    if bonos > 0:
        pdf.cell(90, 8, txt="(+) Bonos por Turnos Extra", border=1); pdf.cell(40, 8, txt=fmt_dinero(bonos), border=1, ln=True, align='R')
    if descuentos > 0:
        pdf.cell(90, 8, txt="(-) Descuentos por Inasistencias", border=1); pdf.cell(40, 8, txt=f"- {fmt_dinero(descuentos)}", border=1, ln=True, align='R')
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(90, 10, txt="TOTAL A PAGAR LÍQUIDO", border=1); pdf.cell(40, 10, txt=fmt_dinero(total), border=1, ln=True, align='R')
    
    pdf.ln(15)
    pdf.set_font("Arial", '', 9)
    pdf.cell(0, 5, txt="Recibí conforme el pago total de mis servicios correspondientes al mes indicado.", ln=True, align='C')
    pdf.ln(15)
    pdf.cell(0, 5, txt="_________________________________________", ln=True, align='C')
    pdf.cell(0, 5, txt=f"Firma: {nombre}", ln=True, align='C')
    
    return pdf.output(dest='S').encode('latin-1', 'replace')

def generar_excel_morosos(df_morosos, mes_texto):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as wr:
        df_export = df_morosos[['calle', 'numero', 'propietario']].copy()
        df_export.columns = [f"VECINOS MOROSOS - {mes_texto.upper()}", "N° CASA", "PROPIETARIO"]
        
        df_export.to_excel(wr, index=False, sheet_name='Morosos')
        ws = wr.sheets['Morosos']
        
        azul_claro = PatternFill(start_color="9BC2E6", end_color="9BC2E6", fill_type="solid")
        fuente_titulos = Font(name='Calibri', size=16, bold=True)
        fuente_datos = Font(name='Calibri', size=11)
        centrado = Alignment(horizontal="center", vertical="center")
        borde_fino = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        
        ws.column_dimensions['A'].width = 38
        ws.column_dimensions['B'].width = 15
        ws.column_dimensions['C'].width = 35
        
        for col in range(1, 4):
            cell_header = ws.cell(row=1, column=col)
            cell_header.fill = azul_claro
            cell_header.font = fuente_titulos
            cell_header.alignment = centrado
            cell_header.border = borde_fino
            
            for row in range(2, len(df_export) + 2):
                cell_data = ws.cell(row=row, column=col)
                cell_data.font = fuente_datos
                cell_data.alignment = centrado
                cell_data.border = borde_fino
                
    return buf.getvalue()

# ==========================================
# INTERFAZ: RECAUDADORA EN TERRENO
# ==========================================
if st.session_state.rol == "Recaudadora":
    st.markdown(f"<h2>📱 Portal de Recaudación</h2>", unsafe_allow_html=True)
    st.info("💡 Registre los pagos en terreno. Use la opción 'Meses a pagar' para abonos adelantados.")
    
    with st.container():
        c_sel = st.selectbox("1. Seleccione Pasaje", df_casas['calle'].unique())
        p_ya = df_pagos_mes[df_pagos_mes['calle'] == c_sel]['numero'].tolist()
        pend = df_casas[(df_casas['calle'] == c_sel) & (~df_casas['numero'].isin(p_ya))]
        
        if pend.empty: st.success("🎉 ¡Pasaje al día en este mes!")
        else:
            opc = {f"N° {r['numero']} - {r['propietario']}": r['numero'] for _, r in pend.iterrows()}
            n_sel = opc[st.selectbox("2. Seleccione Casa", opc.keys())]
            
            meses_a_pagar = st.multiselect("3. Meses que está pagando:", MESES_DISPONIBLES, default=[mes_actual])
            st.warning(f"Monto Total a Cobrar: **{fmt_dinero(len(meses_a_pagar) * CUOTA_MENSUAL)}**")
            
            if st.button("💳 Registrar Pagos", type="primary", use_container_width=True):
                nom = df_casas[(df_casas['calle'] == c_sel) & (df_casas['numero'] == n_sel)]['propietario'].values[0]
                nuevos_pagos = []
                for m in meses_a_pagar:
                    nuevos_pagos.append({'calle': c_sel, 'numero': int(n_sel), 'propietario': nom, 'monto_pagado': CUOTA_MENSUAL, 'fecha': datetime.now().strftime("%Y-%m-%d %H:%M"), 'mes': m, 'registrado_por': st.session_state.usuario})
                
                conn.update(worksheet="Pagos", data=pd.concat([df_pagos_full, pd.DataFrame(nuevos_pagos)], ignore_index=True))
                cargar_pagos.clear() 
                registrar_log("Cobro Múltiple", f"Cobró {len(meses_a_pagar)} meses a casa {c_sel} {n_sel}")
                st.toast("✅ Pagos guardados exitosamente."); st.rerun()

# ==========================================
# INTERFAZ: ADMINISTRADORA / TESORERÍA
# ==========================================
elif st.session_state.rol == "Admin":
    st.markdown(f"<h2>🏢 Panel Administrativo</h2>", unsafe_allow_html=True)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Caja Chica Mes Anterior", fmt_dinero(caja_chica_anterior))
    m2.metric("Nuevos Ingresos", fmt_dinero(total_ingresos_mes))
    m3.metric("Fondo Total Disponible", fmt_dinero(balance_final))
    m4.metric("Casas Morosas", f"{deudores_count} pendientes")
    
    t1, t2, t3, t4, t5 = st.tabs(["📝 1. Pagos Recibidos", "🎁 2. Ingresos Extra", "🛒 3. Gastos Operativos", "👮‍♂️ 4. Personal y Turnos", "📑 5. Documentos y Cierre"])

    with t1:
        st.markdown("#### 📋 Historial de Pagos del Mes")
        if not df_pagos_mes.empty:
            df_mostrar = df_pagos_mes[['calle', 'numero', 'propietario', 'fecha', 'registrado_por']].copy()
            st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
            with st.expander("❌ Anular un pago (Registrado en Auditoría)"):
                with st.form("form_anular"):
                    st.warning("Solo anule si se equivocó de casa o monto.")
                    a_sel = st.selectbox("Seleccione el pago a borrar:", [f"{r['calle']} #{r['numero']} - {r['propietario']}" for _, r in df_pagos_mes.iterrows()])
                    if st.form_submit_button("Eliminar Pago", use_container_width=True):
                        c, n = a_sel.split(" #")[0], int(a_sel.split(" #")[1].split(" - ")[0])
                        df_act = df_pagos_full[~((df_pagos_full['calle'] == c) & (df_pagos_full['numero'] == n) & (df_pagos_full['mes'] == mes_actual))].reset_index(drop=True)
                        conn.update(worksheet="Pagos", data=df_act.reindex(range(len(df_pagos_full))))
                        cargar_pagos.clear()
                        registrar_log("Anulación Pago", f"Borró pago de {c} {n} del mes {mes_actual}")
                        st.rerun()
        else:
            st.info("No hay pagos registrados para este mes.")

    with t2:
        st.markdown("#### 🎁 Registrar Ingresos Extra")
        with st.form("form_extra"):
            con, mon = st.text_input("Concepto (Rifas, Donaciones)"), st.number_input("Monto ($)", step=1000)
            if st.form_submit_button("💰 Guardar", use_container_width=True) and con and mon > 0:
                nuevo_e = pd.DataFrame([{'concepto': con, 'monto': int(mon), 'fecha': datetime.now().strftime("%d/%m/%Y"), 'mes': mes_actual}])
                conn.update(worksheet="Ingresos_Extra", data=pd.concat([df_extra_full, nuevo_e], ignore_index=True))
                cargar_extra.clear()
                registrar_log("Ingreso Extra", f"Agregó {fmt_dinero(mon)} por {con}")
                st.rerun()
        if not df_extra_mes.empty: 
            st.dataframe(df_extra_mes[['concepto', 'monto', 'fecha']], use_container_width=True, hide_index=True)
            with st.expander("❌ Eliminar Ingreso Extra"):
                borrar_e = st.selectbox("Seleccione evento a borrar", [f"{r['concepto']} - {fmt_dinero(r['monto'])}" for _, r in df_extra_mes.iterrows()])
                if st.button("Eliminar Permanentemente"):
                    c_del, m_del_str = borrar_e.split(" - $ ")
                    m_del = float(m_del_str.replace(".", ""))
                    df_act = df_extra_full[~((df_extra_full['concepto'] == c_del) & (pd.to_numeric(df_extra_full['monto'], errors='coerce') == m_del) & (df_extra_full['mes'] == mes_actual))].reset_index(drop=True)
                    conn.update(worksheet="Ingresos_Extra", data=df_act.reindex(range(len(df_extra_full))))
                    cargar_extra.clear()
                    registrar_log("Borró Ingreso Extra", f"Eliminó {c_del}")
                    st.rerun()

    with t3:
        st.markdown("#### 🛒 Registrar Gasto Operativo")
        with st.form("form_gastos"):
            des, val = st.text_input("Descripción (Pilas, focos, materiales)"), st.number_input("Costo ($)", step=1000)
            if st.form_submit_button("🚀 Registrar Gasto", use_container_width=True) and des and val > 0:
                nuevo_g = pd.DataFrame([{'descripcion': des, 'monto': int(val), 'fecha': datetime.now().strftime("%d/%m/%Y"), 'mes': mes_actual}])
                conn.update(worksheet="Gastos", data=pd.concat([df_gastos_full, nuevo_g], ignore_index=True))
                cargar_gastos.clear()
                registrar_log("Nuevo Gasto", f"Gastó {fmt_dinero(val)} en {des}")
                st.rerun()
        if not df_gastos_mes.empty: 
            st.dataframe(df_gastos_mes[['descripcion', 'monto', 'fecha']], use_container_width=True, hide_index=True)
            with st.expander("❌ Eliminar Gasto"):
                borrar_g = st.selectbox("Seleccione gasto a borrar", [f"{r['descripcion']} - {fmt_dinero(r['monto'])}" for _, r in df_gastos_mes.iterrows()])
                if st.button("Confirmar Eliminación"):
                    d_del, m_del_str = borrar_g.split(" - $ ")
                    m_del = float(m_del_str.replace(".", ""))
                    df_act = df_gastos_full[~((df_gastos_full['descripcion'] == d_del) & (pd.to_numeric(df_gastos_full['monto'], errors='coerce') == m_del) & (df_gastos_full['mes'] == mes_actual))].reset_index(drop=True)
                    conn.update(worksheet="Gastos", data=df_act.reindex(range(len(df_gastos_full))))
                    cargar_gastos.clear()
                    registrar_log("Borró Gasto", f"Eliminó {d_del}")
                    st.rerun()

    with t4:
        st.markdown("#### 👮‍♂️ Gestión de Guardias y Novedades")
        c_ver, c_mod = st.columns(2)
        with c_ver:
            st.markdown("##### 💵 Nómina Base")
            if not df_guardias.empty:
                df_g_disp = df_guardias.copy()
                st.dataframe(df_g_disp, use_container_width=True, hide_index=True)
            else:
                st.info("Sin personal registrado.")
        with c_mod:
            st.markdown("##### ⚖️ Ajustar Sueldo del Mes")
            if not df_guardias.empty:
                with st.form("form_ajustes"):
                    g_sel = st.selectbox("Seleccione Guardia", df_guardias['nombre'].tolist())
                    tipo_aj = st.radio("Tipo de Novedad", ["Bono Turno Extra", "Descuento Falta"])
                    monto_aj = st.number_input("Monto ($)", min_value=0, step=5000)
                    det_aj = st.text_input("Motivo (Ej: Reemplazo jueves)")
                    if st.form_submit_button("Aplicar Novedad", use_container_width=True) and monto_aj > 0:
                        n_ajuste = pd.DataFrame([{'mes': mes_actual, 'guardia': g_sel, 'tipo': tipo_aj, 'monto': int(monto_aj), 'detalle': det_aj}])
                        conn.update(worksheet="Ajustes_Guardias", data=pd.concat([df_ajustes_full, n_ajuste], ignore_index=True))
                        cargar_ajustes.clear()
                        registrar_log("Ajuste Sueldo", f"Aplicó {tipo_aj} de {fmt_dinero(monto_aj)} a {g_sel}")
                        st.rerun()
                            
        if not df_ajustes_mes.empty:
            st.markdown("##### 📝 Novedades registradas este mes:")
            st.dataframe(df_ajustes_mes[['guardia', 'tipo', 'monto', 'detalle']], use_container_width=True, hide_index=True)

    with t5:
        st.markdown("#### 📑 Oficina Virtual de Tesorería")
        st.write("Genera y descarga todos los documentos formales de la Villa.")
        
        st.markdown("---")
        st.markdown("##### 📊 1. Balance General de Tesorería")
        doc_balance = generar_pdf_cierre(ingresos_vecinos, ingresos_eventos, egresos_guardias, egresos_otros, balance_final, caja_chica_anterior, df_extra_mes, mes_actual)
        st.download_button("📄 Descargar Balance Comunitario (PDF)", doc_balance, file_name=f"Balance_Raimapu_{mes_actual}.pdf", type="primary", use_container_width=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("##### 📝 2. Planilla de Cobranza")
        df_deu = df_casas.merge(df_pagos_mes[['calle', 'numero']], on=['calle', 'numero'], how='left', indicator=True)
        df_deu = df_deu[df_deu['_merge'] == 'left_only'].drop(columns=['_merge'])
        excel_morosos = generar_excel_morosos(df_deu, mes_actual)
        st.download_button("📥 Descargar Lista de Morosos (Excel)", excel_morosos, file_name=f"Morosos_{mes_actual}.xlsx", use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("##### 👮‍♂️ 3. Liquidaciones de Sueldo (Guardias)")
        st.write("Genera el recibo de pago individual con el cálculo exacto de bonos y descuentos para que el trabajador lo firme.")
        
        if not df_guardias.empty:
            c_liq1, c_liq2 = st.columns([2, 1])
            with c_liq1:
                guardia_liq = st.selectbox("Seleccionar trabajador:", df_guardias['nombre'].tolist())
            with c_liq2:
                st.markdown("<br>", unsafe_allow_html=True)
                datos_g = df_guardias[df_guardias['nombre'] == guardia_liq].iloc[0]
                base = int(pd.to_numeric(datos_g['sueldo'], errors='coerce'))
                bonos = int(pd.to_numeric(df_ajustes_mes[(df_ajustes_mes['guardia'] == guardia_liq) & (df_ajustes_mes['tipo'] == 'Bono Turno Extra')]['monto'], errors='coerce').sum())
                descuentos = int(pd.to_numeric(df_ajustes_mes[(df_ajustes_mes['guardia'] == guardia_liq) & (df_ajustes_mes['tipo'] == 'Descuento Falta')]['monto'], errors='coerce').sum())
                total_pagar = base + bonos - descuentos
                
                pdf_liq = generar_liquidacion_guardia(guardia_liq, datos_g['tipo'], base, bonos, descuentos, total_pagar, mes_actual)
                st.download_button("📄 Generar Liquidación", pdf_liq, file_name=f"Liquidacion_{guardia_liq.replace(' ', '_')}_{mes_actual}.pdf", use_container_width=True)
