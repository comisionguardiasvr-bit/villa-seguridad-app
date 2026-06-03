import streamlit as st
import pandas as pd
import json
import io
from datetime import datetime
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection
import os

st.set_page_config(page_title="Plataforma Raimapu", page_icon="🌿", layout="wide")

# ==========================================
# 🎨 DISEÑO PROFESIONAL FINTECH
# ==========================================
st.markdown("""
<style>
    h1, h2, h3, h4, h5 { font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #5a7d65 !important; }
    div[data-testid="metric-container"] {
        background-color: var(--secondary-background-color); 
        border: 1px solid rgba(90, 125, 101, 0.15); padding: 18px 20px; border-radius: 16px; 
        border-left: 6px solid #6c8d76; transition: all 0.3s ease; box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    }
    div[data-testid="metric-container"]:hover { transform: translateY(-4px); box-shadow: 0 8px 15px rgba(0,0,0,0.08); }
    .stButton>button {
        border-radius: 10px !important; font-weight: 600 !important; letter-spacing: 0.5px;
        background-color: #6c8d76 !important; color: white !important; border: none !important; transition: all 0.3s;
    }
    .stButton>button:hover { background-color: #4a6652 !important; transform: scale(1.02); }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; border-bottom: 2px solid rgba(90, 125, 101, 0.1); }
    .stTabs [data-baseweb="tab"] { border-radius: 8px 8px 0px 0px; padding: 12px 16px; }
    .stTabs [aria-selected="true"] { border-bottom: 3px solid #5a7d65 !important; color: #5a7d65 !important; font-weight: 600;}
    div[data-testid="stForm"], .stAlert { border-radius: 16px !important; border: 1px solid rgba(90, 125, 101, 0.2) !important; }
    #MainMenu, footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

MESES_DISPONIBLES = ["Abril 2026", "Mayo 2026", "Junio 2026", "Julio 2026", "Agosto 2026", "Septiembre 2026", "Octubre 2026", "Noviembre 2026", "Diciembre 2026"]
OPCIONES_CUOTA = [15000, 10000, 5000]

def fmt_dinero(monto): return f"$ {int(monto):,.0f}".replace(",", ".")

# ==========================================
# 🧠 CARGA INICIAL DE CASAS (RUTEO DINÁMICO)
# ==========================================
@st.cache_data
def cargar_casas():
    with open('casas.json', 'r', encoding='utf-8') as f:
        df = pd.DataFrame(json.load(f))
        df['numero'] = pd.to_numeric(df['numero']).astype(int)
        return df.sort_values(by=['calle', 'numero']).reset_index(drop=True)

df_casas = cargar_casas()
calles_disponibles = df_casas['calle'].unique().tolist()

# ==========================================
# 🔐 SISTEMA DE AUTENTICACIÓN MULTI-ROL
# ==========================================
if 'autenticado' not in st.session_state:
    st.session_state.update({'autenticado': False, 'rol': "", 'usuario': "", 'calle_vecino': ""})

if not st.session_state.autenticado:
    st.markdown("<br>", unsafe_allow_html=True)
    _, col_logo, _ = st.columns([2.5, 1.5, 2.5])
    with col_logo:
        if os.path.exists("logo_villa.jpg"): st.image("logo_villa.jpg", use_container_width=True)
        else: st.markdown("<h1 style='text-align: center; font-size: 4em;'>🌿</h1>", unsafe_allow_html=True)
    
    st.markdown("<h2 style='text-align: center;'>Portal Comunitario Raimapu</h2>", unsafe_allow_html=True)
    
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        with st.form("login_form"):
            perfiles_vecinos = [f"Vecinos - {c}" for c in calles_disponibles]
            opciones_login = ["Tesorera / Administradora", "Recaudadora (Dashboard)"] + perfiles_vecinos
            tipo_usuario = st.selectbox("Seleccione su perfil de acceso:", opciones_login)
            pass_input = st.text_input("🔑 Contraseña:", type="password")
            
            if st.form_submit_button("Ingresar", use_container_width=True):
                if tipo_usuario == "Tesorera / Administradora" and pass_input == "villa2026":
                    st.session_state.update({'autenticado': True, 'rol': "Tesorera", 'usuario': "Tesorera General"})
                    st.rerun()
                elif tipo_usuario == "Recaudadora (Dashboard)" and pass_input == "recauda2026":
                    st.session_state.update({'autenticado': True, 'rol': "Recaudadora", 'usuario': "Recaudadora"})
                    st.rerun()
                elif tipo_usuario.startswith("Vecinos - ") and pass_input == "vecino2026":
                    st.session_state.update({'autenticado': True, 'rol': "Vecino", 'usuario': tipo_usuario, 'calle_vecino': tipo_usuario.replace("Vecinos - ", "")})
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas.")
    st.stop()

# ==========================================
# 🛠️ CONEXIÓN Y DATOS BLINDADOS
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_hoja_robusta(nombre_hoja, columnas_esperadas):
    try:
        df = conn.read(worksheet=nombre_hoja, ttl=0).dropna(how="all")
        if df.empty: return pd.DataFrame(columns=columnas_esperadas)
        for col in columnas_esperadas:
            if col not in df.columns: df[col] = None
        return df
    except Exception: return pd.DataFrame(columns=columnas_esperadas)

def ejecutar_transaccion(worksheet_name, df_act, cache_func, msg_exito="Operación exitosa"):
    try:
        conn.update(worksheet=worksheet_name, data=df_act)
        cache_func.clear()
        st.toast(f"✅ {msg_exito}")
        return True
    except Exception as e:
        st.error("⚠️ Error de conexión con el servidor. Intente en unos segundos.")
        return False

@st.cache_data(ttl=600, show_spinner=False)
def cargar_pagos():
    df = cargar_hoja_robusta("Pagos", ['calle', 'numero', 'propietario', 'monto_pagado', 'fecha', 'mes', 'registrado_por', 'metodo_pago'])
    if not df.empty: df['numero'] = pd.to_numeric(df['numero'], errors='coerce').fillna(0).astype(int)
    return df

@st.cache_data(ttl=600, show_spinner=False)
def cargar_gastos(): return cargar_hoja_robusta("Gastos", ['descripcion', 'monto', 'fecha', 'mes'])
@st.cache_data(ttl=600, show_spinner=False)
def cargar_extra(): return cargar_hoja_robusta("Ingresos_Extra", ['concepto', 'monto', 'fecha', 'mes'])
@st.cache_data(ttl=600, show_spinner=False)
def cargar_porteros(): return cargar_hoja_robusta("Porteros", ['nombre', 'tipo', 'sueldo'])
@st.cache_data(ttl=600, show_spinner=False)
def cargar_logs(): return cargar_hoja_robusta("Logs", ['fecha_hora', 'usuario', 'accion', 'detalle'])
@st.cache_data(ttl=600, show_spinner=False)
def cargar_ajustes(): return cargar_hoja_robusta("Ajustes_Porteros", ['mes', 'portero', 'tipo', 'monto', 'detalle'])

df_pagos_full = cargar_pagos()
df_gastos_full = cargar_gastos()
df_extra_full = cargar_extra()
df_porteros = cargar_porteros()
df_logs_full = cargar_logs()
df_ajustes_full = cargar_ajustes()

def registrar_log(accion, detalle):
    df_l = cargar_logs()
    nuevo_log = pd.DataFrame([{'fecha_hora': datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'usuario': st.session_state.usuario, 'accion': accion, 'detalle': detalle}])
    try:
        conn.update(worksheet="Logs", data=pd.concat([df_l, nuevo_log], ignore_index=True))
        cargar_logs.clear()
    except: pass

# --- MENÚ LATERAL ---
with st.sidebar:
    if os.path.exists("logo_villa.jpg"): st.image("logo_villa.jpg", width=150)
    st.markdown(f"<h3 style='text-align: center;'>👤 {st.session_state.usuario}</h3>", unsafe_allow_html=True)
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
# 💰 MATEMÁTICA Y ARRASTRE
# ==========================================
idx_mes = MESES_DISPONIBLES.index(mes_actual)
meses_anteriores = MESES_DISPONIBLES[:idx_mes]

ingresos_ant = pd.to_numeric(df_pagos_full[df_pagos_full['mes'].isin(meses_anteriores)]['monto_pagado'], errors='coerce').fillna(0).sum() + pd.to_numeric(df_extra_full[df_extra_full['mes'].isin(meses_anteriores)]['monto'], errors='coerce').fillna(0).sum() if idx_mes > 0 else 0
egresos_ant = pd.to_numeric(df_gastos_full[df_gastos_full['mes'].isin(meses_anteriores)]['monto'], errors='coerce').fillna(0).sum() if idx_mes > 0 else 0

if idx_mes > 0:
    for m_ant in meses_anteriores:
        sueldos_base = pd.to_numeric(df_porteros['sueldo'], errors='coerce').fillna(0).sum() if not df_porteros.empty else 0
        bonos = pd.to_numeric(df_ajustes_full[(df_ajustes_full['mes'] == m_ant) & (df_ajustes_full['tipo'] == 'Bono Turno Extra')]['monto'], errors='coerce').fillna(0).sum()
        descuentos = pd.to_numeric(df_ajustes_full[(df_ajustes_full['mes'] == m_ant) & (df_ajustes_full['tipo'] == 'Descuento Falta')]['monto'], errors='coerce').fillna(0).sum()
        egresos_ant += (sueldos_base + bonos - descuentos)

caja_chica_anterior = ingresos_ant - egresos_ant
ingresos_vecinos = pd.to_numeric(df_pagos_mes['monto_pagado'], errors='coerce').fillna(0).sum()
ingresos_eventos = pd.to_numeric(df_extra_mes['monto'], errors='coerce').fillna(0).sum()
total_ingresos_mes = ingresos_vecinos + ingresos_eventos

sueldos_base_actual = pd.to_numeric(df_porteros['sueldo'], errors='coerce').fillna(0).sum()
bonos_actual = pd.to_numeric(df_ajustes_mes[df_ajustes_mes['tipo'] == 'Bono Turno Extra']['monto'], errors='coerce').fillna(0).sum()
descuentos_actual = pd.to_numeric(df_ajustes_mes[df_ajustes_mes['tipo'] == 'Descuento Falta']['monto'], errors='coerce').fillna(0).sum()
egresos_porteros = sueldos_base_actual + bonos_actual - descuentos_actual

egresos_otros = pd.to_numeric(df_gastos_mes['monto'], errors='coerce').fillna(0).sum()
total_egresos_mes = egresos_porteros + egresos_otros

balance_final = caja_chica_anterior + total_ingresos_mes - total_egresos_mes
deudores_count = len(df_casas) - len(df_pagos_mes)

# ==========================================
# 📄 GENERADORES DE DOCUMENTOS FORMALES
# ==========================================
def generar_pdf_cierre(ing_v, ing_e, egr_p, egr_o, bal, arrastre, df_ex, mes_t):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 8, txt="BALANCE MENSUAL DE TESORERIA", ln=True, align='L')
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
    pdf.cell(120, 8, txt="(+) Recaudacion Cuotas Vecinos", border=1); pdf.cell(70, 8, txt=fmt_dinero(ing_v), border=1, ln=True, align='R')
    pdf.cell(120, 8, txt="(+) Ingresos Extra (Eventos/Rifas)", border=1); pdf.cell(70, 8, txt=fmt_dinero(ing_e), border=1, ln=True, align='R')
    pdf.cell(120, 8, txt="(-) Liquidaciones Porteros (Base + Ajustes)", border=1); pdf.cell(70, 8, txt=f"- {fmt_dinero(egr_p)}", border=1, ln=True, align='R')
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

def generar_excel_morosos(df_morosos, mes_texto, titulo_calle="VECINOS MOROSOS"):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as wr:
        df_export = df_morosos[['calle', 'numero', 'propietario']].copy()
        df_export.columns = [f"{titulo_calle} - {mes_texto.upper()}", "N° CASA", "PROPIETARIO"]
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
            cell_header.fill = azul_claro; cell_header.font = fuente_titulos; cell_header.alignment = centrado; cell_header.border = borde_fino
            for row in range(2, len(df_export) + 2):
                cell_data = ws.cell(row=row, column=col)
                cell_data.font = fuente_datos; cell_data.alignment = centrado; cell_data.border = borde_fino
    return buf.getvalue()

# ==========================================
# 🧑‍💻 INTERFAZ: TESORERA (ALL PRIVILEGES)
# ==========================================
if st.session_state.rol == "Tesorera":
    st.markdown(f"<h2>🏢 Panel Maestro de Tesorería</h2>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Caja Chica Anterior", fmt_dinero(caja_chica_anterior))
    m2.metric(f"Nuevos Ingresos ({mes_actual})", fmt_dinero(total_ingresos_mes))
    m3.metric("Fondo Total Disponible", fmt_dinero(balance_final))
    m4.metric("Casas Morosas Total", f"{deudores_count} pendientes")
    
    t1, t2, t3, t4, t5 = st.tabs(["📝 1. Gestión de Pagos", "🎁 2. Ingresos Extra", "🛒 3. Gastos", "👮‍♂️ 4. Porteros", "📑 5. Auditoría"])

    with t1:
        c_cobro, c_visor = st.columns([1, 1.5])
        with c_cobro:
            st.markdown("#### 💵 Registrar Nuevo Pago")
            with st.container():
                c_sel = st.selectbox("1. Calle / Pasaje", calles_disponibles)
                p_ya = df_pagos_mes[df_pagos_mes['calle'] == c_sel]['numero'].tolist()
                pend = df_casas[(df_casas['calle'] == c_sel) & (~df_casas['numero'].isin(p_ya))]
                
                if pend.empty: st.success("🎉 Pasaje al día este mes.")
                else:
                    opc = {f"N° {r['numero']} - {r['propietario']}": r['numero'] for _, r in pend.iterrows()}
                    n_sel = opc[st.selectbox("2. Vecino", opc.keys())]
                    m_pagar = st.selectbox("3. Monto a Pagar ($):", OPCIONES_CUOTA, index=0)
                    meses_a_pagar = st.multiselect("4. Meses a cubrir:", MESES_DISPONIBLES, default=[mes_actual])
                    metodo_pago = st.selectbox("5. Método:", ["Efectivo", "Transferencia Bancaria", "Otro"])
                    
                    if st.button("💳 Registrar Pago", type="primary", use_container_width=True):
                        nom = df_casas[(df_casas['calle'] == c_sel) & (df_casas['numero'] == n_sel)]['propietario'].values[0]
                        nuevos_pagos = []
                        for m in meses_a_pagar:
                            nuevos_pagos.append({'calle': c_sel, 'numero': int(n_sel), 'propietario': nom, 'monto_pagado': m_pagar, 'fecha': datetime.now().strftime("%Y-%m-%d %H:%M"), 'mes': m, 'registrado_por': "Tesorera", 'metodo_pago': metodo_pago})
                        df_act = pd.concat([df_pagos_full, pd.DataFrame(nuevos_pagos)], ignore_index=True)
                        if ejecutar_transaccion("Pagos", df_act, cargar_pagos):
                            registrar_log("Cobro", f"Tesorera cobró {fmt_dinero(m_pagar)} a {c_sel} #{n_sel}")
                            st.rerun()
                            
        with c_visor:
            st.markdown("#### 📋 Visor y Edición de Pagos")
            if not df_pagos_mes.empty:
                df_mostrar = df_pagos_mes.copy()
                df_mostrar['monto_pagado'] = df_mostrar['monto_pagado'].apply(fmt_dinero)
                st.dataframe(df_mostrar[['calle', 'numero', 'propietario', 'monto_pagado', 'metodo_pago', 'fecha']], use_container_width=True, hide_index=True)
                
                with st.expander("✏️ Editar o Anular Pago"):
                    opciones_edit = {f"ID {idx} | {r['calle']} #{r['numero']} | {fmt_dinero(r['monto_pagado'])}": idx for idx, r in df_pagos_mes.iterrows()}
                    sel_str = st.selectbox("Seleccione registro:", list(opciones_edit.keys()))
                    idx_obj = opciones_edit[sel_str]
                    
                    c_ed1, c_ed2 = st.columns(2)
                    with c_ed1:
                        nuevo_monto = st.selectbox("Actualizar a monto:", OPCIONES_CUOTA, index=0)
                        if st.button("💾 Actualizar Monto", use_container_width=True):
                            df_act = df_pagos_full.copy()
                            # Obtenemos el indice real en el dataframe full
                            idx_real = df_pagos_full[(df_pagos_full['calle'] == df_pagos_mes.loc[idx_obj, 'calle']) & (df_pagos_full['numero'] == df_pagos_mes.loc[idx_obj, 'numero']) & (df_pagos_full['mes'] == mes_actual)].index[0]
                            df_act.at[idx_real, 'monto_pagado'] = nuevo_monto
                            if ejecutar_transaccion("Pagos", df_act, cargar_pagos, "Monto editado exitosamente"):
                                registrar_log("Edición Pago", f"Actualizó pago ID:{idx_real} a {nuevo_monto}")
                                st.rerun()
                    with c_ed2:
                        st.write("")
                        st.write("")
                        if st.button("❌ Anular Pago (Borrar)", use_container_width=True):
                            idx_real = df_pagos_full[(df_pagos_full['calle'] == df_pagos_mes.loc[idx_obj, 'calle']) & (df_pagos_full['numero'] == df_pagos_mes.loc[idx_obj, 'numero']) & (df_pagos_full['mes'] == mes_actual)].index[0]
                            df_act = df_pagos_full.drop(idx_real).reset_index(drop=True)
                            if ejecutar_transaccion("Pagos", df_act, cargar_pagos, "Pago eliminado."):
                                registrar_log("Anulación Pago", f"Borró pago ID:{idx_real}")
                                st.rerun()
            else:
                st.info("Sin pagos este mes.")

    # ------------------ RESTO PESTAÑAS ADMIN ------------------
    with t2:
        st.markdown("#### 🎁 Registrar Ingresos Extra")
        with st.form("form_extra"):
            con, mon = st.text_input("Concepto"), st.number_input("Monto ($)", step=1000)
            if st.form_submit_button("💰 Guardar Dinero") and con and mon > 0:
                df_act = pd.concat([df_extra_full, pd.DataFrame([{'concepto': con, 'monto': int(mon), 'fecha': datetime.now().strftime("%d/%m/%Y"), 'mes': mes_actual}])], ignore_index=True)
                if ejecutar_transaccion("Ingresos_Extra", df_act, cargar_extra): st.rerun()

    with t3:
        st.markdown("#### 🛒 Registrar Gasto Operativo")
        with st.form("form_gastos"):
            des, val = st.text_input("Descripción"), st.number_input("Costo ($)", step=1000)
            if st.form_submit_button("🚀 Registrar Gasto") and des and val > 0:
                df_act = pd.concat([df_gastos_full, pd.DataFrame([{'descripcion': des, 'monto': int(val), 'fecha': datetime.now().strftime("%d/%m/%Y"), 'mes': mes_actual}])], ignore_index=True)
                if ejecutar_transaccion("Gastos", df_act, cargar_gastos): st.rerun()

    with t4:
        st.markdown("#### 👮‍♂️ Gestión de Porteros")
        c_ver, c_mod = st.columns(2)
        with c_ver:
            st.markdown("##### 💵 Nómina Base")
            if not df_porteros.empty:
                df_p_disp = df_porteros.copy()
                df_p_disp['sueldo'] = df_p_disp['sueldo'].apply(fmt_dinero)
                st.dataframe(df_p_disp, use_container_width=True, hide_index=True)
                with st.expander("➕ / ➖ Personal"):
                    n_gu, t_gu, s_gu = st.text_input("Nombre"), st.selectbox("Turno", ["Full Time", "Part Time", "Reemplazo"]), st.number_input("Sueldo", value=400000)
                    if st.button("Contratar"):
                        df_act = pd.concat([df_porteros, pd.DataFrame([{'nombre': n_gu, 'tipo': t_gu, 'sueldo': int(s_gu)}])], ignore_index=True)
                        ejecutar_transaccion("Porteros", df_act, cargar_porteros); st.rerun()
                    g_borrar = st.selectbox("Seleccione a despedir", df_porteros['nombre'].tolist())
                    if st.button("Desvincular"):
                        df_act = df_porteros[df_porteros['nombre'] != g_borrar].reset_index(drop=True)
                        ejecutar_transaccion("Porteros", df_act, cargar_porteros); st.rerun()
        with c_mod:
            st.markdown("##### ⚖️ Novedades del Mes")
            if not df_porteros.empty:
                with st.form("form_ajustes"):
                    g_sel, tipo_aj, monto_aj, det_aj = st.selectbox("Portero", df_porteros['nombre'].tolist()), st.radio("Tipo", ["Bono Turno Extra", "Descuento Falta"]), st.number_input("Monto ($)", min_value=0, step=5000), st.text_input("Motivo")
                    if st.form_submit_button("Aplicar Novedad") and monto_aj > 0:
                        df_act = pd.concat([df_ajustes_full, pd.DataFrame([{'mes': mes_actual, 'portero': g_sel, 'tipo': tipo_aj, 'monto': int(monto_aj), 'detalle': det_aj}])], ignore_index=True)
                        ejecutar_transaccion("Ajustes_Porteros", df_act, cargar_ajustes); st.rerun()

    with t5:
        st.markdown("#### 📑 Auditoría y Cierre")
        st.download_button("📄 Descargar Balance Comunitario", generar_pdf_cierre(ingresos_vecinos, ingresos_eventos, egresos_porteros, egresos_otros, balance_final, caja_chica_anterior, df_extra_mes, mes_actual), file_name=f"Balance_{mes_actual}.pdf")
        df_deu = df_casas.merge(df_pagos_mes[['calle', 'numero']], on=['calle', 'numero'], how='left', indicator=True)
        st.download_button("📥 Excel de Morosos (Completo)", generar_excel_morosos(df_deu[df_deu['_merge'] == 'left_only'].drop(columns=['_merge']), mes_actual), file_name=f"Morosos_Completos_{mes_actual}.xlsx")
        st.dataframe(df_logs_full.tail(15).sort_index(ascending=False), use_container_width=True, hide_index=True)

# ==========================================
# 📊 INTERFAZ: RECAUDADORA (DASHBOARD ONLY)
# ==========================================
elif st.session_state.rol == "Recaudadora":
    st.markdown("<h2>📊 Dashboard Financiero Raimapu</h2>", unsafe_allow_html=True)
    st.info("Vista gerencial de recaudación. Acceso de solo lectura para auditoría y visualización de progreso.")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Recaudación Vecinos", fmt_dinero(ingresos_vecinos))
    m2.metric("Casas al Día", f"{len(df_pagos_mes)} de {len(df_casas)}")
    m3.metric("Meta Alcanzada", f"{int((len(df_pagos_mes)/len(df_casas))*100)} %" if len(df_casas)>0 else "0%")
    
    st.markdown("<br>#### 📈 Tendencia de Recaudación Anual", unsafe_allow_html=True)
    if not df_pagos_full.empty:
        # Agrupamos por mes para el gráfico
        chart_data = df_pagos_full.groupby('mes')['monto_pagado'].sum().reset_index()
        # Ordenamos los meses según el array original
        chart_data['mes'] = pd.Categorical(chart_data['mes'], categories=MESES_DISPONIBLES, ordered=True)
        chart_data = chart_data.sort_values('mes').set_index('mes')
        st.bar_chart(chart_data, color="#6c8d76", use_container_width=True)
    else:
        st.warning("No hay suficientes datos para generar el gráfico.")

# ==========================================
# 🏘️ INTERFAZ: VECINOS (ACCESO POR CALLE)
# ==========================================
elif st.session_state.rol == "Vecino":
    calle_actual = st.session_state.calle_vecino
    st.markdown(f"<h2>🏘️ Panel Vecinal: {calle_actual}</h2>", unsafe_allow_html=True)
    st.info("Desde aquí puede descargar los reportes de transparencia y ver el estado de su pasaje.")
    
    t1, t2 = st.tabs(["📑 Transparencia y Documentos", f"⚠️ Morosos de {calle_actual}"])
    
    with t1:
        st.markdown(f"#### Balance Oficial de la Villa ({mes_actual})")
        st.write("Descargue el archivo PDF con el detalle de ingresos, gastos y pagos de porteros a nivel general.")
        doc_balance = generar_pdf_cierre(ingresos_vecinos, ingresos_eventos, egresos_porteros, egresos_otros, balance_final, caja_chica_anterior, df_extra_mes, mes_actual)
        st.download_button("📄 Descargar Balance Mensual", doc_balance, file_name=f"Balance_Villa_Raimapu_{mes_actual}.pdf", type="primary")
        
    with t2:
        st.markdown(f"#### Control de Pagos: {calle_actual}")
        df_casas_calle = df_casas[df_casas['calle'] == calle_actual]
        df_pagos_calle = df_pagos_mes[df_pagos_mes['calle'] == calle_actual]
        
        df_deu_calle = df_casas_calle.merge(df_pagos_calle[['calle', 'numero']], on=['calle', 'numero'], how='left', indicator=True)
        df_deu_calle = df_deu_calle[df_deu_calle['_merge'] == 'left_only'].drop(columns=['_merge'])
        
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Casas al Día en su Pasaje", len(df_pagos_calle))
        col_m2.metric("Casas Pendientes (Deudores)", len(df_deu_calle))
        
        st.markdown("---")
        if not df_deu_calle.empty:
            excel_morosos = generar_excel_morosos(df_deu_calle, mes_actual, titulo_calle=f"MOROSOS {calle_actual.upper()}")
            st.download_button(f"📥 Descargar Lista de Deudores ({calle_actual})", excel_morosos, file_name=f"Morosos_{calle_actual.replace(' ', '_')}_{mes_actual}.xlsx")
            st.dataframe(df_deu_calle[['numero', 'propietario']], use_container_width=True, hide_index=True)
        else:
            st.success("🎉 ¡Felicidades! Todas las casas de su pasaje están al día este mes.")
