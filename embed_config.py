# embed_config.py
# Configurações de segurança para garantir que o modo embed funcione corretamente
# Adicione este código no início do seu app.py

import streamlit as st

def configure_embed_mode():
    """
    Configura o aplicativo para funcionar corretamente em modo embed,
    removendo COMPLETAMENTE o acesso ao menu lateral e outras funcionalidades administrativas.
    """
    
    # Detecta o modo embed através de query parameters
    query_params = st.query_params
    embed_mode = query_params.get("embed", "false").lower() == "true"
    
    if not embed_mode:
        return False
    
    # CSS agressivo para remover QUALQUER possibilidade de acesso ao menu
    hide_streamlit_style = """
    <style>
        /* Remove o iframe do Streamlit (logo e menu) */
        iframe[title="streamlit_analytics2"] {display: none !important;}
        
        /* Remove TODOS os botões de menu */
        #MainMenu {display: none !important;}
        button[kind="header"] {display: none !important;}
        div[data-testid="collapsedControl"] {display: none !important;}
        button[title="View fullscreen"] {display: none !important;}
        button[kind="headerNoPadding"] {display: none !important;}
        
        /* Remove a sidebar COMPLETAMENTE */
        section[data-testid="stSidebar"] {
            display: none !important;
            width: 0 !important;
            min-width: 0 !important;
        }
        
        /* Remove o espaço da sidebar */
        .css-1y4p8pa {max-width: 100% !important;}
        .css-1y0tads {padding-top: 1rem !important;}
        
        /* Remove decorações e ícones */
        [data-testid="stDecoration"] {display: none !important;}
        [data-testid="stToolbar"] {display: none !important;}
        
        /* Remove o rodapé */
        footer {display: none !important;}
        .css-h5rgaw {display: none !important;}
        
        /* Remove "Made with Streamlit" */
        .viewerBadge_container__r5tak {display: none !important;}
        .viewerBadge_link__qRIHx {display: none !important;}
        
        /* Força largura total */
        .main .block-container {
            max-width: 100% !important;
            padding: 1rem !important;
        }
        
        /* Esconde elementos de desenvolvimento */
        .stDeployButton {display: none !important;}
        #stDecoration {display: none !important;}
        
        /* Remove animações de carregamento desnecessárias */
        .stSpinner > div {border-color: #667eea !important;}
        
        /* Ajusta o chat */
        .stChatFloatingInputContainer {
            background-color: white !important;
        }
        
        /* Remove qualquer elemento que possa abrir menu */
        button:has(svg[width="18"]) {display: none !important;}
        
        /* Bloqueia teclas de atalho via CSS */
        body {
            user-select: text !important;
            -webkit-user-select: text !important;
        }
    </style>
    """
    
    # JavaScript para bloquear atalhos e remover elementos
    security_script = """
    <script>
        // Aguarda o DOM carregar
        window.addEventListener('DOMContentLoaded', (event) => {
            // Remove fisicamente elementos de menu
            const removeElements = [
                '[data-testid="collapsedControl"]',
                '[kind="header"]',
                '[data-testid="stSidebar"]',
                '.css-1rs6os',
                '#MainMenu',
                '[data-testid="stDecoration"]'
            ];
            
            removeElements.forEach(selector => {
                const elements = document.querySelectorAll(selector);
                elements.forEach(el => {
                    if (el) {
                        el.remove();
                    }
                });
            });
            
            // Bloqueia atalhos de teclado
            document.addEventListener('keydown', function(e) {
                // Bloqueia Ctrl+Shift+A, Ctrl+Shift+D e outras combinações
                if ((e.ctrlKey || e.metaKey) && e.shiftKey) {
                    e.preventDefault();
                    e.stopPropagation();
                    return false;
                }
                
                // Bloqueia F12 (DevTools)
                if (e.keyCode === 123) {
                    e.preventDefault();
                    return false;
                }
                
                // Bloqueia Ctrl+Shift+I (DevTools)
                if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.keyCode === 73) {
                    e.preventDefault();
                    return false;
                }
            });
            
            // Desabilita clique direito (opcional - remova se quiser permitir)
            document.addEventListener('contextmenu', function(e) {
                // e.preventDefault();
                // return false;
            });
            
            // Remove periodicamente elementos que possam reaparecer
            setInterval(() => {
                const sidebar = document.querySelector('[data-testid="stSidebar"]');
                if (sidebar) sidebar.style.display = 'none';
                
                const menuBtn = document.querySelector('[data-testid="collapsedControl"]');
                if (menuBtn) menuBtn.remove();
            }, 1000);
        });
        
        // Mensagem no console
        console.log('%c🐾 Bob - Assistente Everpetz', 
                    'color: #667eea; font-size: 20px; font-weight: bold;');
        console.log('%cModo Embed Ativo - Menu Lateral Desabilitado', 
                    'color: #764ba2; font-size: 12px;');
    </script>
    """
    
    # Aplica as configurações
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)
    st.markdown(security_script, unsafe_allow_html=True)
    
    return True

def create_minimal_header():
    """Cria um header minimalista para o modo embed."""
    st.markdown("""
        <div style='
            background: linear-gradient(90deg, #667eea, #764ba2);
            color: white;
            padding: 12px;
            margin: -1rem -1rem 1rem -1rem;
            text-align: center;
            border-radius: 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        '>
            <h3 style='margin: 0; font-size: 1.1rem; font-weight: 600;'>
                🐾 Bob - Assistente Virtual Everpetz
            </h3>
        </div>
    """, unsafe_allow_html=True)

# Exemplo de uso no seu app.py:
"""
# No início do arquivo app.py, após os imports:

from embed_config import configure_embed_mode, create_minimal_header

# Logo no início da aplicação:
embed_mode = configure_embed_mode()

# Configuração da página
if embed_mode:
    st.set_page_config(
        page_title="Bob - Assistente Everpetz",
        page_icon="🐾",
        layout="centered",
        initial_sidebar_state="collapsed"  # Será ocultada pelo CSS anyway
    )
else:
    st.set_page_config(
        page_title="Everpetz - Assistente Bob",
        page_icon="🐾",
        layout="wide",
        initial_sidebar_state="auto"
    )

# No início da função main():
if embed_mode:
    create_minimal_header()
    # Código do chat sem sidebar
else:
    # Código completo com sidebar
"""