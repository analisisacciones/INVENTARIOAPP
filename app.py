import streamlit as st
import pandas as pd
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets

# =========================
# Configuración básica
# =========================
st.set_page_config(page_title="Parque de zapadores IIScc", layout="wide")

DATA_DIR = "data"
INV_FILE = os.path.join(DATA_DIR, "inventario.csv")
LOG_FILE = os.path.join(DATA_DIR, "movimientos.csv")
USERS_FILE = os.path.join(DATA_DIR, "users.csv")
SESSION_FILE = os.path.join(DATA_DIR, "session.csv")

EMAIL_ADDRESS = st.secrets["EMAIL_ADDRESS"]
EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]
BASE_URL = st.secrets["BASE_URL"]

DEFAULT_USERS = [
    {"usuario": "teniente", "password": "jefe1", "nombre": "Teniente", "correo": ""},
    {"usuario": "parquista", "password": "encargado1", "nombre": "Parquista", "correo": ""}
]

# =========================
# INVENTARIO BASE AGRUPADO POR CATEGORÍA
# =========================
# Inserta aquí el inventario real del PDF. Ejemplo de estructura:

INVENTARIO_BASE = [
    {"categoria": "LOTE 1 - CMAS", "material": "Perrillo", "cantidad_total": 1, "en_parque": 1, "fuera_parque": 0, "operativos": 1, "unidad": "ud"},
    {"categoria": "LOTE 1 - CMAS", "material": "Cuerda 6 m", "cantidad_total": 1, "en_parque": 1, "fuera_parque": 0, "operativos": 1, "unidad": "ud"},
    {"categoria": "LOTE 2 - MOVILIDAD/CONTRAMOVILIDAD 1", "material": "Caja arrastraminas", "cantidad_total": 1, "en_parque": 1, "fuera_parque": 0, "operativos": 1, "unidad": "ud"},
    # ... continúa con todos los materiales de los 19 lotes, mochilas BLAEX, MINAS, MANGUERA LIGERA ...
]

INV_COLS = ["categoria", "material", "cantidad_total", "en_parque", "fuera_parque", "operativos", "unidad"]
LOG_COLS = ["usuario", "categoria", "material", "cantidad", "accion", "hora", "observacion"]
USER_COLS = ["usuario", "password", "nombre", "correo"]

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
    if not os.path.exists(SESSION_FILE):
        pd.DataFrame(columns=["usuario", "token"]).to_csv(SESSION_FILE, index=False)

def load_inventory(): return pd.read_csv(INV_FILE)
def save_inventory(df): df.to_csv(INV_FILE, index=False)
def load_log(): return pd.read_csv(LOG_FILE)
def save_log(df): df.to_csv(LOG_FILE, index=False)
def load_users(): return pd.read_csv(USERS_FILE)
def save_users(df): df.to_csv(USERS_FILE, index=False)

def load_session():
    if os.path.exists(SESSION_FILE):
        return pd.read_csv(SESSION_FILE)
    return pd.DataFrame(columns=["usuario", "token"])

def save_session(usuario, token):
    df = pd.DataFrame([[usuario, token]], columns=["usuario", "token"])
    df.to_csv(SESSION_FILE, index=False)

def clear_session():
    if os.path.exists(SESSION_FILE):
        os.remove(SESSION_FILE)

init_data()

# =========================
# Envío de correos
# =========================
def send_recovery_email(to_email, token):
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = to_email
        msg["Subject"] = "Recuperación de contraseña - Parque de zapadores IIScc"
        reset_link = f"{BASE_URL}?reset={token}"
        body = f"Haz clic en el siguiente enlace para restablecer tu contraseña:\n\n{reset_link}"
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        return True
    except Exception as e:
        st.error(f"Error enviando correo: {e}")
        return False

# =========================
# Estado de sesión
# =========================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.name = None
if "reset_tokens" not in st.session_state:
    st.session_state.reset_tokens = {}

# Restaurar sesión persistente
if not st.session_state.logged_in:
    sess = load_session()
    if not sess.empty:
        usuario = sess.loc[0, "usuario"]
        users = load_users()
        if usuario in users["usuario"].values:
            st.session_state.logged_in = True
            st.session_state.user = usuario
            st.session_state.name = users.loc[users["usuario"] == usuario, "nombre"].values[0]
            st.session_state.token = sess.loc[0, "token"]

# =========================
# Pantalla de inicio
# =========================
if not st.session_state.logged_in:
    tab_login, tab_register, tab_reset = st.tabs(["🔑 Iniciar sesión", "📝 Registrarse", "🔄 Cambiar contraseña"])
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
                token = secrets.token_urlsafe(16)
                st.session_state.token = token
                save_session(usuario, token)
                st.success(f"Bienvenido {st.session_state.name}")
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")
    with tab_register:
        st.subheader("Registro de nuevo usuario")
        new_user = st.text_input("Nuevo usuario")
        new_pass = st.text_input("Nueva contraseña", type="password")
        new_name = st.text_input("Nombre completo")
        new_email = st.text_input("Correo electrónico")
        if st.button("Registrar", use_container_width=True):
            users = load_users()
            if new_user in users["usuario"].values:
                st.error("Ese usuario ya existe")
            elif new_email in users["correo"].values:
                st.error("Ese correo ya está registrado")
            elif any(x.strip() == "" for x in [new_user, new_pass, new_name, new_email]):
                st.error("Todos los campos son obligatorios")
            else:
                new_entry = pd.DataFrame([[new_user, new_pass, new_name, new_email]], columns=USER_COLS)
                users = pd.concat([users, new_entry], ignore_index=True)
                save_users(users)
                st.success("Usuario registrado con éxito. Ahora puedes iniciar sesión.")
    with tab_reset:
        st.subheader("Recuperar contraseña")
        reset_user = st.text_input("Usuario para recuperar contraseña")
        if st.button("Enviar correo de recuperación"):
            users = load_users()
            if reset_user in users["usuario"].values:
                correo = users.loc[users["usuario"] == reset_user, "correo"].values[0]
                if correo.strip() == "":
                    st.error("Ese usuario no tiene correo configurado.")
                else:
                    token = secrets.token_urlsafe(16)
                    st.session_state.reset_tokens[token] = reset_user
                    if send_recovery_email(correo, token):
                        st.success("Se ha enviado un correo con el enlace de recuperación.")
            else:
                st.error("Usuario no encontrado")
    params = st.query_params
    if "reset" in params:
        token = params["reset"]
        if token in st.session_state.reset_tokens:
            usuario_reset = st.session_state.reset_tokens[token]
            st.subheader("🔑 Restablecer contraseña")
            new_pass = st.text_input("Nueva contraseña", type="password")
            if st.button("Guardar nueva contraseña"):
                users = load_users()
                users.loc[users["usuario"] == usuario_reset, "password"] = new_pass
                save_users(users)
                del st.session_state.reset_tokens[token]
                st.success("Contraseña cambiada con éxito. Ya puedes iniciar sesión.")
        st.stop()
    st.stop()

# =========================
# App principal con categorías
# =========================
st.sidebar.success(f"Conectado como {st.session_state.name} ({st.session_state.user})")
if st.sidebar.button("Cerrar sesión"):
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.name = None
    clear_session()
    st.rerun()

inv = load_inventory()
categorias = sorted(inv["categoria"].unique())

st.title("📦 Inventario por categorías")
selected_cat = st.selectbox("Selecciona lote, mochila o caja", categorias)

if selected_cat:
    st.header(f"{selected_cat}")
    cat_inv = inv[inv["categoria"] == selected_cat].copy()
    cat_inv["inoperativos"] = cat_inv["cantidad_total"] - cat_inv["operativos"]
    st.dataframe(cat_inv, use_container_width=True)
    st.divider()
    tab1, tab2 = st.tabs(["🔁 Registrar movimiento", "🕓 Ver historial"])

    with tab1:
        st.subheader("Registrar movimiento")
        material = st.selectbox("Material", cat_inv["material"])
        cant = st.number_input("Cantidad", min_value=1, step=1, value=1)
        accion = st.radio("Acción", ["Sacar", "Devolver", "Marcar inoperativo"], horizontal=True)
        observ = st.text_input("Observación (opcional)", "")
        descontar = False
        if accion == "Marcar inoperativo":
            descontar = st.checkbox("Descontar también del parque")
        if st.button("Confirmar movimiento", type="primary"):
            idx = inv.index[(inv["categoria"] == selected_cat) & (inv["material"] == material)][0]
            if accion == "Sacar":
                if int(inv.loc[idx, "en_parque"]) >= cant:
                    inv.loc[idx, "en_parque"] -= cant
                    inv.loc[idx, "fuera_parque"] += cant
                    st.success(f"Sacaste {cant} {material}")
                else:
                    st.error("No hay suficiente stock en parque"); st.stop()
            elif accion == "Devolver":
                if int(inv.loc[idx, "fuera_parque"]) >= cant:
                    inv.loc[idx, "fuera_parque"] -= cant
                    inv.loc[idx, "en_parque"] += cant
                    st.success(f"Devolviste {cant} {material}")
                else:
                    st.error("No hay suficiente stock fuera del parque"); st.stop()
            elif accion == "Marcar inoperativo":
                if int(inv.loc[idx, "operativos"]) >= cant:
                    inv.loc[idx, "operativos"] -= cant
                    if descontar and int(inv.loc[idx, "en_parque"]) >= cant:
                        inv.loc[idx, "en_parque"] -= cant
                    st.success(f"Marcaste {cant} {material} como inoperativo")
                else:
                    st.error("No hay suficientes materiales operativos"); st.stop()
            save_inventory(inv)
            nuevo = pd.DataFrame([{
                "usuario": st.session_state.user,
                "categoria": selected_cat,
                "material": material,
                "cantidad": cant,
                "accion": accion,
                "hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "observacion": observ
            }], columns=LOG_COLS)
            log = pd.concat([load_log(), nuevo], ignore_index=True)
            save_log(log)

    with tab2:
        st.subheader("Historial de movimientos")
        log = load_log()
        log_cat = log[log["categoria"] == selected_cat]
        st.dataframe(log_cat.sort_values("hora", ascending=False), use_container_width=True)
