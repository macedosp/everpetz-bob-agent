# app.py
# Arquivo principal da aplicação Streamlit com suporte a embedding seguro

import streamlit as st
import os
from agent import EverpetzAgent
import rag_manager
from embed_config import configure_embed_mode, create_minimal_header, apply_embed_css

# 1) Detecta embed ANTES de qualquer UI
embed_mode = configure_embed_mode()

# 2) set_page_config deve ser a PRIMEIRA chamada de UI
if embed_mode:
    st.set_page_config(
        page_title="Bob - Assistente Everpetz",
        page_icon="🐾",
        layout="centered",
        initial_sidebar_state="collapsed",
        menu_items={  # esconde itens do menu no embed
            "Get Help": None,
            "Report a Bug": None,
            "About": None,
        },
    )
    # 3) CSS para remover sidebar e '>>'
    apply_embed_css()
else:
    st.set_page_config(
        page_title="Everpetz - Assistente Bob",
        page_icon="🐾",
        layout="wide",
        initial_sidebar_state="auto",
    )

# --- Lógica para carregar a chave da API ---
try:
    # Para o deploy no Streamlit Community Cloud
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
except (KeyError, FileNotFoundError):
    # Para o desenvolvimento local
    from dotenv import load_dotenv
    load_dotenv()

# --- Constantes ---
BOB_AVATAR_PATH = "assets/bob_avatar.jpg"

# --- Funções da Interface ---

def setup_page():
    """Configura o título e a descrição para a visualização principal."""
    if not embed_mode:
        st.title("🐾 Assistente Virtual Bob da Everpetz")
        st.write("Olá! Sou o Bob, seu assistente virtual. Estou aqui para ajudar com suas dúvidas.")
    # Em modo embed, o header é criado pela função create_minimal_header()

def initialize_session_state():
    """Inicializa variáveis na sessão do Streamlit."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
        # Mensagem inicial apenas em modo embed
        if embed_mode:
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Olá! Sou o Bob, assistente virtual da Everpetz. Como posso ajudar você hoje? 🐾"
            })
    if "agent" not in st.session_state:
        st.session_state.agent = EverpetzAgent()
    if "embed_mode" not in st.session_state:
        st.session_state.embed_mode = embed_mode

def display_chat_history():
    """Exibe o histórico do chat na interface."""
    for message in st.session_state.messages:
        avatar = BOB_AVATAR_PATH if message["role"] == "assistant" else None
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

def handle_user_input():
    """Processa a entrada do usuário e obtém a resposta do agente."""
    prompt_text = "Digite sua mensagem..." if embed_mode else "Como posso te ajudar hoje?"
    
    if prompt := st.chat_input(prompt_text):
        # Adiciona mensagem do usuário
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Gera e exibe resposta do assistente
        with st.chat_message("assistant", avatar=BOB_AVATAR_PATH):
            with st.spinner("O Bob está pensando..."):
                chat_history = st.session_state.messages[:-1]
                response = st.session_state.agent.get_response(prompt, chat_history)
                st.markdown(response)
        
        # Adiciona resposta ao histórico
        st.session_state.messages.append({"role": "assistant", "content": response})

def manage_knowledge_base_sidebar():
    """Cria e gerencia a barra lateral de administração (apenas modo normal)."""
    with st.sidebar:
        st.image(BOB_AVATAR_PATH, caption="Bob, seu assistente virtual")
        st.divider()
        st.header("Base de Conhecimento")
        
        # Upload de arquivos
        uploaded_files = st.file_uploader(
            "Adicionar novos PDFs", 
            type="pdf", 
            accept_multiple_files=True
        )
        
        if uploaded_files:
            for uploaded_file in uploaded_files:
                file_path = os.path.join(rag_manager.KNOWLEDGE_BASE_DIR, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
            st.success(f"{len(uploaded_files)} arquivo(s) carregado(s)!")
        
        # Listar arquivos existentes
        st.subheader("Arquivos Atuais")
        if not os.path.exists(rag_manager.KNOWLEDGE_BASE_DIR):
            os.makedirs(rag_manager.KNOWLEDGE_BASE_DIR)
        
        pdf_files = [f for f in os.listdir(rag_manager.KNOWLEDGE_BASE_DIR) if f.endswith(".pdf")]
        
        if not pdf_files:
            st.info("Nenhum arquivo na base de conhecimento.")
        else:
            for pdf_file in pdf_files:
                col1, col2 = st.columns([0.8, 0.2])
                with col1:
                    st.write(pdf_file)
                with col2:
                    if st.button("🗑️", key=f"delete_{pdf_file}"):
                        os.remove(os.path.join(rag_manager.KNOWLEDGE_BASE_DIR, pdf_file))
                        st.rerun()
        
        # Processar base de conhecimento
        if st.button("Processar Base de Conhecimento"):
            with st.spinner("Processando arquivos..."):
                if rag_manager.process_knowledge_base():
                    st.success("Base de conhecimento processada e atualizada!")
                    st.session_state.agent = EverpetzAgent()
                else:
                    st.warning("Nenhum arquivo para processar.")
        
        st.divider()
        st.header("Controles do Chat")
        
        # Botão de reiniciar
        if st.button("Reiniciar Conversa"):
            st.session_state.messages = []
            st.toast("Conversa reiniciada!")
            st.rerun()

def embed_mode_interface():
    """Interface específica para modo embed - apenas chat."""
    create_minimal_header()
    initialize_session_state()
    display_chat_history()
    handle_user_input()
    
    # Botão de reset discreto no rodapé
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Nova conversa", key="reset_embed", use_container_width=True):
            st.session_state.messages = [{
                "role": "assistant",
                "content": "Conversa reiniciada! Como posso ajudar você? 🐾"
            }]
            st.rerun()

def normal_mode_interface():
    """Interface completa com todas as funcionalidades."""
    setup_page()
    initialize_session_state()
    manage_knowledge_base_sidebar()
    display_chat_history()
    handle_user_input()

# --- Execução Principal ---

def main():
    """Função principal que roda a aplicação."""
    if embed_mode:
        # Modo embed: interface minimalista, sem sidebar
        embed_mode_interface()
    else:
        # Modo normal: interface completa com sidebar
        normal_mode_interface()

# --- Ponto de entrada ---
if __name__ == "__main__":
    main()