# database.py
import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, MetaData, Boolean, Float
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from sqlalchemy import func, desc
from zoneinfo import ZoneInfo
from werkzeug.security import generate_password_hash, check_password_hash

# --- Configuração do Banco de Dados ---
DATABASE_FILE = "bob_database.sqlite"
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Tabelas (Modelos) ---

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    role = Column(String)
    content = Column(Text)

class Settings(Base):
    __tablename__ = "settings"
    key = Column(String, primary_key=True, index=True)
    value = Column(String)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_master = Column(Boolean, default=False)

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    session_id = Column(String, primary_key=True, index=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    is_resolved = Column(Boolean, default=None, nullable=True)
    satisfaction_score = Column(Integer, default=None, nullable=True)

# --- Funções de Utilitário ---

def init_db():
    db_dir = os.path.dirname(DATABASE_FILE)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
    Base.metadata.create_all(bind=engine)

# --- Funções de Conversa e Sessão ---

def register_session(session_id: str):
    db = SessionLocal()
    try:
        exists = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
        if not exists:
            session = ChatSession(session_id=session_id)
            db.add(session)
            db.commit()
    finally:
        db.close()

def log_conversation_turn(session_id: str, role: str, content: str):
    register_session(session_id)
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

def save_session_feedback(session_id: str, resolved: bool, score: int):
    db = SessionLocal()
    try:
        session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
        if session:
            session.is_resolved = resolved
            session.satisfaction_score = score
            db.commit()
            return True
        return False
    finally:
        db.close()

def get_conversation_by_session_id(session_id: str):
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

def get_first_user_message(db_session, session_id: str) -> str:
    first_message = db_session.query(Conversation).filter(Conversation.session_id == session_id, Conversation.role == 'user').order_by(Conversation.timestamp.asc()).first()
    if first_message and first_message.content: return (first_message.content[:70] + '...') if len(first_message.content) > 70 else first_message.content
    return "Conversa iniciada sem mensagem"

def get_conversations_summary(limit: int = None, start_date: str = None, end_date: str = None):
    db = SessionLocal()
    try:
        query = (
            db.query(
                Conversation.session_id,
                func.count(Conversation.id).label("message_count"),
                func.min(Conversation.timestamp).label("start_time")
            )
            .group_by(Conversation.session_id)
            .order_by(desc("start_time"))
        )

        if start_date and end_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(Conversation.timestamp >= start_dt)
            query = query.filter(Conversation.timestamp <= end_dt)

        if limit and not (start_date and end_date):
            query = query.limit(limit)

        summary_query = query.all()
        summary_list = []
        utc_zone = ZoneInfo("UTC")
        try:
            local_zone = ZoneInfo("America/Sao_Paulo")
        except:
            local_zone = utc_zone

        for session_id, message_count, start_time in summary_query:
            aware_utc_time = start_time.replace(tzinfo=utc_zone)
            local_time = aware_utc_time.astimezone(local_zone)
            first_message = get_first_user_message(db, session_id)
            summary_list.append({"session_id": session_id, "first_message": first_message, "message_count": message_count, "start_time_local": local_time})
        return summary_list
    finally:
        db.close()

def get_all_conversations_for_export():
    db = SessionLocal()
    try:
        return db.query(Conversation).order_by(Conversation.timestamp.asc()).all()
    finally:
        db.close()

# --- KPIs ---

def get_kpis():
    db = SessionLocal()
    try:
        total_rated = db.query(func.count(ChatSession.session_id)).filter(ChatSession.is_resolved != None).scalar()
        resolved_count = db.query(func.count(ChatSession.session_id)).filter(ChatSession.is_resolved == True).scalar()

        resolution_rate = 0
        if total_rated and total_rated > 0:
            resolution_rate = int((resolved_count / total_rated) * 100)

        avg_score = db.query(func.avg(ChatSession.satisfaction_score)).filter(ChatSession.satisfaction_score != None).scalar()
        satisfaction = round(avg_score, 1) if avg_score else 0.0

        return resolution_rate, satisfaction
    finally:
        db.close()

def count_sessions_today():
    db = SessionLocal()
    try:
        local_tz = ZoneInfo("America/Sao_Paulo")
        now_local = datetime.now(local_tz)
        midnight_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        midnight_utc = midnight_local.astimezone(ZoneInfo("UTC"))
        midnight_utc_naive = midnight_utc.replace(tzinfo=None)

        count = db.query(func.count(Conversation.session_id.distinct())).filter(Conversation.timestamp >= midnight_utc_naive).scalar()
        return count or 0
    finally:
        db.close()

def get_daily_interaction_counts():
    db = SessionLocal()
    try:
        counts = db.query(func.date(Conversation.timestamp).label("date"), func.count(Conversation.id).label("count")).group_by(func.date(Conversation.timestamp)).order_by(func.date(Conversation.timestamp)).all()
        return counts
    finally:
        db.close()

def get_top_questions(limit=5):
    db = SessionLocal()
    try:
        top_questions = db.query(Conversation.content, func.count(Conversation.content).label("count")).filter(Conversation.role == 'user').group_by(Conversation.content).order_by(desc("count")).limit(limit).all()
        return top_questions
    finally:
        db.close()

# --- Configurações e Usuários ---

def get_setting(key: str, default: str = None):
    db = SessionLocal()
    try:
        setting = db.query(Settings).filter(Settings.key == key).first()
        return setting.value if setting else default
    finally:
        db.close()

def set_setting(key: str, value: str):
    db = SessionLocal()
    try:
        setting = db.query(Settings).filter(Settings.key == key).first()
        if setting: setting.value = value
        else:
            new_setting = Settings(key=key, value=value)
            db.add(new_setting)
        db.commit()
    finally:
        db.close()

def get_all_settings():
    db = SessionLocal()
    try:
        settings = db.query(Settings).all()
        return {s.key: s.value for s in settings}
    finally:
        db.close()

def get_password_hash(password):
    return generate_password_hash(password)

# --- DEBUG: FUNÇÃO VERIFY_PASSWORD FALANTE ---
def verify_password(plain_password, hashed_password):
    print(f"\n--- DEBUG LOGIN ---")
    print(f"Tentativa Senha: '{plain_password}'")
    print(f"Hash no Banco:   '{str(hashed_password)[:20]}...'")
    try:
        if not hashed_password:
            print("ERRO: Hash vazio!")
            return False
        result = check_password_hash(hashed_password, plain_password)
        print(f"Resultado Check: {result}")
        print("-------------------\n")
        return result
    except Exception as e:
        print(f"ERRO EXCEÇÃO: {e}")
        return False

def get_user_by_email(email: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        # Força o carregamento dos atributos antes de fechar a sessão
        if user:
            _ = user.hashed_password 
        return user
    finally:
        db.close()

def get_all_users():
    db = SessionLocal()
    try:
        return db.query(User).all()
    finally:
        db.close()

def create_user(name: str, email: str, plain_password: str, is_master: bool = False):
    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user: return None
        hashed_password = get_password_hash(plain_password)
        new_user = User(name=name, email=email, hashed_password=hashed_password, is_master=is_master)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    finally:
        db.close()

def delete_user_by_id(user_id: int):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            if user.is_master: return False, "Não é permitido deletar o usuário master."
            db.delete(user)
            db.commit()
            return True, "Usuário deletado com sucesso."
        return False, "Usuário não encontrado."
    except Exception as e:
        return False, f"Erro ao deletar: {e}"
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
