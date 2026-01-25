# agent.py - VERSÃO V21 (CORREÇÃO DE TÍTULOS + ESTRUTURA BLINDADA)
import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from rag_manager import get_retriever
import database

# --- CONFIGURAÇÃO DE LINKS ---
WHATSAPP_SUPPORT_LINK = "https://api.whatsapp.com/send?phone=555199013851&text=Ol%C3%A1%2C%20vim%20pelo%20site%20e%20preciso%20de%20ajuda"

# --- 1. PROMPT DE PERSONALIDADE (V21 - SEM RÓTULOS EXPLÍCITOS) ---
AGENT_PROMPT_TEMPLATE = """
Você é o Bob 🐾, o Golden Retriever mascote e consultor da EverPetz.
Sua missão é encantar, fazer o cliente sorrir e vender os melhores produtos.

# SUA PERSONALIDADE:
1.  **Vibe Canina:** Você é leal, empolgado e usa emojis (🐶, 🦴, 🐾).
2.  **Senso de Humor:** Se o usuário pedir algo absurdo (ex: "antipulgas para peixe"), **ENTRE NA BRINCADEIRA**!
3.  **Vendedor Amigo:** Mostre os benefícios de forma leve.

# ESTRUTURA DA RESPOSTA (Siga a ordem lógica, mas NÃO escreva os títulos das seções):

1.  Comece com uma frase conectada com a emoção do cliente ou brincando com a situação (Reação).
2.  Liste os produtos recomendados usando EXATAMENTE este formato visual:

**Nome do Produto**
💰 R$ (Valor)
🖼️ ![Ver Produto](Link da Imagem)
🔗 [COMPRAR AGORA 🛒](Link)
*Por que é legal:* (Uma frase curta sobre o benefício).

3.  Termine com uma despedida simpática de cachorro (Conclusão).

---

# REGRAS TÉCNICAS:
- Use APENAS os dados do CONTEXTO.
- **Imagens:** Se o link da imagem estiver vazio ou quebrado, NÃO mostre a linha 🖼️.
- **Links:** Mantenha o link de compra exato.

# SUPORTE HUMANO:
SOMENTE se pedirem "falar com humano" ou "suporte", use este link:
👉 [Chamar Adestrador (Humano) no WhatsApp]({whatsapp_link})

# CONTEXTO (ESTOQUE):
{context}

# HISTÓRICO:
{chat_history}

# CLIENTE:
{question}
Bob:
"""

# --- 2. PROMPT DE REFINAMENTO (Mantido da V15 para precisão) ---
REWRITE_PROMPT_TEMPLATE = """
Você é um tradutor de intenções de busca. Converta a fala do usuário em palavras-chave de produtos.
Exemplos:
- "Remédio pra carrapato" -> "antipulgas carrapaticida simparic bravecto"
- "Coisa pra dinossauro" -> "brinquedo resistente cachorro grande mordedor"

Histórico: {chat_history}
Usuário: {question}
Busca Otimizada:
"""

class EverpetzAgent:
    def __init__(self):
        # Temperature 0.6: Equilíbrio perfeito entre criatividade (piadas) e precisão (dados)
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.6)
        
        self.main_prompt = PromptTemplate(
            template=AGENT_PROMPT_TEMPLATE,
            input_variables=["agent_name", "context", "chat_history", "question", "whatsapp_link"]
        )
        
        self.rewrite_prompt = PromptTemplate(
            template=REWRITE_PROMPT_TEMPLATE,
            input_variables=["chat_history", "question"]
        )

    def format_chat_history(self, history):
        if not history: return ""
        recent_history = history[-4:] 
        return "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in recent_history])

    def format_docs(self, docs):
        """Formata JSON e prioriza produtos com imagem (Lógica V15 preservada)"""
        if not docs: return "[]"
        
        json_items = []
        for doc in docs:
            meta = doc.metadata
            content = doc.page_content
            
            # Limpeza de Imagem (Mantida integralmente da V15)
            raw_image = meta.get('image', '')
            clean_image = raw_image.strip()
            if clean_image.startswith("//"): clean_image = "https:" + clean_image
            if "http" not in clean_image: clean_image = ""
            
            if meta.get("type") == "product":
                item = {
                    "tipo": "PRODUTO",
                    "nome": meta.get('title', 'Produto'),
                    "preco": meta.get('price', 'Consulte'),
                    "link": meta.get('link', '#').strip(),
                    "imagem": clean_image,
                    "descricao": content.strip()[:400]
                }
                json_items.append(item)
            else:
                item = {"tipo": "INFO", "conteudo": content.strip()}
                json_items.append(item)
        return json.dumps(json_items, ensure_ascii=False, indent=2)

    def get_response(self, user_query, chat_history, session_settings):
        agent_name = session_settings.get("agent_name", "Bob")
        formatted_history = self.format_chat_history(chat_history)

        print("🔌 Conectando ao Banco Vetorial...")
        retriever = get_retriever()
        
        rewrite_chain = (self.rewrite_prompt | self.llm | StrOutputParser())
        main_chain = (self.main_prompt | self.llm | StrOutputParser())

        # Passo 1: Refinamento de Busca
        search_query = user_query
        # Mantemos a lógica agressiva de busca se a frase for curta ou tiver histórico
        if chat_history or len(user_query.split()) < 8: 
            try:
                search_query = rewrite_chain.invoke({
                    "chat_history": formatted_history,
                    "question": user_query
                })
                print(f"🔄 Query: '{search_query}'")
            except: pass

        # Passo 2: Busca Vetorial
        docs = retriever.invoke(search_query)
        context_text = self.format_docs(docs)

        # Passo 3: Resposta Final
        response = main_chain.invoke({
            "context": context_text,
            "chat_history": formatted_history,
            "question": user_query,
            "agent_name": agent_name,
            "whatsapp_link": WHATSAPP_SUPPORT_LINK
        })

        return response