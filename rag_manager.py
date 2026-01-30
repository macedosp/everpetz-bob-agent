# rag_manager.py - VERSÃO V26 (PHOENIX FIX)
# Correção: Re-inicializa a store após o delete_collection para recriar a estrutura vazia.

import os
import json
import logging
import traceback
from datetime import datetime

# Bibliotecas do LangChain
from langchain_chroma import Chroma 
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_core.documents import Document 
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter 

# --- Configurações ---
KNOWLEDGE_BASE_DIR = "knowledge_base"
CHROMA_DB_DIR = "/app/banco_vetorial_seguro" # Caminho do Volume Docker
STATUS_FILE = os.path.join(KNOWLEDGE_BASE_DIR, "status.json")

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_vector_store():
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    # A inicialização aqui conecta e prepara o terreno
    return Chroma(persist_directory=CHROMA_DB_DIR, embedding_function=embeddings)

def get_retriever():
    if not os.path.exists(CHROMA_DB_DIR):
        return get_vector_store().as_retriever()
    
    vector_store = get_vector_store()
    return vector_store.as_retriever(
        search_type="similarity", 
        search_kwargs={"k": 10}
    )

# --- FUNÇÕES DE STATUS DO DASHBOARD ---
def load_status():
    """Lê o arquivo de status de forma segura."""
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erro ao ler status: {e}")
    return {"docs": [], "last_update": "Nunca", "processing": False}

def save_status(status_data):
    """Grava o status garantindo que a pasta existe."""
    try:
        folder = os.path.dirname(STATUS_FILE)
        if not os.path.exists(folder):
            os.makedirs(folder)
            
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Erro GRAVE ao salvar status em {STATUS_FILE}: {e}")

def update_feed_status(status_code, message, count=0):
    """Atualiza o JSON que o Dashboard lê."""
    print(f"📝 Atualizando Status: {status_code} - {message}") 
    
    data = load_status()
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    feed_found = False
    for doc in data.get("docs", []):
        if doc["name"] == "Feed de Produtos (Automático)":
            doc["status"] = status_code
            doc["updated_at"] = now
            doc["info"] = message
            feed_found = True
            break
    
    if not feed_found:
        if "docs" not in data: data["docs"] = []
        data["docs"].append({
            "name": "Feed de Produtos (Automático)",
            "type": "Sistema",
            "status": status_code,
            "updated_at": now,
            "info": message
        })
    
    data["last_update"] = now
    data["processing"] = (status_code == "processing")
    
    save_status(data)

# --- PROCESSAMENTO PRINCIPAL ---

def process_knowledge_base():
    print("--- INICIANDO PROCESSAMENTO (V26 PHOENIX) ---")
    update_feed_status("processing", "Iniciando leitura e indexação...", 0)

    try:
        # Garante diretório
        if not os.path.exists(KNOWLEDGE_BASE_DIR):
            os.makedirs(KNOWLEDGE_BASE_DIR)

        valid_extensions = ('.pdf', '.txt', '.docx')
        files_to_process = [f for f in os.listdir(KNOWLEDGE_BASE_DIR) if f.lower().endswith(valid_extensions)]
        
        if not files_to_process:
            msg = "Nenhum arquivo compatível encontrado."
            update_feed_status("active", msg, 0)
            return False

        documents = []
        total_products_detected = 0 
        
        print(f"Lendo arquivos: {files_to_process}")
        
        for file in files_to_process:
            try:
                file_path = os.path.join(KNOWLEDGE_BASE_DIR, file)
                
                # --- PROCESSAMENTO DE TXT (FEED) ---
                if file.lower().endswith('.txt'):
                    with open(file_path, "r", encoding="utf-8") as f:
                        full_text = f.read()
                    
                    product_blocks = full_text.split("---")
                    count_txt = 0
                    
                    for block in product_blocks:
                        content = block.strip()
                        if content:
                            lines = content.split('\n')
                            title = next((l.split('Title: ')[1] for l in lines if 'Title: ' in l), "").strip()
                            price = next((l.split('Price: ')[1] for l in lines if 'Price: ' in l), "").strip()
                            image = next((l.split('Image: ')[1] for l in lines if 'Image: ' in l), "").strip()
                            link = next((l.split('Link: ')[1] for l in lines if 'Link: ' in l), "").strip()
                            
                            if title and price:
                                meta = {
                                    "source": file,
                                    "type": "product",
                                    "title": title,
                                    "price": price,
                                    "image": image,
                                    "link": link
                                }
                                count_txt += 1
                            else:
                                meta = {"source": file, "type": "info", "title": "Info Geral", "price": "", "image": "", "link": ""}
                            
                            doc = Document(page_content=content, metadata=meta)
                            documents.append(doc)
                    
                    total_products_detected += count_txt
                    print(f" > {file}: {count_txt} produtos reais identificados.")

                # --- PROCESSAMENTO DE PDF ---
                elif file.lower().endswith('.pdf'):
                    loader = PyPDFLoader(file_path)
                    docs_pdf = loader.load()
                    for d in docs_pdf: 
                        d.metadata["type"] = "info" 
                    documents.extend(docs_pdf)
                    print(f" > {file}: {len(docs_pdf)} páginas.")

                # --- PROCESSAMENTO DE DOCX ---
                elif file.lower().endswith('.docx'):
                    loader = Docx2txtLoader(file_path)
                    docs_docx = loader.load()
                    for d in docs_docx:
                        d.metadata["type"] = "info"
                    documents.extend(docs_docx)
                    print(f" > {file}: Carregado.")
                    
            except Exception as e:
                print(f"Erro ao ler {file}: {e}")
                
        if not documents:
            update_feed_status("error", "Conteúdo vazio.", 0)
            return False

        # Chunking
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=100)
        chunks = text_splitter.split_documents(documents)
        print(f"Chunking final: {len(chunks)} vetores gerados.")
        
        # --- [CRÍTICO] MUDANÇA V26: SOFT WIPE + REINIT ---
        print(f"Conectando ao ChromaDB para atualização...")
        vector_store = get_vector_store()
        
        try:
            print("🧹 Resetando coleção via API (Soft Reset)...")
            vector_store.delete_collection() 
        except Exception as e:
            print(f"ℹ️ Aviso na limpeza (coleção nova ou vazia): {e}")

        # [CORREÇÃO V26] Recriar a instância força a criação de uma nova coleção vazia
        # Isso resolve o erro "Collection not initialized" e permite gravar
        print("🔄 Reinicializando Store V26 (Phoenix)...")
        vector_store = get_vector_store() 

        # Gravação no Banco
        print(f"Gravando novos dados no ChromaDB...")
        vector_store.add_documents(chunks)
        
        # --- RELATÓRIO FINAL ---
        if total_products_detected > 0:
            success_msg = f"{total_products_detected} Produtos ({len(chunks)} vetores)."
        else:
            success_msg = f"{len(chunks)} documentos indexados."
            
        print(f"✅ {success_msg}")
        update_feed_status("active", success_msg, len(chunks))
        return True

    except Exception as e:
        err_msg = f"Erro Crítico: {str(e)}"
        print(err_msg)
        traceback.print_exc()
        update_feed_status("error", err_msg, 0)
        return False