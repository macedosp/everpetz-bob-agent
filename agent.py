# agent.py
# Módulo que contém a lógica principal do agente "Bob".
# Define a persona, processa as perguntas e gera as respostas usando o LLM.

import os
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser
from rag_manager import get_retriever

# Links fixos conforme o prompt
VALID_LINKS = {
    "cães": "https://www.everpetzstore.com.br/products/search/?Category=1",
    "gatos": "https://www.everpetzstore.com.br/products/search/?Category=2",
    "pássaros": "https://www.everpetzstore.com.br/products/search/?Category=3",
    "peixes": "https://www.everpetzstore.com.br/products/search/?Category=4",
    "geral": "https://www.everpetzstore.com.br/products/search" # Link geral adicionado
}

WHATSAPP_SUPPORT_LINK = "https://api.whatsapp.com/send?phone=555199013851&text=Ol%C3%A1%2C%20preciso%20de%20ajuda%20com"

# O prompt principal que define a persona e as regras do Bob
# Este é o coração do comportamento do agente.
AGENT_PROMPT_TEMPLATE = """
Você é Bob, um Agente de Suporte Inicial da EverPetz (www.everpetzstore.com.br). Sua missão é fornecer um atendimento humanizado, eficiente e amigável para clientes e vendedores do nosso marketplace de produtos para pets.

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
Bob:
"""

class EverpetzAgent:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
        self.retriever = get_retriever()
        self.prompt = PromptTemplate(
            template=AGENT_PROMPT_TEMPLATE,
            input_variables=["context", "chat_history", "question", "valid_links", "whatsapp_link"]
        )
        
        # Cria a "chain" de execução do LangChain
        self.chain = (
            {
                "context": self.retriever_wrapper, 
                "question": RunnablePassthrough(), 
                "chat_history": RunnablePassthrough(), 
                "valid_links": lambda x: VALID_LINKS,
                "whatsapp_link": lambda x: WHATSAPP_SUPPORT_LINK
            }
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

    def retriever_wrapper(self, inputs):
        """
        Função wrapper para o retriever, para que ele possa ser usado na chain.
        Ele extrai a query do dicionário de inputs.
        """
        query = inputs.get("question", "") # Pega a pergunta do usuário
        if self.retriever:
            return self.retriever.invoke(query)
        return "Nenhuma base de conhecimento foi carregada."

    def format_chat_history(self, history):
        """Formata o histórico de chat para ser inserido no prompt."""
        if not history:
            return "Esta é a primeira mensagem da conversa."
        
        formatted_history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
        return formatted_history

    def get_response(self, user_query, chat_history):
        """
        Processa a query do usuário e retorna a resposta do Bob.
        
        Args:
            user_query (str): A pergunta do usuário.
            chat_history (list): O histórico da conversa.

        Returns:
            str: A resposta gerada pelo agente.
        """
        # Regra específica para "aquário para gatos"
        if "aquário" in user_query.lower() and "gato" in user_query.lower():
            return "Boa! Querendo ver se estou esperto rsrs - aquários são apenas para peixes. Se quiser ver as opções de aquários disponíveis na nossa [seção para peixes](https://www.everpetzstore.com.br/products/search/?Category=4), é só clicar!"

        # Formata o histórico
        formatted_history = self.format_chat_history(chat_history)
        
        # Prepara o input para a chain
        chain_input = {
            "question": user_query,
            "chat_history": formatted_history
        }

        # Invoca a chain para obter a resposta
        response = self.chain.invoke(chain_input)
        
        return response