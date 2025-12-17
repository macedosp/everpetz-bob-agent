# dashboard.py
from apscheduler.schedulers.background import BackgroundScheduler
import feed_manager # Nosso novo script
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, ALL, callback_context, no_update
import plotly.graph_objects as go
import os
import rag_manager
import base64
import datetime
import time
import uuid
import pandas as pd

# --- CONFIGURAÇÃO PARA CALLBACKS EM BACKGROUND ---
import diskcache
from dash import DiskcacheManager
cache = diskcache.Cache("./callback_cache")
background_callback_manager = DiskcacheManager(cache)

# --- Carrega variáveis de ambiente e inicializa o agente ---
from dotenv import load_dotenv
load_dotenv()
from agent import EverpetzAgent
import database
# A inicialização do DB foi movida para o final do arquivo, no ponto de entrada.
agent = EverpetzAgent()

# --- Inicialização da Aplicação Dash ---
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.BOOTSTRAP],
    suppress_callback_exceptions=True,
    background_callback_manager=background_callback_manager,
)
server = app.server

# --- Estilos ---
SIDEBAR_STYLE = {"position": "fixed", "top": 0, "left": 0, "bottom": 0, "width": "18rem", "padding": "2rem 1rem", "background-color": "white", "border-right": "1px solid #dee2e6"}
CONTENT_STYLE = {"margin-left": "18rem", "padding": "2rem 1rem", "background-color": "#f8f9fa", "min-height": "100vh"}

# --- Função Auxiliar para criar as bolhas de conversa (ESTILIZADA) ---
# --- Função Auxiliar para criar as bolhas de conversa ---
def create_chat_bubble(role, content, is_thinking=False):
    if role == 'user':
        # Usuário: Azul (#3C6584 da paleta ou primary), Texto Branco
        bubble = dbc.Card(
            dbc.CardBody(dcc.Markdown(content), className="p-3"), # Padding ajustado
            style={"backgroundColor": "#3C6584", "borderRadius": "15px 15px 0px 15px"}, # Cor da Paleta Everpetz
            inverse=True, # Garante texto branco
            className="shadow-sm border-0"
        )
        return dbc.Row(dbc.Col(bubble, width={"size": 9, "offset": 3}), className="g-0 mb-3 justify-content-end")
    else: # assistant
        # Bob: Branco, Texto Escuro
        content_display = dbc.Spinner(size="sm", color="primary") if is_thinking else dcc.Markdown(content, dangerously_allow_html=False)
        bubble = dbc.Card(
            dbc.CardBody(content_display, className="p-3"), # Padding ajustado
            color="white", 
            className="shadow-sm border-0 text-dark",
            style={"borderRadius": "15px 15px 15px 0px"}
        )
        return dbc.Row(dbc.Col(bubble, width=9), className="g-0 mb-3")

# --- Layouts das Páginas ---
dashboard_layout = html.Div([
    dbc.Row([
        dbc.Col([html.H2("Dashboard"), html.P("Visão geral do desempenho do Bob", className="text-muted")], width=9),
        dbc.Col(dbc.Button("Testar Chat", id="open-chat-modal-btn", color="primary"), width=3, className="d-flex justify-content-end align-items-center"),
    ], className="mb-4"),
    # --- LINHA DE KPIS (ATUALIZADA E ESTILIZADA) ---
    dbc.Row([
        # KPI 1: Documentos
        dbc.Col(dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.H6("Documentos", className="text-muted text-uppercase small fw-bold"),
                        html.H2(id="kpi-total-docs", className="mb-0")
                    ]),
                    dbc.Col(html.I(className="bi bi-file-earmark-text fs-1 text-primary"), width="auto")
                ], align="center")
            ])
        ], className="shadow-sm h-100 border-start border-4 border-primary"), width=12, sm=6, md=3),

        # KPI 2: Conversas Hoje
        dbc.Col(dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.H6("Conversas Hoje", className="text-muted text-uppercase small fw-bold"),
                        html.H2(id="kpi-conversas-hoje", className="mb-0")
                    ]),
                    dbc.Col(html.I(className="bi bi-chat-dots fs-1 text-success"), width="auto")
                ], align="center")
            ])
        ], className="shadow-sm h-100 border-start border-4 border-success"), width=12, sm=6, md=3),

        # KPI 3: Taxa de Resolução
        dbc.Col(dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.H6("Resolução", className="text-muted text-uppercase small fw-bold"),
                        html.H2(id="kpi-resolucao", className="mb-0")
                    ]),
                    dbc.Col(html.I(className="bi bi-check-circle fs-1 text-info"), width="auto")
                ], align="center")
            ])
        ], className="shadow-sm h-100 border-start border-4 border-info"), width=12, sm=6, md=3),

        # KPI 4: Satisfação
        dbc.Col(dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.H6("Satisfação", className="text-muted text-uppercase small fw-bold"),
                        html.H2(id="kpi-satisfacao", className="mb-0")
                    ]),
                    dbc.Col(html.I(className="bi bi-heart fs-1 text-danger"), width="auto")
                ], align="center")
            ])
        ], className="shadow-sm h-100 border-start border-4 border-danger"), width=12, sm=6, md=3),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(dbc.Card([dbc.CardBody([html.H4("Interações por Dia", className="card-title"), dcc.Graph(id="interactions-chart-graph", figure=go.Figure().update_layout(margin=dict(l=0, r=0, t=0, b=0)))])], className="shadow-sm"), width=7),
        dbc.Col(dbc.Card([dbc.CardBody([html.H4("Questões Mais Frequentes", className="card-title"), dbc.ListGroup(id="top-questions-list", flush=True)])], className="shadow-sm"), width=5),
    ]),
    # --- MODAL DO CHAT (VISUAL ARREDONDADO E MODERNO) ---
    dbc.Modal([
        # Cabeçalho
        dbc.ModalHeader(
            dbc.Row([
                dbc.Col(html.Img(id="chat-header-avatar", src=app.get_asset_url('bob_avatar.jpg'), className="rounded-circle border border-2 border-white", style={'width': '45px', 'height': '45px'}), width="auto"),
                dbc.Col([
                    html.H5("Bob", id="chat-header-agent-name", className="mb-0 fw-bold text-white"),
                    html.Small([html.I(className="bi bi-circle-fill text-success me-1", style={'fontSize':'8px'}), "Online"], className="text-white-50")
                ], className="d-flex flex-column justify-content-center")
            ], align="center", className="g-2"),
            id="chat-modal-header",
            close_button=True,
            className="text-white border-0" # Remove borda inferior padrão
        ),
        
        # Corpo (Com fundo cinza suave para contraste)
        dbc.ModalBody(
            html.Div(id="modal-chat-history-div", style={"minHeight": "400px"}),
            style={"height": "450px", "overflowY": "auto", "padding": "20px", "backgroundColor": "#f0f2f5"}
        ),
        
        # Rodapé (Com botões Like/Dislike e Input arredondado)
        dbc.ModalFooter(html.Div([
            # Sugestões (Pílulas)
            html.Div([
                dbc.Button("Como funciona?", id="quick-reply-btn-1", outline=True, color="secondary", size="sm", className="me-2 rounded-pill mb-2"),
                dbc.Button("Quero vender", id="quick-reply-btn-2", outline=True, color="secondary", size="sm", className="me-2 rounded-pill mb-2"),
                dbc.Button("Produtos para pets", id="quick-reply-btn-3", outline=True, color="secondary", size="sm", className="rounded-pill mb-2"),
            ], className="text-center mb-2"),

            # Barra de Input Estilo App
            dbc.Row([
                dbc.Col([
                    dbc.Button(html.I(className="bi bi-hand-thumbs-up"), id="feedback-up-btn", color="link", className="text-muted fs-5 p-1"),
                    dbc.Button(html.I(className="bi bi-hand-thumbs-down"), id="feedback-down-btn", color="link", className="text-muted fs-5 p-1"),
                ], width="auto", className="d-flex align-items-center pe-0"),
                
                dbc.Col(
                    dbc.Input(id="modal-chat-input", placeholder="Digite sua mensagem...", n_submit=0, className="rounded-pill border-0 bg-light py-2"),
                    className="px-2"
                ),
                
                dbc.Col(
                    dbc.Button(html.I(className="bi bi-send-fill"), id="modal-chat-submit-btn", color="primary", n_clicks=0, className="rounded-circle shadow-sm", style={'width': '40px', 'height': '40px'}), 
                    width="auto", className="ps-0"
                )
            ], align="center", className="g-0 bg-white p-2 rounded-4 border")
        ], style={"width": "100%"}), className="border-0 pt-0")
        
    # AQUI ESTÁ O ARREDONDAMENTO: contentClassName="rounded-5 ..."
    ], id="chat-modal", is_open=False, scrollable=True, centered=True, contentClassName="rounded-5 border-0 shadow-lg overflow-hidden"),
    dcc.Store(id='modal-chat-history-store', data=[]),
    dcc.Store(id='chat-session-id-store', data=None),
    dcc.Store(id='chat-session-settings-store', data={}),
])

base_conhecimento_layout = html.Div([
    dcc.Store(id='staged-files-store'),
    dbc.Row([
        dbc.Col([html.H2("Base de Conhecimento"), html.P("Gerencie os documentos e informações do Bob", className="text-muted")]),
        dbc.Col(dbc.Button("Adicionar Documento", id="open-upload-modal-btn", color="primary"), className="d-flex justify-content-end align-items-center"),
    ], className="mb-4"),
    dbc.Row([
        dbc.Col(dbc.Card([dbc.CardHeader("Documentos Carregados"), dbc.CardBody(dbc.ListGroup(id="document-list-group", flush=True))], className="shadow-sm"), width=8),
        dbc.Col([
            dbc.Card([dbc.CardHeader("Estatísticas"), dbc.CardBody(dbc.ListGroup(id="stats-list-group", flush=True))], className="shadow-sm mb-4"),
            dbc.Card([dbc.CardHeader("Ações"), dbc.CardBody([dbc.Button("Processar Base de Conhecimento", id="process-kb-btn", color="primary", className="w-100"), html.P("Clique para que o Bob estude os documentos e atualize sua memória.", className="text-muted small mt-2")])], className="shadow-sm mb-4"),
            dbc.Card([dbc.CardHeader("Formatos Suportados"), dbc.CardBody([dbc.ListGroup([dbc.ListGroupItem("PDF"), dbc.ListGroupItem("TXT"), dbc.ListGroupItem("DOCX")], flush=True), html.P("Tamanho máximo: 10MB por arquivo", className="text-muted small mt-3")])], className="shadow-sm"),
        ], width=4),
    ]),
    dbc.Modal([
        dbc.ModalHeader(html.Div([html.H4("Adicionar Documento"), html.P("Carregue novos documentos para a base de conhecimento do Bob", className="text-muted small mb-0")]), close_button=True),
        dbc.ModalBody([
            dcc.Upload(id='upload-data', children=html.Div([html.I(className="bi bi-upload display-4 text-muted"), html.P("Arraste arquivos aqui ou clique para selecionar", className="mt-3 mb-1"), dbc.Button([html.I(className="bi bi-upload me-2"), "Selecionar Arquivos"], outline=True, color="secondary", className="mt-3")], className="d-flex flex-column justify-content-center align-items-center p-4"), style={'borderWidth': '2px', 'borderStyle': 'dashed', 'borderRadius': '10px', 'minHeight': '200px'}, multiple=True, accept='.pdf,.docx,.txt'),
            html.Div(id='staged-files-list', className="mt-3"),
        ]),
        dbc.ModalFooter([dbc.Button("Cancelar", id="close-upload-modal-btn", color="light"), dbc.Button("Processar", id="process-upload-btn", color="primary", disabled=True)]),
    ], id="upload-modal", is_open=False, size="lg")
])

conversas_layout = html.Div([
    dbc.Row([
        dbc.Col([html.H2("Conversas"), html.P("Acompanhe as interações do Bob com os usuários", className="text-muted")]),
        dbc.Col(
            dbc.ButtonGroup([
                dbc.Button([html.I(className="bi bi-funnel-fill me-2"), "Filtros"], id="open-filter-modal-btn", outline=True, color="secondary"),
                dbc.Button([html.I(className="bi bi-download me-2"), "Exportar"], id="export-conversations-btn", outline=True, color="secondary"),
            ]), 
            className="d-flex justify-content-end align-items-center"
        ),
    ], className="mb-4"),
    dbc.Card([
        dbc.CardHeader("Histórico de Conversas"),
        dbc.CardBody(dbc.ListGroup(id="conversation-list-group", flush=True))
    ], className="shadow-sm"),
    
    dcc.Download(id="download-conversations-csv"),
    
    dbc.Modal([
        dbc.ModalHeader("Filtrar Conversas por Data"),
        dbc.ModalBody([
            dbc.Label("Selecione o intervalo desejado:"),
            html.Div([
                dcc.DatePickerRange(
                    id='filter-date-range',
                    display_format='DD/MM/YYYY',
                    start_date_placeholder_text="Início",
                    end_date_placeholder_text="Fim",
                    className="mb-3"
                )
            ], className="d-flex justify-content-center")
        ]),
        dbc.ModalFooter([
            dbc.Button("Limpar Filtros", id="clear-filter-btn", color="light", className="me-auto"),
            dbc.Button("Aplicar", id="apply-filter-btn", color="primary"),
        ]),
    ], id="filter-modal", is_open=False, centered=True)
])

usuarios_layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.H2("Usuários Autorizados"),
            html.P("Gerencie quem pode acessar o Bob Admin", className="text-muted"),
        ]),
        dbc.Col(
            dbc.Button([html.I(className="bi bi-plus-lg me-2"), "Adicionar Usuário"], id="open-add-user-modal-btn", color="primary"),
            className="d-flex justify-content-end align-items-center"
        ),
    ], className="mb-4"),
    
    html.Div(id="user-list-alert-div", className="mb-3"),
    html.Div(id="user-list-table", className="shadow-sm"),
    
    dbc.Modal([
        dbc.ModalHeader("Adicionar Novo Usuário"),
        dbc.ModalBody([
            html.Div(id="add-user-alert-div"),
            dbc.Label("Nome Completo"),
            dbc.Input(id="add-user-name", type="text", className="mb-3"),
            dbc.Label("E-mail"),
            dbc.Input(id="add-user-email", type="email", className="mb-3"),
            dbc.Label("Senha Temporária"),
            dbc.Input(id="add-user-password", type="password", className="mb-3"),
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancelar", id="close-add-user-modal-btn", color="secondary"),
            dbc.Button("Salvar Usuário", id="save-user-btn", color="primary"),
        ]),
    ], id="add-user-modal", is_open=False)
])

configuracoes_layout = html.Div([
    dbc.Row([dbc.Col([html.H2("Configurações"), html.P("Ajuste o comportamento e aparência do Bob", className="text-muted")])], className="mb-4"),
    dbc.Card([
        dbc.CardHeader(html.H4("⚙️ Configurações do Sistema")),
        dbc.CardBody([
            dbc.Row([
                dbc.Col(dbc.Card([
                    dbc.CardHeader("Personalização"), 
                    dbc.CardBody([
                        dbc.Label("Avatar do Agente"),
                        html.Div([
                            dcc.Upload(
                                id='upload-avatar',
                                children=html.Div(['Arraste ou ', html.A('selecione')], className="d-flex flex-column justify-content-center align-items-center h-100"),
                                style={'width': '120px', 'height': '120px', 'borderWidth': '2px', 'borderStyle': 'dashed', 'borderRadius': '50%', 'textAlign': 'center', 'position': 'relative', 'display': 'inline-block'},
                                accept='image/*'
                            ),
                            html.Img(id='avatar-preview', src=app.get_asset_url('bob_avatar.jpg'), style={'width': '120px', 'height': '120px', 'borderRadius': '50%', 'objectFit': 'cover', 'position': 'absolute', 'top': 0, 'left': 0, 'zIndex': -1})
                        ], style={'position': 'relative', 'width': '120px', 'height': '120px', 'margin': 'auto'}, className="mb-3 text-center"),
                        html.Hr(),
                        dbc.Label("Nome do Agente"),
                        dbc.Input(id="setting-agent-name", type="text", className="mb-3"),
                        dbc.Label("Mensagem de Boas-vindas"),
                        dbc.Textarea(id="setting-welcome-message", style={"height": "100px"}, className="mb-3"),
                        dbc.Label("Cor do Chat"),
                        dbc.RadioItems(
                            id="setting-chat-color",
                            options=[
                                {"label": "", "value": "#008080"}, # 1 - Transformative Teal (Padrão)
                                {"label": "", "value": "#fc8746"}, # 2 - Petz Orange
                                {"label": "", "value": "#006666"}, # 3 - Deepest Teal
                                {"label": "", "value": "#FFB070"}, # 4 - Bright Orange
                                {"label": "", "value": "#E6F2F2"}, # 5 - Transformative Wash
                            ],
                            value="#008080", # Define o Teal como padrão se nenhum estiver salvo
                            inline=True, 
                            className="color-selector mb-3",
                            inputClassName="d-none", 
                            labelClassName="color-swatch",
                        ),
                        html.Hr(),
                        # --- NOVO CAMPO FEED ---
                        dbc.Label("URL do Feed de Produtos (XML)"),
                        dbc.Input(id="setting-feed-url", type="url", placeholder="https://...", className="mb-2"),
                        dbc.Button("Atualizar Feed Agora", id="force-update-feed-btn", color="secondary", size="sm", outline=True, className="mb-3"),
                        html.Div(id="feed-update-status", className="text-muted small"),
                    ])
                ]), width=6),
                dbc.Col(dbc.Card([
                    dbc.CardHeader("Comportamento"), 
                    dbc.CardBody([
                        dbc.Switch(id="setting-auto-response", label="Respostas Automáticas", value=True, className="mb-3"),
                        dbc.Switch(id="setting-auto-escalation", label="Escalação Automática", value=True, className="mb-3"),
                        dbc.Switch(id="setting-log-conversation", label="Logs de Conversa", value=True, className="mb-3"),
                        html.Hr(),
                        dbc.Button([html.I(className="bi bi-save me-2"), "Salvar Configurações"], id="save-settings-btn", color="primary", className="w-100")
                    ])
                ]), width=6),
            ])
        ])
    ], className="shadow-sm")
])

# --- Componentes Principais ---
# --- Componentes Principais e Layout Geral ---
sidebar = html.Div([
    # 1. Cabeçalho do Perfil Refinado
    html.Div([
        html.Img(
            id='sidebar-avatar', 
            src=app.get_asset_url('bob_avatar.jpg'), 
            className="rounded-circle mb-3 border border-2 border-light shadow-sm", # Adicionada borda e sombra
            style={'width': '90px', 'height': '90px', 'objectFit': 'cover'} # Tamanho fixo e cover
        ),
        html.H5("Bob Admin", className="fw-bold mb-0 text-dark"), # Texto mais escuro
        html.P("Agente Everpetz", className="text-muted small mb-0") # Texto menor e cinza
    ], className="text-center py-4"), # Mais espaçamento vertical (py-4)
    
    html.Hr(),
    
    # 2. Navegação com Ícones Padronizados (Bootstrap Icons)
    dbc.Nav([
        dbc.NavLink(
            [html.I(className="bi bi-speedometer2 me-3 fs-5"), "Dashboard"], 
            href="/", active="exact", className="d-flex align-items-center py-2"
        ),
        dbc.NavLink(
            [html.I(className="bi bi-journal-richtext me-3 fs-5"), "Base de Conhecimento"], 
            href="/base-de-conhecimento", active="exact", className="d-flex align-items-center py-2"
        ),
        dbc.NavLink(
            [html.I(className="bi bi-chat-dots me-3 fs-5"), "Conversas"], 
            href="/conversas", active="exact", className="d-flex align-items-center py-2"
        ),
        dbc.NavLink(
            [html.I(className="bi bi-people me-3 fs-5"), "Usuários Autorizados"], 
            href="/usuarios", active="exact", className="d-flex align-items-center py-2"
        ),
        dbc.NavLink(
            [html.I(className="bi bi-gear me-3 fs-5"), "Configurações"], 
            href="/configuracoes", active="exact", className="d-flex align-items-center py-2"
        ),
    ], vertical=True, pills=True, className="flex-grow-1"), # flex-grow empurra o rodapé
    
    # 3. Rodapé Fixo com o Botão Sair
    html.Div([
        html.Hr(),
        dbc.NavLink(
            [html.I(className="bi bi-box-arrow-right me-3 fs-5"), "Sair"], # Ícone de saída correto
            id="logout-button",
            href="/",
            className="text-danger d-flex align-items-center py-2 fw-bold", # Vermelho e negrito
            n_clicks=0
        )
    ], className="mt-auto") # Garante que fique no final
    
], style=SIDEBAR_STYLE, className="d-flex flex-column") # Flexbox para alinhar rodapé

# --- Layout de Login ---
login_layout = dbc.Container([
    dbc.Row(
        dbc.Col(
            dbc.Card([
                dbc.CardHeader(html.H4("Bob Admin - Login", className="text-center")),
                dbc.CardBody([
                    html.Div(id="login-alert-div"),
                    dbc.Label("E-mail"),
                    dbc.Input(id="login-email", type="email", placeholder="seu-email@dominio.com", className="mb-3"),
                    dbc.Label("Senha"),
                    dbc.Input(id="login-password", type="password", placeholder="Sua senha", className="mb-3"),
                    dbc.Button("Login", id="login-button", color="primary", className="w-100", n_clicks=0)
                ])
            ]),
            width=6, md=4,
            className="mt-5"
        ),
        justify="center"
    )
], fluid=True, style={"height": "100vh", "backgroundColor": "#f8f9fa"})

content = html.Div(id="page-content", style=CONTENT_STYLE)

# --- LAYOUT GLOBAL (ROTEADOR) ---
def serve_layout():
    return html.Div([
        dcc.Location(id="url"),
        dcc.Store(id='session-store', storage_type='session'), 
        dcc.Loading(id="loading-feedback", type="default", children=html.Div(id="upload-feedback-div", style={'position': 'fixed', 'top': '10px', 'right': '10px', 'zIndex': 1050})),
        dcc.Store(id='signal-store'),
        html.Div(id="page-container") 
    ])
app.layout = serve_layout

# --- CALLBACKS ---

@app.callback(Output("page-container", "children"), Input("session-store", "data"), Input("url", "pathname"))
def auth_router(session_data, pathname):
    if not session_data: return login_layout
    app_shell = html.Div([sidebar, content])
    return app_shell

@app.callback([Output("session-store", "data"), Output("login-alert-div", "children")], Input("login-button", "n_clicks"), [State("login-email", "value"), State("login-password", "value")], prevent_initial_call=True)
def handle_login(n_clicks, email, password):
    if not email or not password: return no_update, dbc.Alert("E-mail e senha são obrigatórios.", color="warning")
    user = database.get_user_by_email(email)
    if user and database.verify_password(password, user.hashed_password): return {'email': user.email}, "Login bem-sucedido!"
    return no_update, dbc.Alert("E-mail ou senha inválidos.", color="danger")

@app.callback(Output("session-store", "data", allow_duplicate=True), Input("logout-button", "n_clicks"), prevent_initial_call=True)
def handle_logout(n_clicks):
    if n_clicks > 0: return None
    return no_update

@app.callback(Output("page-content", "children"), Input("url", "pathname"), State("session-store", "data"))
def render_page_content(pathname, session_data):
    if not session_data: return no_update
    if pathname == "/": return dashboard_layout
    elif pathname == "/base-de-conhecimento": return base_conhecimento_layout
    elif pathname == "/conversas": return conversas_layout
    elif pathname.startswith("/conversas/"):
        session_id = pathname.split("/")[-1]
        conversation_turns = database.get_conversation_by_session_id(session_id)
        chat_history_bubbles = [create_chat_bubble(turn.role, turn.content) for turn in conversation_turns]
        
        detail_layout = html.Div([
            dcc.Link([html.I(className="bi bi-arrow-left-circle me-2"), "Voltar para a lista de conversas"], href="/conversas", className="mb-3 d-inline-block"),
            html.H2(f"Detalhes da Sessão #{session_id.split('_')[-1][:6]}"),
            
            # --- MUDANÇA AQUI: Adicionamos o ID 'full-conversation-history' ---
            dbc.Card(dbc.CardBody(chat_history_bubbles, id="full-conversation-history"), className="shadow-sm")
        ])
        return detail_layout
    elif pathname == "/usuarios": return usuarios_layout
    elif pathname == "/configuracoes": return configuracoes_layout
    return html.Div([html.H1("404: Not found"), html.P(f"O caminho {pathname} não foi reconhecido...")])

# --- Chat Callbacks ---
@app.callback(
    [Output("chat-modal", "is_open"), Output('modal-chat-history-store', 'data', allow_duplicate=True), Output("modal-chat-history-div", "children", allow_duplicate=True), Output("chat-session-id-store", "data"), Output("chat-session-settings-store", "data"), Output("chat-header-agent-name", "children"), Output("chat-header-avatar", "src", allow_duplicate=True), Output("chat-modal-header", "style"), Output("modal-chat-submit-btn", "style")],
    Input("open-chat-modal-btn", "n_clicks"), State("chat-modal", "is_open"), prevent_initial_call=True
)
def toggle_chat_modal_and_init(n_clicks, is_open):
    if n_clicks:
        session_settings = database.get_all_settings()
        agent_name = session_settings.get("agent_name", "Bob")
        welcome_text = session_settings.get("welcome_message", "Olá! Como posso te ajudar?")
        chat_color = session_settings.get("chat_color", "#526A86")
        welcome_message = {"role": "assistant", "content": welcome_text}
        welcome_bubble = create_chat_bubble(welcome_message['role'], welcome_message['content'])
        new_session_id = str(uuid.uuid4())
        avatar_src = f"{app.get_asset_url('bob_avatar.jpg')}?t={time.time()}"
        header_style = {'backgroundColor': chat_color, 'color': 'white'}
        button_style = {'backgroundColor': chat_color, 'borderColor': chat_color}
        return (not is_open, [welcome_message], [welcome_bubble], new_session_id, session_settings, agent_name, avatar_src, header_style, button_style)
    no_updates = [no_update] * 9
    return is_open, *no_updates[1:]

@app.callback([Output("modal-chat-input", "value", allow_duplicate=True), Output("modal-chat-submit-btn", "n_clicks", allow_duplicate=True)], [Input("quick-reply-btn-1", "n_clicks"), Input("quick-reply-btn-2", "n_clicks"), Input("quick-reply-btn-3", "n_clicks")], State("modal-chat-submit-btn", "n_clicks"), prevent_initial_call=True)
def handle_quick_replies(n1, n2, n3, current_submit_clicks):
    ctx = callback_context
    if not ctx.triggered: return no_update, no_update
    button_id = ctx.triggered_id
    if button_id == "quick-reply-btn-1": question = "Como funciona?"
    elif button_id == "quick-reply-btn-2": question = "Quero vender"
    elif button_id == "quick-reply-btn-3": question = "Produtos para pets"
    else: return no_update, no_update
    return question, (current_submit_clicks or 0) + 1

@app.callback([Output("modal-chat-history-store", "data", allow_duplicate=True), Output("modal-chat-input", "value", allow_duplicate=True)], [Input("modal-chat-submit-btn", "n_clicks"), Input("modal-chat-input", "n_submit")], [State("modal-chat-input", "value"), State("modal-chat-history-store", "data")], prevent_initial_call=True)
def handle_chat_submission(submit_clicks, enter_submissions, user_input, history):
    if not user_input: return no_update, no_update
    history = history or []
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": "thinking..."})
    return history, ""

# Agent Query (Modo Síncrono - Mais estável)
@app.callback(
    [Output("modal-chat-history-store", "data", allow_duplicate=True),
     Output("signal-store", "data", allow_duplicate=True)],
    Input("modal-chat-history-store", "data"),
    [State("chat-session-id-store", "data"),
     State("chat-session-settings-store", "data")],
    prevent_initial_call=True
    # REMOVIDO: background=True (Causa do erro no Windows)
)
def run_agent_query(history, session_id, session_settings):
    # Verifica se a última mensagem é o placeholder "thinking..."
    if history and history[-1].get("content") == "thinking...":
        # Pega a pergunta real do usuário (penúltima mensagem)
        user_query = history[-2].get("content")
        
        try:
            # Chama o Agente
            agent_response_text = agent.get_response(
                user_query=user_query, 
                chat_history=history[:-2], 
                session_settings=session_settings
            )
        except Exception as e:
            # Tratamento de erro para não quebrar o chat
            print(f"Erro no Agente: {e}")
            agent_response_text = "Desculpe, tive um problema técnico ao processar sua solicitação. Tente novamente."

        # Salva no banco
        if session_id:
            database.log_conversation_turn(session_id=session_id, role='user', content=user_query)
            database.log_conversation_turn(session_id=session_id, role='assistant', content=agent_response_text)
        
        # Atualiza o histórico com a resposta real
        history[-1]["content"] = agent_response_text
        
        # Retorna histórico e sinal de atualização
        return history, f"conversation_updated_{time.time()}"
    
    return no_update, no_update

@app.callback(Output("modal-chat-history-div", "children"), Input("modal-chat-history-store", "data"))
def render_chat_from_store(history):
    history = history or []
    return [create_chat_bubble(msg['role'], msg['content'], is_thinking=(msg['content'] == 'thinking...')) for msg in history]

# --- KPIs and Feedback ---
@app.callback(
    [Output("kpi-total-docs", "children"),
     Output("kpi-conversas-hoje", "children"),
     Output("interactions-chart-graph", "figure"),
     Output("top-questions-list", "children"),
     Output("kpi-resolucao", "children"),
     Output("kpi-satisfacao", "children")],
    [Input("url", "pathname"), 
     Input("upload-feedback-div", "children"),
     Input("signal-store", "data")]
)
def update_dashboard_kpis(pathname, feedback, signal):
    if pathname == "/":
        # --- 1. KPIs (Lógica Mantida) ---
        total_docs = "0"
        if os.path.exists(rag_manager.KNOWLEDGE_BASE_DIR):
            try:
                files = [f for f in os.listdir(rag_manager.KNOWLEDGE_BASE_DIR) if f.endswith((".pdf", ".docx", ".txt"))]
                total_docs = str(len(files))
            except FileNotFoundError: pass
        
        conversas_hoje = str(database.count_sessions_today())
        taxa_resolucao, satisfacao_media = database.get_kpis()
        str_resolucao = f"{taxa_resolucao}%"
        str_satisfacao = str(satisfacao_media)

        # --- 2. GRÁFICO APRIMORADO (Area Chart) ---
        interaction_data = database.get_daily_interaction_counts()
        dates = [row.date for row in interaction_data]
        counts = [row.count for row in interaction_data]
        
        # Criando o gráfico com estilo
        chart_fig = go.Figure()
        chart_fig.add_trace(go.Scatter(
            x=dates, 
            y=counts, 
            mode='lines+markers',
            fill='tozeroy', # Preenchimento abaixo da linha (Area Chart)
            line=dict(color='#526A86', width=3), # Cor da marca + linha mais grossa
            marker=dict(size=8, color='#3C6584', line=dict(width=2, color='white')), # Marcadores estilizados
            name="Interações"
        ))
        
        chart_fig.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False), # Remove grade vertical para limpar
            yaxis=dict(showgrid=True, gridcolor='#e1e5eb'), # Grade horizontal suave
            hovermode="x unified" # Tooltip moderno que segue o mouse
        )
        
        # --- 3. LISTA APRIMORADA (Com Barras de Progresso) ---
        top_questions = database.get_top_questions()
        questions_list = []
        
        if not top_questions:
            questions_list = dbc.ListGroupItem("Nenhuma pergunta registrada ainda.", className="text-muted text-center py-4")
        else:
            # Descobre o maior valor para calcular a porcentagem da barra
            max_count = top_questions[0][1] if top_questions else 1
            
            for i, (question, count) in enumerate(top_questions):
                # Calcula % para a barra de progresso
                percent = (count / max_count) * 100
                
                # Trunca texto muito longo
                text = (question[:50] + '...') if len(question) > 50 else question
                
                item = dbc.ListGroupItem([
                    dbc.Row([
                        # Coluna da Pergunta e Barra
                        dbc.Col([
                            html.Div([
                                html.Span(f"#{i+1} ", className="text-muted small me-2"), # Rank
                                html.Span(text, className="fw-bold text-dark")
                            ], className="mb-1"),
                            # A Barra de Progresso
                            dbc.Progress(value=percent, color="info" if i == 0 else "primary", style={"height": "6px"}, className="mb-1")
                        ]),
                        # Coluna do Número (Badge)
                        dbc.Col(
                            dbc.Badge(str(count), color="light", text_color="dark", className="border"), 
                            width="auto", 
                            className="d-flex align-items-center"
                        )
                    ])
                ], className="border-0 border-bottom py-3") # Remove bordas laterais, deixa mais limpo
                questions_list.append(item)

        return total_docs, conversas_hoje, chart_fig, questions_list, str_resolucao, str_satisfacao
    
    return no_update, no_update, no_update, no_update, no_update, no_update

@app.callback(Output("upload-feedback-div", "children", allow_duplicate=True), [Input("feedback-up-btn", "n_clicks"), Input("feedback-down-btn", "n_clicks")], State("chat-session-id-store", "data"), prevent_initial_call=True)
def submit_feedback(n_up, n_down, session_id):
    ctx = callback_context
    if not ctx.triggered or not session_id: return no_update
    button_id = ctx.triggered_id
    if button_id == "feedback-up-btn":
        resolved, score, msg, color = True, 5, "Obrigado pelo feedback positivo! 😺", "success"
    elif button_id == "feedback-down-btn":
        resolved, score, msg, color = False, 1, "Que pena! Vamos melhorar na próxima. 😿", "warning"
    else: return no_update
    if database.save_session_feedback(session_id, resolved, score): return dbc.Alert(msg, color=color, duration=3000, is_open=True)
    return dbc.Alert("Erro ao salvar avaliação.", color="danger", duration=3000, is_open=True)

@app.callback(
    Output("conversation-list-group", "children"),
    [Input("url", "pathname"),
     Input("upload-feedback-div", "children"),
     Input("signal-store", "data"),
     Input("apply-filter-btn", "n_clicks"),  # Gatilho: Botão Aplicar
     Input("clear-filter-btn", "n_clicks")], # Gatilho: Botão Limpar
    [State("filter-date-range", "start_date"),
     State("filter-date-range", "end_date")]
)
def update_conversations_list(pathname, feedback, signal, n_apply, n_clear, start_date, end_date):
    triggered_id = callback_context.triggered_id
    
    # Lógica de Limpar Filtros
    if triggered_id == "clear-filter-btn":
        start_date = None
        end_date = None

    # Se estivermos na página ou se houver um gatilho relevante
    if pathname == "/conversas" or triggered_id in ['signal-store', 'apply-filter-btn', 'clear-filter-btn']:
        
        # Se houver datas selecionadas, passamos para o DB e ignoramos o limite padrão
        # Se NÃO houver datas, usamos o limite de 5
        limit = 5 if not (start_date and end_date) else None
        
        summaries = database.get_conversations_summary(limit=limit, start_date=start_date, end_date=end_date)
        
        if not summaries:
            return dbc.Card(dbc.CardBody(html.Div([
                html.I(className="bi bi-chat-off-fill display-3 text-muted"),
                html.H4("Nenhuma conversa encontrada", className="mt-3"),
                html.P("Tente ajustar os filtros.", className="text-muted") if start_date else None
            ], className="text-center p-4")))
            
        conversation_items = []
        for s in summaries:
            # Formatação limpa: Apenas Data e Hora
            date_text = s['start_time_local'].strftime('%d/%m/%Y às %H:%M')
            
            item = dbc.ListGroupItem([
                dbc.Row([
                    dbc.Col(html.I(className="bi bi-person-circle fs-3 text-muted"), width="auto", className="pe-0"),
                    dbc.Col([
                        html.H6(s['first_message'], className="mb-1 fw-bold"),
                        # CORREÇÃO VISUAL: Mostra apenas a data, sem "Sessão #..."
                        html.Small(date_text, className="text-muted"),
                    ], className="flex-grow-1"),
                    dbc.Col(dbc.Badge("Ver Detalhes", color="light", text_color="primary", pill=True), width="auto")
                ], align="center")
            ])
            conversation_items.append(dcc.Link(item, href=f"/conversas/{s['session_id']}", style={"textDecoration": "none"}))
            
        return conversation_items
        
    return no_update

# --- Users & Knowledge Base & Settings Callbacks ---
@app.callback(Output("user-list-table", "children"), [Input("url", "pathname"), Input("add-user-alert-div", "children"), Input("user-list-alert-div", "children")])
def update_user_list(pathname, save_feedback, delete_feedback):
    if pathname == "/usuarios":
        try:
            users = database.get_all_users()
            table_header = [html.Thead(html.Tr([html.Th("Nome"), html.Th("E-mail"), html.Th("Admin"), html.Th("Ações")]))]
            if not users:
                table_body = [html.Tbody([html.Tr(html.Td("Nenhum usuário cadastrado.", colSpan=4, className="text-center"))])]
            else:
                table_body = [html.Tbody([html.Tr([html.Td(user.name), html.Td(user.email), html.Td(dbc.Badge("Sim", color="success") if user.is_master else dbc.Badge("Não", color="secondary")), html.Td(dbc.Button(html.I(className="bi bi-trash-fill"), id={'type': 'delete-user-btn', 'index': user.id}, color="danger", size="sm", disabled=user.is_master))]) for user in users])]
            return dbc.Card([dbc.CardHeader("Lista de Usuários"), dbc.CardBody(dbc.Table(table_header + table_body, bordered=True, hover=True, striped=True, responsive=True))])
        except Exception as e: return dbc.Alert(f"Erro ao carregar usuários: {e}", color="danger")
    return no_update

@app.callback(Output("add-user-modal", "is_open"), [Input("open-add-user-modal-btn", "n_clicks"), Input("close-add-user-modal-btn", "n_clicks")], State("add-user-modal", "is_open"), prevent_initial_call=True)
def toggle_add_user_modal(n_open, n_close, is_open):
    if n_open or n_close: return not is_open
    return is_open

@app.callback(Output("add-user-alert-div", "children"), Input("save-user-btn", "n_clicks"), [State("add-user-name", "value"), State("add-user-email", "value"), State("add-user-password", "value")], prevent_initial_call=True)
def save_new_user(n_clicks, name, email, password):
    if not n_clicks: return no_update
    if not name or not email or not password: return dbc.Alert("Todos os campos são obrigatórios.", color="warning")
    try:
        new_user = database.create_user(name=name, email=email, plain_password=password, is_master=False)
        if new_user: return dbc.Alert(f"Usuário '{name}' criado com sucesso!", color="success")
        else: return dbc.Alert(f"O e-mail '{email}' já está em uso.", color="danger")
    except Exception as e: return dbc.Alert(f"Erro ao criar usuário: {e}", color="danger")

@app.callback(Output("user-list-alert-div", "children", allow_duplicate=True), Input({'type': 'delete-user-btn', 'index': ALL}, 'n_clicks'), prevent_initial_call=True)
def delete_user_callback(n_clicks):
    triggered_id = callback_context.triggered_id
    if not triggered_id or not any(n_clicks): return no_update
    try:
        user_id_to_delete = triggered_id['index']
        success, message = database.delete_user_by_id(user_id_to_delete)
        if success: return dbc.Alert(message, color="success", duration=3000)
        else: return dbc.Alert(message, color="danger", duration=5000)
    except Exception as e: return dbc.Alert(f"Erro no callback de deleção: {e}", color="danger")

@app.callback(Output("upload-modal", "is_open"), [Input("open-upload-modal-btn", "n_clicks"), Input("close-upload-modal-btn", "n_clicks"), Input("process-upload-btn", "n_clicks")], State("upload-modal", "is_open"), prevent_initial_call=True)
def toggle_upload_modal(n_open, n_close, n_process, is_open):
    ctx = callback_context
    if not ctx.triggered: return is_open
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    if button_id == "open-upload-modal-btn": return True
    if button_id in ["close-upload-modal-btn", "process-upload-btn"]: return False
    return is_open

@app.callback([Output('staged-files-store', 'data', allow_duplicate=True), Output('staged-files-list', 'children', allow_duplicate=True), Output('process-upload-btn', 'disabled', allow_duplicate=True)], Input('open-upload-modal-btn', 'n_clicks'), prevent_initial_call=True)
def clear_upload_modal_on_open(n_clicks):
    return [], [], True

@app.callback([Output('staged-files-store', 'data'), Output('staged-files-list', 'children'), Output('process-upload-btn', 'disabled')], Input('upload-data', 'contents'), State('upload-data', 'filename'), prevent_initial_call=True)
def update_staged_files(list_of_contents, list_of_names):
    if list_of_contents is None: return [], [], True
    staged_data = [{'filename': name, 'contents': contents} for name, contents in zip(list_of_names, list_of_contents)]
    file_list_display = [dbc.ListGroupItem(f"📄 {name}", className="border-0") for name in list_of_names]
    return staged_data, file_list_display, False

@app.callback(Output("upload-feedback-div", "children", allow_duplicate=True), Input("process-upload-btn", "n_clicks"), State("staged-files-store", "data"), prevent_initial_call=True)
def save_staged_files(n_clicks, staged_data):
    if not n_clicks or not staged_data: return no_update
    saved_files = []
    for file_data in staged_data:
        try:
            name, content = file_data['filename'], file_data['contents']
            content_type, content_string = content.split(',')
            decoded = base64.b64decode(content_string)
            if not os.path.exists(rag_manager.KNOWLEDGE_BASE_DIR): os.makedirs(rag_manager.KNOWLEDGE_BASE_DIR)
            file_path = os.path.join(rag_manager.KNOWLEDGE_BASE_DIR, name)
            with open(file_path, "wb") as f: f.write(decoded)
            saved_files.append(name)
        except Exception as e: return dbc.Alert(f"Erro ao salvar o arquivo {name}: {e}", color="danger")
    return dbc.Alert(f"{len(saved_files)} arquivo(s) processado(s): {', '.join(saved_files)}", color="success", duration=4000)

@app.callback(Output("upload-feedback-div", "children", allow_duplicate=True), Input({'type': 'delete-btn', 'index': ALL}, 'n_clicks'), prevent_initial_call=True)
def delete_file_callback(n_clicks):
    if not any(n_clicks): return no_update
    triggered_id = callback_context.triggered_id
    if triggered_id:
        file_to_delete = triggered_id['index']
        file_path = os.path.join(rag_manager.KNOWLEDGE_BASE_DIR, file_to_delete)
        try:
            os.remove(file_path)
            return dbc.Alert(f"Arquivo '{file_to_delete}' deletado com sucesso!", color="success", dismissable=True, duration=4000)
        except Exception as e: return dbc.Alert(f"Erro ao deletar o arquivo: {e}", color="danger", dismissable=True)
    return no_update

@app.callback(Output("upload-feedback-div", "children", allow_duplicate=True), Input("process-kb-btn", "n_clicks"), prevent_initial_call=True)
def process_knowledge_base_callback(n_clicks):
    if n_clicks:
        try:
            if rag_manager.process_knowledge_base(): return dbc.Alert("Base de conhecimento processada e Bob atualizado!", color="success", dismissable=True, duration=4000)
            else: return dbc.Alert("Nenhum documento para processar.", color="warning", dismissable=True, duration=4000)
        except Exception as e: return dbc.Alert(f"Ocorreu um erro durante o processamento: {e}", color="danger", dismissable=True)
    return no_update

@app.callback(Output("document-list-group", "children"), [Input("url", "pathname"), Input("upload-feedback-div", "children")])
def update_document_list(pathname, upload_feedback):
    if pathname == "/base-de-conhecimento":
        if not os.path.exists(rag_manager.KNOWLEDGE_BASE_DIR): os.makedirs(rag_manager.KNOWLEDGE_BASE_DIR)
        files = [f for f in os.listdir(rag_manager.KNOWLEDGE_BASE_DIR) if f.endswith((".pdf", ".docx", ".txt"))]
        if not files: return dbc.ListGroupItem("Nenhum documento na base de conhecimento.")
        document_items = [dbc.ListGroupItem([dbc.Row([dbc.Col(html.Div([html.I(className="bi bi-file-earmark-text-fill text-primary me-2"), file]), width=8), dbc.Col(dbc.Badge("Ativo", color="success"), width="auto"), dbc.Col(dbc.Button("🗑️", id={'type': 'delete-btn', 'index': file}, color="light", size="sm"), width="auto")], align="center")]) for file in files]
        return document_items
    return []

@app.callback(Output("stats-list-group", "children"), [Input("url", "pathname"), Input("upload-feedback-div", "children")])
def update_stats_card(pathname, feedback):
    if pathname == "/base-de-conhecimento":
        total_docs, processing_docs, active_docs, last_update_str = 0, 0, 0, "N/A"
        marker_file = os.path.join(rag_manager.KNOWLEDGE_BASE_DIR, '.last_processed')
        last_processed_time = 0
        if os.path.exists(marker_file):
            last_processed_time = os.path.getmtime(marker_file)
            last_update_str = datetime.datetime.fromtimestamp(last_processed_time).strftime('%d/%m/%Y %H:%M')
        if os.path.exists(rag_manager.KNOWLEDGE_BASE_DIR):
            files = [f for f in os.listdir(rag_manager.KNOWLEDGE_BASE_DIR) if f.endswith((".pdf", ".docx", ".txt"))]
            total_docs = len(files)
            for file in files:
                file_path = os.path.join(rag_manager.KNOWLEDGE_BASE_DIR, file)
                if os.path.getmtime(file_path) > last_processed_time: processing_docs += 1
            active_docs = total_docs - processing_docs
        stats_items = [
            dbc.ListGroupItem(["Total de Documentos", dbc.Badge(str(total_docs), color="primary", className="ms-1")], className="d-flex justify-content-between"),
            dbc.ListGroupItem(["Documentos Ativos", dbc.Badge(str(active_docs), color="success", className="ms-1")], className="d-flex justify-content-between"),
            dbc.ListGroupItem(["Processando", dbc.Badge(str(processing_docs), color="warning" if processing_docs > 0 else "secondary", className="ms-1")], className="d-flex justify-content-between"),
            dbc.ListGroupItem(["Última Atualização", dbc.Badge(last_update_str, color="info", className="ms-1")], className="d-flex justify-content-between"),
        ]
        return stats_items
    return []

@app.callback(
    [Output("setting-agent-name", "value"),
     Output("setting-welcome-message", "value"),
     Output("setting-chat-color", "value"),
     Output("setting-feed-url", "value"),  # <--- NOVO OUTPUT (Campo da URL)
     Output("setting-auto-response", "value"),
     Output("setting-auto-escalation", "value"),
     Output("setting-log-conversation", "value")],
    Input("url", "pathname")
)
def load_settings_on_page_load(pathname):
    if pathname == "/configuracoes":
        # Busca os dados no banco
        agent_name = database.get_setting("agent_name", default="Bob")
        welcome_message = database.get_setting("welcome_message", default="Olá! Tudo bem? Como posso te ajudar hoje?")
        chat_color = database.get_setting("chat_color", default="#526A86")
        feed_url = database.get_setting("product_feed_url", default="") # <--- BUSCA A URL NO BANCO
        
        auto_response = database.get_setting("auto_response", default="True") == "True"
        auto_escalation = database.get_setting("auto_escalation", default="True") == "True"
        log_conversation = database.get_setting("log_conversation", default="True") == "True"
        
        # Retorna todos os valores, INCLUINDO a feed_url na ordem correta
        return agent_name, welcome_message, chat_color, feed_url, auto_response, auto_escalation, log_conversation
    
    # Se não for a página certa, não atualiza nada (agora são 7 itens)
    return [no_update] * 7

@app.callback(
    Output("upload-feedback-div", "children", allow_duplicate=True),
    Input("save-settings-btn", "n_clicks"),
    [State("setting-agent-name", "value"),
     State("setting-welcome-message", "value"),
     State("setting-chat-color", "value"),
     State("setting-feed-url", "value"), # <--- NOVO STATE (Lê o que foi digitado)
     State("setting-auto-response", "value"),
     State("setting-auto-escalation", "value"),
     State("setting-log-conversation", "value")],
    prevent_initial_call=True
)
def save_settings_on_click(n_clicks, name, welcome, color, feed_url, resp, escal, log): # <--- RECEBE feed_url
    if n_clicks:
        try:
            database.set_setting("agent_name", name)
            database.set_setting("welcome_message", welcome)
            database.set_setting("chat_color", color)
            database.set_setting("product_feed_url", feed_url) # <--- SALVA NO BANCO
            database.set_setting("auto_response", str(resp))
            database.set_setting("auto_escalation", str(escal))
            database.set_setting("log_conversation", str(log))
            return dbc.Alert("Configurações salvas com sucesso!", color="success", duration=3000)
        except Exception as e:
            return dbc.Alert(f"Erro ao salvar configurações: {e}", color="danger", duration=5000)
    return no_update

@app.callback(
    [Output("avatar-preview", "src"), Output("sidebar-avatar", "src"), Output("upload-feedback-div", "children", allow_duplicate=True)], # <-- CORRIGIDO (sem o header-avatar)
    Input("upload-avatar", "contents"),
    prevent_initial_call=True
)
def update_avatar(contents):
    if contents:
        try:
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            avatar_path = os.path.join('assets', 'bob_avatar.jpg')
            if not os.path.exists('assets'): os.makedirs('assets')
            with open(avatar_path, 'wb') as f: f.write(decoded)
            feedback_alert = dbc.Alert("Avatar atualizado com sucesso!", color="success", duration=3000)
            new_src = f"{app.get_asset_url('bob_avatar.jpg')}?t={time.time()}"
            return new_src, new_src, feedback_alert # <-- CORRIGIDO (3 retornos)
        except Exception as e: return no_update, no_update, dbc.Alert(f"Erro ao salvar avatar: {e}", color="danger", duration=5000)
    return no_update, no_update, no_update

@app.callback(
    [Output("filter-modal", "is_open"),
     Output("filter-date-range", "start_date"),
     Output("filter-date-range", "end_date")],
    [Input("open-filter-modal-btn", "n_clicks"),
     Input("apply-filter-btn", "n_clicks"),
     Input("clear-filter-btn", "n_clicks")],
    [State("filter-modal", "is_open"),
     State("filter-date-range", "start_date"),
     State("filter-date-range", "end_date")],
    prevent_initial_call=True
)
def toggle_filter_modal(n_open, n_apply, n_clear, is_open, start, end):
    ctx = callback_context
    trigger_id = ctx.triggered_id

    if trigger_id == "open-filter-modal-btn":
        return not is_open, start, end
    
    if trigger_id == "apply-filter-btn":
        return False, start, end # Fecha o modal e mantém as datas para o filtro
        
    if trigger_id == "clear-filter-btn":
        return False, None, None # Fecha o modal e LIMPA as datas visualmente
        
    return is_open, start, end

@app.callback(Output("download-conversations-csv", "data"), Input("export-conversations-btn", "n_clicks"), prevent_initial_call=True)
def export_conversations(n_clicks):
    if n_clicks:
        all_conversations = database.get_all_conversations_for_export()
        data_list = [{"id": convo.id, "session_id": convo.session_id, "timestamp_utc": convo.timestamp.isoformat(), "role": convo.role, "content": convo.content} for convo in all_conversations]
        if not data_list: return no_update
        df = pd.DataFrame(data_list)
        return dcc.send_data_frame(df.to_csv, "historico_conversas.csv", index=False, encoding='utf-8-sig')
    return no_update

# --- CALLBACK PARA ATUALIZAÇÃO MANUAL DO FEED ---
@app.callback(
    Output("feed-update-status", "children"),
    Input("force-update-feed-btn", "n_clicks"),
    prevent_initial_call=True
)
def force_feed_update(n_clicks):
    if n_clicks:
        # Chama a função do arquivo que criamos
        success, msg = feed_manager.process_product_feed()
        
        # Define a cor da mensagem (Verde se sucesso, Vermelho se falha)
        color = "text-success" if success else "text-danger"
        
        return html.Span(msg, className=color)
    return ""

# --- Ponto de Entrada ---
if __name__ == '__main__':
    if not os.path.exists('assets'): os.makedirs('assets')
    database.init_db()

    # --- INÍCIO DA ADIÇÃO: AGENDADOR DE TAREFAS ---
    # Configura o agendador para rodar em segundo plano
    scheduler = BackgroundScheduler()
    # Adiciona a tarefa: rodar 'process_product_feed' a cada 24 horas
    scheduler.add_job(func=feed_manager.process_product_feed, trigger="interval", hours=24)
    scheduler.start()
    # --- FIM DA ADIÇÃO ---

    app.run(debug=True, use_reloader=False, port=8050)
