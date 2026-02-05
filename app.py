import streamlit as st
import pandas as pd
import sqlite3
import time
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Gestión Adifincas", layout="wide", page_icon="🏢")

# Estilos CSS para impresión limpia
st.markdown("""
<style>
    @media print {
        /* Ocultar elementos de Streamlit al imprimir */
        header, footer, .stSidebar, .stButton, button, .stRadio {display: none !important;}
        .block-container {padding-top: 0rem !important; padding-bottom: 0rem !important;}
        /* Asegurar que el contenido se ve bien */
        body {font-size: 12pt;}
        table {width: 100% !important;}
    }
</style>
""", unsafe_allow_html=True)

# --- BASE DE DATOS ---
def get_connection():
    return sqlite3.connect('tickets.db', check_same_thread=False)

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
    mes_actual = datetime.now().strftime("%Y/%m") # Formato Año/Mes
    
    # Buscamos el último del mes
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
        
    return f"{mes_actual}/{nuevo_num:03d}" # Ej: 2026/02/001

def buscar_coincidencias(texto):
    if not texto or len(texto) < 3: return []
    conn = get_connection()
    # Busca en cliente O contacto
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
    
    # NUEVO ORDEN: Lo nuevo ARRIBA
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
    df = pd.read_sql_query("SELECT * FROM tickets ORDER BY id DESC", conn)
    conn.close()
    return df

# Inicializar
init_db()

# --- GESTIÓN DE SESIÓN PARA IMPRESIÓN ---
if 'vista_impresion_lista' not in st.session_state:
    st.session_state['vista_impresion_lista'] = False
if 'vista_impresion_ficha' not in st.session_state:
    st.session_state['vista_impresion_ficha'] = None

# --- VISTA DE IMPRESIÓN (Si está activa, oculta el resto) ---
if st.session_state['vista_impresion_lista']:
    st.button("🔙 Volver al sistema")
    st.title("Listado de Tickets - Adifincas")
    st.write(f"Fecha de impresión: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    df = leer_todos()
    st.table(df[['codigo', 'fecha_creacion', 'cliente', 'motivo', 'prioridad', 'estado', 'asignado_a']])
    st.warning("Pulsa Ctrl + P para imprimir ahora.")
    if st.button("Salir de impresión"):
        st.session_state['vista_impresion_lista'] = False
        st.rerun()
    st.stop()

if st.session_state['vista_impresion_ficha']:
    t = st.session_state['vista_impresion_ficha'] # Datos del ticket
    st.button("🔙 Volver")
    
    st.markdown(f"""
    # 🎫 Ficha de Incidencia: {t['codigo']}
    **Fecha:** {t['fecha_creacion']}  |  **Estado:** {t['estado']}  |  **Prioridad:** {t['prioridad']}
    
    ---
    ### 👤 Datos del Cliente
    * **Nombre:** {t['cliente']}
    * **Contacto:** {t['contacto']}
    
    ### 📝 Motivo / Descripción
    {t['motivo']}
    
    ### 👷 Asignado a
    {t['asignado_a']} (Creado por: {t['creado_por']})
    
    ---
    ### 📜 Historial de Gestión
    """)
    # Formatear historial para papel
    lineas = t['historial'].split('\n')
    for l in lineas:
        if "|" in l:
            parts = l.split("|", 2)
            st.markdown(f"**[{parts[0].strip()}] {parts[1].strip()}:** {parts[2].strip()}")
            
    st.success("Pulsa Ctrl + P para imprimir o guardar como PDF.")
    if st.button("Cerrar Vista Impresión"):
        st.session_state['vista_impresion_ficha'] = None
        st.rerun()
    st.stop()


# --- INTERFAZ NORMAL ---

# Sidebar
st.sidebar.title("🔐 Acceso")
usuario = st.sidebar.selectbox("Usuario", ["Seleccionar...", "Inés", "Gloria", "Inma", "Chema"])
if usuario == "Seleccionar...":
    st.info("Selecciona tu usuario para comenzar.")
    st.stop()

st.title("🏢 Adifincas")

tab1, tab2 = st.tabs(["📞 NUEVA LLAMADA", "📋 LISTADO Y GESTIÓN"])

# --- TAB 1: ALTA ---
with tab1:
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            cliente = st.text_input("Cliente / Comunidad")
            contacto = st.text_input("Teléfono / Contacto")
            
            # --- DETECTOR DE COINCIDENCIAS ---
            if contacto or cliente:
                duplicados = buscar_coincidencias(contacto if contacto else cliente)
                if not duplicados.empty:
                    st.warning(f"⚠️ ¡Atención! He encontrado {len(duplicados)} tickets relacionados:")
                    st.dataframe(duplicados[['codigo', 'estado', 'motivo']], hide_index=True)
                else:
                    if len(str(contacto)) > 4:
                        st.caption("✅ No hay tickets recientes con este contacto.")
        
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
                st.error("Faltan datos obligatorios.")

# --- TAB 2: LISTADO ---
with tab2:
    df = leer_todos()
    
    # Cabecera con botón de imprimir
    col_head1, col_head2 = st.columns([5, 1])
    col_head1.subheader("Listado de Incidencias")
    if col_head2.button("🖨️ Imprimir Lista"):
        st.session_state['vista_impresion_lista'] = True
        st.rerun()
    
    # Filtro ver cerrados
    ver_cerrados = st.checkbox("Ver cerrados", value=False)
    if not ver_cerrados:
        df = df[df['estado'] != 'Cerrado']
        
    for i, row in df.iterrows():
        # Icono estado
        icon = "🔴" if row['prioridad'] == "MUY URGENTE" else "🟢"
        if row['estado'] == "Cerrado": icon = "⚫"
        
        with st.expander(f"{icon} {row['codigo']} | {row['cliente']} | {row['motivo']}"):
            c_det, c_hist = st.columns([1, 1])
            
            with c_det:
                st.write(f"**Contacto:** {row['contacto']}")
                st.write(f"**Asignado:** {row['asignado_a']}")
                if st.button("🖨️ Imprimir Ficha", key=f"print_{row['id']}"):
                    st.session_state['vista_impresion_ficha'] = row.to_dict()
                    st.rerun()
                
                st.divider()
                # Acciones
                nota = st.text_area("Nueva nota:", key=f"txt_{row['id']}")
                col_btn1, col_btn2 = st.columns(2)
                
                # Lógica botones
                if row['estado'] == "Cerrado":
                    if col_btn1.button("Reabrir", key=f"reopen_{row['id']}"):
                        agregar_nota(row['id'], usuario, "Reapertura del caso", "En Gestión")
                        st.rerun()
                else:
                    if col_btn1.button("Añadir Nota", key=f"add_{row['id']}"):
                        if nota:
                            agregar_nota(row['id'], usuario, nota)
                            st.success("Añadido")
                            st.rerun()
                    if col_btn2.button("Cerrar Ticket", key=f"close_{row['id']}"):
                        agregar_nota(row['id'], usuario, nota if nota else "Cierre manual", "Cerrado")
                        st.rerun()

            with c_hist:
                st.caption("📜 Historial (Más reciente arriba)")
                hist_text = row['historial']
                # Renderizado estilo chat
                container = st.container(height=300)
                for linea in hist_text.split('\n'):
                    if "|" in linea:
                        parts = linea.split("|", 2)
                        # parts[0]=fecha, parts[1]=user, parts[2]=msg
                        if len(parts) == 3:
                            if "SISTEMA" in parts[1]:
                                container.caption(f"🤖 {parts[2]} ({parts[0]})")
                            else:
                                container.markdown(f"**{parts[1].strip()}:** {parts[2].strip()}")
                                container.caption(f"_{parts[0]}_")
                            container.write("---")
