# app.py
# Versão unificada e limpa para deploy em qualquer ambiente.

import streamlit as st
import os
from agent import EverpetzAgent
import rag_manager

# Importa as funções do nosso novo arquivo de configuração de UI
from ui_config import is_embed_mode, apply_embed_css, create_minimal_header

# --- Detecção de Modo ---
# A detecção é feita uma única vez no início.
embed_mode = is_embed_mode()

# --- Configuração da Página ---
# A configuração da página é a primeira chamada do Streamlit.
# Usamos um if ternário para definir o layout de forma concisa.
st.set_page_config(
    page_title="Assistente Everpetz",
    page_icon="🐾",
    layout="centered" if embed_mode else "wide",
)

# --- Carregamento da Chave da API ---
try:
    # Para deploy em nuvem (lê dos secrets do Streamlit ou variáveis de ambiente)
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
except (KeyError, FileNotFoundError):
    # Para desenvolvimento local (lê do arquivo .env)
    from dotenv import load_dotenv
    load_dotenv()

# --- Constantes ---
BOB_AVATAR_PATH = "assets/bob_avatar.jpg"

# --- Inicialização de Sessão ---
def initialize_session_state():
    """Inicializa as variáveis de sessão necessárias."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
        if embed_mode:
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Olá! Sou o Bob, assistente virtual da Everpetz. Como posso ajudar?"
            })
    if "agent" not in st.session_state:
        st.session_state.agent = EverpetzAgent()

# --- Funções de Interface ---

def render_sidebar():
    """Renderiza a barra lateral de administração."""
    with st.sidebar:
        st.image(BOB_AVATAR_PATH, caption="Bob, seu assistente virtual")
        st.divider()
        st.header("Base de Conhecimento")
        
        uploaded_files = st.file_uploader(
            "Adicionar novos PDFs", type="pdf", accept_multiple_files=True
        )
        if uploaded_files:
            # Lógica para salvar arquivos...
            for uploaded_file in uploaded_files:
                file_path = os.path.join(rag_manager.KNOWLEDGE_BASE_DIR, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
            st.success(f"{len(uploaded_files)} arquivo(s) carregado(s)!")
        
        st.subheader("Arquivos Atuais")
        if not os.path.exists(rag_manager.KNOWLEDGE_BASE_DIR):
            os.makedirs(rag_manager.KNOWLEDGE_BASE_DIR)
        
        pdf_files = [f for f in os.listdir(rag_manager.KNOWLEDGE_BASE_DIR) if f.endswith(".pdf")]
        if not pdf_files:
            st.info("Nenhum arquivo na base de conhecimento.")
        else:
            for pdf_file in pdf_files:
                # Lógica para listar e deletar arquivos...
                col1, col2 = st.columns([0.8, 0.2])
                with col1: st.write(pdf_file)
                with col2:
                    if st.button("🗑️", key=f"delete_{pdf_file}"):
                        os.remove(os.path.join(rag_manager.KNOWLEDGE_BASE_DIR, pdf_file))
                        st.rerun()
        
        if st.button("Processar Base de Conhecimento"):
            with st.spinner("Processando..."):
                if rag_manager.process_knowledge_base():
                    st.success("Base de conhecimento atualizada!")
                    st.session_state.agent = EverpetzAgent()
                else:
                    st.warning("Nenhum arquivo para processar.")
        
        st.divider()
        st.header("Controles do Chat")
        if st.button("Reiniciar Conversa (Admin)"):
            st.session_state.messages = []
            st.toast("Conversa reiniciada!")
            st.rerun()

def render_chat_interface():
    """Renderiza a interface principal do chat (histórico e input)."""
    # Exibe o histórico de mensagens
    for message in st.session_state.messages:
        avatar = BOB_AVATAR_PATH if message["role"] == "assistant" else None
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])
    
    # Campo de input do usuário
    if prompt := st.chat_input("Como posso te ajudar?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        with st.chat_message("assistant", avatar=BOB_AVATAR_PATH):
            with st.spinner("O Bob está pensando..."):
                chat_history = st.session_state.messages[:-1]
                response = st.session_state.agent.get_response(prompt, chat_history)
                st.markdown(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})

# --- Execução Principal ---
if __name__ == "__main__":
    
    initialize_session_state()

    # A lógica principal agora é muito mais limpa:
    if embed_mode:
        # Modo embed: aplica CSS customizado, mostra um cabeçalho simples e o chat.
        apply_embed_css()
        create_minimal_header()
    else:
        # Modo normal: mostra o título principal e a barra lateral de admin.
        st.title("🐾 Painel de Administração - Agente Bob")
        st.write("Olá! Sou o Bob, seu assistente virtual. Estou aqui para ajudar com suas dúvidas.")
        render_sidebar()
    
    # A interface de chat é renderizada em ambos os modos.
    render_chat_interface()