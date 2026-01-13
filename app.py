import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
from datetime import datetime
from fpdf import FPDF

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gestión Ascensores - Naiara", layout="wide")

# --- CABECERA CON LOGOS ---
col_l1, col_l2 = st.columns(2)
with col_l1:
    st.image("https://ascensoresdadri.com/wp-content/uploads/2025/01/ascensores-dadir-logo.png", width=250)
with col_l2:
    st.image("https://agrascensores.com/wp-content/uploads/2025/10/Diseno-sin-titulo-24.png", width=250)

st.title("🏗️ Gestión de Obras y Rentabilidad")
st.divider()

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
menu = ["📊 Dashboard Mensual", "📝 Registrar Parte", "💰 Registrar Gastos", "⚙️ Configuración", "🛠️ Panel de Administración"]
choice = st.sidebar.radio("Menú", menu)

# --- PANEL DE ADMINISTRACIÓN (BORRAR) ---
if choice == "🛠️ Panel de Administración":
    st.header("Gestión de Registros")
    tab1, tab2 = st.tabs(["Eliminar Trabajadores", "Eliminar Obras"])
    
    with tab1:
        df_t = pd.read_sql_query("SELECT id, nombre, dni FROM trabajadores", conn)
        st.dataframe(df_t, use_container_width=True)
        id_t = st.number_input("ID del trabajador a eliminar", min_value=1, step=1)
        if st.button("Confirmar Eliminación Trabajador"):
            c.execute(f"DELETE FROM trabajadores WHERE id={id_t}")
            conn.commit()
            st.success("Trabajador eliminado.")
            st.rerun()

    with tab2:
        df_o = pd.read_sql_query("SELECT id, nombre, estado, presupuesto FROM obras", conn)
        st.dataframe(df_o, use_container_width=True)
        id_o = st.number_input("ID de la obra a eliminar", min_value=1, step=1)
        if st.button("Confirmar Eliminación Obra"):
            c.execute(f"DELETE FROM obras WHERE id={id_o}")
            conn.commit()
            st.success("Obra eliminada.")
            st.rerun()

# --- CONFIGURACIÓN ---
elif choice == "⚙️ Configuración":
    st.header("Altas")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Añadir Trabajador")
        t_nom = st.text_input("Nombre Completo")
        t_dni = st.text_input("DNI") # Cambio a DNI
        if st.button("Guardar"):
            c.execute("INSERT INTO trabajadores (nombre, dni) VALUES (?,?)", (t_nom, t_dni))
            conn.commit()
            st.success("Añadido")
    with c2:
        st.subheader("Nueva Obra")
        o_nom = st.text_input("Nombre Obra")
        o_pre = st.number_input("Presupuesto (€)", min_value=0.0)
        o_est = st.selectbox("Estado", ["no iniciada", "en curso", "bloqueada", "finalizada"])
        if st.button("Crear Obra"):
            c.execute("INSERT INTO obras (nombre, presupuesto, estado) VALUES (?,?,?)", (o_nom, o_pre, o_est))
            conn.commit()
            st.success("Obra Creada")

# --- GASTOS ---
elif choice == "💰 Registrar Gastos":
    st.header("Registro de Gastos")
    obs = pd.read_sql_query("SELECT * FROM obras", conn)
    if not obs.empty:
        with st.form("gastos"):
            o_sel = st.selectbox("Obra", obs['nombre'])
            tipo = st.selectbox("Tipo", ["Dietas", "Gasolina", "Materiales", "Contenedor", "Otros"])
            # Campo extra para "Otros"
            desc = ""
            if tipo == "Otros":
                desc = st.text_input("Especificar concepto de 'Otros'")
            monto = st.number_input("Importe (€)", min_value=0.0)
            fec = st.date_input("Fecha", datetime.now())
            if st.form_submit_button("Guardar Gasto"):
                oid = int(obs[obs['nombre']==o_sel]['id'].values[0])
                c.execute("INSERT INTO gastos (o_id, tipo, importe, fecha, descripcion) VALUES (?,?,?,?,?)", 
                          (oid, tipo, monto, fec.strftime("%Y-%m-%d"), desc))
                conn.commit()
                st.success("Gasto registrado")

# --- DASHBOARD E INFORMES ---
elif choice == "📊 Dashboard Mensual":
    st.header("Informes para Ricardo")
    
    # Filtro por mes
    mes_sel = st.selectbox("Mes", ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"])
    mes_num = str(["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"].index(mes_sel) + 1).zfill(2)
    
    df_obras = pd.read_sql_query("SELECT * FROM obras", conn)
    
    if not df_obras.empty:
        st.subheader(f"Resumen de {mes_sel}")
        
        # Gráfico de barras: Gastos vs Presupuesto
        nombres = []
        presus = []
        gastos = []
        
        for index, row in df_obras.iterrows():
            g_mes = pd.read_sql_query(f"SELECT SUM(importe) FROM gastos WHERE o_id={row['id']} AND strftime('%m', fecha)='{mes_num}'", conn).iloc[0,0] or 0
            nombres.append(row['nombre'])
            presus.append(row['presupuesto'])
            gastos.append(g_mes)

        fig = go.Figure(data=[
            go.Bar(name='Presupuesto Total', x=nombres, y=presus, marker_color='#1f77b4'),
            go.Bar(name=f'Gastos {mes_sel}', x=nombres, y=gastos, marker_color='#ef553b')
        ])
        fig.update_layout(barmode='group', title="Comparativa Económica por Obra")
        st.plotly_chart(fig, use_container_width=True)

        # Tabla de Rentabilidad
        st.subheader("Tabla de Rendimiento Mensual")
        informe_final = []
        for index, row in df_obras.iterrows():
            g_tot = pd.read_sql_query(f"SELECT SUM(importe) FROM gastos WHERE o_id={row['id']}", conn).iloc[0,0] or 0
            h_tot = pd.read_sql_query(f"SELECT SUM(horas) FROM partes WHERE o_id={row['id']}", conn).iloc[0,0] or 0
            rent = (row['presupuesto'] - g_tot) / h_tot if h_tot > 0 else 0
            informe_final.append({
                "Obra": row['nombre'],
                "Presupuesto": f"{row['presupuesto']}€",
                "Gastos Acum.": f"{g_tot}€",
                "Horas Tot.": h_tot,
                "Rentabilidad": f"{round(rent, 2)} €/h"
            })
        st.table(informe_final)

        # Generador de PDF "Bonito"
        if st.button("Generar Informe PDF para Ricardo"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, f"INFORME DE RENTABILIDAD - {mes_sel.upper()} 2026", ln=True, align='C')
            pdf.ln(10)
            
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(60, 10, "Obra", 1)
            pdf.cell(40, 10, "Presu.", 1)
            pdf.cell(40, 10, "Gastos", 1)
            pdf.cell(40, 10, "Rentab.", 1)
            pdf.ln()
            
            pdf.set_font("Arial", '', 10)
            for item in informe_final:
                pdf.cell(60, 10, item['Obra'][:25], 1)
                pdf.cell(40, 10, item['Presupuesto'], 1)
                pdf.cell(40, 10, item['Gastos Acum.'], 1)
                pdf.cell(40, 10, item['Rentabilidad'], 1)
                pdf.ln()
            
            pdf_data = pdf.output(dest='S')
            st.download_button("📥 Descargar PDF", pdf_data, f"Informe_{mes_sel}_Ricardo.pdf", "application/pdf")
