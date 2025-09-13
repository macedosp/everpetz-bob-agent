# embed_config.py
# Configurações ULTRA AGRESSIVAS para garantir que o modo embed funcione corretamente
# Esta versão usa múltiplas técnicas para forçar a remoção do menu lateral

import streamlit as st
import streamlit.components.v1 as components

def configure_embed_mode():
    """
    Configura o aplicativo para funcionar em modo embed com segurança máxima.
    Remove COMPLETAMENTE o acesso ao menu lateral usando múltiplas técnicas.
    """
    
    # Detecta o modo embed através de query parameters
    try:
        query_params = st.query_params
        embed_mode = query_params.get("embed", "false").lower() == "true"
    except:
        try:
            # Fallback para versões antigas
            query_params = st.experimental_get_query_params()
            embed_mode = "embed" in query_params and query_params["embed"][0].lower() == "true"
        except:
            embed_mode = False
    
    if not embed_mode:
        return False
    
    # CSS ULTRA AGRESSIVO - Técnica 1: CSS com !important em tudo
    aggressive_css = """
    <style>
        /* NUCLEAR OPTION - Remove tudo relacionado a sidebar */
        * [data-testid*="sidebar"],
        * [data-testid*="Sidebar"],
        * [class*="sidebar"],
        * [class*="Sidebar"],
        * [id*="sidebar"],
        * [id*="Sidebar"] {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
            width: 0px !important;
            height: 0px !important;
            min-width: 0px !important;
            max-width: 0px !important;
            overflow: hidden !important;
            position: absolute !important;
            left: -99999px !important;
            top: -99999px !important;
            z-index: -99999 !important;
        }
        
        /* Remove botão de menu com múltiplas técnicas */
        [data-testid="collapsedControl"],
        [data-testid="baseButton-header"],
        button[kind="header"],
        button[kind="headerNoPadding"],
        .st-emotion-cache-1wbqy5l,
        .st-emotion-cache-6qob1r {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
            position: fixed !important;
            left: -99999px !important;
            width: 0 !important;
            height: 0 !important;
            padding: 0 !important;
            margin: 0 !important;
            border: none !important;
            clip: rect(0,0,0,0) !important;
            clip-path: inset(100%) !important;
            overflow: hidden !important;
            white-space: nowrap !important;
        }
        
        /* Força conteúdo principal a 100% */
        .main, 
        [data-testid="stAppViewContainer"],
        .stApp,
        [data-testid="main"] {
            width: 100vw !important;
            max-width: 100vw !important;
            margin-left: 0 !important;
            padding-left: 1rem !important;
        }
        
        /* Remove TODOS os outros elementos do Streamlit */
        #MainMenu,
        footer,
        header,
        [data-testid="stHeader"],
        [data-testid="stDecoration"],
        [data-testid="stToolbar"],
        .stDeployButton {
            display: none !important;
        }
        
        /* Override de classes específicas do Streamlit */
        .css-1y4p8pa,
        .css-1y0tads,
        .css-13ln4jf,
        .css-1rs6os,
        .css-17ziqus,
        .css-h5rgaw,
        .css-1g6gooi,
        .css-1ec6rqw,
        .st-ae,
        .st-af,
        .st-ag,
        .st-ah,
        .st-ai {
            max-width: 100% !important;
            width: 100% !important;
        }
        
        /* Remove animações para evitar glitches */
        *, *::before, *::after {
            animation-duration: 0s !important;
            animation-delay: 0s !important;
            transition-duration: 0s !important;
            transition-delay: 0s !important;
        }
        
        /* Esconde qualquer nav */
        nav, [role="navigation"] {
            display: none !important;
        }
        
        /* Força remoção de SVGs de menu */
        svg[width="18"],
        svg[width="20"],
        svg[viewBox="0 0 18 18"],
        svg[viewBox="0 0 20 20"] {
            display: none !important;
        }
    </style>
    """
    
    # JavaScript ULTRA AGRESSIVO - Técnica 2: JavaScript com múltiplos métodos
    aggressive_js = """
    <script>
        (function() {
            'use strict';
            
            // Função nuclear para destruir elementos
            function nukeElement(element) {
                if (!element) return;
                
                // Método 1: Estilo
                element.style.cssText = 'display: none !important; visibility: hidden !important; opacity: 0 !important; pointer-events: none !important; position: fixed !important; left: -99999px !important; top: -99999px !important; width: 0 !important; height: 0 !important;';
                
                // Método 2: Atributos
                element.setAttribute('hidden', 'true');
                element.setAttribute('aria-hidden', 'true');
                element.setAttribute('disabled', 'true');
                
                // Método 3: Classes
                element.className = '';
                
                // Método 4: Remoção do DOM
                try {
                    element.remove();
                } catch(e) {
                    try {
                        if (element.parentNode) {
                            element.parentNode.removeChild(element);
                        }
                    } catch(e2) {}
                }
            }
            
            // Lista completa de seletores para destruir
            const killList = [
                '[data-testid="stSidebar"]',
                '[data-testid="collapsedControl"]',
                '[data-testid="baseButton-header"]',
                'button[kind="header"]',
                'button[kind="headerNoPadding"]',
                '#MainMenu',
                'nav',
                '[role="navigation"]',
                '.st-emotion-cache-1wbqy5l',
                '.st-emotion-cache-6qob1r',
                '.st-emotion-cache-1gv3hkh',
                '.st-emotion-cache-uf99v8'
            ];
            
            // Função para limpar todos os elementos
            function cleanupUI() {
                // Adiciona seletores dinâmicos
                document.querySelectorAll('*').forEach(el => {
                    const testId = el.getAttribute('data-testid') || '';
                    const className = el.className || '';
                    const id = el.id || '';
                    
                    if (testId.toLowerCase().includes('sidebar') ||
                        testId.toLowerCase().includes('collapsed') ||
                        testId.toLowerCase().includes('header') ||
                        className.toString().toLowerCase().includes('sidebar') ||
                        id.toLowerCase().includes('sidebar')) {
                        nukeElement(el);
                    }
                });
                
                // Remove elementos da kill list
                killList.forEach(selector => {
                    try {
                        document.querySelectorAll(selector).forEach(nukeElement);
                    } catch(e) {}
                });
            }
            
            // Executa limpeza imediatamente
            cleanupUI();
            
            // Executa quando DOM estiver pronto
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', cleanupUI);
            } else {
                cleanupUI();
            }
            
            // Executa quando janela carregar
            window.addEventListener('load', cleanupUI);
            
            // Observador de mutações super agressivo
            const observer = new MutationObserver(function(mutations) {
                cleanupUI();
                
                // Verifica cada mutação individualmente
                mutations.forEach(mutation => {
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === 1) { // Element node
                            const testId = node.getAttribute?.('data-testid') || '';
                            if (testId.includes('sidebar') || testId.includes('collapsed')) {
                                nukeElement(node);
                            }
                        }
                    });
                });
            });
            
            // Observa TUDO
            observer.observe(document.documentElement, {
                childList: true,
                subtree: true,
                attributes: true,
                attributeOldValue: false,
                characterData: false
            });
            
            // Limpeza contínua (nuclear option)
            let cleanupInterval = setInterval(cleanupUI, 50);
            
            // Para o interval após 10 segundos para economizar recursos
            setTimeout(() => {
                clearInterval(cleanupInterval);
                // Mas continua com interval mais lento
                setInterval(cleanupUI, 1000);
            }, 10000);
            
            // Bloqueia atalhos de teclado
            const blockKeys = (e) => {
                if ((e.ctrlKey || e.metaKey) && e.shiftKey) {
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    return false;
                }
            };
            
            document.addEventListener('keydown', blockKeys, true);
            document.addEventListener('keyup', blockKeys, true);
            document.addEventListener('keypress', blockKeys, true);
            
            // Bloqueia cliques em botões suspeitos
            document.addEventListener('click', function(e) {
                const target = e.target;
                if (target && target.tagName === 'BUTTON') {
                    const kind = target.getAttribute('kind');
                    if (kind === 'header' || kind === 'headerNoPadding') {
                        e.preventDefault();
                        e.stopPropagation();
                        e.stopImmediatePropagation();
                        nukeElement(target);
                        return false;
                    }
                }
            }, true);
            
            // Log de confirmação
            console.log('%c🔐 MODO EMBED ULTRA SEGURO ATIVADO', 
                        'background: linear-gradient(90deg, #667eea, #764ba2); color: white; font-size: 14px; font-weight: bold; padding: 5px 10px; border-radius: 5px;');
        })();
    </script>
    """
    
    # Aplica TODAS as técnicas
    st.markdown(aggressive_css, unsafe_allow_html=True)
    st.markdown(aggressive_js, unsafe_allow_html=True)
    
    # Técnica 3: Injeta um iframe invisível que bloqueia interações (opcional)
    blocking_layer = """
    <div id="blocking-layer" style="
        position: fixed;
        top: 0;
        left: 0;
        width: 200px;
        height: 100vh;
        z-index: 99999;
        pointer-events: all;
        background: transparent;
    " onclick="return false;"></div>
    """
    st.markdown(blocking_layer, unsafe_allow_html=True)
    
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
            position: relative;
            z-index: 1000;
        '>
            <h3 style='margin: 0; font-size: 1.1rem; font-weight: 600;'>
                🐾 Bob - Assistente Virtual Everpetz
            </h3>
        </div>
    """, unsafe_allow_html=True)