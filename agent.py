import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from operator import itemgetter
from rag_manager import get_retriever
import database

VALID_LINKS = {
    "cães": "https://www.everpetzstore.com.br/products/search/?Category=1",
    "gatos": "https://www.everpetzstore.com.br/products/search/?Category=2",
    "pássaros": "https://www.everpetzstore.com.br/products/search/?Category=3",
    "peixes": "https://www.everpetzstore.com.br/products/search/?Category=4",
    "geral": "https://www.everpetzstore.com.br/products/search"
}
WHATSAPP_SUPPORT_LINK = "https://api.whatsapp.com/send?phone=555199013851&text=Ol%C3%A1%2C%20preciso%20de%20ajuda%20com"

# --- ATUALIZAÇÃO V12: PROMPT HÍBRIDO (PRODUTOS + FAQ) ---
AGENT_PROMPT_TEMPLATE = """
Você é {agent_name}, um Agente de Suporte e Vendas da EverPetz.

# OBJETIVOS
1. Vender produtos (Prioridade Máxima).
2. Tirar dúvidas institucionais (como vender no marketplace, entregas, etc) baseadas EXCLUSIVAMENTE no contexto.

# REGRAS DE OURO (Siga rigorosamente)

### 1. QUANDO FOR SOBRE PRODUTOS:
   - **FORMATO OBRIGATÓRIO:**
     * **Nome do Produto**
     * 💰 Preço: R$ valor
     * 🔗 [CLIQUE AQUI PARA COMPRAR](URL)
     * ![Imagem](URL_IMAGEM)
     * *Breve descrição*
   - **LINK É LEI:** Nunca mostre um produto sem o link de compra.

### 2. QUANDO FOR SOBRE DÚVIDAS INSTITUCIONAIS (FAQ):
   - Se o contexto trouxer informações explicativas (ex: "Como vender", "Prazos"), responda a pergunta do usuário de forma natural e polida, usando essas informações.
   - Não tente forçar o formato de produto para respostas de texto.

### 3. SEGURANÇA E ANTI-ALUCINAÇÃO:
   - **Use APENAS a Base de Conhecimento abaixo.**
   - Se o usuário pedir um produto e não houver nada no contexto, diga: "No momento, não encontrei opções disponíveis nesta categoria."
   - JAMAIS INVENTE PRODUTOS OU LINKS.

# BASE DE CONHECIMENTO (O que você sabe)
{context}

# HISTÓRICO
{chat_history}

# PERGUNTA DO CLIENTE
Usuário: {question}
{agent_name}:
"""

class EverpetzAgent:
    def __init__(self):
        # Temperature 0.2 mantém a precisão mas permite frases mais naturais para o FAQ
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.2)
        self.retriever = get_retriever()
        self.prompt = PromptTemplate(
            template=AGENT_PROMPT_TEMPLATE,
            input_variables=["agent_name", "context", "chat_history", "question", "valid_links", "whatsapp_link"]
        )

        self.chain = (
            {
                "context": itemgetter("question") | self.retriever | self.format_docs,
                "question": itemgetter("question"),
                "chat_history": itemgetter("chat_history"),
                "agent_name": itemgetter("agent_name"),
                "valid_links": lambda x: VALID_LINKS,
                "whatsapp_link": lambda x: WHATSAPP_SUPPORT_LINK
            }
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

    def format_chat_history(self, history):
        if not history: return "Início da conversa."
        recent_history = history[-6:]
        return "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in recent_history])

    def format_docs(self, docs):
        formatted_chunks = []
        for doc in docs:
            meta = doc.metadata
            content = doc.page_content
            
            if meta.get("type") == "product":
                # Estrutura para produtos
                product_block = f"""
                [TIPO: PRODUTO DA LOJA]
                NOME: {meta.get('title')}
                PREÇO: {meta.get('price')}
                LINK: {meta.get('link')}
                IMAGEM: {meta.get('image')}
                DESCRIÇÃO: {content.strip()}
                --------------------------
                """
                formatted_chunks.append(product_block)
            else:
                # Estrutura clara para o FAQ/Texto
                formatted_chunks.append(f"[TIPO: INFORMAÇÃO INSTITUCIONAL/FAQ]\nCONTEÚDO: {content}\n--------------------------\n")
        
        return "\n".join(formatted_chunks)

    def get_response(self, user_query, chat_history, session_settings):
        if "aquário" in user_query.lower() and "gato" in user_query.lower():
            return "Haha! Gatos adoram aquários... mas só para assistir a TV de peixe! 🐟📺 Se quiser um aquário de verdade, temos ótimas opções na seção de peixes!"

        agent_name = session_settings.get("agent_name", "Bob")
        formatted_history = self.format_chat_history(chat_history)

        chain_input = {
            "question": user_query,
            "chat_history": formatted_history,
            "agent_name": agent_name
        }

        return self.chain.invoke(chain_input)