# rag_manager.py
import os
from datetime import datetime
import traceback

# Bibliotecas do LangChain para o processo de RAG
from langchain_chroma import Chroma 
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter 

# --- Constantes ---
KNOWLEDGE_BASE_DIR = "knowledge_base"
CHROMA_DB_DIR = "chroma_db"

def get_vector_store():
    """
    Função auxiliar para garantir que usamos SEMPRE o mesmo modelo de embeddings
    tanto para PDFs quanto para Produtos (Feed XML).
    """
    # IMPORTANTE: O modelo deve ser o mesmo usado no feed_manager.py
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    
    return Chroma(
        persist_directory=CHROMA_DB_DIR, 
        embedding_function=embeddings
    )

def process_knowledge_base():
    """
    Carrega documentos da base de conhecimento, processa-os e adiciona ao ChromaDB.
    """
    print("Iniciando o processamento da base de conhecimento...")

    try:
        # 1. Listar os arquivos a serem processados
        if not os.path.exists(KNOWLEDGE_BASE_DIR):
            os.makedirs(KNOWLEDGE_BASE_DIR)
            print(f"Diretório '{KNOWLEDGE_BASE_DIR}' criado.")

        files_to_process = [f for f in os.listdir(KNOWLEDGE_BASE_DIR) if f.endswith(".pdf")]
        
        if not files_to_process:
            print("Nenhum arquivo PDF encontrado para processar.")
            return False

        print(f"Arquivos encontrados para processamento: {files_to_process}")

        # 2. Carregar os documentos
        documents = []
        for file in files_to_process:
            try:
                file_path = os.path.join(KNOWLEDGE_BASE_DIR, file)
                loader = PyPDFLoader(file_path)
                documents.extend(loader.load())
            except Exception as e:
                print(f"Erro ao ler arquivo {file}: {e}")
                continue
                
        if not documents:
            print("Nenhum conteúdo extraído dos documentos.")
            return False

        print(f"Total de {len(documents)} páginas carregadas dos documentos.")

        # 3. Dividir os documentos em pedaços (chunks)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents(documents)
        print(f"Documentos divididos em {len(chunks)} pedaços (chunks).")

        # 4. Criar os embeddings e armazenar no ChromaDB
        # Usamos a função auxiliar para garantir compatibilidade com o feed de produtos
        vector_store = get_vector_store()
        
        print(f"Adicionando chunks ao banco de dados em '{CHROMA_DB_DIR}'...")
        vector_store.add_documents(chunks)
        
        # 5. Criar o arquivo marcador
        marker_file_path = os.path.join(KNOWLEDGE_BASE_DIR, '.last_processed')
        with open(marker_file_path, 'w') as f:
            f.write(datetime.now().isoformat())
        print(f"Arquivo marcador '{marker_file_path}' criado/atualizado.")

        return True

    except Exception as e:
        print(f"Ocorreu um erro durante o processamento da base de conhecimento: {e}")
        traceback.print_exc()
        return False

def get_retriever():
    """
    Carrega o banco de dados vetorial Chroma e o retorna como um retriever.
    Configurado para buscar mais resultados (k=5) para misturar Produtos e Textos.
    """
    if not os.path.exists(CHROMA_DB_DIR):
        print(f"AVISO: Diretório do ChromaDB ('{CHROMA_DB_DIR}') não encontrado ao criar retriever.")
        # Retorna um retriever vazio ou None para evitar quebra total, 
        # mas idealmente o banco deve existir.
        # Tenta criar um vazio para não quebrar a app
        return get_vector_store().as_retriever()
        
    vector_store = get_vector_store()
    
    # search_kwargs={"k": 5}: Aumenta a busca para 5 documentos 
    # para garantir que produtos E textos de suporte sejam encontrados.
    return vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 5})