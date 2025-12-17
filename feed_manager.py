# feed_manager.py
import requests
import xml.etree.ElementTree as ET
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document 
import os
import database
from datetime import datetime

# Configuração do ChromaDB
CHROMA_DB_DIR = "chroma_db"

def get_vector_store():
    """Retorna a instância do banco vetorial."""
    embedding_function = OpenAIEmbeddings(model="text-embedding-3-small")
    return Chroma(persist_directory=CHROMA_DB_DIR, embedding_function=embedding_function)

def strip_namespace(tag):
    """Remove o namespace da tag (ex: {url}item -> item)."""
    if '}' in tag:
        return tag.split('}', 1)[1]
    return tag

def find_child_text_agnostic(parent, target_tag_name):
    """
    Procura o texto de um filho ignorando namespaces.
    Ex: Se procuramos 'price', acha tanto 'price' quanto 'g:price'.
    """
    target_tag_name = target_tag_name.lower()
    for child in parent:
        tag_clean = strip_namespace(child.tag).lower()
        if tag_clean == target_tag_name:
            return child.text
    return None

def process_product_feed():
    """
    Busca o XML, processa os produtos (ignorando namespaces) e atualiza o ChromaDB.
    """
    feed_source = database.get_setting("product_feed_url")
    
    if not feed_source:
        return False, "Fonte do feed não configurada."

    print(f"\n[FEED] --- Iniciando processamento (Modo Universal) ---")
    
    xml_content = None

    try:
        # 1. Obter Conteúdo (URL ou Local)
        if feed_source.startswith("http"):
            print("[FEED] Modo URL. Baixando...")
            response = requests.get(feed_source, timeout=60)
            response.raise_for_status()
            xml_content = response.content
        else:
            print(f"[FEED] Modo Local: {feed_source}")
            if not os.path.exists(feed_source):
                return False, f"Arquivo não encontrado: {feed_source}"
            
            with open(feed_source, 'rb') as f:
                xml_content = f.read()

        # 2. Parse do XML
        root = ET.fromstring(xml_content)
        
        documents = []
        count_found = 0
        count_ignored = 0
        
        print("[FEED] Varrendo estrutura XML...")

        # 3. Iteração Universal (Ignora a estrutura de pastas do XML)
        # Varre TODOS os elementos procurando por 'item' ou 'entry'
        for element in root.iter():
            tag_clean = strip_namespace(element.tag).lower()
            
            if tag_clean in ['item', 'entry']:
                count_found += 1
                try:
                    # Usa a função auxiliar para achar os campos, não importa o namespace
                    title = find_child_text_agnostic(element, 'title') or "Sem Título"
                    description = find_child_text_agnostic(element, 'description') or ""
                    link = find_child_text_agnostic(element, 'link') or ""
                    
                    # Campos específicos (tenta variações comuns)
                    price = find_child_text_agnostic(element, 'price') or find_child_text_agnostic(element, 'sale_price') or "Consulte"
                    image_link = find_child_text_agnostic(element, 'image_link') or find_child_text_agnostic(element, 'link') or ""
                    availability = find_child_text_agnostic(element, 'availability') or "in stock"

                    # --- FILTRO DE ESTOQUE ---
                    avail_clean = str(availability).lower().strip()
                    termos_positivos = ['in stock', 'in_stock', 'instock', 'em estoque', 'disponivel', 'yes', 'true']
                    
                    if avail_clean not in termos_positivos:
                        count_ignored += 1
                        continue

                    # Conteúdo textual para a IA
                    text_content = f"""
                    PRODUTO: {title}
                    PREÇO: {price}
                    DESCRIÇÃO: {description}
                    """
                    
                    metadata = {
                        "source": "product_feed",
                        "type": "product",
                        "title": title,
                        "price": price,
                        "link": link,
                        "image": image_link,
                        "updated_at": datetime.now().isoformat()
                    }
                    
                    doc = Document(page_content=text_content, metadata=metadata)
                    documents.append(doc)

                except Exception as e:
                    print(f"[FEED] Erro ao ler item: {e}")
                    continue

        print(f"[FEED] Tags de produto encontradas: {count_found}")
        print(f"[FEED] Itens ignorados (sem estoque): {count_ignored}")
        print(f"[FEED] Itens válidos para indexação: {len(documents)}")

        if not documents:
            return False, f"XML lido, {count_found} itens achados, mas 0 válidos. Verifique o estoque."

        # 4. Atualização do Banco
        print(f"[FEED] Atualizando ChromaDB...")
        vector_store = get_vector_store()
        vector_store.add_documents(documents)
        
        database.set_setting("last_feed_update", datetime.now().strftime("%d/%m/%Y %H:%M"))
        
        msg = f"Sucesso! {len(documents)} produtos indexados."
        print(f"[FEED] Concluído: {msg}")
        return True, msg

    except Exception as e:
        print(f"[FEED] Erro Fatal: {e}")
        return False, f"Erro: {str(e)}"

if __name__ == "__main__":
    process_product_feed()