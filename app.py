import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.graph_objects as go
from datetime import datetime
from fpdf import FPDF

# --- CONFIGURACIÓN DE BASE DE DATOS Y PERSISTENCIA ---
# Usamos /data para que Easypanel lo mantenga fijo
db_dir = os.path.join(os.getcwd(), 'data')
if not os.path.exists(db_dir):
    os.makedirs(db_dir)

db_path = os.path.join(db_dir, 'obras_datos.db')
conn = sqlite3.connect(db_path, check_same_thread=False)
c = conn.cursor()

def init_db():
    # Estructura con DNI y estados de obra
    c.execute('''CREATE TABLE IF NOT EXISTS obras 
                 (id INTEGER PRIMARY KEY, nombre TEXT, presupuesto REAL, 
                  estado TEXT, contratista TEXT, fecha_fin TEXT)''')
    c.execute('CREATE TABLE IF NOT EXISTS trabajadores (id INTEGER PRIMARY KEY, nombre TEXT, dni TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS partes (id INTEGER PRIMARY KEY, t_id INTEGER, o_id INTEGER, fecha TEXT, horas REAL, notas TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS gastos (id INTEGER PRIMARY KEY, o_id INTEGER, tipo TEXT, importe REAL, fecha TEXT, descripcion TEXT)')
    conn.commit()

init_db()

# --- DISEÑO CSS "SUPERBONITO" ---
st.set_page_config(page_title="Gestión Ascensores Pro", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stButton>button { border-radius: 8px; height: 3em; background-color: #004a99; color: white; border: none; font-weight: bold; }
    .stButton>button:hover { background-color: #003366; }
    .card { background-color: white; padding: 25px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 20px; border: 1px solid #e1e4e8; }
    .sidebar .sidebar-content { background-image: linear-gradient(#2e7bcf,#004a99); color: white; }
    h1, h2, h3 { color: #004a99; }
    </style>
    """, unsafe_allow_html=True)

# --- CABECERA ---
def cabecera():
    c1, c2 = st.columns(2)
    with c1: st.image("https://ascensoresdadri.com/wp-content/uploads/2025/01/ascensores-dadir-logo.png", width=230)
    with c2: st.image("https://agrascensores.com/wp-content/uploads/2025/10/Diseno-sin-titulo-24.png", width=230)
    st.divider()

cabecera()

# --- NAVEGACIÓN ---
menu = ["📊 Dashboard Ricardo", "📝 Gestión Diaria (Partes/Gastos)", "⚙️ Configuración (Altas)", "🛠️ Administración (Borrar)"]
choice = st.sidebar.radio("Navegación", menu)

# --- 1. DASHBOARD GLOBAL (PDF CORREGIDO) ---
if choice == "📊 Dashboard Ricardo":
    st.header("📈 Informe de Rentabilidad")
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    mes_sel = st.selectbox("Selecciona el mes:", meses)
    mes_num = str(meses.index(mes_sel) + 1).zfill(2)
    
    # Solo mostramos las que no están finalizadas o las que se finalizaron este mes
    df_obras = pd.read_sql_query("SELECT * FROM obras WHERE estado != 'finalizada' OR strftime('%m', fecha_fin) = '"+mes_num+"'", conn)
    
    if not df_obras.empty:
        stats = []
        for _, row in df_obras.iterrows():
            g_mes = pd.read_sql_query(f"SELECT SUM(importe) FROM gastos WHERE o_id={row['id']} AND strftime('%m', fecha)='{mes_num}'", conn).iloc[0,0] or 0
            h_mes = pd.read_sql_query(f"SELECT SUM(horas) FROM partes WHERE o_id={row['id']} AND strftime('%m', fecha)='{mes_num}'", conn).iloc[0,0] or 0
            
            # Fórmula de Ricardo
            g_total = pd.read_sql_query(f"SELECT SUM(importe) FROM gastos WHERE o_id={row['id']}", conn).iloc[0,0] or 0
            h_total = pd.read_sql_query(f"SELECT SUM(horas) FROM partes WHERE o_id={row['id']}", conn).iloc[0,0] or 0
            rent = (row['presupuesto'] - g_total) / h_total if h_total > 0 else 0
            
            stats.append({
                "Obra": row['nombre'], "Presupuesto": row['presupuesto'], 
                "Gastos Mes": g_mes, "Horas Mes": h_mes, "Rentabilidad": round(rent, 2)
            })
        
        df_stats = pd.DataFrame(stats)
        
        # Gráfico Pro
        fig = go.Figure(data=[
            go.Bar(name='Presupuesto', x=df_stats['Obra'], y=df_stats['Presupuesto'], marker_color='#004a99'),
            go.Bar(name='Gastos Mes', x=df_stats['Obra'], y=df_stats['Gastos Mes'], marker_color='#ff4b4b')
        ])
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabla Formateada
        df_v = df_stats.copy()
        df_v["Presupuesto"] = df_v["Presupuesto"].map("{:,.2f} €".format)
        df_v["Rentabilidad"] = df_v["Rentabilidad"].map("{:,.2f} €/h".format)
        st.dataframe(df_v, use_container_width=True)

        # GENERACIÓN PDF (FIX KEYERROR)
        if st.button("Generar Informe PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(190, 10, f"INFORME MENSUAL - {mes_sel.upper()} 2026", ln=True, align='C')
            pdf.ln(10)
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(65, 10, "Obra", 1); pdf.cell(35, 10, "Presu.", 1); pdf.cell(35, 10, "Gastos M.", 1); pdf.cell(35, 10, "Rentab.", 1); pdf.ln()
            pdf.set_font("Arial", '', 9)
            for s in stats:
                # Usamos el nombre de llave correcto: 'Rentabilidad'
                pdf.cell(65, 10, s['Obra'][:30], 1)
                pdf.cell(35, 10, f"{s['Presupuesto']}e", 1)
                pdf.cell(35, 10, f"{s['Gastos Mes']}e", 1)
                pdf.cell(35, 10, f"{s['Rentabilidad']}e/h", 1)
                pdf.ln()
            
            pdf_bytes = bytes(pdf.output())
            st.download_button("📥 Descargar PDF", pdf_bytes, f"Informe_{mes_sel}.pdf", "application/pdf")

# --- 2. GESTIÓN DIARIA (Diseño Moderno) ---
elif choice == "📝 Gestión Diaria (Partes/Gastos)":
    st.header("Operaciones de Naiara")
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📝 Nuevo Parte")
        t_l = pd.read_sql_query("SELECT * FROM trabajadores", conn)
        o_l = pd.read_sql_query("SELECT * FROM obras WHERE estado != 'finalizada'", conn)
        if not t_l.empty and not o_l.empty:
            t_s = st.selectbox("Trabajador", t_l['nombre'])
            o_s = st.selectbox("Obra", o_l['nombre'])
            f_p = st.date_input("Fecha", datetime.now())
            # Lógica 8h o 6h
            sug = 6.0 if f_p.weekday() == 4 else 8.0
            h_p = st.number_input("Horas", value=sug, step=0.5)
            not_p = st.text_area("Notas")
            if st.button("Guardar Parte"):
                tid = int(t_l[t_l['nombre']==t_s]['id'].values[0])
                oid = int(o_l[o_l['nombre']==o_s]['id'].values[0])
                c.execute("INSERT INTO partes (t_id, o_id, fecha, horas, notas) VALUES (?,?,?,?,?)", (tid, oid, f_p.strftime("%Y-%m-%d"), h_p, not_p))
                conn.commit(); st.success("Ok")
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("💰 Nuevo Gasto")
        if not o_l.empty:
            og_s = st.selectbox("Obra ", o_l['nombre'])
            cat = st.selectbox("Tipo", ["Dietas", "Gasolina", "Materiales", "Contenedor", "Otros"])
            desc_o = ""
            if cat == "Otros": desc_o = st.text_input("Especificar concepto")
            imp = st.number_input("Importe (€)", min_value=0.0)
            if st.button("Guardar Gasto"):
                oid = int(o_l[o_l['nombre']==og_s]['id'].values[0])
                c.execute("INSERT INTO gastos (o_id, tipo, importe, fecha, descripcion) VALUES (?,?,?,?,?)", (oid, cat, imp, datetime.now().strftime("%Y-%m-%d"), desc_o))
                conn.commit(); st.success("Gasto guardado")
        st.markdown('</div>', unsafe_allow_html=True)

# --- 3. CONFIGURACIÓN (Altas y Cierre de Obra) ---
elif choice == "⚙️ Configuración (Altas)":
    st.header("Configuración del Sistema")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Trabajador (DNI)")
        n_t = st.text_input("Nombre")
        d_t = st.text_input("DNI")
        if st.button("Añadir Personal"):
            c.execute("INSERT INTO trabajadores (nombre, dni) VALUES (?,?)", (n_t, d_t))
            conn.commit(); st.success("Añadido")
    with c2:
        st.subheader("Cierre de Obra")
        obras_a = pd.read_sql_query("SELECT id, nombre FROM obras WHERE estado != 'finalizada'", conn)
        o_cerrar = st.selectbox("Obra a finalizar", obras_a['nombre'] if not obras_a.empty else ["Vacío"])
        if st.button("🏁 Marcar Finalizada"):
            f_hoy = datetime.now().strftime("%Y-%m-%d")
            c.execute(f"UPDATE obras SET estado='finalizada', fecha_fin='{f_hoy}' WHERE nombre='{o_cerrar}'")
            conn.commit(); st.success("Obra finalizada con éxito")

    st.divider()
    with st.expander("➕ Crear Nueva Obra"):
        n_o = st.text_input("Nombre Proyecto")
        p_o = st.number_input("Presupuesto", min_value=0.0)
        if st.button("Crear"):
            c.execute("INSERT INTO obras (nombre, presupuesto, estado) VALUES (?,?,'en curso')", (n_o, p_o))
            conn.commit(); st.success("Creada")

# --- 4. ADMINISTRACIÓN ---
elif choice == "🛠️ Administración (Borrar)":
    st.header("Limpieza de Datos")
    df_o = pd.read_sql_query("SELECT id, nombre, estado FROM obras", conn)
    st.dataframe(df_o, use_container_width=True)
    id_del = st.number_input("ID a eliminar", min_value=0)
    if st.button("❌ Eliminar Obra"):
        c.execute(f"DELETE FROM obras WHERE id={id_del}")
        conn.commit(); st.rerun()
