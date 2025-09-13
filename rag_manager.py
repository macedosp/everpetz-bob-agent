# rag_manager.py
# Módulo responsável por gerenciar a base de conhecimento (documentos PDF).
# Funções: carregar, processar e criar um banco de dados vetorial para busca.

import os
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

# Constantes para os diretórios
KNOWLEDGE_BASE_DIR = "knowledge_base"
VECTOR_STORE_DIR = "vector_store"

def process_knowledge_base():
    """
    Processa todos os arquivos PDF na pasta 'knowledge_base'.
    1. Carrega os PDFs.
    2. Divide os textos em pedaços menores (chunks).
    3. Gera embeddings para cada chunk usando a API da OpenAI.
    4. Cria e salva um índice vetorial FAISS localmente.
    
    Retorna:
        bool: True se o processamento foi bem-sucedido, False caso contrário.
    """
    print("Iniciando o processamento da base de conhecimento...")
    
    # Verifica se o diretório da base de conhecimento existe
    if not os.path.exists(KNOWLEDGE_BASE_DIR):
        os.makedirs(KNOWLEDGE_BASE_DIR)
        print(f"Diretório '{KNOWLEDGE_BASE_DIR}' criado. Adicione seus PDFs aqui.")
        return False

    pdf_files = [f for f in os.listdir(KNOWLEDGE_BASE_DIR) if f.endswith(".pdf")]
    if not pdf_files:
        print("Nenhum arquivo PDF encontrado na base de conhecimento.")
        return False

    all_docs = []
    for pdf_file in pdf_files:
        file_path = os.path.join(KNOWLEDGE_BASE_DIR, pdf_file)
        try:
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            all_docs.extend(documents)
            print(f"Arquivo '{pdf_file}' carregado com sucesso.")
        except Exception as e:
            print(f"Erro ao carregar o arquivo '{pdf_file}': {e}")
            continue
    
    if not all_docs:
        print("Nenhum documento pôde ser carregado. Processamento cancelado.")
        return False

    # 2. Dividir os textos em chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,  # Tamanho de cada pedaço de texto
        chunk_overlap=200 # Sobreposição para manter o contexto
    )
    chunks = text_splitter.split_documents(all_docs)
    print(f"Documentos divididos em {len(chunks)} chunks.")

    # 3. Gerar embeddings e criar o Vector Store
    try:
        embeddings = OpenAIEmbeddings()
        vector_store = FAISS.from_documents(chunks, embeddings)
        
        # 4. Salvar o Vector Store localmente
        if not os.path.exists(VECTOR_STORE_DIR):
            os.makedirs(VECTOR_STORE_DIR)
        
        vector_store.save_local(VECTOR_STORE_DIR)
        print(f"Base de conhecimento processada e salva em '{VECTOR_STORE_DIR}'.")
        return True
    except Exception as e:
        print(f"Erro ao criar ou salvar o vector store: {e}")
        return False

def get_retriever():
    """
    Carrega o índice vetorial FAISS do disco e o retorna como um retriever.
    O retriever é o objeto que faz a busca por similaridade.

    Retorna:
        FAISS.as_retriever or None: O objeto retriever se o índice existir, senão None.
    """
    if not os.path.exists(VECTOR_STORE_DIR):
        return None
    
    try:
        embeddings = OpenAIEmbeddings()
        vector_store = FAISS.load_local(VECTOR_STORE_DIR, embeddings, allow_dangerous_deserialization=True)
        return vector_store.as_retriever(search_kwargs={"k": 3}) # Retorna os 3 chunks mais relevantes
    except Exception as e:
        print(f"Erro ao carregar o vector store: {e}")
        return None
    