# embed_config.py
import os
import streamlit as st
from typing import Optional

def _get_query_param(name: str, default=None):
    """
    Usa apenas st.query_params (API nova) para evitar avisos de depreciação.
    Valores podem ser str (API nova) ou lista (compat em alguns contextos).
    """
    try:
        qp = st.query_params  # API nova do Streamlit
        v = qp.get(name, default)
        if v is default:
            return default
        if isinstance(v, (list, tuple)):
            return v[0] if v else default
        return v
    except Exception:
        # Se algo muito incomum acontecer, apenas retorne o default
        return default

def configure_embed_mode() -> bool:
    """
    Apenas DETECTA se é embed (não gera UI aqui).
    """
    embed = _get_query_param("embed", None)
    if embed is None:
        embed = os.environ.get("EMBED_MODE", "false")
    embed_str = str(embed).lower()
    return embed_str in ("1", "true", "yes", "on")

def apply_embed_css():
    """
    Some com sidebar, controle '>>', header, toolbar, menu e footer no modo embed.
    """
    st.markdown(
        """
        <style>
        /* Esconde header/toolbar/menu/footer do Streamlit */
        header[data-testid="stHeader"] { display: none !important; }
        [data-testid="stToolbar"] { display: none !important; }
        #MainMenu { visibility: hidden !important; }
        footer { visibility: hidden !important; }

        /* Esconde sidebar e o controle '>>' de colapso */
        [data-testid="stSidebar"] { display: none !important; }
        section[data-testid="stSidebar"] { display: none !important; }
        [data-testid="stSidebarNav"] { display: none !important; }
        [data-testid="collapsedControl"] { display: none !important; }

        /* Remove margens reservadas à sidebar e ajusta padding */
        div[role="main"] { margin-left: 0 !important; }
        .block-container {
            padding-top: 0.5rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def create_minimal_header(
    title: str = "Fale com o Bob",
    subtitle: Optional[str] = None,
    avatar_url: Optional[str] = None,
):
    """
    Cabeçalho leve para o modo embed.
    """
    st.markdown(
        f"""
        <div style="
            display:flex; align-items:center; gap:10px;
            padding:10px 12px; border-radius:12px;
            background:#f7f9fc; border:1px solid #e6eef6; margin-bottom:8px;">
            {'<img src="'+avatar_url+'" style="width:28px;height:28px;border-radius:50%;object-fit:cover;" />' if avatar_url else ''}
            <div style="display:flex; flex-direction:column;">
                <span style="font-weight:600; color:#111827;">{title}</span>
                {'<small style="color:#6b7280;">'+subtitle+'</small>' if subtitle else ''}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )