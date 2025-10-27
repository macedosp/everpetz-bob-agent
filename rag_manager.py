# rag_manager.py
import os
from datetime import datetime
import traceback

# Bibliotecas do LangChain para o processo de RAG
from langchain_chroma import Chroma # <-- IMPORT ATUALIZADO
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter # <-- CORREÇÃO AQUI

# --- Constantes ---
# Diretório onde os PDFs originais são armazenados
KNOWLEDGE_BASE_DIR = "knowledge_base"
# Diretório onde o banco de dados vetorial processado será salvo
CHROMA_DB_DIR = "chroma_db"

def process_knowledge_base():
    """
    Carrega documentos da base de conhecimento, processa-os (divide, cria embeddings)
    e os armazena em um banco de dados vetorial ChromaDB.
    Se bem-sucedido, cria um arquivo marcador com o timestamp.
    """
    print("Iniciando o processamento da base de conhecimento...")

    try:
        # 1. Listar os arquivos a serem processados
        if not os.path.exists(KNOWLEDGE_BASE_DIR):
            os.makedirs(KNOWLEDGE_BASE_DIR)
            print(f"Diretório '{KNOWLEDGE_BASE_DIR}' criado.")

        files_to_process = [f for f in os.listdir(KNOWLEDGE_BASE_DIR) if f.endswith(".pdf")]
        
        if not files_to_process:
            print("Nenhum arquivo encontrado para processar.")
            return False

        print(f"Arquivos encontrados para processamento: {files_to_process}")

        # 2. Carregar os documentos
        documents = []
        for file in files_to_process:
            file_path = os.path.join(KNOWLEDGE_BASE_DIR, file)
            loader = PyPDFLoader(file_path)
            documents.extend(loader.load())
        print(f"Total de {len(documents)} páginas carregadas dos documentos.")

        # 3. Dividir os documentos em pedaços (chunks)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents(documents)
        print(f"Documentos divididos em {len(chunks)} pedaços (chunks).")

        # 4. Criar os embeddings e armazenar no ChromaDB
        # (Certifique-se que sua chave OPENAI_API_KEY está configurada como variável de ambiente)
        embeddings = OpenAIEmbeddings()
        
        # O ChromaDB criará o banco de dados no diretório especificado e o salvará no disco.
        vector_store = Chroma.from_documents(
            documents=chunks, 
            embedding=embeddings,
            persist_directory=CHROMA_DB_DIR
        )
        print(f"Embeddings criados e salvos em '{CHROMA_DB_DIR}'.")
        
        # 5. Se tudo deu certo, criar o arquivo marcador
        marker_file_path = os.path.join(KNOWLEDGE_BASE_DIR, '.last_processed')
        with open(marker_file_path, 'w') as f:
            f.write(datetime.now().isoformat())
        print(f"Arquivo marcador '{marker_file_path}' criado/atualizado.")

        return True

    except Exception as e:
        print(f"Ocorreu um erro durante o processamento da base de conhecimento: {e}")
        return False
def get_retriever():
    """
    Carrega o banco de dados vetorial Chroma e o retorna como um retriever.
    O retriever é o componente que busca os documentos relevantes.
    """
    if not os.path.exists(CHROMA_DB_DIR):
        print(f"AVISO: Diretório do ChromaDB ('{CHROMA_DB_DIR}') não encontrado ao criar retriever.")
        return None
        
    embeddings = OpenAIEmbeddings()
    vector_store = Chroma(
        persist_directory=CHROMA_DB_DIR, 
        embedding_function=embeddings
    )
    return vector_store.as_retriever()