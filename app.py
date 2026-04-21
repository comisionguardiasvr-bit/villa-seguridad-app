import streamlit as st
import pandas as pd
import json
import io
from datetime import datetime
from openpyxl.styles import Font, Alignment, Border, Side
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection
import os

st.set_page_config(page_title="Tesorería Villa Raimapu", page_icon="🌿", layout="wide")

# ==========================================
# 🎨 DISEÑO Y ESTILOS PASTEL (ADAPTABLE)
# ==========================================
st.markdown("""
<style>
    /* Títulos en tono verde pastel que resaltan en fondo negro o blanco */
    h1, h2, h3, h4, h5 { color: #8fae9a !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    
    /* Tarjetas de Métricas usando colores adaptables */
    div[data-testid="metric-container"] {
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(143, 174, 154, 0.3);
        padding: 15px 20px; border-radius: 12px;
        border-left: 5px solid #8fae9a; transition: transform 0.2s ease-in-out;
    }
    div[data-testid="metric-container"]:hover { transform: translateY(-3px); }
    
    /* Botones */
    .stButton>button {
        border-radius: 20px !important; font-weight: 600 !important;
        background-color: rgba(143, 174, 154, 0.8) !important;
        color: white !important; border: none !important; transition: all 0.3s;
    }
    .stButton>button:hover { background-color: #728f7d !important; transform: scale(1.02); }
    
    /* Pestañas */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; border-radius: 10px 10px 0px 0px; }
    .stTabs [aria-selected="true"] { border-bottom: 4px solid #8fae9a !important; color: #8fae9a !important; }
    
    /* Formularios solucionados: Usan el fondo adaptable de Streamlit */
    div[data-testid="stForm"] { 
        background-color: var(--secondary-background-color); 
        padding: 20px; border-radius: 12px; 
        border: 1px solid rgba(143, 174, 154, 0.4); 
    }
    
    #MainMenu, footer {visibility: hidden;}
    [data-testid="stImage"] img { border-radius: 25px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
</style>
""", unsafe_allow_html=True)

CUOTA_MENSUAL = 10000 
MESES_DISPONIBLES = ["Abril 2026", "Mayo 2026", "Junio 2026", "Julio 2026", "Agosto 2026", "Septiembre 2026", "Octubre 2026", "Noviembre 2026", "Diciembre 2026"]

# ==========================================
# 🔐 SISTEMA DE LOGIN Y ROLES
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
    
    st.markdown("<h2 style='text-align: center;'>Acceso al Sistema Raimapu</h2>", unsafe_allow_html=True)
    
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        with st.form("login_form"):
            tipo_usuario = st.selectbox("Perfil de Usuario:", ["Tesorera / Administradora", "Recaudadora en Terreno"])
            pass_input = st.text_input("🔑 Contraseña:", type="password")
            if st.form_submit_button("Entrar al Sistema", use_container_width=True):
                if tipo_usuario == "Tesorera / Administradora" and pass_input == "villa2026":
                    st.session_state.autenticado = True; st.session_state.rol = "Admin"; st.session_state.usuario = "Tesorera Principal"; st.rerun()
                elif tipo_usuario == "Recaudadora en Terreno" and pass_input == "recauda2026":
                    st.session_state.autenticado = True; st.session_state.rol = "Recaudadora"; st.session_state.usuario = "Recaudadora Móvil"; st.rerun()
                else:
                    st.error("❌ Contraseña incorrecta para el perfil seleccionado.")
    st.stop()

conn = st.connection("gsheets", type=GSheetsConnection)

# ==========================================
# 🧠 MEMORIAS INDEPENDIENTES Y CACHÉ
# ==========================================
@st.cache_data(ttl=600, show_spinner=False)
def cargar_pagos():
    try: return conn.read(worksheet="Pagos", ttl=0).dropna(how="all").assign(numero=lambda x: pd.to_numeric(x['numero']).astype(int))
    except: return pd.DataFrame(columns=['calle', 'numero', 'propietario', 'monto_pagado', 'fecha', 'mes', 'registrado_por'])

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

@st.cache_data(ttl=600, show_spinner=False)
def cargar_logs():
    try: return conn.read(worksheet="Logs", ttl=0).dropna(how="all")
    except: return pd.DataFrame(columns=['fecha_hora', 'usuario', 'accion', 'detalle'])

@st.cache_data(ttl=600, show_spinner=False)
def cargar_ajustes():
    try: return conn.read(worksheet="Ajustes_Guardias", ttl=0).dropna(how="all")
    except: return pd.DataFrame(columns=['mes', 'guardia', 'tipo', 'monto', 'detalle'])

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

# ==========================================
# 🕵️‍♂️ FUNCIÓN DE AUDITORÍA (LOGS SILENCIOSOS)
# ==========================================
def registrar_log(accion, detalle):
    df_l = cargar_logs()
    nuevo_log = pd.DataFrame([{'fecha_hora': datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'usuario': st.session_state.usuario, 'accion': accion, 'detalle': detalle}])
    conn.update(worksheet="Logs", data=pd.concat([df_l, nuevo_log], ignore_index=True))
    cargar_logs.clear() 

# --- BARRA LATERAL ---
with st.sidebar:
    if os.path.exists("logo_villa.jpg"): st.image("logo_villa.jpg", use_container_width=True)
    st.markdown(f"<h3 style='text-align: center;'>Perfil: {st.session_state.rol}</h3>", unsafe_allow_html=True)
    st.markdown("---")
    mes_actual = st.selectbox("📅 Mes Operativo:", MESES_DISPONIBLES)
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
# 💰 MATEMÁTICA Y ARRASTRE DE CAJA CHICA
# ==========================================
idx_mes = MESES_DISPONIBLES.index(mes_actual)
meses_anteriores = MESES_DISPONIBLES[:idx_mes]

ingresos_ant = df_pagos_full[df_pagos_full['mes'].isin(meses_anteriores)]['monto_pagado'].sum() + df_extra_full[df_extra_full['mes'].isin(meses_anteriores)]['monto'].sum() if idx_mes > 0 else 0
egresos_ant = df_gastos_full[df_gastos_full['mes'].isin(meses_anteriores)]['monto'].sum() if idx_mes > 0 else 0
if idx_mes > 0:
    for m_ant in meses_anteriores:
        sueldos_base = df_guardias['sueldo'].sum() if not df_guardias.empty else 0
        bonos = df_ajustes_full[(df_ajustes_full['mes'] == m_ant) & (df_ajustes_full['tipo'] == 'Bono Turno Extra')]['monto'].sum()
        descuentos = df_ajustes_full[(df_ajustes_full['mes'] == m_ant) & (df_ajustes_full['tipo'] == 'Descuento Falta')]['monto'].sum()
        egresos_ant += (sueldos_base + bonos - descuentos)

caja_chica_anterior = ingresos_ant - egresos_ant

ingresos_vecinos = pd.to_numeric(df_pagos_mes['monto_pagado']).sum() if not df_pagos_mes.empty else 0
ingresos_eventos = pd.to_numeric(df_extra_mes['monto']).sum() if not df_extra_mes.empty else 0
total_ingresos_mes = ingresos_vecinos + ingresos_eventos

sueldos_base_actual = pd.to_numeric(df_guardias['sueldo']).sum() if not df_guardias.empty else 0
bonos_actual = df_ajustes_mes[df_ajustes_mes['tipo'] == 'Bono Turno Extra']['monto'].sum() if not df_ajustes_mes.empty else 0
descuentos_actual = df_ajustes_mes[df_ajustes_mes['tipo'] == 'Descuento Falta']['monto'].sum() if not df_ajustes_mes.empty else 0
egresos_guardias = sueldos_base_actual + bonos_actual - descuentos_actual

egresos_otros = pd.to_numeric(df_gastos_mes['monto']).sum() if not df_gastos_mes.empty else 0
total_egresos_mes = egresos_guardias + egresos_otros

balance_final = caja_chica_anterior + total_ingresos_mes - total_egresos_mes
deudores_count = len(df_casas) - len(df_pagos_mes)

# ==========================================
# 📄 GENERADORES DE DOCUMENTOS (FPDF & EXCEL)
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
    pdf.cell(0, 10, txt=f"TOTAL PAGADO: $ {monto:,.0f}", border=1, ln=True, align='C')
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
    
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, txt="1. Resumen de Caja", ln=True, fill=True)
    pdf.set_font("Arial", '', 11)
    if arrastre != 0:
        pdf.cell(110, 8, txt="(+) Saldo a favor mes anterior (Caja Chica)", border=1); pdf.cell(80, 8, txt=f"$ {arrastre:,.0f}", border=1, ln=True, align='R')
    pdf.cell(110, 8, txt="(+) Recaudación Cuotas Vecinos", border=1); pdf.cell(80, 8, txt=f"$ {ing_v:,.0f}", border=1, ln=True, align='R')
    pdf.cell(110, 8, txt="(+) Ingresos Extra (Eventos/Rifas)", border=1); pdf.cell(80, 8, txt=f"$ {ing_e:,.0f}", border=1, ln=True, align='R')
    pdf.cell(110, 8, txt="(-) Liquidaciones Guardias (Base + Ajustes)", border=1); pdf.cell(80, 8, txt=f"- $ {egr_g:,.0f}", border=1, ln=True, align='R')
    pdf.cell(110, 8, txt="(-) Gastos Operativos e Insumos", border=1); pdf.cell(80, 8, txt=f"- $ {egr_o:,.0f}", border=1, ln=True, align='R')
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(110, 10, txt="SALDO FINAL DISPONIBLE EN CAJA", border=1); pdf.cell(80, 10, txt=f"$ {bal:,.0f}", border=1, ln=True, align='R')
    
    if not df_ex.empty:
        pdf.ln(10); pdf.set_font("Arial", 'B', 12); pdf.cell(0, 8, txt="2. Detalle de Ingresos Extra", ln=True, fill=True)
        pdf.set_font("Arial", 'B', 10); pdf.cell(130, 8, txt="Actividad / Concepto", border=1); pdf.cell(60, 8, txt="Monto Recaudado", border=1, ln=True, align='C')
        pdf.set_font("Arial", '', 10)
        for _, r in df_ex.iterrows():
            pdf.cell(130, 8, txt=str(r['concepto']), border=1); pdf.cell(60, 8, txt=f"$ {int(r['monto']):,.0f}", border=1, ln=True, align='R')
            
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
    pdf.cell(90, 8, txt="Sueldo Base Acordado", border=1); pdf.cell(40, 8, txt=f"$ {base:,.0f}", border=1, ln=True, align='R')
    if bonos > 0:
        pdf.cell(90, 8, txt="(+) Bonos por Turnos Extra", border=1); pdf.cell(40, 8, txt=f"$ {bonos:,.0f}", border=1, ln=True, align='R')
    if descuentos > 0:
        pdf.cell(90, 8, txt="(-) Descuentos por Inasistencias", border=1); pdf.cell(40, 8, txt=f"- $ {descuentos:,.0f}", border=1, ln=True, align='R')
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(90, 10, txt="TOTAL A PAGAR LÍQUIDO", border=1); pdf.cell(40, 10, txt=f"$ {total:,.0f}", border=1, ln=True, align='R')
    
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
        df_morosos.rename(columns={'calle': 'PASAJE', 'numero': 'N° CASA', 'propietario': 'PROPIETARIO'}).to_excel(wr, index=False, sheet_name='Morosos')
        ws = wr.sheets['Morosos']
        ws['A1'] = f"VECINOS MOROSOS - {mes_texto.upper()}"
        ws['A1'].font = Font(bold=True)
        for col in ['A', 'B', 'C']: ws.column_dimensions[col].width = 20
    return buf.getvalue()

# ==========================================
# INTERFAZ DEPENDIENDO DEL ROL
# ==========================================
if st.session_state.rol == "Recaudadora":
    st.markdown(f"<h2>📱 Portal de Recaudación</h2>", unsafe_allow_html=True)
    st.info("💡 Desde aquí puedes registrar los pagos en terreno. Usa la opción 'Meses a pagar' si un vecino paga por adelantado.")
    
    with st.container():
        c_sel = st.selectbox("1. Seleccione Pasaje", df_casas['calle'].unique())
        p_ya = df_pagos_mes[df_pagos_mes['calle'] == c_sel]['numero'].tolist()
        pend = df_casas[(df_casas['calle'] == c_sel) & (~df_casas['numero'].isin(p_ya))]
        
        if pend.empty: st.success("🎉 ¡Pasaje al día en este mes!")
        else:
            opc = {f"N° {r['numero']} - {r['propietario']}": r['numero'] for _, r in pend.iterrows()}
            n_sel = opc[st.selectbox("2. Seleccione Casa", opc.keys())]
            
            meses_a_pagar = st.multiselect("3. Meses que está pagando:", MESES_DISPONIBLES, default=[mes_actual])
            st.warning(f"Monto Total a Cobrar: **${len(meses_a_pagar) * CUOTA_MENSUAL:,.0f}**")
            
            if st.button("💳 Registrar Pagos", type="primary", use_container_width=True):
                nom = df_casas[(df_casas['calle'] == c_sel) & (df_casas['numero'] == n_sel)]['propietario'].values[0]
                nuevos_pagos = []
                for m in meses_a_pagar:
                    nuevos_pagos.append({'calle': c_sel, 'numero': int(n_sel), 'propietario': nom, 'monto_pagado': CUOTA_MENSUAL, 'fecha': datetime.now().strftime("%Y-%m-%d %H:%M"), 'mes': m, 'registrado_por': st.session_state.usuario})
                
                conn.update(worksheet="Pagos", data=pd.concat([df_pagos_full, pd.DataFrame(nuevos_pagos)], ignore_index=True))
                cargar_pagos.clear()
                registrar_log("Cobro Múltiple", f"Cobró {len(meses_a_pagar)} meses a casa {c_sel} {n_sel}")
                st.toast("✅ Pagos guardados en la base central."); st.rerun()

elif st.session_state.rol == "Admin":
    st.markdown(f"<h2>🏢 Panel Administrativo</h2>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Caja Chica Mes Anterior", f"${caja_chica_anterior:,.0f}")
    m2.metric("Nuevos Ingresos", f"${total_ingresos_mes:,.0f}")
    m3.metric("Fondo Total Disponible", f"${balance_final:,.0f}")
    m4.metric("Casas Morosas", f"{deudores_count} pendientes")
    
    t1, t2, t3, t4, t5 = st.tabs(["📝 1. Pagos Recaudación", "🎁 2. Ingresos Extra", "🛒 3. Gastos Operativos", "👮‍♂️ 4. Personal y Turnos", "📑 5. Documentos y Cierre"])

    with t1:
        st.markdown("#### 📋 Historial de Pagos del Mes")
        if not df_pagos_mes.empty:
            st.dataframe(df_pagos_mes[['calle', 'numero', 'propietario', 'fecha', 'registrado_por']], use_container_width=True, hide_index=True)
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

    with t2:
        st.markdown("#### 🎁 Registrar Ingresos Extra")
        with st.form("form_extra"):
            con, mon = st.text_input("Concepto (Rifas, Donaciones)"), st.number_input("Monto ($)", step=1000)
            if st.form_submit_button("💰 Guardar", use_container_width=True) and con and mon > 0:
                nuevo_e = pd.DataFrame([{'concepto': con, 'monto': int(mon), 'fecha': datetime.now().strftime("%d/%m/%Y"), 'mes': mes_actual}])
                conn.update(worksheet="Ingresos_Extra", data=pd.concat([df_extra_full, nuevo_e], ignore_index=True))
                cargar_extra.clear()
                registrar_log("Ingreso Extra", f"Agregó {mon} por {con}")
                st.rerun()
        if not df_extra_mes.empty: 
            st.dataframe(df_extra_mes[['concepto', 'monto']], use_container_width=True, hide_index=True)
            with st.expander("❌ Eliminar Ingreso Extra"):
                borrar_e = st.selectbox("Seleccione evento a borrar", [f"{r['concepto']} - ${r['monto']}" for _, r in df_extra_mes.iterrows()])
                if st.button("Eliminar Permanentemente"):
                    c_del, m_del = borrar_e.split(" - $")
                    df_act = df_extra_full[~((df_extra_full['concepto'] == c_del) & (df_extra_full['monto'] == float(m_del)) & (df_extra_full['mes'] == mes_actual))].reset_index(drop=True)
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
                registrar_log("Nuevo Gasto", f"Gastó {val} en {des}")
                st.rerun()
        if not df_gastos_mes.empty: 
            st.dataframe(df_gastos_mes[['descripcion', 'monto']], use_container_width=True, hide_index=True)
            with st.expander("❌ Eliminar Gasto"):
                borrar_g = st.selectbox("Seleccione gasto a borrar", [f"{r['descripcion']} - ${r['monto']}" for _, r in df_gastos_mes.iterrows()])
                if st.button("Confirmar Eliminación"):
                    d_del, m_del = borrar_g.split(" - $")
                    df_act = df_gastos_full[~((df_gastos_full['descripcion'] == d_del) & (df_gastos_full['monto'] == float(m_del)) & (df_gastos_full['mes'] == mes_actual))].reset_index(drop=True)
                    conn.update(worksheet="Gastos", data=df_act.reindex(range(len(df_gastos_full))))
                    cargar_gastos.clear()
                    registrar_log("Borró Gasto", f"Eliminó {d_del}")
                    st.rerun()

    with t4:
        st.markdown("#### 👮‍♂️ Gestión de Guardias y Novedades")
        c_ver, c_mod = st.columns(2)
        with c_ver:
            st.markdown("##### 💵 Nómina Base")
            st.dataframe(df_guardias, use_container_width=True, hide_index=True)
        with c_mod:
            st.markdown("##### ⚖️ Ajustar Sueldo del Mes (Turnos Extra o Faltas)")
            if not df_guardias.empty:
                with st.form("form_ajustes"):
                    g_sel = st.selectbox("Seleccione Guardia", df_guardias['nombre'].tolist())
                    tipo_aj = st.radio("Tipo de Novedad", ["Bono Turno Extra", "Descuento Falta"])
                    monto_aj = st.number_input("Monto ($)", min_value=0, step=5000)
                    det_aj = st.text_input("Motivo (Ej: Reemplazo Juan jueves)")
                    if st.form_submit_button("Aplicar Novedad", use_container_width=True) and monto_aj > 0:
                        n_ajuste = pd.DataFrame([{'mes': mes_actual, 'guardia': g_sel, 'tipo': tipo_aj, 'monto': int(monto_aj), 'detalle': det_aj}])
                        conn.update(worksheet="Ajustes_Guardias", data=pd.concat([df_ajustes_full, n_ajuste], ignore_index=True))
                        cargar_ajustes.clear()
                        registrar_log("Ajuste Sueldo", f"Aplicó {tipo_aj} de ${monto_aj} a {g_sel}")
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
                base = int(datos_g['sueldo'])
                bonos = int(df_ajustes_mes[(df_ajustes_mes['guardia'] == guardia_liq) & (df_ajustes_mes['tipo'] == 'Bono Turno Extra')]['monto'].sum())
                descuentos = int(df_ajustes_mes[(df_ajustes_mes['guardia'] == guardia_liq) & (df_ajustes_mes['tipo'] == 'Descuento Falta')]['monto'].sum())
                total_pagar = base + bonos - descuentos
                
                pdf_liq = generar_liquidacion_guardia(guardia_liq, datos_g['tipo'], base, bonos, descuentos, total_pagar, mes_actual)
                st.download_button("📄 Generar Liquidación", pdf_liq, file_name=f"Liquidacion_{guardia_liq.replace(' ', '_')}_{mes_actual}.pdf", use_container_width=True)
