# ui_config.py
import streamlit as st

def is_embed_mode() -> bool:
    """
    Verifica se a aplicação está rodando em modo embed através de um parâmetro na URL.
    Exemplo: https://sua-app.com/?embed=true
    """
    return st.query_params.get("embed", "false").lower() == "true"

def apply_embed_css():
    """
    Aplica CSS para remover elementos da interface do Streamlit que são desnecessários
    em um iframe, como o cabeçalho, a barra de ferramentas e o menu principal.
    """
    st.markdown("""
        <style>
            /* Esconde o cabeçalho, a barra de ferramentas e o menu hambúrguer */
            header[data-testid="stHeader"],
            [data-testid="stToolbar"],
            #MainMenu {
                display: none !important;
                visibility: hidden !important;
            }
            
            /* Esconde o botão de deploy e o rodapé */
            .stDeployButton,
            footer {
                display: none !important;
                visibility: hidden !important;
            }

            /* Ajusta o padding do container principal para remover espaços extras */
            .block-container {
                padding-top: 1rem !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

def create_minimal_header():
    """
    Cria um cabeçalho simples e customizado para o modo embed.
    """
    st.markdown("""
        <div style="padding-bottom: 1rem;">
            <h3 style='margin: 0; font-size: 1.2rem; font-weight: 600;'>
                🐾 Fale com o Bob
            </h3>
        </div>
    """, unsafe_allow_html=True)