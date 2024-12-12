import streamlit as st
import pandas as pd
from datetime import datetime
from storage import StorageHandler
import plotly.express as px
import os
import redis

# Conectar ao Redis
redis_client = redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=int(os.getenv('REDIS_PORT', 6380)), decode_responses=True)

# Função para salvar configurações no Redis
def save_to_redis(key, value):
    try:
        redis_client.set(key, value)
        st.success(f"Configuração {key} salva com sucesso!")
    except Exception as e:
        st.error(f"Erro ao salvar no Redis: {key} -> {e}")

# Função para buscar configurações no Redis
def get_from_redis(key, default=None):
    try:
        value = redis_client.get(key)
        return value if value is not None else default
    except Exception as e:
        st.error(f"Erro ao buscar no Redis: {key} -> {e}")
        return default

# Configuração da página
st.set_page_config(
    page_title="TranscreveZAP by Impacte AI",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Configuração do storage
storage = StorageHandler()

# Função para carregar configurações do Redis para o Streamlit
def load_settings():
    try:
        st.session_state.settings = {
            "GROQ_API_KEY": get_from_redis("GROQ_API_KEY", "default_key"),
            "BUSINESS_MESSAGE": get_from_redis("BUSINESS_MESSAGE", "*Impacte AI* Premium Services"),
            "PROCESS_GROUP_MESSAGES": get_from_redis("PROCESS_GROUP_MESSAGES", "false"),
            "PROCESS_SELF_MESSAGES": get_from_redis("PROCESS_SELF_MESSAGES", "true"),
        }
    except Exception as e:
        st.error(f"Erro ao carregar configurações do Redis: {e}")

# Carregar configurações na sessão, se necessário
if "settings" not in st.session_state:
    load_settings()

# Função para salvar configurações do Streamlit no Redis
def save_settings():
    try:
        save_to_redis("GROQ_API_KEY", st.session_state.groq_api_key)
        save_to_redis("BUSINESS_MESSAGE", st.session_state.business_message)
        save_to_redis("PROCESS_GROUP_MESSAGES", st.session_state.process_group_messages)
        save_to_redis("PROCESS_SELF_MESSAGES", st.session_state.process_self_messages)
        st.success("Configurações salvas com sucesso!")
    except Exception as e:
        st.error(f"Erro ao salvar configurações: {e}")

def show_logo():
    try:
        logo_path = os.path.join(os.path.dirname(__file__), "static", "fluxo.png")
        if os.path.exists(logo_path):
            st.image(logo_path, width=150)
        else:
            st.warning("Logo não encontrada.")
    except Exception as e:
        st.error(f"Erro ao carregar logo: {e}")

def show_footer():
    st.markdown(
        """
        <div class="footer">
            <p>Desenvolvido por <a href="https://impacte.ai" target="_blank">Impacte AI</a> | 
            Código fonte no <a href="https://github.com/impacte-ai/transcrevezap" target="_blank">GitHub</a></p>
        </div>
        """,
        unsafe_allow_html=True,
    )

def login_page():
    show_logo()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            st.markdown("<h2 style='text-align: center;'>Login</h2>", unsafe_allow_html=True)
            username = st.text_input('Usuário')
            password = st.text_input('Senha', type='password')
            if st.form_submit_button('Entrar', use_container_width=True):
                if username == os.getenv('MANAGER_USER') and password == os.getenv('MANAGER_PASSWORD'):
                    st.session_state.authenticated = True
                    st.experimental_rerun()
                else:
                    st.error('Credenciais inválidas')

def dashboard():
    show_logo()
    st.sidebar.markdown('<div class="sidebar-header">TranscreveZAP - Menu</div>', unsafe_allow_html=True)
    page = st.sidebar.radio(
        "Navegação",
        ["📊 Painel de Controle", "👥 Gerenciar Grupos", "🚫 Gerenciar Bloqueios", "⚙️ Configurações"]
    )
    if st.sidebar.button("Sair"):
        st.session_state.authenticated = False
        st.experimental_rerun()

    if page == "📊 Painel de Controle":
        show_statistics()
    elif page == "👥 Gerenciar Grupos":
        manage_groups()
    elif page == "🚫 Gerenciar Bloqueios":
        manage_blocks()
    elif page == "⚙️ Configurações":
        manage_settings()

def show_statistics():
    st.title("📊 Painel de Controle")
    try:
        stats = storage.get_statistics()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Áudios Processados", stats.get("total_processed", 0))
        with col2:
            last_processed = stats.get("last_processed", "Nunca")
            st.metric("Último Processamento", last_processed)
        with col3:
            total_groups = len(storage.get_allowed_groups())
            st.metric("Grupos Permitidos", total_groups)

        daily_data = stats["stats"]["daily_count"]
        if daily_data:
            df = pd.DataFrame(list(daily_data.items()), columns=['Data', 'Processamentos'])
            df['Data'] = pd.to_datetime(df['Data'])
            fig = px.line(df, x='Data', y='Processamentos', title='Processamentos por Dia')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Ainda não há dados de processamento disponíveis.")
    except Exception as e:
        st.error(f"Erro ao carregar estatísticas: {e}")

def manage_groups():
    st.title("👥 Gerenciar Grupos")
    st.subheader("Adicionar Grupo Permitido")
    col1, col2 = st.columns([3, 1])
    with col1:
        new_group = st.text_input("Número do Grupo", placeholder="Ex: 5521999999999")
    with col2:
        if st.button("Adicionar"):
            formatted_group = f"{new_group}@g.us"
            storage.add_allowed_group(formatted_group)
            st.success(f"Grupo {formatted_group} adicionado com sucesso!")
            st.experimental_rerun()

    st.subheader("Grupos Permitidos")
    allowed_groups = storage.get_allowed_groups()
    if allowed_groups:
        for group in allowed_groups:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.text(group)
            with col2:
                if st.button("Remover", key=f"remove_{group}"):
                    storage.remove_allowed_group(group)
                    st.success(f"Grupo {group} removido!")
                    st.experimental_rerun()
    else:
        st.info("Nenhum grupo permitido.")

def manage_blocks():
    st.title("🚫 Gerenciar Bloqueios")
    st.subheader("Bloquear Usuário")
    col1, col2 = st.columns([3, 1])
    with col1:
        new_user = st.text_input("Número do Usuário", placeholder="Ex: 5521999999999")
    with col2:
        if st.button("Bloquear"):
            formatted_user = f"{new_user}@s.whatsapp.net"
            storage.add_blocked_user(formatted_user)
            st.success(f"Usuário {formatted_user} bloqueado!")
            st.experimental_rerun()

    st.subheader("Usuários Bloqueados")
    blocked_users = storage.get_blocked_users()
    if blocked_users:
        for user in blocked_users:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.text(user)
            with col2:
                if st.button("Desbloquear", key=f"unblock_{user}"):
                    storage.remove_blocked_user(user)
                    st.success(f"Usuário {user} desbloqueado!")
                    st.experimental_rerun()
    else:
        st.info("Nenhum usuário bloqueado.")

def manage_settings():
    st.title("⚙️ Configurações")
    st.subheader("Configurações do Sistema")
    st.text_input("GROQ_API_KEY", value=st.session_state.settings["GROQ_API_KEY"], key="groq_api_key")
    st.text_input("Mensagem de Boas-Vindas", value=st.session_state.settings["BUSINESS_MESSAGE"], key="business_message")
    st.selectbox("Processar Mensagens em Grupos", options=["true", "false"], index=["true", "false"].index(st.session_state.settings["PROCESS_GROUP_MESSAGES"]), key="process_group_messages")
    st.selectbox("Processar Mensagens Próprias", options=["true", "false"], index=["true", "false"].index(st.session_state.settings["PROCESS_SELF_MESSAGES"]), key="process_self_messages")
    if st.button("Salvar Configurações"):
        save_settings()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if st.session_state.authenticated:
    dashboard()
else:
    login_page()

show_footer()