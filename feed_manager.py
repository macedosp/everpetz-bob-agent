# V5 PRECISION - UPLOAD FORCADO
import requests
import xml.etree.ElementTree as ET
import os
import re
import database
import rag_manager
import logging

logging.basicConfig(level=logging.INFO)

def clean_html(raw_html):
    if not raw_html: return ""
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html)

def process_product_feed(override_url=None):
    try:
        url = override_url or database.get_setting("product_feed_url")
        if not url: return False, "Nenhuma URL configurada."

        print(f"--- [V5 PRECISION RE-APPLY] Baixando feed: {url} ---")
        
        headers = {'User-Agent': 'Mozilla/5.0 (BobAgent/1.0)'}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as e:
            return False, f"Erro crítico de XML: {e}"

        products_text = []
        count = 0
        
        # BUSCA DE PRECISÃO (Lógica V5)
        for elem in root.iter():
            if elem.tag.endswith('item') or elem.tag.endswith('entry'):
                try:
                    title = "Produto sem nome"
                    price = "Sob consulta"
                    link = ""
                    image = ""
                    description = ""

                    for child in elem:
                        tag = child.tag.lower()
                        
                        if tag.endswith('title'): 
                            title = child.text
                        elif tag.endswith('price') or tag.endswith('sale_price'): 
                            price = child.text
                        # AQUI ESTÁ A CORREÇÃO CRÍTICA
                        elif 'image_link' in tag: 
                            image = child.text
                        elif tag.endswith('link') and 'image' not in tag: 
                            link = child.text
                        elif tag.endswith('description') or tag.endswith('summary'): 
                            description = clean_html(child.text)

                    entry = f"PRODUTO: {title}\nPREÇO: {price}\nLINK: {link}\nIMAGEM: {image}\nDETALHES: {description}\n---\n"
                    products_text.append(entry)
                    count += 1
                except:
                    continue

        if count == 0:
            return False, "XML lido mas 0 itens encontrados."

        output_file = os.path.join(rag_manager.KNOWLEDGE_BASE_DIR, "feed_produtos_everpetz.txt")
        if not os.path.exists(rag_manager.KNOWLEDGE_BASE_DIR):
            os.makedirs(rag_manager.KNOWLEDGE_BASE_DIR)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"CATÁLOGO V5 RESTAURADO - TOTAL: {count}\n\n")
            f.write("\n".join(products_text))

        print(f"--- SUCESSO V5: Arquivo salvo. Links corrigidos. ---")

        rag_manager.process_knowledge_base()

        return True, f"Sucesso! {count} produtos corrigidos."

    except Exception as e:
        print(f"Erro Crítico V5: {e}")
        return False, str(e)
