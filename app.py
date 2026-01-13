import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.graph_objects as go
from datetime import datetime
from fpdf import FPDF

# --- CONFIGURACIÓN DE BASE DE DATOS Y PERSISTENCIA ---
db_dir = os.path.join(os.getcwd(), 'data')
if not os.path.exists(db_dir):
    os.makedirs(db_dir)

db_path = os.path.join(db_dir, 'obras_datos.db')
conn = sqlite3.connect(db_path, check_same_thread=False)
c = conn.cursor()

def init_db():
    # Añadimos fecha_finalizacion para control de cierre
    c.execute('''CREATE TABLE IF NOT EXISTS obras 
                 (id INTEGER PRIMARY KEY, nombre TEXT, presupuesto REAL, 
                  estado TEXT, contratista TEXT, fecha_inicio TEXT, fecha_fin TEXT)''')
    c.execute('CREATE TABLE IF NOT EXISTS trabajadores (id INTEGER PRIMARY KEY, nombre TEXT, dni TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS partes (id INTEGER PRIMARY KEY, t_id INTEGER, o_id INTEGER, fecha TEXT, horas REAL, notas TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS gastos (id INTEGER PRIMARY KEY, o_id INTEGER, tipo TEXT, importe REAL, fecha TEXT, descripcion TEXT)')
    conn.commit()

init_db()

# --- DISEÑO CSS PERSONALIZADO (SUPERBONITO) ---
st.set_page_config(page_title="Gestión Ascensores Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #004a99; color: white; border: none; }
    .stButton>button:hover { background-color: #003366; border: none; }
    .card { background-color: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; border: 1px solid #e0e0e0; }
    h1, h2, h3 { color: #004a99; font-family: 'Helvetica Neue', sans-serif; }
    .reportview-container .main .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

# --- CABECERA CON LOGOS CORPORATIVOS ---
def cabecera():
    col1, col2 = st.columns([1,1])
    with col1:
        st.image("https://ascensoresdadri.com/wp-content/uploads/2025/01/ascensores-dadir-logo.png", width=220)
    with col2:
        st.image("https://agrascensores.com/wp-content/uploads/2025/10/Diseno-sin-titulo-24.png", width=220)
    st.divider()

cabecera()

# --- MENÚ LATERAL ---
with st.sidebar:
    st.title("⚙️ Menú de Naiara")
    choice = st.radio("Ir a:", ["📊 Dashboard Ricardo", "📝 Gestión de Obras", "👷 Gestión de Personal", "🛠️ Administración Avanzada"])

# --- 1. DASHBOARD RICARDO (Filtro por estado) ---
if choice == "📊 Dashboard Ricardo":
    st.header("📈 Informe de Rentabilidad Mensual")
    ver_finalizadas = st.checkbox("Incluir obras finalizadas en el informe")
    
    query = "SELECT * FROM obras" if ver_finalizadas else "SELECT * FROM obras WHERE estado != 'finalizada'"
    df_obras = pd.read_sql_query(query, conn)
    
    if not df_obras.empty:
        # Lógica de meses
        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        mes_sel = st.selectbox("Consultar Mes:", meses)
        mes_num = str(meses.index(mes_sel) + 1).zfill(2)
        
        stats = []
        for _, row in df_obras.iterrows():
            g_mes = pd.read_sql_query(f"SELECT SUM(importe) FROM gastos WHERE o_id={row['id']} AND strftime('%m', fecha)='{mes_num}'", conn).iloc[0,0] or 0
            h_mes = pd.read_sql_query(f"SELECT SUM(horas) FROM partes WHERE o_id={row['id']} AND strftime('%m', fecha)='{mes_num}'", conn).iloc[0,0] or 0
            
            # Rentabilidad Global
            g_total = pd.read_sql_query(f"SELECT SUM(importe) FROM gastos WHERE o_id={row['id']}", conn).iloc[0,0] or 0
            h_total = pd.read_sql_query(f"SELECT SUM(horas) FROM partes WHERE o_id={row['id']}", conn).iloc[0,0] or 0
            rent = (row['presupuesto'] - g_total) / h_total if h_total > 0 else 0
            
            stats.append({
                "Obra": row['nombre'], "Presupuesto": row['presupuesto'], 
                "Gastos Mes": g_mes, "Horas Mes": h_mes, "Rentabilidad Global (€/h)": round(rent, 2)
            })
        
        df_stats = pd.DataFrame(stats)
        
        # Gráficos Pro
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_stats['Obra'], y=df_stats['Presupuesto'], name='Presupuesto', marker_color='#004a99'))
        fig.add_trace(go.Bar(x=df_stats['Obra'], y=df_stats['Gastos Mes'], name=f'Gastos {mes_sel}', marker_color='#ff4b4b'))
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabla Visualmente Limpia
        st.subheader("Resumen Económico")
        df_display = df_stats.copy()
        df_display["Presupuesto"] = df_display["Presupuesto"].map("{:,.2f} €".format)
        df_display["Gastos Mes"] = df_display["Gastos Mes"].map("{:,.2f} €".format)
        st.dataframe(df_display, use_container_width=True)

        # Botón PDF Corregido
        if st.button("Generar Informe PDF para Ricardo"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(190, 10, f"INFORME GLOBAL - {mes_sel.upper()} 2026", ln=True, align='C')
            pdf.ln(10)
            pdf.set_font("Arial", 'B', 10)
            # Cabecera tabla PDF
            pdf.cell(60, 10, "Obra", 1); pdf.cell(40, 10, "Presu.", 1); pdf.cell(40, 10, "Gastos M.", 1); pdf.cell(40, 10, "Rentab.", 1); pdf.ln()
            pdf.set_font("Arial", '', 9)
            for s in stats:
                pdf.cell(60, 10, s['Obra'][:28], 1); pdf.cell(40, 10, f"{s['Presupuesto']}e", 1); pdf.cell(40, 10, f"{s['Gastos Mes']}e", 1); pdf.cell(40, 10, f"{s['Rentabilidad Global']}", 1); pdf.ln()
            
            pdf_bytes = bytes(pdf.output())
            st.download_button("📥 Descargar PDF Global", pdf_bytes, f"Informe_{mes_sel}_2026.pdf", "application/pdf")

# --- 2. GESTIÓN DE OBRAS (All-in-One Panel) ---
elif choice == "📝 Gestión de Obras":
    st.header("🗂️ Panel de Proyectos Activos")
    
    col_add, col_close = st.columns(2)
    with col_add:
        with st.expander("➕ Añadir Nueva Obra"):
            n_o = st.text_input("Nombre del Proyecto")
            p_o = st.number_input("Presupuesto Total (€)", min_value=0.0)
            if st.button("Guardar Obra"):
                c.execute("INSERT INTO obras (nombre, presupuesto, estado) VALUES (?,?,'en curso')", (n_o, p_o))
                conn.commit(); st.success("Obra Creada"); st.rerun()
    
    with col_close:
        with st.expander("🏁 Finalizar una Obra"):
            obs_activas = pd.read_sql_query("SELECT id, nombre FROM obras WHERE estado != 'finalizada'", conn)
            o_fin = st.selectbox("Obra a cerrar", obs_activas['nombre'] if not obs_activas.empty else ["Sin obras"])
            if st.button("Marcar como Finalizada"):
                hoy = datetime.now().strftime("%Y-%m-%d")
                c.execute(f"UPDATE obras SET estado='finalizada', fecha_fin='{hoy}' WHERE nombre='{o_fin}'")
                conn.commit(); st.success(f"{o_fin} finalizada"); st.rerun()

    st.divider()
    
    # Registro de Partes y Gastos con diseño limpio
    st.subheader("Operaciones Diarias")
    c_p, c_g = st.columns(2)
    
    with c_p:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 📝 Registrar Parte de Horas")
        tbs = pd.read_sql_query("SELECT * FROM trabajadores", conn)
        obs = pd.read_sql_query("SELECT * FROM obras WHERE estado='en curso'", conn)
        if not tbs.empty and not obs.empty:
            t_s = st.selectbox("Trabajador", tbs['nombre'], key="p_t")
            o_s = st.selectbox("Obra", obs['nombre'], key="p_o")
            f_p = st.date_input("Fecha", datetime.now(), key="p_f")
            # Lógica Viernes 6h / Resto 8h
            sug = 6.0 if f_p.weekday() == 4 else 8.0
            h_p = st.number_input("Horas", value=sug, step=0.5, key="p_h")
            not_p = st.text_area("Tareas", key="p_n")
            if st.button("Guardar Parte"):
                tid = int(tbs[tbs['nombre']==t_s]['id'].values[0])
                oid = int(obs[obs['nombre']==o_s]['id'].values[0])
                c.execute("INSERT INTO partes (t_id, o_id, fecha, horas, notas) VALUES (?,?,?,?,?)", (tid, oid, f_p.strftime("%Y-%m-%d"), h_p, not_p))
                conn.commit(); st.success("Guardado")
        st.markdown('</div>', unsafe_allow_html=True)

    with c_g:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 💰 Registrar Gasto")
        if not obs.empty:
            og_s = st.selectbox("Obra", obs['nombre'], key="g_o")
            cat = st.selectbox("Concepto", ["Dietas", "Gasolina", "Materiales", "Contenedor", "Otros"], key="g_c")
            desc = ""
            if cat == "Otros": desc = st.text_input("Especificar concepto", key="g_d")
            imp = st.number_input("Importe (€)", min_value=0.0, key="g_i")
            if st.button("Guardar Gasto"):
                oid = int(obs[obs['nombre']==og_s]['id'].values[0])
                c.execute("INSERT INTO gastos (o_id, tipo, importe, fecha, descripcion) VALUES (?,?,?,?,?)", (oid, cat, imp, datetime.now().strftime("%Y-%m-%d"), desc))
                conn.commit(); st.success("Gasto registrado")
        st.markdown('</div>', unsafe_allow_html=True)

# --- 3. PERSONAL (Con DNI) ---
elif choice == "👷 Gestión de Personal":
    st.header("👥 Plantilla de Trabajadores")
    with st.expander("➕ Añadir Nuevo Trabajador"):
        n_t = st.text_input("Nombre y Apellidos")
        d_t = st.text_input("DNI / NIE")
        if st.button("Registrar Trabajador"):
            c.execute("INSERT INTO trabajadores (nombre, dni) VALUES (?,?)", (n_t, d_t))
            conn.commit(); st.success(f"{n_t} añadido"); st.rerun()
    
    st.write("### Listado Actual")
    df_t = pd.read_sql_query("SELECT id, nombre, dni FROM trabajadores", conn)
    st.table(df_t)

# --- 4. ADMINISTRACIÓN (Eliminar) ---
elif choice == "🛠️ Administración Avanzada":
    st.header("⚙️ Limpieza de Base de Datos")
    st.warning("Cuidado: Las eliminaciones son permanentes.")
    
    df_o_all = pd.read_sql_query("SELECT id, nombre, estado, fecha_fin FROM obras", conn)
    st.dataframe(df_o_all, use_container_width=True)
    id_del = st.number_input("ID de Obra a eliminar", min_value=0, step=1)
    if st.button("❌ Eliminar Obra Permanentemente"):
        c.execute(f"DELETE FROM obras WHERE id={id_del}")
        conn.commit(); st.success("Obra eliminada"); st.rerun()
