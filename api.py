from flask import Flask, request, jsonify
import sqlite3
from flask_cors import CORS
import math  # <--- NOVA IMPORTAÇÃO

app = Flask(__name__)
CORS(app)
DB_NAME = "farma_hub.db"

# --- FUNÇÃO MATEMÁTICA NOVA (Fórmula de Haversine) ---
def calcular_distancia(lat1, lon1, lat2, lon2):
    # Raio da Terra em km
    R = 6371.0
    
    # Converte graus para radianos
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2)**2 + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dlon / 2)**2
    
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c # Retorna distância em KM

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return jsonify({"status": "online", "message": "API FarmaHub com Geolocalização!"})

# --- ROTA DE BUSCA ATUALIZADA ---
@app.route('/search', methods=['GET'])
def search_product():
    ean_buscado = request.args.get('ean')
    user_lat = request.args.get('lat', type=float)
    user_lon = request.args.get('lon', type=float)
    
    if not ean_buscado:
        return jsonify({"error": "Informe o EAN do produto"}), 400

    conn = get_db_connection()
    
    # ATENÇÃO AQUI: Adicionei 'ph.id' na primeira linha do SELECT
    query = '''
        SELECT 
            ph.id, 
            ph.name as farmacia, 
            ph.address, 
            ph.latitude,
            ph.longitude,
            st.qty as quantidade, 
            st.price as preco
        FROM stock st
        JOIN pharmacies ph ON st.pharmacy_id = ph.id
        WHERE st.product_ean = ? AND st.qty > 0
    '''
    rows = conn.execute(query, (ean_buscado,)).fetchall()
    conn.close()

    resultados = []
    for row in rows:
        distancia_km = 0
        tempo_estimado = "Calcular..."
        
        if user_lat is not None and user_lon is not None:
            farma_lat = row['latitude']
            farma_lon = row['longitude']
            distancia_km = calcular_distancia(user_lat, user_lon, farma_lat, farma_lon)
            tempo_minutos = int((distancia_km / 20) * 60) + 10
            tempo_estimado = f"{tempo_minutos} min"

        resultados.append({
            "id": row['id'],  # <--- NOVA LINHA FUNDAMENTAL
            "farmacia": row['farmacia'],
            "endereco": row['address'],
            "estoque": row['quantidade'],
            "preco": f"R$ {row['preco']:.2f}",
            "distancia_raw": distancia_km,
            "distancia_txt": f"{distancia_km:.1f} km",
            "tempo": tempo_estimado
        })

    if user_lat:
        resultados.sort(key=lambda x: x['distancia_raw'])

    return jsonify(resultados)

@app.route('/sync', methods=['POST'])
def sync_stock():
    dados = request.get_json()
    api_key = request.headers.get('X-API-KEY')
    
    conn = get_db_connection()
    farmacia = conn.execute('SELECT id FROM pharmacies WHERE api_key = ?', (api_key,)).fetchone()
    
    if not farmacia:
        conn.close()
        return jsonify({"error": "Acesso negado."}), 401
    
    pharmacy_id = farmacia['id']

    for item in dados.get('estoque', []):
        ean = item['ean']
        qty = item['qty']
        price = item['price']
        
        conn.execute('''
            INSERT INTO stock (pharmacy_id, product_ean, qty, price, last_updated) 
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(pharmacy_id, product_ean) 
            DO UPDATE SET qty=excluded.qty, price=excluded.price, last_updated=CURRENT_TIMESTAMP
        ''', (pharmacy_id, ean, qty, price))
    
    conn.commit()
    conn.close()
    
    return jsonify({"status": "sucesso", "message": "Estoque atualizado"})
    # --- ROTA DE REGISTRO (O App chama essa rota escondido) ---
@app.route('/log_action', methods=['POST'])
def log_action():
    dados = request.get_json()
    # Espera receber: { "pharmacy_id": 1, "ean": "...", "action": "clique_zap" }
    
    farma_id = dados.get('pharmacy_id')
    ean = dados.get('ean')
    acao = dados.get('action')
    
    conn = get_db_connection()
    conn.execute('INSERT INTO leads (pharmacy_id, product_ean, action_type) VALUES (?, ?, ?)', 
                 (farma_id, ean, acao))
    conn.commit()
    conn.close()
    return jsonify({"status": "logged"})

# --- ROTA DE RELATÓRIO (Só você acessa para ver os números) ---
@app.route('/dashboard', methods=['GET'])
def dashboard():
    conn = get_db_connection()
    
    # 1. Totais por Farmácia
    query_totais = '''
        SELECT ph.name, COUNT(l.id) as total
        FROM leads l
        JOIN pharmacies ph ON l.pharmacy_id = ph.id
        GROUP BY ph.name
    '''
    rows_totais = conn.execute(query_totais).fetchall()
    
    # 2. Últimas 10 ações (A PROVA REAL)
    query_detalhe = '''
        SELECT ph.name, l.product_ean, l.action_type, l.created_at
        FROM leads l
        JOIN pharmacies ph ON l.pharmacy_id = ph.id
        ORDER BY l.created_at DESC
        LIMIT 10
    '''
    rows_detalhe = conn.execute(query_detalhe).fetchall()
    conn.close()
    
    # Monta a resposta bonita
    totais = {row['name']: row['total'] for row in rows_totais}
    detalhes = []
    for row in rows_detalhe:
        detalhes.append(f"[{row['created_at']}] {row['name']} - {row['product_ean']} ({row['action_type']})")
        
    return jsonify({
        "resumo_mensal": totais,
        "auditoria_ultimos_cliques": detalhes
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
