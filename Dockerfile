# Dockerfile
FROM python:3.10-slim

# Define fuso horário (Brasil/São Paulo)
ENV TZ=America/Sao_Paulo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Diretório de trabalho
WORKDIR /app

# Instala compiladores básicos (necessário para algumas libs Python)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código
COPY . .

# Expõe a porta do Dash
EXPOSE 8050

# Inicia o aplicativo
CMD ["python", "dashboard.py"]