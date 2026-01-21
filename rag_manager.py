# rag_manager.py - VERSÃO V13 (SAFE WIPE / DOCKER FRIENDLY)
import os
import shutil
from datetime import datetime
import traceback

# Bibliotecas do LangChain
from langchain_chroma import Chroma 
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_core.documents import Document 
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter 

# --- Constantes ---
KNOWLEDGE_BASE_DIR = "knowledge_base"
CHROMA_DB_DIR = "chroma_db"

def get_vector_store():
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    return Chroma(persist_directory=CHROMA_DB_DIR, embedding_function=embeddings)

def process_knowledge_base():
    print("Iniciando o processamento da base de conhecimento...")

    try:
        if not os.path.exists(KNOWLEDGE_BASE_DIR):
            os.makedirs(KNOWLEDGE_BASE_DIR)

        # Extensões válidas
        valid_extensions = ('.pdf', '.txt', '.docx')
        files_to_process = [f for f in os.listdir(KNOWLEDGE_BASE_DIR) if f.lower().endswith(valid_extensions)]
        
        if not files_to_process:
            print("Nenhum arquivo compatível encontrado.")
            return False

        print(f"Arquivos encontrados: {files_to_process}")

        documents = []
        
        for file in files_to_process:
            try:
                file_path = os.path.join(KNOWLEDGE_BASE_DIR, file)
                
                # --- ESTRATÉGIA INTELIGENTE PARA O FEED (.TXT) ---
                if file.lower().endswith('.txt'):
                    with open(file_path, "r", encoding="utf-8") as f:
                        full_text = f.read()
                    
                    product_blocks = full_text.split("---")
                    
                    count_txt = 0
                    for block in product_blocks:
                        if block.strip():
                            doc = Document(page_content=block.strip(), metadata={"source": file})
                            documents.append(doc)
                            count_txt += 1
                    print(f" > Arquivo {file}: {count_txt} produtos/blocos extraídos.")

                elif file.lower().endswith('.pdf'):
                    loader = PyPDFLoader(file_path)
                    docs_pdf = loader.load()
                    documents.extend(docs_pdf)
                    print(f" > Arquivo {file}: {len(docs_pdf)} páginas carregadas.")
                
                elif file.lower().endswith('.docx'):
                    loader = Docx2txtLoader(file_path)
                    docs_docx = loader.load()
                    documents.extend(docs_docx)
                    print(f" > Arquivo {file}: Carregado.")
                    
            except Exception as e:
                print(f"Erro ao ler arquivo {file}: {e}")
                continue
                
        if not documents:
            print("Nada para processar (lista vazia).")
            return False

        print(f"Total geral de documentos: {len(documents)}")

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=2500, chunk_overlap=200)
        chunks = text_splitter.split_documents(documents)
        print(f"Chunking final: {len(chunks)} pedaços.")

        # ======================================================================
        # [ATUALIZADO] SAFE WIPE (Limpa CONTEÚDO, mantém a PASTA)
        # ======================================================================
        if os.path.exists(CHROMA_DB_DIR):
            print(f"🧹 EXECUTANDO LIMPEZA SEGURA em '{CHROMA_DB_DIR}'...")
            try:
                # Remove arquivo por arquivo, evitando erro de permissão na pasta raiz
                for filename in os.listdir(CHROMA_DB_DIR):
                    file_path = os.path.join(CHROMA_DB_DIR, filename)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except Exception as e:
                        print(f'Falha ao deletar {file_path}. Razão: {e}')
                print("✅ Banco antigo limpo (Estrutura mantida).")
            except Exception as e:
                print(f"⚠️ Aviso na limpeza: {e}")
        
        print(f"Gravando {len(chunks)} novos vetores...")
        vector_store = get_vector_store()
        vector_store.add_documents(chunks)
        
        with open(os.path.join(KNOWLEDGE_BASE_DIR, '.last_processed'), 'w') as f:
            f.write(datetime.now().isoformat())

        print("Processamento concluído com sucesso.")
        return True

    except Exception as e:
        print(f"Erro crítico: {e}")
        traceback.print_exc()
        return False

def get_retriever():
    if not os.path.exists(CHROMA_DB_DIR):
        return get_vector_store().as_retriever()
    vector_store = get_vector_store()
    return vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 25})