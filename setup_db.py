import sqlite3
import os

# Nome do arquivo do banco de dados
DB_NAME = "farma_hub.db"

def create_database():
    # Remove o banco antigo se existir (para começar limpo)
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print(f"Banco antigo removido: {DB_NAME}")

    # Conecta (ou cria) o banco
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    print("Criando tabelas...")

    # 1. Tabela de Farmácias (Parceiros)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pharmacies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        cnpj TEXT UNIQUE,
        api_key TEXT UNIQUE, -- Chave que o Agente vai usar para autenticar
        address TEXT,
        latitude REAL,
        longitude REAL
    )
    ''')

    # 2. Tabela de Produtos (Catálogo Mestre)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        ean TEXT PRIMARY KEY, -- Código de Barras é a chave
        name TEXT NOT NULL,
        description TEXT,
        manufacturer TEXT
    )
    ''')

    # 3. Tabela de Estoque (A "Mágica")
    # Liga uma Farmácia a um Produto com preço e quantidade
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS stock (
        pharmacy_id INTEGER,
        product_ean TEXT,
        qty INTEGER NOT NULL,
        price REAL NOT NULL,
        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (pharmacy_id, product_ean),
        FOREIGN KEY(pharmacy_id) REFERENCES pharmacies(id),
        FOREIGN KEY(product_ean) REFERENCES products(ean)
    )
    ''')

    # --- DADOS DE TESTE (SEED) ---
    print("Inserindo dados de teste...")

    # Criar uma Farmácia Fictícia
    cursor.execute('''
    INSERT INTO pharmacies (name, cnpj, api_key, address, latitude, longitude)
    VALUES ('Farmácia do Bairro', '12345678000199', 'key_farma_01', 'Rua das Flores, 100', -23.5505, -46.6333)
    ''')

    # Criar alguns produtos (Dipirona e Tylenol)
    cursor.execute("INSERT INTO products (ean, name) VALUES ('789101010', 'Dipirona 500mg')")
    cursor.execute("INSERT INTO products (ean, name) VALUES ('789202020', 'Tylenol 750mg')")

    # Simular que a farmácia tem estoque desses produtos
    # Farmácia ID 1 tem 50 Dipironas a R$ 10.00 e 0 Tylenol
    cursor.execute("INSERT INTO stock (pharmacy_id, product_ean, qty, price) VALUES (1, '789101010', 50, 10.00)")
    cursor.execute("INSERT INTO stock (pharmacy_id, product_ean, qty, price) VALUES (1, '789202020', 0, 25.90)")

    conn.commit()
    conn.close()
    print(f"Sucesso! Banco de dados '{DB_NAME}' criado com dados de teste.")

if __name__ == "__main__":
    create_database()
