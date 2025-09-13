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
    
    # --- CSS de Cirurgia de Precisão ---
    # Esta é a regra mais importante, baseada na sua depuração.
    hide_streamlit_style = """
    <style>
        /* ALVO PRINCIPAL: Encontra qualquer botão que contenha o ícone ">>"
        e remove-o da página. Esta é a solução definitiva.
        */
        button:has([data-testid="stIconMaterial"]) {
            display: none !important;
        }

        /* ALVOS SECUNDÁRIOS: Regras de segurança para garantir que, mesmo que o botão
        escape, a própria barra lateral e outros elementos sejam escondidos.
        */
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        #MainMenu,
        .stDeployButton,
        .stToolbar,
        footer,
        header {
            display: none !important;
            visibility: hidden !important;
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