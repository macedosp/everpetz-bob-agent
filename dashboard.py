# dashboard.py
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State, ALL, callback_context
import plotly.graph_objects as go
import os
import rag_manager
import base64
import datetime
import time
import uuid

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

# --- Estilos ---
SIDEBAR_STYLE = {"position": "fixed", "top": 0, "left": 0, "bottom": 0, "width": "18rem", "padding": "2rem 1rem", "background-color": "white", "border-right": "1px solid #dee2e6"}
CONTENT_STYLE = {"margin-left": "18rem", "padding": "2rem 1rem", "background-color": "#f8f9fa", "min-height": "100vh"}

# --- Função Auxiliar para criar as bolhas de conversa ---
def create_chat_bubble(role, content, is_thinking=False):
    if role == 'user':
        bubble = dbc.Card(dbc.CardBody(dcc.Markdown(content)), color="secondary", inverse=True, style={"borderRadius": "20px 20px 5px 20px"})
        return dbc.Row(dbc.Col(bubble, width={"size": 8, "offset": 4}), className="g-0 mb-2")
    else: # assistant
        content_display = dbc.Spinner(size="sm") if is_thinking else dcc.Markdown(content, dangerously_allow_html=False)
        bubble = dbc.Card(dbc.CardBody(content_display), color="light", style={"borderRadius": "20px 20px 20px 5px"})
        return dbc.Row(dbc.Col(bubble, width=8), className="g-0 mb-2")

# --- Layouts das Páginas ---
dashboard_layout = html.Div([
    dbc.Row([
        dbc.Col([html.H2("Dashboard"), html.P("Visão geral do desempenho do Bob", className="text-muted")], width=9),
        dbc.Col(dbc.Button("Testar Chat", id="open-chat-modal-btn", color="primary"), width=3, className="d-flex justify-content-end align-items-center"),
    ], className="mb-4"),
    dbc.Row([
        dbc.Col(dbc.Card([dbc.CardBody([html.H4("Total de Documentos"), html.P(id="kpi-total-docs", className="h2")])], className="shadow-sm")),
        dbc.Col(dbc.Card([dbc.CardBody([html.H4("Conversas Hoje"), html.P(id="kpi-conversas-hoje", className="h2")])], className="shadow-sm")),
        dbc.Col(dbc.Card([dbc.CardBody([html.H4("Taxa de Resolução"), html.P("0%", className="h2")])], className="shadow-sm")),
        dbc.Col(dbc.Card([dbc.CardBody([html.H4("Satisfação"), html.P("0.0", className="h2")])], className="shadow-sm")),
    ], className="mb-4"),
    dbc.Row([
        dbc.Col(dbc.Card([dbc.CardBody([html.H4("Interações por Dia", className="card-title"), dcc.Graph(id="interactions-chart-graph", figure=go.Figure().update_layout(margin=dict(l=0, r=0, t=0, b=0)))])], className="shadow-sm"), width=7),
        dbc.Col(dbc.Card([dbc.CardBody([html.H4("Questões Mais Frequentes", className="card-title"), dbc.ListGroup(id="top-questions-list", flush=True)])], className="shadow-sm"), width=5),
    ]),
    dbc.Modal([
    # O ID foi adicionado ao ModalHeader.
    # O conteúdo foi envolvido em um parâmetro 'children' para o ID funcionar corretamente.
    dbc.ModalHeader(
        id="chat-modal-header", 
        children=[
            dbc.Row([
                dbc.Col(html.Img(id="chat-header-avatar", src=app.get_asset_url('bob_avatar.jpg'), className="rounded-circle", style={'width': '40px', 'height': '40px'}), width="auto"),
                dbc.Col([
                    html.H5("Bob", id="chat-header-agent-name", className="mb-0 text-white"),
                    html.P([html.Span("●", style={"color": "limegreen"}), " Online • Teste"], className="small text-white-50 mb-0")
                ])
            ], align="center")
        ], 
        close_button=True, 
        className="text-white"
    ),
    dbc.ModalBody(html.Div(id="modal-chat-history-div", style={"height": "400px", "overflowY": "auto", "padding": "10px"})),
    dbc.ModalFooter(html.Div([
        html.Div([
            dbc.Button("Como funciona?", id="quick-reply-btn-1", outline=True, color="secondary", size="sm", className="me-2"),
            dbc.Button("Quero vender", id="quick-reply-btn-2", outline=True, color="secondary", size="sm", className="me-2"),
            dbc.Button("Produtos para pets", id="quick-reply-btn-3", outline=True, color="secondary", size="sm"),
        ], className="text-center mb-3"),
        dbc.Row([
            dbc.Col(dbc.Input(id="modal-chat-input", placeholder="Digite sua mensagem...", n_submit=0, className="rounded-pill")),
            # O botão de envio já tem o ID correto, nenhuma mudança aqui.
            dbc.Col(dbc.Button(html.I(className="bi bi-send-fill"), id="modal-chat-submit-btn", color="primary", n_clicks=0, className="rounded-circle"), width="auto", className="ps-0")
        ], align="center")
    ], style={"width": "100%"}))
], id="chat-modal", is_open=False, scrollable=True, centered=True, className="rounded-4"),
    dcc.Store(id='modal-chat-history-store', data=[]),
    dcc.Store(id='chat-session-id-store', data=None),
    dcc.Store(id='chat-session-settings-store', data={}),
])

base_conhecimento_layout = html.Div([dcc.Store(id='staged-files-store'), dbc.Row([dbc.Col([html.H2("Base de Conhecimento"), html.P("Gerencie os documentos e informações do Bob", className="text-muted")]), dbc.Col(dbc.Button("Adicionar Documento", id="open-upload-modal-btn", color="primary"), className="d-flex justify-content-end align-items-center")], className="mb-4"), dbc.Row([dbc.Col(dbc.Card([dbc.CardHeader("Documentos Carregados"), dbc.CardBody(dbc.ListGroup(id="document-list-group", flush=True))], className="shadow-sm"), width=8), dbc.Col([dbc.Card([dbc.CardHeader("Estatísticas"), dbc.CardBody(dbc.ListGroup(id="stats-list-group", flush=True))], className="shadow-sm mb-4"), dbc.Card([dbc.CardHeader("Ações"), dbc.CardBody([dbc.Button("Processar Base de Conhecimento", id="process-kb-btn", color="primary", className="w-100"), html.P("Clique para que o Bob estude os documentos e atualize sua memória.", className="text-muted small mt-2")])], className="shadow-sm mb-4"), dbc.Card([dbc.CardHeader("Formatos Suportados"), dbc.CardBody([dbc.ListGroup([dbc.ListGroupItem("PDF"), dbc.ListGroupItem("TXT"), dbc.ListGroupItem("DOCX")], flush=True), html.P("Tamanho máximo: 10MB por arquivo", className="text-muted small mt-3")])], className="shadow-sm")], width=4)]), dbc.Modal([dbc.ModalHeader(html.Div([html.H4("Adicionar Documento"), html.P("Carregue novos documentos para a base de conhecimento do Bob", className="text-muted small mb-0")]), close_button=True), dbc.ModalBody([dcc.Upload(id='upload-data', children=html.Div([html.I(className="bi bi-upload display-4 text-muted"), html.P("Arraste arquivos aqui ou clique para selecionar", className="mt-3 mb-1"), dbc.Button([html.I(className="bi bi-upload me-2"), "Selecionar Arquivos"], outline=True, color="secondary", className="mt-3")], className="d-flex flex-column justify-content-center align-items-center p-4"), style={'borderWidth': '2px', 'borderStyle': 'dashed', 'borderRadius': '10px', 'minHeight': '200px'}, multiple=True, accept='.pdf,.docx,.txt'), html.Div(id='staged-files-list', className="mt-3")]), dbc.ModalFooter([dbc.Button("Cancelar", id="close-upload-modal-btn", color="light"), dbc.Button("Processar", id="process-upload-btn", color="primary", disabled=True)])], id="upload-modal", is_open=False, size="lg")])
conversas_layout = html.Div([dbc.Row([dbc.Col([html.H2("Conversas"), html.P("Acompanhe as interações do Bob com os usuários", className="text-muted")]), dbc.Col(dbc.ButtonGroup([dbc.Button([html.I(className="bi bi-funnel-fill me-2"), "Filtros"], outline=True, color="secondary"), dbc.Button([html.I(className="bi bi-download me-2"), "Exportar"], outline=True, color="secondary")]), className="d-flex justify-content-end align-items-center")], className="mb-4"), dbc.Card([dbc.CardHeader("Histórico de Conversas"), dbc.CardBody(dbc.ListGroup(id="conversation-list-group", flush=True))], className="shadow-sm")])
usuarios_layout = html.Div([dbc.Row([dbc.Col([html.H2("Usuários Autorizados"), html.P("Gerencie quem pode acessar o Bob Admin", className="text-muted")]), dbc.Col(dbc.Button([html.I(className="bi bi-plus-lg me-2"), "Adicionar Usuário"], color="primary"), className="d-flex justify-content-end align-items-center")], className="mb-4"), dbc.Card([dbc.CardBody([html.Div([html.I(className="bi bi-person-circle display-1 text-muted"), html.H3("Nenhum usuário autorizado", className="mt-4"), html.P("Comece adicionando usuários que podem acessar o Bob Admin.", className="text-muted"), dbc.Button([html.I(className="bi bi-plus-lg me-2"), "Adicionar Primeiro Usuário"], color="primary", className="mt-3")], className="text-center p-5")])], className="shadow-sm")])

configuracoes_layout = html.Div([
    dbc.Row([dbc.Col([html.H2("Configurações"), html.P("Ajuste o comportamento e aparência do Bob", className="text-muted")])], className="mb-4"),
    dbc.Card([
        dbc.CardHeader(html.H4("⚙️ Configurações do Sistema")),
        dbc.CardBody([
            dbc.Row([
                dbc.Col(dbc.Card([
                    dbc.CardHeader("Personalização"), 
                    dbc.CardBody([
                        # --- CORREÇÃO DE LAYOUT DO AVATAR ---
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Avatar do Agente"),
                                html.Div([
                                    # ... (dentro do layout de configurações)
dcc.Upload(
    id='upload-avatar',
    children=html.Div([
        'Arraste ou',
        html.A('selecione')
    # Usamos classes Flexbox para centralizar tudo perfeitamente
    ], className="d-flex flex-column justify-content-center align-items-center h-100"),
    style={
        'width': '120px', 'height': '120px', 'borderWidth': '2px',
        'borderStyle': 'dashed', 'borderRadius': '50%', 'textAlign': 'center',
        'position': 'relative', 'display': 'inline-block'
    },
    accept='image/*'
),
# ...
                                    html.Img(id='avatar-preview', src=app.get_asset_url('bob_avatar.jpg'), style={'width': '120px', 'height': '120px', 'borderRadius': '50%', 'objectFit': 'cover', 'position': 'absolute', 'top': 0, 'left': 0, 'zIndex': -1})
                                ], style={'position': 'relative', 'width': '120px', 'height': '120px', 'margin': 'auto'}, className="mb-3")
                            ], className="text-center"),
                        ]),
                        html.Hr(),
                        dbc.Label("Nome do Agente"),
                        dbc.Input(id="setting-agent-name", type="text", className="mb-3"),
                        dbc.Label("Mensagem de Boas-vindas"),
                        dbc.Textarea(id="setting-welcome-message", style={"height": "100px"}, className="mb-3"),

                        # --- NOVA SEÇÃO DE CORES ---
                        dbc.Label("Cor do Chat"),
                        dbc.RadioItems(
                            id="setting-chat-color",
                            options=[
                                {"label": "", "value": "#526A86"},
                                {"label": "", "value": "#3C6584"},
                                {"label": "", "value": "#D1751C"},
                                {"label": "", "value": "#ED7700"},
                                {"label": "", "value": "#9B9B9C"},
                            ],
                            value="#526A86",  # Cor padrão
                            inline=True,
                            className="color-selector mb-3", # Classe principal para CSS
                            inputClassName="d-none",        # Esconde input padrão
                            labelClassName="color-swatch",  # Classe para estilizar label
                            labelCheckedClassName="checked", # (Opcional, se precisar de estilo extra ao checar)
                        ),
                        # --- FIM DA SEÇÃO DE CORES ---
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

# --- Componentes Principais e Layout Geral ---
sidebar = html.Div([html.Div([html.Img(id='sidebar-avatar', src=app.get_asset_url('bob_avatar.jpg'), className="rounded-circle me-2", style={'width': '80px', 'height': '80px'}), html.P("Bob Admin", className="lead", style={'margin-top': '10px', 'font-weight': 'bold'}), html.P("Agente Everpetz", style={'font-size': '0.9rem'})], className="text-center"), html.Hr(), dbc.Nav([dbc.NavLink("📊 Dashboard", href="/", active="exact"), dbc.NavLink("📚 Base de Conhecimento", href="/base-de-conhecimento", active="exact"), dbc.NavLink("💬 Conversas", href="/conversas", active="exact"), dbc.NavLink("👤 Usuários Autorizados", href="/usuarios", active="exact"), dbc.NavLink("⚙️ Configurações", href="/configuracoes", active="exact")], vertical=True, pills=True)], style=SIDEBAR_STYLE)
content = html.Div(id="page-content", style=CONTENT_STYLE)
app.layout = html.Div([
    dcc.Location(id="url"),
    sidebar,
    dcc.Loading(id="loading-feedback", type="default", children=html.Div(id="upload-feedback-div", style={'position': 'fixed', 'top': '10px', 'right': '10px', 'zIndex': 1050})),
    dcc.Store(id='signal-store'),
    content
])

# --- CALLBACKS ---
@app.callback(Output("page-content", "children"), Input("url", "pathname"))
def render_page_content(pathname):
    # ... (código do roteador permanece o mesmo)
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
            dbc.Card(dbc.CardBody(chat_history_bubbles)),
        ])
        return detail_layout
    elif pathname == "/usuarios": return usuarios_layout
    elif pathname == "/configuracoes": return configuracoes_layout
    return html.Div([html.H1("404: Not found"), html.P(f"O caminho {pathname} não foi reconhecido...")])

# --- Callbacks do Chat Modal ---
# dashboard.py

@app.callback(
    [Output("chat-modal", "is_open"),
     Output('modal-chat-history-store', 'data', allow_duplicate=True),
     Output("modal-chat-history-div", "children", allow_duplicate=True),
     Output("chat-session-id-store", "data"),
     Output("chat-session-settings-store", "data"),
     Output("chat-header-agent-name", "children"),
     Output("chat-header-avatar", "src"),
     Output("chat-modal-header", "style"), # <-- Nova Saída (estilo do header)
     Output("modal-chat-submit-btn", "style")],# <-- Nova Saída (estilo do botão)
    Input("open-chat-modal-btn", "n_clicks"),
    State("chat-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_chat_modal_and_init(n_clicks, is_open):
    if n_clicks:
        session_settings = database.get_all_settings()
        agent_name = session_settings.get("agent_name", "Bob")
        welcome_text = session_settings.get("welcome_message", "Olá! Como posso te ajudar?")
        chat_color = session_settings.get("chat_color", "#526A86") # Pega a cor
        
        welcome_message = {"role": "assistant", "content": welcome_text}
        welcome_bubble = create_chat_bubble(welcome_message['role'], welcome_message['content'])
        new_session_id = str(uuid.uuid4())
        avatar_src = f"{app.get_asset_url('bob_avatar.jpg')}?t={time.time()}"
        
        # Define os estilos baseados na cor
        header_style = {'backgroundColor': chat_color, 'color': 'white'}
        button_style = {'backgroundColor': chat_color, 'borderColor': chat_color} # Para o botão
        
        # Retorna 9 itens agora
        return (not is_open, [welcome_message], [welcome_bubble], new_session_id, 
                session_settings, agent_name, avatar_src, header_style, button_style)
        
    # Retorna no_update para todas as saídas
    no_updates = [dash.no_update] * 9
    return is_open, *no_updates[1:]

@app.callback(
    [Output("modal-chat-input", "value", allow_duplicate=True),
     Output("modal-chat-submit-btn", "n_clicks", allow_duplicate=True)],
    [Input("quick-reply-btn-1", "n_clicks"),
     Input("quick-reply-btn-2", "n_clicks"),
     Input("quick-reply-btn-3", "n_clicks")],
    State("modal-chat-submit-btn", "n_clicks"),
    prevent_initial_call=True
)
def handle_quick_replies(n1, n2, n3, current_submit_clicks):
    ctx = callback_context
    if not ctx.triggered: return dash.no_update, dash.no_update
    button_id = ctx.triggered_id
    if button_id == "quick-reply-btn-1": question = "Como funciona?"
    elif button_id == "quick-reply-btn-2": question = "Quero vender"
    elif button_id == "quick-reply-btn-3": question = "Produtos para pets"
    else: return dash.no_update, dash.no_update
    return question, (current_submit_clicks or 0) + 1

@app.callback(
    [Output("modal-chat-history-store", "data", allow_duplicate=True),
     Output("modal-chat-input", "value", allow_duplicate=True)],
    [Input("modal-chat-submit-btn", "n_clicks"),
     Input("modal-chat-input", "n_submit")],
    [State("modal-chat-input", "value"),
     State("modal-chat-history-store", "data")],
    prevent_initial_call=True
)
def handle_chat_submission(submit_clicks, enter_submissions, user_input, history):
    if not user_input: return dash.no_update, dash.no_update
    history = history or []
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": "thinking..."})
    return history, ""

@app.callback(
    [Output("modal-chat-history-store", "data", allow_duplicate=True),
     Output("signal-store", "data", allow_duplicate=True)], # <-- MUDANÇA AQUI
    Input("modal-chat-history-store", "data"),
    [State("chat-session-id-store", "data"),
     State("chat-session-settings-store", "data")],
    prevent_initial_call=True,
    background=True
)
def run_agent_query(history, session_id, session_settings):
    if history and history[-1].get("content") == "thinking...":
        user_query = history[-2].get("content")
        agent_response_text = agent.get_response(user_query=user_query, chat_history=history[:-2], session_settings=session_settings)
        if session_id:
            database.log_conversation_turn(session_id=session_id, role='user', content=user_query)
            database.log_conversation_turn(session_id=session_id, role='assistant', content=agent_response_text)
        history[-1]["content"] = agent_response_text
        
        # O sinal agora é enviado para o Store invisível
        return history, f"conversation_updated_{time.time()}"
    return dash.no_update, dash.no_update

@app.callback(Output("modal-chat-history-div", "children"), Input("modal-chat-history-store", "data"))
def render_chat_from_store(history):
    history = history or []
    return [create_chat_bubble(msg['role'], msg['content'], is_thinking=(msg['content'] == 'thinking...')) for msg in history]

# --- Outros Callbacks ---
# dashboard.py

@app.callback(
    [Output("kpi-total-docs", "children"),
     Output("kpi-conversas-hoje", "children"),
     Output("interactions-chart-graph", "figure"),
     Output("top-questions-list", "children")],
    [Input("url", "pathname"), 
     Input("upload-feedback-div", "children"), # Continua escutando por uploads
     Input("signal-store", "data")]           # <-- NOVO INPUT
)
def update_dashboard_kpis(pathname, feedback, signal): # Adicionado 'signal'
    # O callback roda ao carregar a página OU ao receber um novo sinal/feedback
    if pathname == "/":
        # ... (a lógica interna da função permanece a mesma) ...
        total_docs = "0"
        if os.path.exists(rag_manager.KNOWLEDGE_BASE_DIR):
            try:
                files = [f for f in os.listdir(rag_manager.KNOWLEDGE_BASE_DIR) if f.endswith((".pdf", ".docx", ".txt"))]
                total_docs = str(len(files))
            except FileNotFoundError: pass
        
        conversas_hoje = str(database.count_sessions_today())
        
        interaction_data = database.get_daily_interaction_counts()
        dates = [row.date for row in interaction_data]
        counts = [row.count for row in interaction_data]
        chart_fig = go.Figure(data=[go.Scatter(x=dates, y=counts, mode='lines+markers')])
        chart_fig.update_layout(margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        
        top_questions = database.get_top_questions()
        if not top_questions:
            questions_list = dbc.ListGroupItem("Nenhuma pergunta registrada ainda.")
        else:
            questions_list = [dbc.ListGroupItem([ (q[:45] + '...') if len(q) > 45 else q, dbc.Badge(str(c), color="primary", pill=True, className="ms-1")], className="d-flex justify-content-between align-items-center") for q, c in top_questions]

        return total_docs, conversas_hoje, chart_fig, questions_list
    
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update

# dashboard.py

@app.callback(
    Output("conversation-list-group", "children"),
    [Input("url", "pathname"),
     Input("upload-feedback-div", "children"), # Continua escutando por uploads
     Input("signal-store", "data")]           # <-- NOVO INPUT
)
def update_conversations_list(pathname, feedback, signal): # Adicionado 'signal'
    # O callback roda se estivermos na página OU se receber um novo sinal/feedback
    triggered_id = callback_context.triggered_id
    if pathname == "/conversas" or triggered_id == 'signal-store':
        # ... (a lógica interna da função permanece a mesma) ...
        summaries = database.get_conversations_summary()
        if not summaries:
            return dbc.Card(dbc.CardBody(html.Div([html.I(className="bi bi-chat-off-fill display-3 text-muted"), html.H4("Nenhuma conversa registrada", className="mt-3")], className="text-center p-4")))
            
        conversation_items = [dcc.Link(dbc.ListGroupItem([dbc.Row([dbc.Col(html.I(className="bi bi-person-circle fs-3 text-muted"), width="auto", className="pe-0"), dbc.Col([html.H6(s['first_message'], className="mb-1 fw-bold"), html.Small(f"Sessão #{s['session_id'].split('_')[-1][:6]} • {s['start_time_local'].strftime('%d/%m/%Y, %H:%M')}", className="text-muted")], className="flex-grow-1"), dbc.Col(dbc.Badge("Ver Detalhes", color="light", text_color="primary", pill=True), width="auto")], align="center")]), href=f"/conversas/{s['session_id']}", style={"textDecoration": "none"}) for s in summaries]
        return conversation_items
        
    return dash.no_update

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
    if not n_clicks or not staged_data: return dash.no_update
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
        except Exception as e:
            return dbc.Alert(f"Erro ao salvar o arquivo {name}: {e}", color="danger")
    return dbc.Alert(f"{len(saved_files)} arquivo(s) processado(s): {', '.join(saved_files)}", color="success", duration=4000)

@app.callback(Output("upload-feedback-div", "children", allow_duplicate=True), Input({'type': 'delete-btn', 'index': ALL}, 'n_clicks'), prevent_initial_call=True)
def delete_file_callback(n_clicks):
    if not any(n_clicks): return dash.no_update
    triggered_id = callback_context.triggered_id
    if triggered_id:
        file_to_delete = triggered_id['index']
        file_path = os.path.join(rag_manager.KNOWLEDGE_BASE_DIR, file_to_delete)
        try:
            os.remove(file_path)
            return dbc.Alert(f"Arquivo '{file_to_delete}' deletado com sucesso!", color="success", dismissable=True, duration=4000)
        except Exception as e:
            return dbc.Alert(f"Erro ao deletar o arquivo: {e}", color="danger", dismissable=True)
    return dash.no_update

@app.callback(Output("upload-feedback-div", "children", allow_duplicate=True), Input("process-kb-btn", "n_clicks"), prevent_initial_call=True)
def process_knowledge_base_callback(n_clicks):
    if n_clicks:
        try:
            if rag_manager.process_knowledge_base():
                return dbc.Alert("Base de conhecimento processada e Bob atualizado!", color="success", dismissable=True, duration=4000)
            else:
                return dbc.Alert("Nenhum documento para processar.", color="warning", dismissable=True, duration=4000)
        except Exception as e:
            return dbc.Alert(f"Ocorreu um erro durante o processamento: {e}", color="danger", dismissable=True)
    return dash.no_update

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
                if os.path.getmtime(file_path) > last_processed_time:
                    processing_docs += 1
            active_docs = total_docs - processing_docs
        stats_items = [
            dbc.ListGroupItem(["Total de Documentos", dbc.Badge(str(total_docs), color="primary", className="ms-1")], className="d-flex justify-content-between"),
            dbc.ListGroupItem(["Documentos Ativos", dbc.Badge(str(active_docs), color="success", className="ms-1")], className="d-flex justify-content-between"),
            dbc.ListGroupItem(["Processando", dbc.Badge(str(processing_docs), color="warning" if processing_docs > 0 else "secondary", className="ms-1")], className="d-flex justify-content-between"),
            dbc.ListGroupItem(["Última Atualização", dbc.Badge(last_update_str, color="info", className="ms-1")], className="d-flex justify-content-between"),
        ]
        return stats_items
    return []

# Callbacks da Página de Configurações
# dashboard.py

@app.callback(
    [Output("setting-agent-name", "value"),
     Output("setting-welcome-message", "value"),
     Output("setting-chat-color", "value"), # <-- Nova Saída
     Output("setting-auto-response", "value"),
     Output("setting-auto-escalation", "value"),
     Output("setting-log-conversation", "value")],
    Input("url", "pathname")
)
def load_settings_on_page_load(pathname):
    if pathname == "/configuracoes":
        agent_name = database.get_setting("agent_name", default="Bob")
        welcome_message = database.get_setting("welcome_message", default="Olá! Tudo bem? Como posso te ajudar hoje?")
        chat_color = database.get_setting("chat_color", default="#526A86") # <-- Carrega a cor
        auto_response = database.get_setting("auto_response", default="True") == "True"
        auto_escalation = database.get_setting("auto_escalation", default="True") == "True"
        log_conversation = database.get_setting("log_conversation", default="True") == "True"
        
        return agent_name, welcome_message, chat_color, auto_response, auto_escalation, log_conversation # <-- Retorna a cor
        
    # Retorna dash.no_update para todas as saídas
    no_updates = [dash.no_update] * 6 
    return no_updates

@app.callback(
    Output("upload-feedback-div", "children", allow_duplicate=True),
    Input("save-settings-btn", "n_clicks"),
    [State("setting-agent-name", "value"),
     State("setting-welcome-message", "value"),
     State("setting-chat-color", "value"), # <-- Novo State
     State("setting-auto-response", "value"),
     State("setting-auto-escalation", "value"),
     State("setting-log-conversation", "value")],
    prevent_initial_call=True
)
def save_settings_on_click(n_clicks, name, welcome, color, resp, escal, log): # <-- Novo parâmetro 'color'
    if n_clicks:
        try:
            database.set_setting("agent_name", name)
            database.set_setting("welcome_message", welcome)
            database.set_setting("chat_color", color) # <-- Salva a cor
            database.set_setting("auto_response", str(resp))
            database.set_setting("auto_escalation", str(escal))
            database.set_setting("log_conversation", str(log))
            
            return dbc.Alert("Configurações salvas com sucesso!", color="success", duration=3000)
        except Exception as e:
            return dbc.Alert(f"Erro ao salvar configurações: {e}", color="danger", duration=5000)
    return dash.no_update

# --- NOVO CALLBACK PARA UPLOAD DO AVATAR ---
@app.callback(
    [Output("avatar-preview", "src"),
     Output("sidebar-avatar", "src"),
     Output("upload-feedback-div", "children", allow_duplicate=True)],
    Input("upload-avatar", "contents"),
    prevent_initial_call=True
)
def update_avatar(contents):
    if contents:
        try:
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            avatar_path = os.path.join('assets', 'bob_avatar.jpg')
            with open(avatar_path, 'wb') as f:
                f.write(decoded)
            
            feedback_alert = dbc.Alert("Avatar atualizado com sucesso!", color="success", duration=3000)
            
            # Força o recarregamento da imagem no navegador
            new_src = f"{app.get_asset_url('bob_avatar.jpg')}?t={time.time()}"
            
            return new_src, new_src, feedback_alert
            
        except Exception as e:
            return dash.no_update, dash.no_update, dbc.Alert(f"Erro ao salvar avatar: {e}", color="danger", duration=5000)
    
    return dash.no_update, dash.no_update, dash.no_update

# --- Ponto de Entrada ---
if __name__ == '__main__':
    if not os.path.exists('assets'):
        os.makedirs('assets')
    database.init_db()
    app.run(debug=True, use_reloader=False, port=8050)