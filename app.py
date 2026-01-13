import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.graph_objects as go
from datetime import datetime
from fpdf import FPDF

# --- BASE DE DATOS Y PERSISTENCIA ---
db_dir = os.path.join(os.getcwd(), 'data')
if not os.path.exists(db_dir):
    os.makedirs(db_dir)

db_path = os.path.join(db_dir, 'obras_datos.db')
conn = sqlite3.connect(db_path, check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute('''CREATE TABLE IF NOT EXISTS obras 
                 (id INTEGER PRIMARY KEY, nombre TEXT, presupuesto REAL, 
                  estado TEXT, contratista TEXT, fecha_fin TEXT)''')
    c.execute('CREATE TABLE IF NOT EXISTS trabajadores (id INTEGER PRIMARY KEY, nombre TEXT, dni TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS partes (id INTEGER PRIMARY KEY, t_id INTEGER, o_id INTEGER, fecha TEXT, horas REAL, notas TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS gastos (id INTEGER PRIMARY KEY, o_id INTEGER, tipo TEXT, importe REAL, fecha TEXT, descripcion TEXT)')
    conn.commit()

init_db()

# --- DISEÑO CSS ESPECTACULAR (DASHBOARD DARK) ---
st.set_page_config(page_title="ASCENSOR.IO - Gestión Pro", layout="wide")

st.markdown("""
    <style>
    /* Fondo General Dark */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #f8fafc;
    }
    
    /* Tarjetas Estilo Glassmorphism */
    .css-1r6slb0, .stMetric, .stDataFrame, .card-pro {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    }
    
    /* Botones Pro */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.5em;
        background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        font-weight: bold;
        border: none;
        transition: 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(37, 99, 235, 0.4);
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #0f172a;
        border-right: 1px solid rgba(255,255,255,0.1);
    }
    
    h1, h2, h3 { color: #60a5fa !important; font-family: 'Inter', sans-serif; }
    </style>
    """, unsafe_allow_html=True)

# --- CABECERA ---
def cabecera():
    c1, c2 = st.columns([1,1])
    with c1: st.image("https://ascensoresdadri.com/wp-content/uploads/2025/01/ascensores-dadir-logo.png", width=220)
    with c2: st.image("https://agrascensores.com/wp-content/uploads/2025/10/Diseno-sin-titulo-24.png", width=220)
    st.markdown("<hr style='border: 0.5px solid rgba(255,255,255,0.1)'>", unsafe_allow_html=True)

cabecera()

# --- MENÚ ---
menu = ["📊 Dashboard", "📝 Gestión Diaria", "⚙️ Configuración", "🛠️ Administración"]
choice = st.sidebar.radio("Navegación", menu)

# --- 1. DASHBOARD (REPORTE MENSUAL) ---
if choice == "📊 Dashboard":
    st.header("📈 Rendimiento de Proyectos")
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    mes_sel = st.selectbox("Mes de Análisis:", meses)
    mes_num = str(meses.index(mes_sel) + 1).zfill(2)
    
    df_obras = pd.read_sql_query("SELECT * FROM obras WHERE estado != 'finalizada' OR strftime('%m', fecha_fin) = '"+mes_num+"'", conn)
    
    if not df_obras.empty:
        stats = []
        for _, row in df_obras.iterrows():
            g_mes = pd.read_sql_query(f"SELECT SUM(importe) FROM gastos WHERE o_id={row['id']} AND strftime('%m', fecha)='{mes_num}'", conn).iloc[0,0] or 0
            h_mes = pd.read_sql_query(f"SELECT SUM(horas) FROM partes WHERE o_id={row['id']} AND strftime('%m', fecha)='{mes_num}'", conn).iloc[0,0] or 0
            g_total = pd.read_sql_query(f"SELECT SUM(importe) FROM gastos WHERE o_id={row['id']}", conn).iloc[0,0] or 0
            h_total = pd.read_sql_query(f"SELECT SUM(horas) FROM partes WHERE o_id={row['id']}", conn).iloc[0,0] or 0
            
            # Rentabilidad: (Presupuesto - Gastos) / Horas
            rent = (row['presupuesto'] - g_total) / h_total if h_total > 0 else 0
            stats.append({"Obra": row['nombre'], "Presupuesto": row['presupuesto'], "Gastos Mes": g_mes, "Horas Mes": h_mes, "Rentabilidad": round(rent, 2)})
        
        df_stats = pd.DataFrame(stats)
        
        # Gráficos Plotly Dark
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_stats['Obra'], y=df_stats['Presupuesto'], name='Presupuesto', marker_color='#3b82f6'))
        fig.add_trace(go.Bar(x=df_stats['Obra'], y=df_stats['Gastos Mes'], name='Gastos Mes', marker_color='#f97316'))
        fig.update_layout(template="plotly_dark", barmode='group', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabla Formateada
        df_v = df_stats.copy()
        df_v["Presupuesto"] = df_v["Presupuesto"].map("{:,.2f} EUR".format)
        df_v["Rentabilidad"] = df_v["Rentabilidad"].map("{:,.2f} EUR/h".format)
        st.dataframe(df_v, use_container_width=True)

        # PDF CORREGIDO (CON LOGOS Y SÍMBOLO SEGURO)
        if st.button("📥 Generar Informe PDF Profesional"):
            pdf = FPDF()
            pdf.add_page()
            # Inserción de Logos en PDF
            pdf.image("https://ascensoresdadri.com/wp-content/uploads/2025/01/ascensores-dadir-logo.png", 10, 8, 40)
            pdf.image("https://agrascensores.com/wp-content/uploads/2025/10/Diseno-sin-titulo-24.png", 160, 8, 40)
            pdf.ln(30)
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(190, 10, f"INFORME MENSUAL - {mes_sel.upper()} 2026", ln=True, align='C')
            pdf.ln(10)
            # Cabecera Tabla
            pdf.set_fill_color(30, 41, 59); pdf.set_text_color(255, 255, 255)
            pdf.cell(70, 10, " Obra", 1, 0, 'L', True); pdf.cell(40, 10, " Presu.", 1, 0, 'C', True); pdf.cell(40, 10, " Gastos", 1, 0, 'C', True); pdf.cell(40, 10, " Rentab.", 1, 1, 'C', True)
            pdf.set_text_color(0, 0, 0)
            for s in stats:
                pdf.cell(70, 10, s['Obra'][:32], 1); pdf.cell(40, 10, f"{s['Presupuesto']} EUR", 1); pdf.cell(40, 10, f"{s['Gastos Mes']} EUR", 1); pdf.cell(40, 10, f"{s['Rentabilidad']} EUR/h", 1); pdf.ln()
            
            pdf_bytes = bytes(pdf.output())
            st.download_button("💾 Guardar Informe", pdf_bytes, f"Informe_{mes_sel}.pdf", "application/pdf")

# --- 2. GESTIÓN DIARIA (PARTES/GASTOS) ---
elif choice == "📝 Gestión Diaria":
    st.header("🛠️ Registro de Actividad")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="card-pro">', unsafe_allow_html=True)
        st.subheader("📝 Nuevo Parte")
        t_l = pd.read_sql_query("SELECT * FROM trabajadores", conn)
        o_l = pd.read_sql_query("SELECT * FROM obras WHERE estado != 'finalizada'", conn)
        if not t_l.empty and not o_l.empty:
            t_s = st.selectbox("Trabajador", t_l['nombre'], key="ts")
            o_s = st.selectbox("Obra", o_l['nombre'], key="os")
            f_p = st.date_input("Fecha", datetime.now(), key="fs")
            # Sugerencia 8h o 6h
            sug = 6.0 if f_p.weekday() == 4 else 8.0
            h_p = st.number_input("Horas", value=sug, step=0.5, key="hs")
            not_p = st.text_area("Tareas Realizadas", key="ns")
            if st.button("Guardar Parte de Trabajo"):
                tid = int(t_l[t_l['nombre']==t_s]['id'].values[0])
                oid = int(o_l[o_l['nombre']==o_s]['id'].values[0])
                c.execute("INSERT INTO partes (t_id, o_id, fecha, horas, notas) VALUES (?,?,?,?,?)", (tid, oid, f_p.strftime("%Y-%m-%d"), h_p, not_p))
                conn.commit(); st.success("Parte registrado")
    with c2:
        st.markdown('<div class="card-pro">', unsafe_allow_html=True)
        st.subheader("💰 Nuevo Gasto")
        if not o_l.empty:
            og_s = st.selectbox("Asignar a Obra", o_l['nombre'], key="gs")
            cat = st.selectbox("Categoría", ["Dietas", "Gasolina", "Materiales", "Contenedor", "Otros"], key="cs")
            desc_o = st.text_input("Nota Extra (opcional)") if cat == "Otros" else ""
            imp = st.number_input("Importe (EUR)", min_value=0.0, key="is")
            if st.button("Registrar Gasto en Obra"):
                oid = int(o_l[o_l['nombre']==og_s]['id'].values[0])
                c.execute("INSERT INTO gastos (o_id, tipo, importe, fecha, descripcion) VALUES (?,?,?,?,?)", (oid, cat, imp, datetime.now().strftime("%Y-%m-%d"), desc_o))
                conn.commit(); st.success("Gasto guardado")

# --- 3. CONFIGURACIÓN (ALTAS) ---
elif choice == "⚙️ Configuración":
    st.header("⚙️ Configuración del Sistema")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("👷 Alta de Trabajador")
        n_t = st.text_input("Nombre y Apellidos")
        d_t = st.text_input("DNI del trabajador")
        if st.button("Registrar Personal"):
            c.execute("INSERT INTO trabajadores (nombre, dni) VALUES (?,?)", (n_t, d_t))
            conn.commit(); st.success("Añadido")
    with c2:
        st.subheader("🏁 Finalizar Obra")
        obras_a = pd.read_sql_query("SELECT id, nombre FROM obras WHERE estado != 'finalizada'", conn)
        o_cerrar = st.selectbox("Obra a concluir", obras_a['nombre'] if not obras_a.empty else ["Sin obras"])
        if st.button("Marcar como Obra Finalizada"):
            f_hoy = datetime.now().strftime("%Y-%m-%d")
            c.execute(f"UPDATE obras SET estado='finalizada', fecha_fin='{f_hoy}' WHERE nombre='{o_cerrar}'")
            conn.commit(); st.success("Obra cerrada")

    st.divider()
    with st.expander("🏗️ Crear Nueva Obra"):
        n_o = st.text_input("Nombre del Proyecto")
        p_o = st.number_input("Presupuesto (EUR)", min_value=0.0)
        if st.button("Crear Obra"):
            c.execute("INSERT INTO obras (nombre, presupuesto, estado) VALUES (?,?,'en curso')", (n_o, p_o))
            conn.commit(); st.success("Proyecto activo")

# --- 4. ADMINISTRACIÓN (ELIMINAR) ---
elif choice == "🛠️ Administración":
    st.header("🛠️ Panel de Control Crítico")
    st.warning("Las acciones en este panel son permanentes.")
    
    t1, t2 = st.tabs(["👥 Trabajadores", "🏗️ Obras"])
    
    with t1:
        st.subheader("Eliminar Personal")
        df_tr = pd.read_sql_query("SELECT id, nombre, dni FROM trabajadores", conn)
        st.dataframe(df_tr, use_container_width=True)
        id_t_del = st.number_input("ID Trabajador a eliminar", min_value=0, step=1)
        if st.button("❌ Eliminar Trabajador"):
            c.execute(f"DELETE FROM trabajadores WHERE id={id_t_del}")
            conn.commit(); st.rerun()
            
    with t2:
        st.subheader("Eliminar Obras")
        df_ob = pd.read_sql_query("SELECT id, nombre, estado FROM obras", conn)
        st.dataframe(df_ob, use_container_width=True)
        id_o_del = st.number_input("ID Obra a eliminar", min_value=0, step=1)
        if st.button("❌ Eliminar Obra del Sistema"):
            c.execute(f"DELETE FROM obras WHERE id={id_o_del}")
            conn.commit(); st.rerun()
