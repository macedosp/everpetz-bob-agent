# embed.py
# Ponto de entrada exclusivo para o modo de incorporação (iframe).
# Esta versão NÃO contém NENHUM código relacionado à barra lateral.

import streamlit as st
import os
from agent import EverpetzAgent
from embed_config import apply_embed_css, create_minimal_header

# --- Lógica para carregar a chave da API (idêntica ao app.py) ---
try:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
except (KeyError, FileNotFoundError):
    from dotenv import load_dotenv
    load_dotenv()

# --- Constantes ---
BOB_AVATAR_PATH = "assets/bob_avatar.jpg"

# --- Configuração da Página ---
# Deve ser a primeira chamada do Streamlit
st.set_page_config(
    page_title="Bob - Assistente Everpetz",
    page_icon="🐾",
    layout="centered",
    initial_sidebar_state="collapsed", # Será removida pelo CSS de qualquer forma
)
apply_embed_css()

# --- Funções da Interface ---

def initialize_session_state():
    """Inicializa as variáveis de sessão para o chat."""
    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "assistant",
            "content": "Olá! Sou o Bob, assistente virtual da Everpetz. Como posso ajudar você hoje? 🐾"
        }]
    if "agent" not in st.session_state:
        st.session_state.agent = EverpetzAgent()

def display_chat_history():
    """Exibe o histórico do chat na interface."""
    for message in st.session_state.messages:
        avatar = BOB_AVATAR_PATH if message["role"] == "assistant" else None
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

def handle_user_input():
    """Processa a entrada do usuário e obtém a resposta do agente."""
    if prompt := st.chat_input("Digite sua mensagem..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant", avatar=BOB_AVATAR_PATH):
            with st.spinner("O Bob está pensando..."):
                chat_history = st.session_state.messages[:-1]
                response = st.session_state.agent.get_response(prompt, chat_history)
                st.markdown(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})

def embed_mode_interface():
    """Renderiza a interface minimalista completa para o modo embed."""
    create_minimal_header(avatar_url="https://raw.githubusercontent.com/macedosp/everpetz-bob-agent/main/assets/bob_avatar.jpg")
    initialize_session_state()
    display_chat_history()
    handle_user_input()
    
    # Botão de reset
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Nova conversa", key="reset_embed", use_container_width=True):
            st.session_state.messages = [{
                "role": "assistant",
                "content": "Conversa reiniciada! Como posso ajudar você? 🐾"
            }]
            st.rerun()

# --- Execução Principal ---
if __name__ == "__main__":
    embed_mode_interface()