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
    
    # Recebe a localização do usuário (pode vir vazia se ele negar)
    user_lat = request.args.get('lat', type=float)
    user_lon = request.args.get('lon', type=float)
    
    if not ean_buscado:
        return jsonify({"error": "Informe o EAN do produto"}), 400

    conn = get_db_connection()
    
    # QUERY ATUALIZADA: Agora buscamos latitude e longitude da farmácia
    query = '''
        SELECT 
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
        
        # Só calcula se o usuário mandou a posição dele
        if user_lat is not None and user_lon is not None:
            # Pega posição da farmácia do banco
            farma_lat = row['latitude']
            farma_lon = row['longitude']
            
            # Faz a mágica matemática
            distancia_km = calcular_distancia(user_lat, user_lon, farma_lat, farma_lon)
            
            # Lógica de Motoboy: 
            # Velocidade média de 20km/h na cidade + 10 min para separar o pedido
            tempo_minutos = int((distancia_km / 20) * 60) + 10
            tempo_estimado = f"{tempo_minutos} min"

        resultados.append({
            "farmacia": row['farmacia'],
            "endereco": row['address'],
            "estoque": row['quantidade'],
            "preco": f"R$ {row['preco']:.2f}",
            "distancia_raw": distancia_km, # Usado só para ordenar
            "distancia_txt": f"{distancia_km:.1f} km", # Usado para mostrar na tela
            "tempo": tempo_estimado
        })

    # ORDENAÇÃO: Se tiver distância, mostra o mais perto primeiro
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
