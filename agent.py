# agent.py
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from operator import itemgetter
from rag_manager import get_retriever
import database

# Links fixos de categorias (Fundamentais para as regras rígidas)
VALID_LINKS = {
    "cães": "https://www.everpetzstore.com.br/products/search/?Category=1",
    "gatos": "https://www.everpetzstore.com.br/products/search/?Category=2",
    "pássaros": "https://www.everpetzstore.com.br/products/search/?Category=3",
    "peixes": "https://www.everpetzstore.com.br/products/search/?Category=4",
    "geral": "https://www.everpetzstore.com.br/products/search"
}
WHATSAPP_SUPPORT_LINK = "https://api.whatsapp.com/send?phone=555199013851&text=Ol%C3%A1%2C%20preciso%20de%20ajuda%20com"

# Template do Prompt (FUSÃO: Suas Regras Rígidas + Novas Capacidades de Venda)
AGENT_PROMPT_TEMPLATE = """
Você é {agent_name}, um Agente de Suporte e Vendas da EverPetz (www.everpetzstore.com.br).

# SUA MISSÃO
Fornecer atendimento humanizado, resolver dúvidas usando a base de conhecimento e, PRINCIPALMENTE, ajudar o cliente a encontrar os produtos certos no nosso catálogo.

# REGRAS RÍGIDAS (MANTIDAS INTEGRALMENTE)
- ❌ NUNCA use: "Não posso", "Infelizmente", "Não consigo". Em vez disso, ofereça alternativas.
- ❌ NUNCA invente produtos, URLs ou informações.
- ❌ NUNCA mencione ou compare com outras empresas.
- ✅ SEMPRE use a base de conhecimento para responder perguntas.
- ✅ Ao fornecer um link, SEMPRE mascare a URL com um texto descritivo usando a formatação Markdown. Por exemplo: "Você pode encontrar o que precisa na nossa [seção para gatos](URL_AQUI)". NUNCA mostre a URL completa sozinha na resposta.
- ✅ Ao direcionar para uma categoria de animal (cães, gatos, pássaros, peixes), você DEVE usar EXATAMENTE a URL correspondente da lista de links válidos. Não crie, simplifique ou adivinhe URLs. A lista é: {valid_links}.
- ✅ Se o usuário perguntar sobre promoções, ofertas ou produtos em geral, sem especificar um animal, direcione-o para a página geral de produtos usando o link 'geral' da lista de links válidos.
- ✅ Use um tom irreverente e amigável se identificar que o usuário está fazendo perguntas absurdas para te testar (ex: "tem aquário para gatos?").

# INSTRUÇÕES DE VENDA (NOVAS - INTEGRAÇÃO COM XML)
1. O contexto pode conter "Fichas de Produto" vindas do nosso sistema.
2. Se identificar um produto relevante para a pergunta, você DEVE recomendá-lo.
3. Ao recomendar, mostre o Nome, o Preço e o Link de Compra.
4. Se o contexto tiver uma imagem de produto, certifique-se de que ela seja exibida na resposta (use markdown de imagem: ![Alt](url)).

# ESCALAÇÃO PARA SUPORTE HUMANO
Se a resposta para a pergunta do usuário NÃO estiver no contexto da base de conhecimento, ou se for um problema complexo (reclamação, problema técnico, etc.), você DEVE encaminhar para o suporte humano.
Use a seguinte frase e forneça o link de suporte:
"Para te ajudar melhor com essa questão, por favor, entre em contato com um de nossos especialistas através do [nosso WhatsApp]({whatsapp_link}). Eles terão o maior prazer em ajudar!"

# BASE DE CONHECIMENTO (Contexto Recuperado)
{context}

# HISTÓRICO DA CONVERSA
{chat_history}

# PERGUNTA DO USUÁRIO
Usuário: {question}
{agent_name}:
"""

class EverpetzAgent:
    def __init__(self):
        # Temperatura 0.5 para equilibrar criatividade na conversa com precisão nos dados do produto
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.5)
        self.retriever = get_retriever()
        self.prompt = PromptTemplate(
            template=AGENT_PROMPT_TEMPLATE,
            input_variables=["agent_name", "context", "chat_history", "question", "valid_links", "whatsapp_link"]
        )
        
        # Chain de execução com a formatação de documentos incluída
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
        """
        Formata os documentos recuperados para o Prompt.
        Esta é a "mágica" que permite ao agente entender o XML.
        - Se for PRODUTO (do XML): Monta uma 'vitrine' com dados estruturados.
        - Se for TEXTO (do PDF): Mostra o conteúdo normal.
        """
        formatted_chunks = []
        
        for doc in docs:
            meta = doc.metadata
            content = doc.page_content
            
            # Verifica se é um produto vindo do feed XML (identificado pelo metadata 'type')
            if meta.get("type") == "product":
                # Monta um bloco de destaque para o produto
                product_display = f"""
                ---
                📦 **OPÇÃO ENCONTRADA:** {meta.get('title')}
                💰 **Preço:** {meta.get('price')}
                🔗 **Link:** [Comprar Agora]({meta.get('link')})
                🖼️ **Imagem:** ![{meta.get('title')}]({meta.get('image')})
                
                *Detalhes:* {content.strip()}
                ---
                """
                formatted_chunks.append(product_display)
            else:
                # Documento padrão (Base de Conhecimento PDF/TXT)
                formatted_chunks.append(f"📄 [Informação]: {content}\n")
                
        return "\n".join(formatted_chunks)

    def get_response(self, user_query, chat_history, session_settings):
        # Mantemos a regra do aquário aqui também como um "atalho rápido"
        if "aquário" in user_query.lower() and "gato" in user_query.lower():
            return "Haha! Gatos adoram aquários... mas só para assistir a TV de peixe! 🐟📺 Se quiser um aquário de verdade, temos ótimas opções na seção de peixes!"

        agent_name = session_settings.get("agent_name", "Bob")
        formatted_history = self.format_chat_history(chat_history)
        
        chain_input = {
            "question": user_query,
            "chat_history": formatted_history,
            "agent_name": agent_name 
        }

        response = self.chain.invoke(chain_input)
        return response