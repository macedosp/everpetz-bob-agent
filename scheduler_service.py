# scheduler_service.py - VERSÃO V22 (DECIFRADOR ATOM / GOOGLE MERCHANT)
import os
import requests
import shutil
import logging
import xml.etree.ElementTree as ET
from apscheduler.schedulers.background import BackgroundScheduler
from rag_manager import process_knowledge_base, update_feed_status

# --- Configurações ---
FEED_URL = "https://www.everpetzstore.com.br/api/v1/google-shopping"
KNOWLEDGE_BASE_DIR = "knowledge_base"
TARGET_FILE = os.path.join(KNOWLEDGE_BASE_DIR, "feed_produtos_everpetz.txt")
TEMP_XML = os.path.join(KNOWLEDGE_BASE_DIR, "temp_google_shopping.xml")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_tag_name(tag):
    """Remove o namespace chato (ex: {http://...}title -> title)"""
    if '}' in tag:
        return tag.split('}', 1)[1]
    return tag

def convert_xml_to_clean_txt(xml_path, txt_path):
    """
    V22: Suporte Total para formato ATOM (<entry>) e RSS (<item>).
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        products_count = 0
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            # Tenta encontrar itens (RSS) ou entradas (ATOM)
            # A busca é feita por qualquer tag que termine com 'item' ou 'entry'
            all_elements = root.findall('.//*')
            product_nodes = [
                el for el in all_elements 
                if clean_tag_name(el.tag).lower() in ['item', 'entry']
            ]
            
            for node in product_nodes:
                # Dicionário padrão
                data = {
                    "title": "Produto",
                    "price": "Consulte",
                    "image": "",
                    "link": "",
                    "description": ""
                }
                
                # Varre os filhos do nó (Força Bruta Inteligente)
                for child in node:
                    tag = clean_tag_name(child.tag).lower()
                    text = child.text.strip() if child.text else ""
                    
                    if 'title' in tag:
                        data['title'] = text
                    
                    elif 'price' in tag:
                        data['price'] = text
                        
                    elif 'image_link' in tag or 'image' in tag:
                        data['image'] = text
                        
                    elif 'description' in tag or 'summary' in tag:
                        clean_desc = text.replace('<div', '').replace('</div>', '').replace('>', '').replace('<', '')
                        data['description'] = clean_desc[:600]
                    
                    elif tag == 'link':
                        # Link pode ser texto (<g:link>...) ou atributo (<link href=...>)
                        if text:
                            data['link'] = text
                        elif child.attrib.get('href'):
                            data['link'] = child.attrib.get('href')

                # Validação: Só grava se tiver Link válido
                if data['link'] and "http" in data['link']:
                    f.write(f"Title: {data['title']}\n")
                    f.write(f"Price: {data['price']}\n")
                    f.write(f"Image: {data['image']}\n")
                    f.write(f"Link: {data['link']}\n")
                    f.write(f"Description: {data['description']}\n")
                    f.write("---\n") # Separador Padrão V17
                    
                    products_count += 1

        return True, f"V22 Sucesso: {products_count} produtos extraídos do formato ATOM/RSS."
        
    except Exception as e:
        return False, f"Erro na conversão V22: {str(e)}"

def download_and_update_feed():
    logger.info("🤖 Scheduler V22: Baixando feed Atom...")
    update_feed_status("processing", "Baixando e decifrando Feed Atom...", 0)

    try:
        if not os.path.exists(KNOWLEDGE_BASE_DIR): os.makedirs(KNOWLEDGE_BASE_DIR)

        # 1. Download
        headers = {'User-Agent': 'BobAgent/1.0'}
        response = requests.get(FEED_URL, headers=headers, timeout=60)
        if response.status_code != 200: raise Exception(f"Erro HTTP {response.status_code}")

        with open(TEMP_XML, 'w', encoding='utf-8') as f:
            f.write(response.text)

        # 2. Conversão
        success, msg = convert_xml_to_clean_txt(TEMP_XML, TARGET_FILE)
        if not success: raise Exception(msg)
            
        logger.info(f"✅ {msg}")

        # 3. Limpeza
        if os.path.exists(TEMP_XML): os.remove(TEMP_XML)

        # 4. Re-Indexação
        process_knowledge_base()
        
    except Exception as e:
        logger.error(f"❌ Falha: {e}")
        update_feed_status("error", f"Falha V22: {str(e)}", 0)

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(download_and_update_feed, 'cron', hour=3, minute=0)
    scheduler.start()
    logger.info("🕒 Scheduler V22 iniciado.")