# app.py
# Arquivo principal da aplicação Streamlit.
# Cria a interface de usuário, gerencia o estado da conversa e interage com o agente.

import streamlit as st
import os
# A lógica para carregar a chave da API depende do ambiente (local vs. deploy)
try:
    # Tenta carregar dos segredos do Streamlit (para deploy)
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
except (KeyError, FileNotFoundError):
    # Se falhar, tenta carregar do arquivo .env (para desenvolvimento local)
    from dotenv import load_dotenv
    load_dotenv()

from agent import EverpetzAgent
import rag_manager

# --- Constantes ---
BOB_AVATAR_PATH = "assets/bob_avatar.jpg"

# --- Funções Auxiliares ---

def setup_page():
    """Configura a página do Streamlit."""
    st.set_page_config(page_title="Everpetz - Assistente Bob", page_icon=BOB_AVATAR_PATH)
    st.title("🐾 Assistente Virtual Bob da Everpetz")
    st.write("Olá! Sou o Bob, seu assistente virtual. Estou aqui para ajudar com suas dúvidas sobre a Everpetz.")

def initialize_session_state():
    """Inicializa o estado da sessão para armazenar o histórico do chat e o agente."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "agent" not in st.session_state:
        st.session_state.agent = EverpetzAgent()

def display_chat_history():
    """Exibe as mensagens do histórico do chat na interface."""
    for message in st.session_state.messages:
        # Define o avatar a ser usado com base no 'role' da mensagem
        avatar = BOB_AVATAR_PATH if message["role"] == "assistant" else None
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

def handle_user_input():
    """Captura e processa a entrada do usuário."""
    if prompt := st.chat_input("Como posso te ajudar hoje?"):
        # Adiciona a mensagem do usuário ao histórico e exibe
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Gera e exibe a resposta do assistente
        with st.chat_message("assistant", avatar=BOB_AVATAR_PATH):
            with st.spinner("O Bob está pensando..."):
                # Obtém o histórico de chat para passar ao agente
                chat_history = st.session_state.messages[:-1] # Exclui a última mensagem do usuário
                
                # Chama o agente para obter a resposta
                response = st.session_state.agent.get_response(prompt, chat_history)
                
                st.markdown(response)
        
        # Adiciona a resposta do assistente ao histórico
        st.session_state.messages.append({"role": "assistant", "content": response})

def manage_knowledge_base_sidebar():
    """Cria e gerencia a barra lateral para upload e exclusão de PDFs."""
    with st.sidebar:
        # Adiciona a imagem do avatar do Bob
        st.image(BOB_AVATAR_PATH, caption="Bob, seu assistente virtual")
        st.divider()

        st.header("Base de Conhecimento")
        st.write("Gerencie os arquivos PDF que o Bob utiliza para responder.")

        # Upload de novos arquivos
        uploaded_files = st.file_uploader(
            "Adicionar novos PDFs", type="pdf", accept_multiple_files=True
        )
        if uploaded_files:
            for uploaded_file in uploaded_files:
                # Salva o arquivo na pasta 'knowledge_base'
                file_path = os.path.join(rag_manager.KNOWLEDGE_BASE_DIR, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
            st.success(f"{len(uploaded_files)} arquivo(s) carregado(s) com sucesso!")

        # Listar e excluir arquivos existentes
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
                        st.rerun() # Recarrega a página para atualizar a lista

        # Botão para processar a base de conhecimento
        if st.button("Processar Base de Conhecimento"):
            with st.spinner("Processando arquivos... Isso pode levar um momento."):
                if rag_manager.process_knowledge_base():
                    st.success("Base de conhecimento processada e atualizada!")
                    # Recria o agente para carregar o novo retriever
                    st.session_state.agent = EverpetzAgent()
                else:
                    st.warning("Nenhum arquivo para processar ou ocorreu um erro.")
        
        st.divider() # Adiciona uma linha divisória para separar as seções
        st.header("Controles do Chat")
        if st.button("Reiniciar Agente"):
            # Limpa o histórico de mensagens da sessão
            st.session_state.messages = []
            # Mostra uma notificação de sucesso
            st.toast("Conversa reiniciada!")
            # Força o recarregamento da página para limpar a interface
            st.rerun()

# --- Execução Principal ---

def main():
    """Função principal que executa a aplicação Streamlit."""
    
    # Verifica os parâmetros da URL para decidir se a barra lateral deve ser mostrada
    query_params = st.query_params
    is_embedded = "embed_chat" in query_params and query_params["embed_chat"] == "true"

    # Se não estiver no modo 'embed_chat', mostra o título e a barra lateral de admin
    if not is_embedded:
        setup_page()
        manage_knowledge_base_sidebar()
    
    initialize_session_state()
    display_chat_history()
    handle_user_input()

if __name__ == "__main__":
    main()