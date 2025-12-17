import database
import getpass

print("--- Criação do Usuário Master (Admin) ---")

# Substitua pelo seu nome e e-mail
name = "Vamilson Macedo" 
email = "macedosp@gmail.com"

# Verifica se o usuário já existe
if database.get_user_by_email(email):
    print(f"Erro: O usuário master com o e-mail '{email}' já existe.")
else:
    # Solicita a senha de forma segura no terminal
    password = getpass.getpass(f"Digite a senha para {email}: ")

    # Cria o usuário
    user = database.create_user(
        name=name,
        email=email,
        plain_password=password,
        is_master=True
    )

    if user:
        print(f"✅ Sucesso! Usuário master '{user.name}' criado com o e-mail '{user.email}'.")
    else:
        print("❌ Falha ao criar o usuário.")

print("-----------------------------------------")