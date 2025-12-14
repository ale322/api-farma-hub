import sqlite3
import os

# Nome do arquivo do banco de dados
DB_NAME = "farma_hub.db"

def create_database():
    # 1. Remove o banco antigo se existir (para começar limpo)
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        print(f"Banco antigo removido: {DB_NAME}")

    # 2. Conecta (ou cria) o banco
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    print("Criando tabelas...")

    # Tabela de Farmácias (Parceiros)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pharmacies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        cnpj TEXT UNIQUE,
        api_key TEXT UNIQUE,
        address TEXT,
        latitude REAL,
        longitude REAL
    )
    ''')

    # Tabela de Produtos (Catálogo Mestre)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        ean TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT,
        manufacturer TEXT
    )
    ''')

    # Tabela de Estoque
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
    # Tabela de Métricas (Leads/Cliques)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pharmacy_id INTEGER,
        product_ean TEXT,
        action_type TEXT, -- Ex: 'clique_ver', 'clique_zap', 'rota'
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(pharmacy_id) REFERENCES pharmacies(id)
    )
    ''')

    # --- DADOS DE TESTE (SEED) ---
    print("Inserindo dados de teste...")

    # 1. Criar Farmácia em SÃO PAULO (Para comparação)
    cursor.execute('''
    INSERT INTO pharmacies (name, cnpj, api_key, address, latitude, longitude)
    VALUES ('Farmácia do Bairro (SP)', '12345678000199', 'key_farma_01', 'Rua das Flores, SP', -23.5505, -46.6333)
    ''')

    # 2. Criar Farmácia em SALVADOR (Pelourinho) - PARA SEU TESTE LOCAL
    cursor.execute('''
    INSERT INTO pharmacies (name, cnpj, api_key, address, latitude, longitude)
    VALUES ('Farmácia Pelourinho (BA)', '99887766000100', 'key_salvador', 'Largo do Pelourinho, Salvador - BA', -12.9714, -38.5114)
    ''')

    # Criar Produtos
    cursor.execute("INSERT INTO products (ean, name) VALUES ('789101010', 'Dipirona 500mg')")
    cursor.execute("INSERT INTO products (ean, name) VALUES ('789202020', 'Tylenol 750mg')")

    # --- ESTOQUE ---
    
    # Estoque da Farmácia de SP (ID 1)
    cursor.execute("INSERT INTO stock (pharmacy_id, product_ean, qty, price) VALUES (1, '789101010', 50, 10.00)")
    
    # Estoque da Farmácia de Salvador (ID 2)
    # Vamos colocar preços diferentes para você ver a diferença
    cursor.execute("INSERT INTO stock (pharmacy_id, product_ean, qty, price) VALUES (2, '789101010', 100, 9.50)")  # Dipirona mais barata
    cursor.execute("INSERT INTO stock (pharmacy_id, product_ean, qty, price) VALUES (2, '789202020', 20, 29.90)")   # Tem Tylenol

    conn.commit()
    conn.close()
    print(f"Sucesso! Banco de dados '{DB_NAME}' recriado com farmácias em SP e Salvador.")

if __name__ == "__main__":
    create_database()
