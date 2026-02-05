import streamlit as st
import pandas as pd
import sqlite3
import time
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Gestión Adifincas", layout="wide", page_icon="🏢")

# Estilos CSS para impresión limpia y gráficos
st.markdown("""
<style>
    @media print {
        header, footer, .stSidebar, .stButton, button, .stRadio, .stTextInput {display: none !important;}
        .block-container {padding-top: 0rem !important; padding-bottom: 0rem !important;}
        body {font-size: 12pt;}
    }
</style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS ---
def get_connection():
    # Mantenemos v2 para no perder lo que hayas probado hoy
    return sqlite3.connect('adifincas_v2.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT,
            fecha_creacion TEXT,
            creado_por TEXT,
            cliente TEXT,
            contacto TEXT,
            motivo TEXT,
            prioridad TEXT,
            asignado_a TEXT,
            estado TEXT,
            historial TEXT
        )
    ''')
    conn.commit()
    conn.close()

def generar_nuevo_codigo():
    conn = get_connection()
    c = conn.cursor()
    mes_actual = datetime.now().strftime("%Y/%m")
    c.execute("SELECT codigo FROM tickets WHERE codigo LIKE ? ORDER BY id DESC LIMIT 1", (f"{mes_actual}%",))
    resultado = c.fetchone()
    conn.close()
    
    if resultado:
        try:
            ultimo_num = int(resultado[0].split('/')[-1])
            nuevo_num = ultimo_num + 1
        except:
            nuevo_num = 1
    else:
        nuevo_num = 1
    return f"{mes_actual}/{nuevo_num:03d}"

def buscar_coincidencias(texto):
    if not texto or len(texto) < 3: return []
    conn = get_connection()
    df = pd.read_sql_query(f"SELECT codigo, cliente, motivo, estado, fecha_creacion FROM tickets WHERE cliente LIKE '%{texto}%' OR contacto LIKE '%{texto}%' ORDER BY id DESC LIMIT 5", conn)
    conn.close()
    return df

def crear_ticket(usuario, cliente, contacto, motivo, prioridad, asignado):
    conn = get_connection()
    c = conn.cursor()
    codigo = generar_nuevo_codigo()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    historial_inicial = f"{fecha} | SISTEMA | Ticket creado por {usuario} (Asignado a: {asignado})\n"
    
    c.execute('''
        INSERT INTO tickets (codigo, fecha_creacion, creado_por, cliente, contacto, motivo, prioridad, asignado_a, estado, historial)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (codigo, fecha, usuario, cliente, contacto, motivo, prioridad, asignado, "Pendiente", historial_inicial))
    conn.commit()
    conn.close()
    return codigo

def agregar_nota(id_ticket, usuario, texto, nuevo_estado=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT historial, estado FROM tickets WHERE id=?", (id_ticket,))
    data = c.fetchone()
    if not data: return
    
    historial_viejo, estado_viejo = data
    fecha = datetime.now().strftime("%d/%m %H:%M")
    bloque_nuevo = f"{fecha} | {usuario} | {texto}\n"
    
    if nuevo_estado and nuevo_estado != estado_viejo:
        bloque_nuevo += f"{fecha} | SISTEMA | 🔄 Cambio estado: {estado_viejo} -> {nuevo_estado}\n"
        estado_final = nuevo_estado
    else:
        estado_final = estado_viejo
    
    historial_actualizado = bloque_nuevo + historial_viejo
    c.execute("UPDATE tickets SET historial=?, estado=? WHERE id=?", (historial_actualizado, estado_final, id_ticket))
    conn.commit()
    conn.close()

def leer_todos():
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM tickets ORDER BY id DESC", conn)
    except:
        df = pd.DataFrame()
    conn.close()
    return df

# Inicializar
init_db()

# --- GESTIÓN DE SESIÓN PARA IMPRESIÓN ---
if 'vista_impresion_lista' not in st.session_state:
    st.session_state['vista_impresion_lista'] = False
if 'vista_impresion_ficha' not in st.session_state:
    st.session_state['vista_impresion_ficha'] = None

# --- VISTAS DE IMPRESIÓN ---
if st.session_state['vista_impresion_lista']:
    st.button("🔙 Volver al sistema")
    st.title("Listado de Tickets - Adifincas")
    df = leer_todos()
    if not df.empty:
        st.table(df[['codigo', 'cliente', 'motivo', 'prioridad', 'estado', 'asignado_a']])
    st.warning("Pulsa Ctrl + P para imprimir.")
    if st.button("Salir de impresión"):
        st.session_state['vista_impresion_lista'] = False
        st.rerun()
    st.stop()

if st.session_state['vista_impresion_ficha']:
    t = st.session_state['vista_impresion_ficha']
    st.button("🔙 Volver")
    st.markdown(f"# 🎫 Ficha: {t['codigo']}")
    st.markdown(f"**Cliente:** {t['cliente']} | **Estado:** {t['estado']} | **Prioridad:** {t['prioridad']}")
    st.markdown(f"**Motivo:** {t['motivo']}")
    st.markdown("---")
    st.markdown("### Historial")
    if t['historial']:
        for l in t['historial'].split('\n'):
            if "|" in l:
                parts = l.split("|", 2)
                if len(parts) >= 3:
                    st.markdown(f"**{parts[0]} - {parts[1]}:** {parts[2]}")
    st.success("Pulsa Ctrl + P para imprimir.")
    if st.button("Cerrar Vista"):
        st.session_state['vista_impresion_ficha'] = None
        st.rerun()
    st.stop()

# --- INTERFAZ PRINCIPAL ---
st.sidebar.title("🔐 Acceso")
usuario = st.sidebar.selectbox("Usuario", ["Seleccionar...", "Inés", "Gloria", "Inma", "Chema"])
if usuario == "Seleccionar...":
    st.info("Selecciona tu usuario para comenzar.")
    st.stop()

st.title("🏢 Adifincas")

# PESTAÑAS
tab1, tab2, tab3 = st.tabs(["📞 NUEVA LLAMADA", "📋 LISTADO Y GESTIÓN", "📊 ESTADÍSTICAS"])

# --- TAB 1: ALTA ---
with tab1:
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            cliente = st.text_input("Cliente / Comunidad")
            contacto = st.text_input("Teléfono / Email")
            if contacto or cliente:
                try:
                    dups = buscar_coincidencias(contacto if contacto else cliente)
                    if not dups.empty:
                        st.warning(f"⚠️ {len(dups)} coincidencias encontradas:")
                        st.dataframe(dups[['codigo', 'estado', 'motivo']], hide_index=True)
                except: pass
        with c2:
            motivo = st.text_area("Motivo", height=100)
            prio = st.select_slider("Prioridad", ["Normal", "Urgente", "MUY URGENTE"])
            asig = st.selectbox("Asignar a", ["Administración", "Gerencia", "Mantenimiento", "Inés", "Gloria", "Inma", "Chema"])
            
        if st.button("Guardar Ticket", type="primary", use_container_width=True):
            if cliente and motivo:
                cod = crear_ticket(usuario, cliente, contacto, motivo, prio, asig)
                st.success(f"Creado: {cod}")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Faltan datos.")

# --- TAB 2: LISTADO ---
with tab2:
    df = leer_todos()
    if df.empty:
        st.info("No hay tickets.")
    else:
        # 1. BUSCADOR GLOBAL
        busqueda = st.text_input("🔍 Buscar ticket (Nombre, Teléfono, Calle, Código...)", placeholder="Escribe aquí para filtrar...")
        
        if busqueda:
            # Filtro mágico que busca en todas las columnas
            mask = df.apply(lambda row: row.astype(str).str.contains(busqueda, case=False).any(), axis=1)
            df_display = df[mask]
        else:
            df_display = df

        # Cabecera
        c_head1, c_head2 = st.columns([5, 1])
        c_head1.caption(f"Mostrando {len(df_display)} registros")
        if c_head2.button("🖨️ Imprimir"):
            st.session_state['vista_impresion_lista'] = True
            st.rerun()
            
        # Filtro cerrados
        ver_cerrados = st.checkbox("Ver Cerrados", value=False)
        if not ver_cerrados:
            df_display = df_display[df_display['estado'] != 'Cerrado']

        # Listado
        for i, row in df_display.iterrows():
            icon = "🔴" if row['prioridad'] == "MUY URGENTE" else "🟢"
            if row['estado'] == "Cerrado": icon = "⚫"
            
            with st.expander(f"{icon} {row['codigo']} | {row['cliente']} | {row['motivo']}"):
                c_det, c_hist = st.columns([1, 1])
                with c_det:
                    st.write(f"**Asignado:** {row['asignado_a']}")
                    st.write(f"**Contacto:** {row['contacto']}")
                    
                    # 2. BOTÓN EMAIL INTELIGENTE
                    if "@" in str(row['contacto']):
                        subject = f"Incidencia {row['codigo']} - Adifincas"
                        body = f"Estimado/a {row['cliente']},\n\nRespecto a su incidencia reportada ({row['motivo']})...\n\nAtentamente,\nAdifincas."
                        st.link_button("📧 Enviar Email Rápido", f"mailto:{row['contacto']}?subject={subject}&body={body}")
                    
                    if st.button("🖨️ Ficha", key=f"p_{row['id']}"):
                        st.session_state['vista_impresion_ficha'] = row.to_dict()
                        st.rerun()
                    
                    st.divider()
                    nota = st.text_area("Nota:", key=f"n_{row['id']}")
                    b1, b2 = st.columns(2)
                    
                    if row['estado'] == "Cerrado":
                        if b1.button("Reabrir", key=f"r_{row['id']}"):
                            agregar_nota(row['id'], usuario, "Reapertura", "En Gestión")
                            st.rerun()
                    else:
                        if b1.button("Añadir", key=f"a_{row['id']}"):
                            if nota:
                                agregar_nota(row['id'], usuario, nota)
                                st.rerun()
                        if b2.button("Cerrar", key=f"c_{row['id']}"):
                            agregar_nota(row['id'], usuario, nota if nota else "Cierre", "Cerrado")
                            st.rerun()

                with c_hist:
                    st.caption("📜 Historial")
                    if row['historial']:
                        h_cont = st.container(height=250)
                        for l in row['historial'].split('\n'):
                            if "|" in l:
                                pts = l.split("|", 2)
                                if len(pts) == 3:
                                    if "SISTEMA" in pts[1]: h_cont.caption(f"🤖 {pts[2]}")
                                    else: h_cont.markdown(f"**{pts[1]}:** {pts[2]}")
                                    h_cont.divider()

# --- TAB 3: ESTADÍSTICAS ---
with tab3:
    st.header("📊 Cuadro de Mando")
    df_stats = leer_todos()
    
    if df_stats.empty:
        st.info("Aún no hay datos suficientes.")
    else:
        # Métricas grandes
        k1, k2, k3, k4 = st.columns(4)
        total = len(df_stats)
        abiertos = len(df_stats[df_stats['estado'] != 'Cerrado'])
        urgentes = len(df_stats[df_stats['prioridad'] == 'MUY URGENTE'])
        cerrados = total - abiertos
        
        k1.metric("Total Tickets", total)
        k2.metric("Abiertos", abiertos, delta=f"{abiertos/total*100:.1f}% del total" if total > 0 else 0, delta_color="inverse")
        k3.metric("Muy Urgentes", urgentes)
        k4.metric("Cerrados", cerrados)
        
        st.divider()
        
        g1, g2 = st.columns(2)
        with g1:
            st.subheader("Carga de Trabajo (Por persona)")
            # Conteo por asignado
            if 'asignado_a' in df_stats.columns:
                st.bar_chart(df_stats['asignado_a'].value_counts())
                
        with g2:
            st.subheader("Estado de los Tickets")
            if 'estado' in df_stats.columns:
                st.bar_chart(df_stats['estado'].value_counts(), color="#ffaa00")
