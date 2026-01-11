# agent.py - VERSÃO V14.1 (VENDEDOR CONSULTIVO + REFINAMENTO + IMAGENS RESTAURADAS)

import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from operator import itemgetter
from rag_manager import get_retriever
import database

# Mantendo seus links e constantes originais
VALID_LINKS = {
    "cães": "https://www.everpetzstore.com.br/products/search/?Category=1",
    "gatos": "https://www.everpetzstore.com.br/products/search/?Category=2",
    "pássaros": "https://www.everpetzstore.com.br/products/search/?Category=3",
    "peixes": "https://www.everpetzstore.com.br/products/search/?Category=4",
    "geral": "https://www.everpetzstore.com.br/products/search"
}
WHATSAPP_SUPPORT_LINK = "https://api.whatsapp.com/send?phone=555199013851&text=Ol%C3%A1%2C%20preciso%20de%20ajuda%20com"

# --- 1. NOVO PROMPT DE VENDAS (Personalidade Ativa & Visual) ---
AGENT_PROMPT_TEMPLATE = """
Você é {agent_name}, o consultor especialista em vendas da EverPetz. 
Sua missão não é apenas responder, mas ENCANTAR, CONSULTAR e CONVERTER vendas mostrando os produtos.

# DIRETRIZES DE PERSONALIDADE (VENDEDOR PROATIVO):
1.  **Nunca dê um "Não" seco:** Se o usuário pedir algo que não está no contexto, ofereça IMEDIATAMENTE uma alternativa.
2.  **Venda Benefícios:** Diga como o produto ajuda o pet.
3.  **Visual é Tudo:** Sempre mostre a imagem do produto se disponível no contexto.
4.  **Use Emojis:** Seja simpático (🐾, 🐶, 🐱, 💰).

# FORMATO OBRIGATÓRIO PARA PRODUTOS (Siga a risca):
Para cada produto encontrado, use este bloco:

**Nome do Produto** (Use Negrito)
💰 Preço: R$ valor
🔗 [CLIQUE AQUI PARA COMPRAR](URL_DO_LINK)
![Imagem do Produto](URL_DA_IMAGEM)
*Breve comentário vendedor sobre o item.*

# FORMATO PARA DÚVIDAS (FAQ):
- Responda de forma polida e clara baseada no contexto institucional.

# SEGURANÇA:
- Use APENAS a Base de Conhecimento abaixo.

# BASE DE CONHECIMENTO (Produtos encontrados):
{context}

# HISTÓRICO DA CONVERSA:
{chat_history}

# PERGUNTA DO CLIENTE:
Usuário: {question}
{agent_name}:
"""

# --- 2. PROMPT DE REFINAMENTO (Contexto Inteligente) ---
REWRITE_PROMPT_TEMPLATE = """
Dada a conversa a seguir e uma pergunta de acompanhamento, reescreva a pergunta de acompanhamento para ser uma pergunta independente e completa para busca em banco de dados.

Histórico:
{chat_history}

Pergunta (Usuário): {question}

Pergunta Reescrita (Apenas a frase):
"""

class EverpetzAgent:
    def __init__(self):
        # Temperature 0.3: Equilíbrio entre criatividade de vendas e seguir o formato de imagem
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
        self.retriever = get_retriever()
        
        self.main_prompt = PromptTemplate(
            template=AGENT_PROMPT_TEMPLATE,
            input_variables=["agent_name", "context", "chat_history", "question"]
        )
        
        self.rewrite_prompt = PromptTemplate(
            template=REWRITE_PROMPT_TEMPLATE,
            input_variables=["chat_history", "question"]
        )

        self.rewrite_chain = (self.rewrite_prompt | self.llm | StrOutputParser())
        self.main_chain = (self.main_prompt | self.llm | StrOutputParser())

    def format_chat_history(self, history):
        if not history: return ""
        recent_history = history[-4:] 
        return "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in recent_history])

    def format_docs(self, docs):
        formatted_chunks = []
        if not docs:
            return "Nenhum produto específico encontrado para esta busca no catálogo."
            
        for doc in docs:
            meta = doc.metadata
            content = doc.page_content
            
            if meta.get("type") == "product":
                # [CORREÇÃO] Garantindo que a IMAGEM vá para o contexto
                product_block = f"""
                [PRODUTO DISPONÍVEL]
                NOME: {meta.get('title')}
                PREÇO: {meta.get('price')}
                LINK: {meta.get('link')}
                IMAGEM: {meta.get('image')}
                DESCRIÇÃO: {content.strip()}
                --------------------------
                """
                formatted_chunks.append(product_block)
            else:
                formatted_chunks.append(f"[INFO INSTITUCIONAL]: {content}\n--------------------------\n")
        
        return "\n".join(formatted_chunks)

    def get_response(self, user_query, chat_history, session_settings):
        # Easter Egg
        if "aquário" in user_query.lower() and "gato" in user_query.lower():
            return "Haha! Gatos adoram aquários... mas só para assistir a TV de peixe! 🐟📺 Se quiser um aquário de verdade, temos ótimas opções na seção de peixes!"

        agent_name = session_settings.get("agent_name", "Bob")
        formatted_history = self.format_chat_history(chat_history)

        # PASSO 1: REFINAMENTO
        search_query = user_query
        if chat_history:
            try:
                search_query = self.rewrite_chain.invoke({
                    "chat_history": formatted_history,
                    "question": user_query
                })
                print(f"🔄 Query Refinada: '{search_query}'")
            except Exception as e:
                print(f"⚠️ Erro no refinamento: {e}")

        # PASSO 2: BUSCA
        docs = self.retriever.invoke(search_query)
        context_text = self.format_docs(docs)

        # PASSO 3: GERAÇÃO COM IMAGENS
        response = self.main_chain.invoke({
            "context": context_text,
            "chat_history": formatted_history,
            "question": user_query,
            "agent_name": agent_name
        })

        return response