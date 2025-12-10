import requests
import time
import random

# CONFIGURAÇÕES DA FARMÁCIA (Isso estaria num arquivo config.ini na vida real)
API_URL = "http://localhost:5000/sync"
API_KEY = "key_farma_01" # A mesma chave que cadastramos no banco de dados

# Simulação do ERP Local da Farmácia
# Na vida real, aqui leríamos do SQL Server ou MySQL da loja
def ler_erp_local():
    print("--- Lendo ERP Local... ---")
    
    # Vamos simular que o estoque muda aleatoriamente para testar
    estoque_atual = [
        {
            "ean": "789101010", # Dipirona
            "qty": random.randint(10, 60), # Gera um número entre 10 e 60
            "price": 10.50
        },
        {
            "ean": "789202020", # Tylenol
            "qty": random.randint(0, 5), # Gera entre 0 e 5 (às vezes falta!)
            "price": 28.90
        }
    ]
    return estoque_atual

def enviar_para_nuvem(dados_estoque):
    payload = {
        "estoque": dados_estoque
    }
    
    headers = {
        "X-API-KEY": API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        print(f"Enviando {len(dados_estoque)} produtos para a nuvem...")
        resposta = requests.post(API_URL, json=payload, headers=headers)
        
        if resposta.status_code == 200:
            print("✅ SUCESSO! Nuvem respondeu: ", resposta.json())
        elif resposta.status_code == 401:
            print("❌ ERRO: Chave de API inválida!")
        else:
            print(f"⚠️ AVISO: Erro {resposta.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ ERRO: Não foi possível conectar na API. O servidor está rodando?")

if __name__ == "__main__":
    # Loop infinito (simula o serviço rodando 24h)
    while True:
        dados = ler_erp_local()
        enviar_para_nuvem(dados)
        
        print("Dormindo por 10 segundos...")
        print("-" * 30)
        time.sleep(10) # Espera 10 segundos antes de enviar de novo
