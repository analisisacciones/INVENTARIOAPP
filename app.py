import streamlit as st
import pandas as pd
import os
from datetime import datetime

# =========================
# Configuración básica
# =========================
st.set_page_config(page_title="Parque de zapadores IIScc", layout="wide")

DATA_DIR = "data"
INV_FILE = os.path.join(DATA_DIR, "inventario.csv")
LOG_FILE = os.path.join(DATA_DIR, "movimientos.csv")
USERS_FILE = os.path.join(DATA_DIR, "users.csv")

# Usuarios iniciales (solo se crean si no existe users.csv)
DEFAULT_USERS = [
    {"usuario": "teniente", "password": "jefe1", "nombre": "Teniente"},
    {"usuario": "parquista", "password": "encargado1", "nombre": "Parquista"}
]

INVENTARIO_BASE = [
    {"material": "Pala inglesa", "cantidad_total": 10, "en_parque": 10, "fuera_parque": 0, "unidad": "uds"},
    {"material": "Zapapico (mango corto)", "cantidad_total": 16, "en_parque": 16, "fuera_parque": 0, "unidad": "uds"},
    {"material": "Almádena", "cantidad_total": 4, "en_parque": 4, "fuera_parque": 0, "unidad": "uds"},
    {"material": "Motosierra Stihl", "cantidad_total": 1, "en_parque": 1, "fuera_parque": 0, "unidad": "ud"},
    {"material": "Tijera corta-alambrada zapador", "cantidad_total": 8, "en_parque": 8, "fuera_parque": 0, "unidad": "uds"},
]

INV_COLS = ["material", "cantidad_total", "en_parque", "fuera_parque", "unidad"]
LOG_COLS = ["usuario", "material", "cantidad", "accion", "hora", "observacion"]
USER_COLS = ["usuario", "password", "nombre"]

# =========================
# Funciones de datos
# =========================
def init_data():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(INV_FILE):
        pd.DataFrame(INVENTARIO_BASE, columns=INV_COLS).to_csv(INV_FILE, index=False)
    if not os.path.exists(LOG_FILE):
        pd.DataFrame(columns=LOG_COLS).to_csv(LOG_FILE, index=False)
    if not os.path.exists(USERS_FILE):
        pd.DataFrame(DEFAULT_USERS, columns=USER_COLS).to_csv(USERS_FILE, index=False)

def load_inventory():
    return pd.read_csv(INV_FILE)

def save_inventory(df):
    df.to_csv(INV_FILE, index=False)

def load_log():
    return pd.read_csv(LOG_FILE)

def save_log(df):
    df.to_csv(LOG_FILE, index=False)

def load_users():
    return pd.read_csv(USERS_FILE)

def save_users(df):
    df.to_csv(USERS_FILE, index=False)

# Inicializa almacenamiento
init_data()

# =========================
# Login / Registro
# =========================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.name = None

st.title("Parque de zapadores IIScc")

if not st.session_state.logged_in:
    tab_login, tab_register = st.tabs(["🔑 Iniciar sesión", "📝 Registrarse"])

    with tab_login:
        st.subheader("Inicia sesión")
        users = load_users()
        usuario = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        if st.button("Entrar", use_container_width=True):
            if ((users["usuario"] == usuario) & (users["password"] == password)).any():
                st.session_state.logged_in = True
                st.session_state.user = usuario
                st.session_state.name = users.loc[users["usuario"] == usuario, "nombre"].values[0]
                st.success(f"Bienvenido {st.session_state.name}")
            else:
                st.error("Usuario o contraseña incorrectos")

    with tab_register:
        st.subheader("Registro de nuevo usuario")
        new_user = st.text_input("Nuevo usuario")
        new_pass = st.text_input("Nueva contraseña", type="password")
        new_name = st.text_input("Nombre completo")
        if st.button("Registrar", use_container_width=True):
            users = load_users()
            if new_user in users["usuario"].values:
                st.error("Ese usuario ya existe")
            elif new_user.strip() == "" or new_pass.strip() == "" or new_name.strip() == "":
                st.error("Todos los campos son obligatorios")
            else:
                new_entry = pd.DataFrame([[new_user, new_pass, new_name]], columns=USER_COLS)
                users = pd.concat([users, new_entry], ignore_index=True)
                save_users(users)
                st.success("Usuario registrado con éxito. Ahora puedes iniciar sesión.")

    st.stop()

# =========================
# App principal
# =========================
st.sidebar.success(f"Conectado como {st.session_state.name} ({st.session_state.user})")
if st.sidebar.button("Cerrar sesión"):
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.name = None
    st.rerun()

inv = load_inventory()
log = load_log()

# Tabs (el historial solo visible a teniente y parquista)
if st.session_state.user in ["teniente", "parquista"]:
    tab_inv, tab_mov, tab_hist = st.tabs(["📋 Inventario", "🔁 Movimientos", "📝 Historial"])
else:
    tab_inv, tab_mov = st.tabs(["📋 Inventario", "🔁 Movimientos"])
    tab_hist = None

# -------- Inventario
with tab_inv:
    st.subheader("Estado actual")
    inv_view = inv.copy()
    inv_view["disponible"] = inv_view["en_parque"]
    st.dataframe(inv_view, use_container_width=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total de materiales", len(inv_view))
    with c2:
        st.metric("Unidades en parque", int(inv_view["en_parque"].sum()))
    with c3:
        st.metric("Unidades fuera de parque", int(inv_view["fuera_parque"].sum()))

# -------- Movimientos
with tab_mov:
    st.subheader("Registrar movimiento")
    material = st.selectbox("Material", inv["material"])
    cant = st.number_input("Cantidad", min_value=1, step=1, value=1)
    accion = st.radio("Acción", ["Sacar", "Devolver"], horizontal=True)
    observ = st.text_input("Observación (opcional)", "")

    if st.button("Confirmar movimiento", type="primary"):
        idx = inv.index[inv["material"] == material][0]
        if accion == "Sacar":
            if int(inv.loc[idx, "en_parque"]) >= cant:
                inv.loc[idx, "en_parque"] -= int(cant)
                inv.loc[idx, "fuera_parque"] += int(cant)
                st.success(f"Sacaste {cant} {material}")
            else:
                st.error("No hay suficiente stock en parque")
                st.stop()
        else:  # Devolver
            if int(inv.loc[idx, "fuera_parque"]) >= cant:
                inv.loc[idx, "fuera_parque"] -= int(cant)
                inv.loc[idx, "en_parque"] += int(cant)
                st.success(f"Devolviste {cant} {material}")
            else:
                st.error("No hay suficiente stock fuera del parque")
                st.stop()

        # Guarda inventario y log
        save_inventory(inv)
        nuevo = pd.DataFrame([{
            "usuario": st.session_state.user,
            "material": material,
            "cantidad": int(cant),
            "accion": accion,
            "hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "observacion": observ
        }], columns=LOG_COLS)
        log = pd.concat([load_log(), nuevo], ignore_index=True)
        save_log(log)

# -------- Historial (solo jefes)
if tab_hist is not None:
    with tab_hist:
        st.subheader("Historial de movimientos")
        colf1, colf2, colf3 = st.columns(3)
        with colf1:
            f_user = st.selectbox("Filtrar por usuario", ["(Todos)"] + log["usuario"].unique().tolist())
        with colf2:
            f_mat = st.selectbox("Filtrar por material", ["(Todos)"] + sorted(inv["material"].unique().tolist()))
        with colf3:
            f_acc = st.selectbox("Filtrar por acción", ["(Todas)", "Sacar", "Devolver"])

        log_view = load_log().copy()
        if f_user != "(Todos)":
            log_view = log_view[log_view["usuario"] == f_user]
        if f_mat != "(Todos)":
            log_view = log_view[log_view["material"] == f_mat]
        if f_acc != "(Todas)":
            log_view = log_view[log_view["accion"] == f_acc]

        st.dataframe(log_view.sort_values("hora", ascending=False), use_container_width=True)
