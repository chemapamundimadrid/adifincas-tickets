import streamlit as st
import pandas as pd
import sqlite3
import time
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA Y AUTO-REFRESCO ---
st.set_page_config(page_title="Adifincas Tickets", layout="wide")

# Función para auto-refrescar la página cada X segundos
# Esto permite que si otro usuario cambia algo, tú lo veas pronto.
def auto_refresh(segundos=10):
    time.sleep(segundos)
    st.rerun()

# --- GESTIÓN DE BASE DE DATOS ---
def get_connection():
    # Usamos check_same_thread=False para permitir múltiples usuarios simultáneos en SQLite
    conn = sqlite3.connect('tickets.db', check_same_thread=False)
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_creacion TEXT,
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

# Inicializamos la DB al arrancar
init_db()

# --- FUNCIONES DE DATOS ---
def crear_ticket(cliente, contacto, motivo, prioridad, asignado):
    conn = get_connection()
    c = conn.cursor()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    historial_inicial = f"[{fecha}] 🟢 Ticket creado por Usuario. Estado: Pendiente\n"
    c.execute('''
        INSERT INTO tickets (fecha_creacion, cliente, contacto, motivo, prioridad, asignado_a, estado, historial)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (fecha, cliente, contacto, motivo, prioridad, asignado, "Pendiente", historial_inicial))
    conn.commit()
    conn.close()

def leer_tickets():
    conn = get_connection()
    # Leemos solo lo necesario para que sea rápido
    df = pd.read_sql_query("SELECT * FROM tickets ORDER BY id DESC", conn)
    conn.close()
    return df

def actualizar_ticket(id_ticket, nuevo_estado, nota_usuario):
    conn = get_connection()
    c = conn.cursor()
    
    # 1. Recuperar historial antiguo
    c.execute("SELECT historial, estado FROM tickets WHERE id=?", (id_ticket,))
    resultado = c.fetchone()
    if not resultado:
        conn.close()
        return
    
    historial_actual, estado_anterior = resultado
    
    # 2. Construir nuevo historial
    timestamp = datetime.now().strftime("%d/%m %H:%M")
    nuevo_historial = historial_actual
    
    # Si hubo cambio de estado
    if nuevo_estado != estado_anterior:
        nuevo_historial += f"[{timestamp}] 🔄 Estado: {estado_anterior} -> {nuevo_estado}\n"
    
    # Si hubo nota
    if nota_usuario:
        nuevo_historial += f"[{timestamp}] 📝 Nota: {nota_usuario}\n"

    # 3. Guardar cambios
    c.execute("UPDATE tickets SET estado=?, historial=? WHERE id=?", (nuevo_estado, nuevo_historial, id_ticket))
    conn.commit()
    conn.close()

# --- INTERFAZ DE USUARIO ---

st.title("🏢 Adifincas - Control Centralizado")

# Interruptor de actualización automática (visible en la barra lateral)
st.sidebar.header("Conexión")
modo_vivo = st.sidebar.toggle("Modo 'En Vivo' (Actualizar cada 5s)", value=True)
if modo_vivo:
    st.toast("Buscando cambios...", icon="🔄") # Muestra un aviso discreto

# Métricas Globales (Siempre visibles arriba)
df = leer_tickets()
col1, col2, col3, col4 = st.columns(4)
col1.metric("Pendientes", len(df[df['estado'] == 'Pendiente']))
col2.metric("En Gestión", len(df[df['estado'] == 'En Gestión']))
col3.metric("Urgentes", len(df[df['prioridad'] == 'MUY URGENTE']))
if not df.empty:
    ultimo_ticket = df.iloc[0]['fecha_creacion']
else:
    ultimo_ticket = "N/A"
col4.metric("Última actividad", ultimo_ticket.split(" ")[1] if df.empty is False else "-")

st.divider()

# PESTAÑAS PRINCIPALES (Mejor que menú lateral para rapidez)
tab1, tab2 = st.tabs(["📞 NUEVA LLAMADA", "📋 GESTIÓN DE TICKETS"])

with tab1:
    with st.container(border=True):
        st.subheader("Registrar Llamada Entrante")
        c1, c2 = st.columns(2)
        with c1:
            cliente = st.text_input("Cliente / Comunidad", placeholder="Ej: Comunidad C/ Mayor 12")
            contacto = st.text_input("Teléfono / Contacto", placeholder="600...")
            asignado = st.selectbox("Asignar a", ["Administración", "Gerencia", "Mantenimiento"])
        with c2:
            motivo = st.text_area("Motivo de la llamada", height=100)
            prioridad = st.radio("Prioridad", ["Normal", "Urgente", "MUY URGENTE"], horizontal=True)
        
        if st.button("Guardar Llamada (Enter)", type="primary", use_container_width=True):
            if cliente and motivo:
                crear_ticket(cliente, contacto, motivo, prioridad, asignado)
                st.success("Guardado. Aparecerá en el panel de todos los usuarios.")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Falta Cliente o Motivo")

with tab2:
    st.subheader("Listado de Incidencias")
    
    # Filtros rápidos
    filtro_col1, filtro_col2 = st.columns([3,1])
    with filtro_col1:
        estados_sel = st.multiselect("Filtrar Estado", ["Pendiente", "En Gestión", "Esperando Respuesta", "Cerrado/Resuelto"], default=["Pendiente", "En Gestión", "Esperando Respuesta"])
    with filtro_col2:
        if st.button("🔄 Forzar Actualización"):
            st.rerun()

    # Filtrado de datos
    if estados_sel:
        df_show = df[df['estado'].isin(estados_sel)]
    else:
        df_show = df

    # MOSTRAR TICKETS COMO TARJETAS (Más visual)
    if df_show.empty:
        st.info("No hay tickets con estos filtros.")
    
    for index, row in df_show.iterrows():
        # Color según prioridad
        color_borde = "red" if row['prioridad'] == "MUY URGENTE" else "grey"
        
        with st.expander(f"#{row['id']} | {row['cliente']} | {row['motivo']} ({row['estado']})"):
            col_izq, col_der = st.columns([2, 1])
            
            with col_izq:
                st.caption(f"📅 Creado: {row['fecha_creacion']} | 👤 Asignado: {row['asignado_a']} | 📞 {row['contacto']}")
                st.write(f"**Asunto:** {row['motivo']}")
                st.text_area("Historial de acciones:", value=row['historial'], height=150, disabled=True, key=f"hist_{row['id']}")
            
            with col_der:
                st.write("**Acciones Rápidas**")
                nuevo_estado = st.selectbox("Estado", ["Pendiente", "En Gestión", "Esperando Respuesta", "Cerrado/Resuelto"], index=["Pendiente", "En Gestión", "Esperando Respuesta", "Cerrado/Resuelto"].index(row['estado']), key=f"sel_{row['id']}")
                nueva_nota = st.text_input("Añadir nota rápida", key=f"nota_{row['id']}")
                
                if st.button("Actualizar Ticket", key=f"btn_{row['id']}"):
                    actualizar_ticket(row['id'], nuevo_estado, nueva_nota)
                    st.success("Actualizado")
                    st.rerun()

# --- LÓGICA DE AUTO-REFRESCO AL FINAL ---
if modo_vivo:
    time.sleep(5) # Espera 5 segundos
    st.rerun()    # Recarga la página