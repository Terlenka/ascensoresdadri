import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestión Ascensores - Naiara", layout="wide")

# --- ESTILOS Y LOGOS ---
def mostrar_cabecera():
    col_logo1, col_logo2 = st.columns([1, 1])
    with col_logo1:
        # Logo 1
        st.image("https://ascensoresdadri.com/wp-content/uploads/2025/01/ascensores-dadir-logo.png", width=250)
    with col_logo2:
        # Logo 2
        st.image("https://agrascensores.com/wp-content/uploads/2025/10/Diseno-sin-titulo-24.png", width=250)
    st.title("🏗️ Sistema de Control de Obras y Rentabilidad")
    st.divider()

# --- CONEXIÓN BASE DE DATOS ---
conn = sqlite3.connect('datos_gestion.db', check_same_thread=False)
c = conn.cursor()

def crear_tablas():
    # Tabla de Obras con los 4 estados
    c.execute('''CREATE TABLE IF NOT EXISTS obras 
                 (id INTEGER PRIMARY KEY, nombre TEXT, presupuesto REAL, estado TEXT, contratista TEXT)''')
    # Tabla de Trabajadores y sus funciones
    c.execute('''CREATE TABLE IF NOT EXISTS trabajadores 
                 (id INTEGER PRIMARY KEY, nombre TEXT, funcion TEXT)''')
    # Tabla de Partes (Trabajos diarios)
    c.execute('''CREATE TABLE IF NOT EXISTS partes 
                 (id INTEGER PRIMARY KEY, trabajador_id INTEGER, obra_id INTEGER, fecha TEXT, horas REAL, notas TEXT)''')
    # Tabla de Gastos
    c.execute('''CREATE TABLE IF NOT EXISTS gastos 
                 (id INTEGER PRIMARY KEY, obra_id INTEGER, tipo TEXT, importe REAL, fecha TEXT)''')
    conn.commit()

crear_tablas()

# --- AUTENTICACIÓN SIMPLE PARA NAIARA ---
def check_password():
    if "password_correct" not in st.session_state:
        st.sidebar.title("🔐 Acceso Privado")
        password = st.sidebar.text_input("Introduce la contraseña", type="password")
        if st.sidebar.button("Entrar"):
            # CAMBIA 'admin2026' por la contraseña que tú quieras
            if password == "admin2026": 
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.sidebar.error("❌ Contraseña incorrecta")
        return False
    return True

# --- LÓGICA DE LA APLICACIÓN ---
if check_password():
    mostrar_cabecera()
    
    menu = ["📈 Dashboard y Rentabilidad", "📝 Registrar Parte Diario", "💰 Registrar Gastos", "⚙️ Configuración (Obras/Personal)"]
    choice = st.sidebar.radio("Navegación", menu)

    # --- SECCIÓN: CONFIGURACIÓN ---
    if choice == "⚙️ Configuración (Obras/Personal)":
        st.header("Gestión de Obras y Trabajadores")
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Añadir Trabajador")
            t_nombre = st.text_input("Nombre del trabajador")
            t_funcion = st.text_input("Función (Oficial, Peón, etc.)")
            if st.button("Guardar Trabajador"):
                c.execute("INSERT INTO trabajadores (nombre, funcion) VALUES (?,?)", (t_nombre, t_funcion))
                conn.commit()
                st.success(f"Empleado {t_nombre} registrado.")

        with col2:
            st.subheader("Añadir Obra")
            o_nombre = st.text_input("Nombre de la Obra")
            o_presu = st.number_input("Presupuesto (€)", min_value=0.0)
            o_contra = st.text_input("Contratista (ej: OTIS, SHINDLER)")
            o_estado = st.selectbox("Estado inicial", ["no iniciada", "en curso", "bloqueada", "finalizada"])
            if st.button("Crear Obra"):
                c.execute("INSERT INTO obras (nombre, presupuesto, estado, contratista) VALUES (?,?,?,?)", 
                          (o_nombre, o_presu, o_estado, o_contra))
                conn.commit()
                st.success(f"Obra {o_nombre} registrada.")

    # --- SECCIÓN: REGISTRO DE PARTES ---
    elif choice == "📝 Registrar Parte Diario":
        st.header("Entrada de Trabajo")
        df_trab = pd.read_sql_query("SELECT * FROM trabajadores", conn)
        df_obras = pd.read_sql_query("SELECT * FROM obras WHERE estado='en curso'", conn)
        
        if not df_trab.empty and not df_obras.empty:
            with st.form("form_partes"):
                t_sel = st.selectbox("Trabajador", df_trab['nombre'])
                o_sel = st.selectbox("Obra", df_obras['nombre'])
                fecha = st.date_input("Fecha", datetime.now())
                
                # Lógica de horas: L-J 8h, V 6h
                sug_horas = 6.0 if fecha.weekday() == 4 else 8.0
                horas = st.number_input("Horas dedicadas (puedes repartir el día en varias obras)", value=sug_horas, step=0.5)
                notas = st.text_area("Descripción del trabajo realizado")
                
                if st.form_submit_button("Guardar Parte"):
                    tid = int(df_trab[df_trab['nombre'] == t_sel]['id'].values[0])
                    oid = int(df_obras[df_obras['nombre'] == o_sel]['id'].values[0])
                    c.execute("INSERT INTO partes (trabajador_id, obra_id, fecha, horas, notas) VALUES (?,?,?,?,?)",
                              (tid, oid, fecha.strftime("%Y-%m-%d"), horas, notas))
                    conn.commit()
                    st.success("El parte ha sido guardado.")
        else:
            st.warning("Asegúrate de tener trabajadores y obras 'en curso' creados.")

    # --- SECCIÓN: REGISTRO DE GASTOS ---
    elif choice == "💰 Registrar Gastos":
        st.header("Gastos de Obra")
        df_obras_g = pd.read_sql_query("SELECT * FROM obras", conn)
        
        if not df_obras_g.empty:
            with st.form("form_gastos"):
                o_sel_g = st.selectbox("Obra", df_obras_g['nombre'])
                # Categorías de gastos
                tipo_g = st.selectbox("Tipo de Gasto", ["Dietas", "Gasolina", "Materiales", "Contenedor", "Otros"])
                importe = st.number_input("Importe (€)", min_value=0.0)
                fecha_g = st.date_input("Fecha Gasto", datetime.now())
                
                if st.form_submit_button("Guardar Gasto"):
                    oid_g = int(df_obras_g[df_obras_g['nombre'] == o_sel_g]['id'].values[0])
                    c.execute("INSERT INTO gastos (obra_id, tipo, importe, fecha) VALUES (?,?,?,?)",
                              (oid_g, tipo_g, importe, fecha_g.strftime("%Y-%m-%d")))
                    conn.commit()
                    st.success("Gasto registrado.")

    # --- SECCIÓN: DASHBOARD ---
    elif choice == "📈 Dashboard y Rentabilidad":
        st.header("Resumen para Ricardo")
        obras_inf = pd.read_sql_query("SELECT * FROM obras", conn)
        
        if not obras_inf.empty:
            obra_sel = st.selectbox("Ver informe de:", obras_inf['nombre'])
            o_row = obras_inf[obras_inf['nombre'] == obra_sel].iloc[0]
            oid, presu = int(o_row['id']), o_row['presupuesto']
            
            # Cálculos según audio
            g_tot = pd.read_sql_query(f"SELECT SUM(importe) FROM gastos WHERE obra_id={oid}", conn).iloc[0,0] or 0
            h_tot = pd.read_sql_query(f"SELECT SUM(horas) FROM partes WHERE obra_id={oid}", conn).iloc[0,0] or 0
            
            rentabilidad = (presu - g_tot) / h_tot if h_tot > 0 else 0
            
            st.subheader(f"Rentabilidad: {round(rentabilidad, 2)} €/h")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Presupuesto", f"{presu} €")
            c2.metric("Total Gastos", f"{g_tot} €")
            c3.metric("Horas Totales", f"{h_tot} h")
            
            st.divider()
            st.write("### Detalle de partes de trabajo")
            detalle_p = pd.read_sql_query(f'''
                SELECT t.nombre as Empleado, p.fecha, p.horas, p.notas 
                FROM partes p JOIN trabajadores t ON p.trabajador_id = t.id 
                WHERE p.obra_id={oid} ORDER BY p.fecha DESC''', conn)
            st.dataframe(detalle_p, use_container_width=True)
            
            # Botón para descargar a Excel (CSV)
            csv = detalle_p.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar Datos para Imprimir (CSV)", csv, f"Informe_{obra_sel}.csv", "text/csv")
