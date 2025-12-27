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

# --- ATUALIZAÇÃO V11: PROMPT COM BLINDAGEM ANTI-ALUCINAÇÃO ---
AGENT_PROMPT_TEMPLATE = """
Você é {agent_name}, um Agente de Suporte e Vendas da EverPetz.

# OBJETIVO PRINCIPAL
Ajudar o cliente e VENDER. Todo produto mencionado TEM QUE ter link de compra.

# REGRAS DE OURO (Siga ou falhará)
1. **LINK É LEI:** NUNCA mencione um produto específico sem colocar o link [Comprar Agora](URL) logo em seguida.
2. **LISTAS, NÃO TEXTÃO:** Se o usuário pedir 2 coisas (ex: ração e remédio), separe em itens de lista. Não escreva tudo num parágrafo só.
3. **FORMATO OBRIGATÓRIO PARA PRODUTOS:**
   Para cada produto encontrado, use EXATAMENTE este formato:
   
   * **Nome do Produto Aqui**
   * 💰 Preço: R$ valor
   * 🔗 [CLIQUE AQUI PARA COMPRAR](URL_DO_PRODUTO)
   * ![Imagem do Produto](URL_DA_IMAGEM)
   * *Pequena descrição...*

4. **ANTI-ALUCINAÇÃO (CRÍTICO - LEIA COM ATENÇÃO):**
   - **USE APENAS** os produtos listados abaixo em "BASE DE CONHECIMENTO".
   - Se o usuário pedir "mais opções" e você não encontrar novos produtos no contexto abaixo, **DIGA EXATAMENTE**: "No momento, essas são todas as opções que encontrei disponíveis no nosso catálogo para essa categoria."
   - **JAMAIS INVENTE PRODUTOS.** Se não está no contexto, não existe.
   - **JAMAIS GERE LINKS FALSOS.** Se o link não veio no contexto, não mostre o produto.

# BASE DE CONHECIMENTO
{context}

# HISTÓRICO
{chat_history}

# PERGUNTA
Usuário: {question}
{agent_name}:
"""

class EverpetzAgent:
    def __init__(self):
        # Temperatura baixa (0.2) para ele obedecer o formato rigidamente
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
            # Verifica se o metadata veio preenchido (casos legados) ou se é texto puro
            if meta.get("type") == "product":
                # Passa os dados estruturados
                product_block = f"""
                [PRODUTO DETECTADO]
                NOME: {meta.get('title')}
                PREÇO: {meta.get('price')}
                LINK: {meta.get('link')}
                IMAGEM: {meta.get('image')}
                DESCRIÇÃO: {content.strip()}
                --------------------------
                """
                formatted_chunks.append(product_block)
            else:
                # Caso V11 (Smart Splitter): O conteúdo já contém Nome, Preço e Link em texto
                formatted_chunks.append(f"📄 [Info do Catálogo]: {content}\n")
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