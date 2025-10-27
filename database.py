# database.py
import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, MetaData
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from sqlalchemy import func, desc 
from zoneinfo import ZoneInfo

# --- Configuração do Banco de Dados ---
DATABASE_FILE = "bob_database.sqlite"
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

# Cria o "motor" de conexão com o banco de dados
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Cria uma sessão para interagir com o banco
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para a criação dos nossos modelos (tabelas)
Base = declarative_base()


# --- Definição das Tabelas (Modelos) ---

class Conversation(Base):
    """
    Modelo da tabela que irá armazenar cada turno da conversa.
    """
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    role = Column(String) # 'user' ou 'assistant'
    content = Column(Text)

class Settings(Base):
    """
    Modelo da tabela que irá armazenar as configurações do sistema (chave-valor).
    """
    __tablename__ = "settings"
    
    key = Column(String, primary_key=True, index=True)
    value = Column(String)

# --- Funções de Utilitário ---

def init_db():
    """
    Cria as tabelas no banco de dados se elas ainda não existirem.
    """
    print("Inicializando o banco de dados...")
    # Cria a pasta 'database' se não existir
    db_dir = os.path.dirname(DATABASE_FILE)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
        
    Base.metadata.create_all(bind=engine)
    print("Banco de dados inicializado com sucesso.")


def log_conversation_turn(session_id: str, role: str, content: str):
    """
    Salva um turno da conversa (uma mensagem do usuário ou do assistente)
    no banco de dados.
    """
    db = SessionLocal()
    try:
        new_turn = Conversation(
            session_id=session_id,
            role=role,
            content=content
        )
        db.add(new_turn)
        db.commit()
    finally:
        db.close()

def get_first_user_message(db_session, session_id: str) -> str:
    """Busca a primeira mensagem de um usuário para uma dada sessão."""
    first_message = (
        db_session.query(Conversation)
        .filter(Conversation.session_id == session_id, Conversation.role == 'user')
        .order_by(Conversation.timestamp.asc())
        .first()
    )
    if first_message and first_message.content:
        # Limita o tamanho da prévia para não quebrar o layout
        return (first_message.content[:70] + '...') if len(first_message.content) > 70 else first_message.content
    return "Conversa iniciada sem mensagem"



def get_conversations_summary():
    """
    Busca no banco de dados um resumo de todas as sessões de conversa,
    incluindo a primeira mensagem do usuário.
    """
    db = SessionLocal()
    try:
        summary_query = (
            db.query(
                Conversation.session_id,
                func.count(Conversation.id).label("message_count"),
                func.min(Conversation.timestamp).label("start_time")
            )
            .group_by(Conversation.session_id)
            .order_by(desc("start_time"))
            .all()
        )
        
        summary_list = []
        utc_zone = ZoneInfo("UTC")
        local_zone = ZoneInfo("America/Sao_Paulo")

        for session_id, message_count, start_time in summary_query:
            aware_utc_time = start_time.replace(tzinfo=utc_zone)
            local_time = aware_utc_time.astimezone(local_zone)
            
            # Busca a primeira mensagem do usuário para esta sessão
            first_message = get_first_user_message(db, session_id)
            
            summary_list.append({
                "session_id": session_id,
                "first_message": first_message,
                "message_count": message_count,
                "start_time_local": local_time
            })
            
        return summary_list

    finally:
        db.close()

def count_sessions_today():
    """Conta o número de sessões de conversa únicas iniciadas hoje (em UTC)."""
    db = SessionLocal()
    try:
        today_start_utc = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        count = (
            db.query(func.count(Conversation.session_id.distinct()))
            .filter(Conversation.timestamp >= today_start_utc)
            .scalar()
        )
        return count or 0
    finally:
        db.close()

def get_conversation_by_session_id(session_id: str):
    """
    Busca todos os turnos de uma conversa específica, ordenados por tempo.
    """
    db = SessionLocal()
    try:
        conversation_turns = (
            db.query(Conversation)
            .filter(Conversation.session_id == session_id)
            .order_by(Conversation.timestamp.asc())
            .all()
        )
        return conversation_turns
    finally:
        db.close()

def get_daily_interaction_counts():
    """Conta o número total de mensagens (usuário + assistente) por dia."""
    db = SessionLocal()
    try:
        # Consulta para agrupar por data e contar as mensagens
        counts = (
            db.query(
                func.date(Conversation.timestamp).label("date"),
                func.count(Conversation.id).label("count")
            )
            .group_by(func.date(Conversation.timestamp))
            .order_by(func.date(Conversation.timestamp))
            .all()
        )
        # Retorna uma lista de tuplas (data, contagem)
        return counts
    finally:
        db.close()

def get_top_questions(limit=5):
    """Busca as perguntas mais frequentes feitas pelos usuários."""
    db = SessionLocal()
    try:
        top_questions = (
            db.query(
                Conversation.content,
                func.count(Conversation.content).label("count")
            )
            .filter(Conversation.role == 'user')
            .group_by(Conversation.content)
            .order_by(desc("count"))
            .limit(limit)
            .all()
        )
        # Retorna uma lista de tuplas (pergunta, contagem)
        return top_questions
    finally:
        db.close()

def get_setting(key: str, default: str = None):
    """Busca o valor de uma configuração no banco de dados."""
    db = SessionLocal()
    try:
        setting = db.query(Settings).filter(Settings.key == key).first()
        return setting.value if setting else default
    finally:
        db.close()

def set_setting(key: str, value: str):
    """Salva ou atualiza o valor de uma configuração no banco de dados."""
    db = SessionLocal()
    try:
        setting = db.query(Settings).filter(Settings.key == key).first()
        if setting:
            setting.value = value
        else:
            new_setting = Settings(key=key, value=value)
            db.add(new_setting)
        db.commit()
    finally:
        db.close()

# Nova função para buscar todas as configurações de uma vez
def get_all_settings():
    """Busca TODAS as configurações do banco de dados e retorna um dicionário."""
    db = SessionLocal()
    try:
        settings = db.query(Settings).all()
        return {s.key: s.value for s in settings}
    finally:
        db.close()

# --- Bloco de Execução Principal (para testes) ---
if __name__ == "__main__":
    # Se você executar 'python database.py', ele criará o arquivo do banco e as tabelas
    print("Criando o banco de dados e as tabelas necessárias...")
    init_db()
    print("Processo concluído.")