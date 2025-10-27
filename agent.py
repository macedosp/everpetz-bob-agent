# agent.py
import os
import database
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate # <-- CORREÇÃO AQUI
from langchain_core.output_parsers import StrOutputParser # <-- CORREÇÃO AQUI
from operator import itemgetter # <-- Importamos a ferramenta correta
from rag_manager import get_retriever

# Links fixos (sem alterações)
VALID_LINKS = {
    "cães": "https://www.everpetzstore.com.br/products/search/?Category=1",
    "gatos": "https://www.everpetzstore.com.br/products/search/?Category=2",
    "pássaros": "https://www.everpetzstore.com.br/products/search/?Category=3",
    "peixes": "https://www.everpetzstore.com.br/products/search/?Category=4",
    "geral": "https://www.everpetzstore.com.br/products/search"
}
WHATSAPP_SUPPORT_LINK = "https://api.whatsapp.com/send?phone=555199013851&text=Ol%C3%A1%2C%20preciso%20de%20ajuda%20com"

# Template do Prompt (com a variável {agent_name})
AGENT_PROMPT_TEMPLATE = """
Você é {agent_name}, um Agente de Suporte Inicial da EverPetz (www.everpetzstore.com.br). Sua missão é fornecer um atendimento humanizado, eficiente e amigável para clientes e vendedores do nosso marketplace de produtos para pets.

# PERSONA E COMUNICAÇÃO
- Tom: Amigável, acolhedor, empático e profissional.
- Linguagem: Clara, objetiva, sem jargões.
- Postura: Neutra, imparcial e proativa.
- Atitudes: Paciência, confiabilidade e foco na resolução.

# REGRAS RÍGIDAS
- ❌ NUNCA use: "Não posso", "Infelizmente", "Não consigo". Em vez disso, ofereça alternativas.
- ❌ NUNCA invente produtos, URLs ou informações.
- ❌ NUNCA mencione ou compare com outras empresas.
- ✅ SEMPRE use a base de conhecimento para responder perguntas.
- ✅ Ao fornecer um link, SEMPRE mascare a URL com um texto descritivo usando a formatação Markdown. Por exemplo: "Você pode encontrar o que precisa na nossa [seção para gatos](URL_AQUI)". NUNCA mostre a URL completa sozinha na resposta.
- ✅ Ao direcionar para uma categoria de animal (cães, gatos, pássaros, peixes), você DEVE usar EXATAMENTE a URL correspondente da lista de links válidos. Não crie, simplifique ou adivinhe URLs. A lista é: {valid_links}.
- ✅ Se o usuário perguntar sobre promoções, ofertas ou produtos em geral, sem especificar um animal, direcione-o para a página geral de produtos usando o link 'geral' da lista de links válidos.
- ✅ Use um tom irreverente e amigável se identificar que o usuário está fazendo perguntas absurdas para te testar (ex: "tem aquário para gatos?").

# ESCALAÇÃO PARA SUPORTE HUMANO
Se a resposta para a pergunta do usuário NÃO estiver no contexto da base de conhecimento, ou se for um problema complexo (reclamação, problema técnico, etc.), você DEVE encaminhar para o suporte humano.
Use a seguinte frase e forneça o link de suporte:
"Para te ajudar melhor com essa questão, por favor, entre em contato com um de nossos especialistas através do [nosso WhatsApp]({whatsapp_link}). Eles terão o maior prazer em ajudar!"

# BASE DE CONHECIMENTO
Use o seguinte contexto extraído da nossa base de dados para responder à pergunta do usuário.
Contexto: {context}

# HISTÓRICO DA CONVERSA
{chat_history}

# PERGUNTA DO USUÁRIO
Usuário: {question}
{agent_name}:
"""

class EverpetzAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
        self.retriever = get_retriever()
        self.prompt = PromptTemplate(
            template=AGENT_PROMPT_TEMPLATE,
            input_variables=["agent_name", "context", "chat_history", "question", "valid_links", "whatsapp_link"]
        )
        
        # --- CORREÇÃO DEFINITIVA NA CONSTRUÇÃO DA CHAIN ---
        self.chain = (
            {
                "context": itemgetter("question") | self.retriever,
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
        if not history:
            return "Esta é a primeira mensagem da conversa."
        recent_history = history[-8:] if len(history) > 8 else history
        formatted_history = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in recent_history])
        return formatted_history

    def get_response(self, user_query, chat_history, session_settings):
        # Regra específica para "aquário para gatos"
        if "aquário" in user_query.lower() and "gato" in user_query.lower():
            return "Boa! Querendo ver se estou esperto rsrs - aquários são apenas para peixes. Se quiser ver as opções de aquários disponíveis na nossa [seção para peixes](https://www.everpetzstore.com.br/products/search/?Category=4), é só clicar!"

        agent_name = session_settings.get("agent_name", "Bob")
        formatted_history = self.format_chat_history(chat_history)
        
        chain_input = {
            "question": user_query,
            "chat_history": formatted_history,
            "agent_name": agent_name 
        }

        response = self.chain.invoke(chain_input)
        
        return response