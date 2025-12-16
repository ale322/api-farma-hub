import time
import requests
import csv
import os
import shutil  # Biblioteca para copiar arquivos

# --- CONFIGURAÇÕES DO SISTEMA ---
# Substitua pelo ID da farmácia que você cadastrou no banco
FARMACIA_ID = 2 

# URL da sua API no Render
API_URL = "https://api-farma-hub.onrender.com/update_stock"

# Nome do arquivo que o sistema da farmácia gera
ARQUIVO_ORIGINAL = "estoque.csv"

# Nome do arquivo temporário (Cópia de segurança para leitura)
ARQUIVO_TEMP = "temp_estoque_leitura.csv"


def ler_csv_e_enviar():
    print(f"\n📂 Detectada alteração! Iniciando processamento...")

    # --- PROTEÇÃO 1: SHADOW COPY (Evita erro se o Excel estiver aberto) ---
    try:
        shutil.copyfile(ARQUIVO_ORIGINAL, ARQUIVO_TEMP)
    except PermissionError:
        print("⚠️ ALERTA: O arquivo 'estoque.csv' está bloqueado pelo sistema/Excel.")
        print("   -> Tentarei novamente em 5 segundos...")
        return # Aborta esta tentativa, mas mantem o programa rodando
    except FileNotFoundError:
        print("❌ ERRO: Arquivo 'estoque.csv' sumiu da pasta.")
        return
    except Exception as e:
        print(f"❌ ERRO ao copiar arquivo: {e}")
        return

    # --- LEITURA DOS DADOS (Lê a cópia, nunca o original) ---
    produtos_para_envio = []
    
    try:
        with open(ARQUIVO_TEMP, mode='r', encoding='utf-8') as file:
            leitor = csv.DictReader(file)
            
            print("   --- Lendo Produtos ---")
            for linha in leitor:
                try:
                    # Converte e valida os dados
                    item = {
                        "ean": linha["EAN"].strip(),
                        "qty": int(linha["QUANTIDADE"]),
                        "price": float(linha["PRECO"].replace(',', '.')) # Garante que lê 9,50 ou 9.50
                    }
                    
                    # Mostra no terminal o que está lendo (Visualização)
                    print(f"   -> Item: {item['ean']} | Est: {item['qty']} | R$ {item['price']:.2f}")
                    
                    produtos_para_envio.append(item)
                except ValueError:
                    print(f"   ⚠️ Linha ignorada (dados inválidos): {linha}")
                    continue

    except Exception as e:
        print(f"❌ Erro ao ler CSV: {e}")
        return

    # --- PROTEÇÃO 2: ENVIO SEGURO (Não fecha se cair a internet) ---
    if produtos_para_envio:
        print(f"🚀 Enviando {len(produtos_para_envio)} produtos para a Nuvem...")
        
        try:
            # O timeout=10 impede que o programa trave eternamente se a internet estiver lenta
            resposta = requests.post(API_URL, json={
                "pharmacy_id": FARMACIA_ID,
                "products": produtos_para_envio
            }, timeout=10)
            
            if resposta.status_code == 200:
                print("✅ SUCESSO! Estoque atualizado na nuvem.")
            else:
                print(f"❌ ERRO NA API: {resposta.status_code} - {resposta.text}")
                
        except requests.exceptions.ConnectionError:
            print("⚠️ SEM INTERNET: Não foi possível conectar ao servidor.")
            print("   -> Os dados serão enviados assim que a conexão voltar.")
        except requests.exceptions.Timeout:
            print("⚠️ TIMEOUT: O servidor demorou muito para responder.")
        except Exception as e:
            print(f"❌ ERRO DESCONHECIDO NO ENVIO: {e}")
    else:
        print("⚠️ O arquivo CSV estava vazio ou sem produtos válidos.")

    # Remove o arquivo temporário para não deixar lixo na pasta
    try:
        os.remove(ARQUIVO_TEMP)
    except:
        pass


def main():
    print("🤖 Agente FarmaHub Iniciado v2.0 (Blindado)")
    print(f"👀 Vigiando arquivo: {ARQUIVO_ORIGINAL}")
    print("------------------------------------------------")
    
    ultimo_processamento = 0
    
    while True:
        try:
            if os.path.exists(ARQUIVO_ORIGINAL):
                data_modificacao = os.path.getmtime(ARQUIVO_ORIGINAL)
                
                # Se o arquivo mudou desde a última vez
                if data_modificacao > ultimo_processamento:
                    # Pequena pausa para garantir que o sistema da farmácia terminou de salvar o arquivo
                    time.sleep(1) 
                    
                    ler_csv_e_enviar()
                    ultimo_processamento = data_modificacao
                    print("⏳ Aguardando próxima atualização do estoque...")
            
            else:
                # Se o arquivo não existe, avisa mas não fecha
                pass 
                
        except Exception as e:
            print(f"❌ Erro fatal no loop principal: {e}")
            
        time.sleep(5) # Verifica a cada 5 segundos

if __name__ == "__main__":
    main()
