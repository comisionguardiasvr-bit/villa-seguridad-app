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
# 🎨 DISEÑO Y ESTILOS (Paleta Pastel Sobria y Bonita)
# ==========================================
st.markdown("""
<style>
    /* Fondo principal y textos */
    .reportview-container {
        background: #fdfcf9; /* Crema muy pálido */
        color: #4a4a4a; /* Gris oscuro sobrio */
    }
    h1, h2, h3 { color: #5a6e5f; } /* Verde musgo suave */

    /* Tarjetas de Métricas */
    div[data-testid="metric-container"] {
        background-color: #ffffff; 
        border: 1px solid #e0e0e0;
        padding: 15px 20px; border-radius: 12px; box-shadow: 0px 4px 10px rgba(0,0,0,0.03);
        border-left: 5px solid #a8c3b1; /* Verde pastel suave */
        transition: transform 0.2s ease-in-out;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-3px);
        box-shadow: 0px 6px 15px rgba(0,0,0,0.06);
    }

    /* Botones */
    .stButton>button {
        border-radius: 20px !important;
        font-weight: 600 !important;
        background-color: #a8c3b1; /* Verde pastel suave */
        color: white;
        border: none;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #8fae9a; /* Un tono más oscuro para el hover */
        transform: scale(1.02);
    }

    /* Pestañas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f0f0;
        border-radius: 10px 10px 0px 0px;
        color: #4a4a4a;
    }
    .stTabs [aria-selected="true"] {
        background-color: #d8e2dc; /* Beige pastel muy suave */
        color: #5a6e5f;
        font-weight: bold;
    }

    /* Formularios y entradas */
    .stForm {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #e0e0e0;
    }
    .stTextInput>div>div>input, .stSelectbox>div>div>div>select {
        border-radius: 8px;
    }

    #MainMenu, footer {visibility: hidden;}
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
    _, col_logo, _ = st.columns([1.5, 1, 1.5])
    with col_logo:
        if os.path.exists("logo_villa.jpg"): st.image("logo_villa.jpg", use_container_width=True)
        else: st.markdown("<h1 style='text-align: center; font-size: 4em;'>🌿</h1>", unsafe_allow_html=True)
    
    st.markdown("<h2 style='text-align: center; color: #2e7d32;'>Acceso al Sistema Raimapu</h2>", unsafe_allow_html=True)
    
    _, col_login, _ = st.columns([1, 1.5, 1])
    with col_login:
        with st.form("login_form"):
            tipo_usuario = st.selectbox("Perfil de Usuario:", ["Tesorera / Administradora", "Recaudadora en Terreno"])
            pass_input = st.text_input("🔑 Contraseña:", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                # CLAVES DE ACCESO
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
def cargar_bd():
    def get_df(sheet, cols):
        try: return conn.read(worksheet=sheet, ttl=0).dropna(how="all")
        except: return pd.DataFrame(columns=cols)
    return (
        get_df("Pagos", ['calle', 'numero', 'propietario', 'monto_pagado', 'fecha', 'mes', 'registrado_por']),
        get_df("Gastos", ['descripcion', 'monto', 'fecha', 'mes']),
        get_df("Ingresos_Extra", ['concepto', 'monto', 'fecha', 'mes']),
        get_df("Guardias", ['nombre', 'tipo', 'sueldo']),
        get_df("Logs", ['fecha_hora', 'usuario', 'accion', 'detalle']),
        get_df("Ajustes_Guardias", ['mes', 'guardia', 'tipo', 'monto', 'detalle'])
    )

df_pagos_full, df_gastos_full, df_extra_full, df_guardias, df_logs_full, df_ajustes_full = cargar_bd()

@st.cache_data
def cargar_casas():
    with open('casas.json', 'r', encoding='utf-8') as f:
        df = pd.DataFrame(json.load(f))
        df['numero'] = pd.to_numeric(df['numero']).astype(int)
        return df.sort_values(by=['calle', 'numero']).reset_index(drop=True)
df_casas = cargar_casas()

# ==========================================
# 🕵️‍♂️ FUNCIÓN DE AUDITORÍA (LOGS)
# ==========================================
def registrar_log(accion, detalle):
    nuevo_log = pd.DataFrame([{'fecha_hora': datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'usuario': st.session_state.usuario, 'accion': accion, 'detalle': detalle}])
    conn.update(worksheet="Logs", data=pd.concat([df_logs_full, nuevo_log], ignore_index=True))

# --- BARRA LATERAL ---
with st.sidebar:
    if os.path.exists("logo_villa.jpg"): st.image("logo_villa.jpg", use_container_width=True)
    st.markdown(f"<h3 style='text-align: center; color: #5a6e5f;'>Hola, {st.session_state.rol}</h3>", unsafe_allow_html=True)
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
bonos_actual = df_ajustes_mes[df_ajustes_mes['tipo'] == 'Bono Extra']['monto'].sum() if not df_ajustes_mes.empty else 0
descuentos_actual = df_ajustes_mes[df_ajustes_mes['tipo'] == 'Descuento Falta']['monto'].sum() if not df_ajustes_mes.empty else 0
egresos_guardias = sueldos_base_actual + bonos_actual - descuentos_actual

egresos_otros = pd.to_numeric(df_gastos_mes['monto']).sum() if not df_gastos_mes.empty else 0
total_egresos_mes = egresos_guardias + egresos_otros

balance_final = caja_chica_anterior + total_ingresos_mes - total_egresos_mes
deudores_count = len(df_casas) - len(df_pagos_mes)

# --- GENERADORES DE PDF (fpdt) - Simplificado para el chat ---
def generar_excel_morosos(df_morosos, mes_texto):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as wr:
        df_morosos.rename(columns={'calle': 'PASAJE', 'numero': 'N° CASA', 'propietario': 'PROPIETARIO'}).to_excel(wr, index=False, sheet_name='Morosos')
        ws = wr.sheets['Morosos']
        ws['A1'] = f"MOROSOS - {mes_texto.upper()}"
        ws['A1'].font = Font(bold=True)
    return buf.getvalue()

# ==========================================
# INTERFAZ DEPENDIENDO DEL ROL
# ==========================================
if st.session_state.rol == "Recaudadora":
    st.markdown(f"<h2>📱 Portal de Recaudación <span style='color: #2e7d32;'>| {mes_actual}</span></h2>", unsafe_allow_html=True)
    st.info("💡 Desde aquí puedes registrar los pagos en terreno. Usa la opción 'Meses a pagar' si un vecino paga por adelantado.")
    
    with st.container():
        c_sel = st.selectbox("1. Seleccione Pasaje", df_casas['calle'].unique())
        p_ya = df_pagos_mes[df_pagos_mes['calle'] == c_sel]['numero'].tolist()
        pend = df_casas[(df_casas['calle'] == c_sel) & (~df_casas['numero'].isin(p_ya))]
        
        if pend.empty: st.success("🎉 ¡Pasaje al día en este mes!")
        else:
            opc = {f"N° {r['numero']} - {r['propietario']}": r['numero'] for _, r in pend.iterrows()}
            n_sel = opc[st.selectbox("2. Seleccione Casa", opc.keys())]
            
            # PAGOS ADELANTADOS (MÚLTIPLES MESES)
            meses_a_pagar = st.multiselect("3. Meses que está pagando:", MESES_DISPONIBLES, default=[mes_actual])
            st.warning(f"Monto Total a Cobrar: **${len(meses_a_pagar) * CUOTA_MENSUAL:,.0f}**")
            
            if st.button("💳 Registrar Pagos", type="primary", use_container_width=True):
                nom = df_casas[(df_casas['calle'] == c_sel) & (df_casas['numero'] == n_sel)]['propietario'].values[0]
                nuevos_pagos = []
                for m in meses_a_pagar:
                    nuevos_pagos.append({'calle': c_sel, 'numero': int(n_sel), 'propietario': nom, 'monto_pagado': CUOTA_MENSUAL, 'fecha': datetime.now().strftime("%Y-%m-%d %H:%M"), 'mes': m, 'registrado_por': st.session_state.usuario})
                
                conn.update(worksheet="Pagos", data=pd.concat([df_pagos_full, pd.DataFrame(nuevos_pagos)], ignore_index=True))
                registrar_log("Cobro Múltiple", f"Cobró {len(meses_a_pagar)} meses a casa {c_sel} {n_sel}")
                cargar_bd.clear(); st.toast("✅ Pagos guardados en la base central."); st.rerun()

elif st.session_state.rol == "Admin":
    st.markdown(f"<h2>🏢 Panel Administrativo <span style='color: #2e7d32;'>| {mes_actual}</span></h2>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Caja Chica Anterior", f"${caja_chica_anterior:,.0f}", help="Dinero que sobró de meses pasados")
    m2.metric("Ingresos del Mes", f"${total_ingresos_mes:,.0f}", help="Vecinos + Eventos")
    m3.metric("Fondo Real en Caja", f"${balance_final:,.0f}")
    m4.metric("Casas Morosas", f"{deudores_count} pendientes")
    
    t1, t2, t3, t4, t5 = st.tabs(["📝 1. Pagos Recaudación", "🎁 2. Ingresos Extra", "🛒 3. Gastos Operativos", "👮‍♂️ 4. Personal y Turnos", "📑 5. Reportes y Auditoría"])

    # PESTAÑA 1: PAGOS
    with t1:
        st.markdown("#### 📋 Historial de Pagos del Mes")
        if not df_pagos_mes.empty:
            st.dataframe(df_pagos_mes[['calle', 'numero', 'propietario', 'monto_pagado', 'fecha', 'registrado_por']], use_container_width=True, hide_index=True)
            with st.expander("❌ Anular un pago (Requiere Auditoría)"):
                with st.form("form_anular"):
                    st.warning("Al borrar, quedará registro de qué Tesorera realizó la anulación.")
                    a_sel = st.selectbox("Seleccione el pago a borrar:", [f"{r['calle']} #{r['numero']} - {r['propietario']}" for _, r in df_pagos_mes.iterrows()])
                    if st.form_submit_button("Eliminar Pago", use_container_width=True):
                        c, n = a_sel.split(" #")[0], int(a_sel.split(" #")[1].split(" - ")[0])
                        df_act = df_pagos_full[~((df_pagos_full['calle'] == c) & (df_pagos_full['numero'] == n) & (df_pagos_full['mes'] == mes_actual))].reset_index(drop=True)
                        conn.update(worksheet="Pagos", data=df_act.reindex(range(len(df_pagos_full))))
                        registrar_log("Anulación Pago", f"Borró pago de {c} {n} del mes {mes_actual}")
                        cargar_bd.clear(); st.rerun()

    # PESTAÑA 2 y 3: EXTRA Y GASTOS
    with t2:
        st.markdown("#### 🎁 Registrar Ingresos Extra")
        with st.form("form_extra"):
            con, mon = st.text_input("Concepto"), st.number_input("Monto ($)", step=1000)
            if st.form_submit_button("💰 Guardar", use_container_width=True) and con and mon > 0:
                nuevo_e = pd.DataFrame([{'concepto': con, 'monto': int(mon), 'fecha': datetime.now().strftime("%d/%m/%Y"), 'mes': mes_actual}])
                conn.update(worksheet="Ingresos_Extra", data=pd.concat([df_extra_full, nuevo_e], ignore_index=True))
                registrar_log("Ingreso Extra", f"Agregó {mon} por {con}"); cargar_bd.clear(); st.rerun()
        if not df_extra_mes.empty: st.dataframe(df_extra_mes[['concepto', 'monto']], use_container_width=True, hide_index=True)

    with t3:
        st.markdown("#### 🛒 Registrar Gasto de la Villa")
        with st.form("form_gastos"):
            des, val = st.text_input("Descripción"), st.number_input("Costo ($)", step=1000)
            if st.form_submit_button("🚀 Registrar", use_container_width=True) and des and val > 0:
                nuevo_g = pd.DataFrame([{'descripcion': des, 'monto': int(val), 'fecha': datetime.now().strftime("%d/%m/%Y"), 'mes': mes_actual}])
                conn.update(worksheet="Gastos", data=pd.concat([df_gastos_full, nuevo_g], ignore_index=True))
                registrar_log("Nuevo Gasto", f"Gastó {val} en {des}"); cargar_bd.clear(); st.rerun()
        if not df_gastos_mes.empty: st.dataframe(df_gastos_mes[['descripcion', 'monto']], use_container_width=True, hide_index=True)

    # PESTAÑA 4: PERSONAL Y TURNOS
    with t4:
        st.markdown("#### 👮‍♂️ Gestión de Personal y Horarios")
        st.info("🕒 **Horarios Estándar:** Full Time (Lunes a Sábado) | Part Time (Sábado y Domingo)")
        
        c_ver, c_mod = st.columns(2)
        with c_ver:
            st.markdown("##### 💵 Nómina Base")
            st.dataframe(df_guardias, use_container_width=True, hide_index=True)
        with c_mod:
            st.markdown("##### ⚖️ Ajustar Sueldo del Mes")
            if not df_guardias.empty:
                with st.form("form_ajustes"):
                    g_sel = st.selectbox("Seleccione Guardia", df_guardias['nombre'].tolist())
                    tipo_aj = st.radio("Tipo de Ajuste", ["Bono Turno Extra", "Descuento Falta"])
                    monto_aj = st.number_input("Monto ($)", min_value=0, step=5000)
                    det_aj = st.text_input("Motivo (Ej: Reemplazo Juan jueves)")
                    if st.form_submit_button("Aplicar Ajuste", use_container_width=True) and monto_aj > 0:
                        n_ajuste = pd.DataFrame([{'mes': mes_actual, 'guardia': g_sel, 'tipo': tipo_aj, 'monto': int(monto_aj), 'detalle': det_aj}])
                        conn.update(worksheet="Ajustes_Guardias", data=pd.concat([df_ajustes_full, n_ajuste], ignore_index=True))
                        registrar_log("Ajuste Sueldo", f"Aplicó {tipo_aj} de ${monto_aj} a {g_sel}")
                        cargar_bd.clear(); st.rerun()
                            
        if not df_ajustes_mes.empty:
            st.markdown("##### 📝 Novedades del mes:")
            st.dataframe(df_ajustes_mes[['guardia', 'tipo', 'monto', 'detalle']], use_container_width=True, hide_index=True)

    # PESTAÑA 5: REPORTES Y AUDITORÍA
    with t5:
        st.markdown("#### 🕵️‍♂️ Registro de Auditoría (LOGS)")
        st.write("Historial de seguridad. Nadie puede borrar este historial.")
        st.dataframe(df_logs_full.tail(15).sort_index(ascending=False), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.markdown("#### 📑 Cierre y Descargas")
        
        df_deu = df_casas.merge(df_pagos_mes[['calle', 'numero']], on=['calle', 'numero'], how='left', indicator=True)
        df_deu = df_deu[df_deu['_merge'] == 'left_only'].drop(columns=['_merge'])
        
        excel_morosos = generar_excel_morosos(df_deu, mes_actual)
        st.download_button("📥 Descargar Planilla de Morosos (Excel)", excel_morosos, file_name=f"Morosos_{mes_actual}.xlsx", use_container_width=True)
