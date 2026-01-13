import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
from datetime import datetime
from fpdf import FPDF

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gestión Ascensores - Naiara", layout="wide")

# --- CABECERA CON LOGOS ---
def mostrar_logos():
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        st.image("https://ascensoresdadri.com/wp-content/uploads/2025/01/ascensores-dadir-logo.png", width=250)
    with col_l2:
        st.image("https://agrascensores.com/wp-content/uploads/2025/10/Diseno-sin-titulo-24.png", width=250)

# --- CONEXIÓN DB ---
conn = sqlite3.connect('obras_datos.db', check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute('CREATE TABLE IF NOT EXISTS obras (id INTEGER PRIMARY KEY, nombre TEXT, presupuesto REAL, estado TEXT, contratista TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS trabajadores (id INTEGER PRIMARY KEY, nombre TEXT, dni TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS partes (id INTEGER PRIMARY KEY, t_id INTEGER, o_id INTEGER, fecha TEXT, horas REAL, notas TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS gastos (id INTEGER PRIMARY KEY, o_id INTEGER, tipo TEXT, importe REAL, fecha TEXT, descripcion TEXT)')
    conn.commit()

init_db()

# --- NAVEGACIÓN ---
mostrar_logos()
menu = ["📊 Dashboard Mensual (Ricardo)", "📝 Registrar Parte", "💰 Registrar Gastos", "⚙️ Configuración", "🛠️ Panel de Administración"]
choice = st.sidebar.radio("Menú de Naiara", menu)

# --- PANEL DE ADMINISTRACIÓN (BORRAR) ---
if choice == "🛠️ Panel de Administración":
    st.header("Administración de Datos")
    t1, t2 = st.tabs(["Trabajadores", "Obras"])
    with t1:
        st.write("Lista de Trabajadores")
        df_t = pd.read_sql_query("SELECT id, nombre, dni FROM trabajadores", conn)
        st.dataframe(df_t, use_container_width=True)
        id_eliminar_t = st.number_input("ID Trabajador a eliminar", min_value=0, step=1)
        if st.button("Eliminar Trabajador"):
            c.execute(f"DELETE FROM trabajadores WHERE id={id_eliminar_t}")
            conn.commit()
            st.rerun()
    with t2:
        st.write("Lista de Obras")
        df_o = pd.read_sql_query("SELECT id, nombre, estado FROM obras", conn)
        st.dataframe(df_o, use_container_width=True)
        id_eliminar_o = st.number_input("ID Obra a eliminar", min_value=0, step=1)
        if st.button("Eliminar Obra"):
            c.execute(f"DELETE FROM obras WHERE id={id_eliminar_o}")
            conn.commit()
            st.rerun()

# --- CONFIGURACIÓN (ALTAS) ---
elif choice == "⚙️ Configuración":
    st.header("Altas de Sistema")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Añadir Trabajador")
        t_nom = st.text_input("Nombre Completo")
        t_dni = st.text_input("DNI del trabajador")
        if st.button("Guardar Trabajador"):
            c.execute("INSERT INTO trabajadores (nombre, dni) VALUES (?,?)", (t_nom, t_dni))
            conn.commit()
            st.success("Guardado")
    with c2:
        st.subheader("Nueva Obra")
        o_nom = st.text_input("Nombre de la Obra")
        o_pre = st.number_input("Presupuesto (€)", min_value=0.0)
        o_est = st.selectbox("Estado", ["no iniciada", "en curso", "bloqueada", "finalizada"])
        if st.button("Crear Obra"):
            c.execute("INSERT INTO obras (nombre, presupuesto, estado) VALUES (?,?,?)", (o_nom, o_pre, o_est))
            conn.commit()
            st.success("Creada")

# --- REGISTRO DE GASTOS ---
elif choice == "💰 Registrar Gastos":
    st.header("Gastos de Obra")
    obs = pd.read_sql_query("SELECT * FROM obras", conn)
    if not obs.empty:
        with st.form("gastos_form"):
            o_sel = st.selectbox("Seleccionar Obra", obs['nombre'])
            tipo = st.selectbox("Concepto", ["Dietas", "Gasolina", "Materiales", "Contenedor", "Otros"])
            desc = ""
            if tipo == "Otros":
                desc = st.text_input("Especificar concepto de gasto")
            monto = st.number_input("Importe (€)", min_value=0.0)
            fec = st.date_input("Fecha", datetime.now())
            if st.form_submit_button("Guardar Gasto"):
                oid = int(obs[obs['nombre']==o_sel]['id'].values[0])
                c.execute("INSERT INTO gastos (o_id, tipo, importe, fecha, descripcion) VALUES (?,?,?,?,?)", 
                          (oid, tipo, monto, fec.strftime("%Y-%m-%d"), desc))
                conn.commit()
                st.success("Gasto registrado")

# --- REGISTRO DE PARTES ---
elif choice == "📝 Registrar Parte":
    st.header("Partes de Trabajo Diarios")
    tbs = pd.read_sql_query("SELECT * FROM trabajadores", conn)
    obs = pd.read_sql_query("SELECT * FROM obras WHERE estado='en curso'", conn)
    if not tbs.empty and not obs.empty:
        with st.form("partes_form"):
            t_sel = st.selectbox("Trabajador", tbs['nombre'])
            o_sel = st.selectbox("Obra", obs['nombre'])
            fec = st.date_input("Fecha", datetime.now())
            # Sugerencia 8h lun-jue, 6h vie
            sug = 6.0 if fec.weekday() == 4 else 8.0
            hrs = st.number_input("Horas dedicadas", value=sug, step=0.5)
            notas = st.text_area("Notas / Tareas")
            if st.form_submit_button("Registrar Parte"):
                tid = int(tbs[tbs['nombre']==t_sel]['id'].values[0])
                oid = int(obs[obs['nombre']==o_sel]['id'].values[0])
                c.execute("INSERT INTO partes (t_id, o_id, fecha, horas, notas) VALUES (?,?,?,?,?)", 
                          (tid, oid, fec.strftime("%Y-%m-%d"), hrs, notas))
                conn.commit()
                st.success("Parte guardado")

# --- DASHBOARD MENSUAL GLOBAL ---
elif choice == "📊 Dashboard Mensual (Ricardo)":
    st.header("Informe Global de Rentabilidad Mensual")
    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    mes_sel = st.selectbox("Ver informe del mes:", meses)
    mes_idx = str(meses.index(mes_sel) + 1).zfill(2)
    
    df_obras = pd.read_sql_query("SELECT * FROM obras", conn)
    if not df_obras.empty:
        # Gráfico Comparativo de Gastos
        stats = []
        for i, row in df_obras.iterrows():
            g_mes = pd.read_sql_query(f"SELECT SUM(importe) FROM gastos WHERE o_id={row['id']} AND strftime('%m', fecha)='{mes_idx}'", conn).iloc[0,0] or 0
            h_mes = pd.read_sql_query(f"SELECT SUM(horas) FROM partes WHERE o_id={row['id']} AND strftime('%m', fecha)='{mes_idx}'", conn).iloc[0,0] or 0
            # Rentabilidad global
            g_total_obra = pd.read_sql_query(f"SELECT SUM(importe) FROM gastos WHERE o_id={row['id']}", conn).iloc[0,0] or 0
            h_total_obra = pd.read_sql_query(f"SELECT SUM(horas) FROM partes WHERE o_id={row['id']}", conn).iloc[0,0] or 0
            rent = (row['presupuesto'] - g_total_obra) / h_total_obra if h_total_obra > 0 else 0
            
            stats.append({
                "Obra": row['nombre'],
                "Presupuesto": row['presupuesto'],
                "Gastos Mes": g_mes,
                "Horas Mes": h_mes,
                "Rentabilidad Global": round(rent, 2)
            })
        
        df_stats = pd.DataFrame(stats)
        
        # Gráfico
        fig = go.Figure(data=[
            go.Bar(name='Presupuesto', x=df_stats['Obra'], y=df_stats['Presupuesto'], marker_color='#1f77b4'),
            go.Bar(name='Gastos Mes', x=df_stats['Obra'], y=df_stats['Gastos Mes'], marker_color='#ef553b')
        ])
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Resumen Económico")
        st.table(df_stats)

        # GENERADOR PDF GLOBAL
        if st.button("Generar Informe PDF para Ricardo"):
            pdf = FPDF()
            pdf.add_page()
            # Logos en PDF
            pdf.image("https://ascensoresdadri.com/wp-content/uploads/2025/01/ascensores-dadir-logo.png", 10, 8, 50)
            pdf.image("https://agrascensores.com/wp-content/uploads/2025/10/Diseno-sin-titulo-24.png", 150, 8, 50)
            pdf.ln(30)
            
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(190, 10, f"INFORME MENSUAL - {mes_sel.upper()} 2026", ln=True, align='C')
            pdf.ln(10)
            
            pdf.set_font("Arial", 'B', 10)
            pdf.cell(60, 10, "Obra", 1)
            pdf.cell(30, 10, "Presu.", 1)
            pdf.cell(30, 10, "Gastos Mes", 1)
            pdf.cell(30, 10, "Horas Mes", 1)
            pdf.cell(40, 10, "Rentab. (EUR/h)", 1)
            pdf.ln()
            
            pdf.set_font("Arial", '', 9)
            for s in stats:
                pdf.cell(60, 10, s['Obra'][:25], 1)
                pdf.cell(30, 10, f"{s['Presupuesto']}e", 1)
                pdf.cell(30, 10, f"{s['Gastos Mes']}e", 1)
                pdf.cell(30, 10, f"{s['Horas Mes']}h", 1)
                pdf.cell(40, 10, f"{s['Rentabilidad Global']}", 1)
                pdf.ln()
            
            pdf_data = pdf.output(dest='S')
            st.download_button("📥 Descargar PDF Global", pdf_data, f"Informe_Mensual_{mes_sel}.pdf", "application/pdf")
