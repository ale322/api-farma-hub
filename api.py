
from flask import Flask, request, jsonify
import sqlite3
from flask_cors import CORS
app = Flask(__name__)
CORS(app)
DB_NAME = "farma_hub.db"

# Função auxiliar para conectar no banco
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # Permite acessar colunas pelo nome
    return conn

# --- ROTA 1: Health Check (Para ver se está vivo) ---
@app.route('/')
def index():
    return jsonify({"status": "online", "message": "API FarmaHub rodando no Parrot OS!"})

# --- ROTA 2: Busca de Medicamentos (Usada pela Telemedicina) ---
# Exemplo de uso: /search?ean=789101010
@app.route('/search', methods=['GET'])
def search_product():
    ean_buscado = request.args.get('ean')
    
    if not ean_buscado:
        return jsonify({"error": "Informe o EAN do produto"}), 400

    conn = get_db_connection()
    # Essa query mágica cruza o Estoque com a Farmácia
    # Só traz se tiver estoque (qty > 0)
    query = '''
        SELECT 
            ph.name as farmacia, 
            ph.address, 
            st.qty as quantidade, 
            st.price as preco
        FROM stock st
        JOIN pharmacies ph ON st.pharmacy_id = ph.id
        WHERE st.product_ean = ? AND st.qty > 0
    '''
    rows = conn.execute(query, (ean_buscado,)).fetchall()
    conn.close()

    # Formata a resposta em JSON bonito
    resultados = []
    for row in rows:
        resultados.append({
            "farmacia": row['farmacia'],
            "endereco": row['address'],
            "estoque": row['quantidade'],
            "preco": f"R$ {row['preco']:.2f}"
        })

    return jsonify(resultados)

# --- ROTA 3: Sincronização (Usada pelo Agente da Farmácia) ---
# O Agente manda um JSON com o estoque atualizado
@app.route('/sync', methods=['POST'])
def sync_stock():
    dados = request.get_json()
    
    # 1. Validação simples de segurança (API Key)
    api_key = request.headers.get('X-API-KEY')
    conn = get_db_connection()
    
    # Verifica qual farmácia é dona dessa chave
    farmacia = conn.execute('SELECT id FROM pharmacies WHERE api_key = ?', (api_key,)).fetchone()
    
    if not farmacia:
        conn.close()
        return jsonify({"error": "Acesso negado. Chave API inválida."}), 401
    
    pharmacy_id = farmacia['id']

    # 2. Atualiza o estoque no banco
    # (dados['estoque'] deve ser uma lista de produtos)
    for item in dados.get('estoque', []):
        ean = item['ean']
        qty = item['qty']
        price = item['price']
        
        # INSERT OR REPLACE: Se já existe, atualiza. Se não, cria.
        conn.execute('''
            INSERT INTO stock (pharmacy_id, product_ean, qty, price, last_updated) 
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(pharmacy_id, product_ean) 
            DO UPDATE SET qty=excluded.qty, price=excluded.price, last_updated=CURRENT_TIMESTAMP
        ''', (pharmacy_id, ean, qty, price))
    
    conn.commit()
    conn.close()
    
    return jsonify({"status": "sucesso", "message": "Estoque atualizado"})

if __name__ == '__main__':
    # Roda o servidor na porta 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
