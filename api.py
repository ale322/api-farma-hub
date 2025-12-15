from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import math

app = Flask(__name__)
CORS(app)  # Permite que o site no GitHub acesse esta API

def get_db_connection():
    conn = sqlite3.connect('farma_hub.db')
    conn.row_factory = sqlite3.Row
    return conn

# Função auxiliar para calcular distância (Fórmula de Haversine)
def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371  # Raio da Terra em km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# --- ROTA 1: Status (Para checar se está online) ---
@app.route('/')
def home():
    return jsonify({"status": "online", "message": "API FarmaHub Operando 24h"})

# --- ROTA 2: Busca de Produtos (Com GPS e ID da Farmácia) ---
@app.route('/search', methods=['GET'])
def search_product():
    ean_buscado = request.args.get('ean')
    user_lat = request.args.get('lat', type=float)
    user_lon = request.args.get('lon', type=float)
    
    if not ean_buscado:
        return jsonify({"error": "Informe o EAN do produto"}), 400

    conn = get_db_connection()
    
    # Busca produtos com estoque > 0
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
        tempo_estimado = "A calcular"
        
        # Se o usuário mandou GPS, calcula a distância real
        if user_lat is not None and user_lon is not None:
            farma_lat = row['latitude']
            farma_lon = row['longitude']
            distancia_km = calcular_distancia(user_lat, user_lon, farma_lat, farma_lon)
            tempo_minutos = int((distancia_km / 20) * 60) + 10 # 20km/h média motoboy + 10min preparo
            tempo_estimado = f"{tempo_minutos} min"

        resultados.append({
            "id": row['id'],
            "farmacia": row['farmacia'],
            "endereco": row['address'],
            "estoque": row['quantidade'],
            "preco": f"R$ {row['preco']:.2f}",
            "distancia_raw": distancia_km,
            "distancia_txt": f"{distancia_km:.1f} km",
            "tempo": tempo_estimado
        })

    # Ordena: Mais perto primeiro
    if user_lat:
        resultados.sort(key=lambda x: x['distancia_raw'])

    return jsonify(resultados)

# --- ROTA 3: Monitoramento de Vendas (Espião) ---
@app.route('/log_action', methods=['POST'])
def log_action():
    dados = request.get_json()
    farma_id = dados.get('pharmacy_id')
    ean = dados.get('ean')
    acao = dados.get('action')
    
    conn = get_db_connection()
    # Grava o horário UTC padrão do servidor
    conn.execute('INSERT INTO leads (pharmacy_id, product_ean, action_type) VALUES (?, ?, ?)', 
                 (farma_id, ean, acao))
    conn.commit()
    conn.close()
    return jsonify({"status": "logged"})

# --- ROTA 4: Painel do Dono (Dashboard - CORRIGIDO HORA) ---
@app.route('/dashboard', methods=['GET'])
def dashboard():
    conn = get_db_connection()
    
    # Totais por farmácia
    query_totais = '''
        SELECT ph.name, COUNT(l.id) as total
        FROM leads l
        JOIN pharmacies ph ON l.pharmacy_id = ph.id
        GROUP BY ph.name
    '''
    rows_totais = conn.execute(query_totais).fetchall()
    
    # Últimas 10 ações (Auditoria com ajuste de Fuso -3h)
    # A função datetime(..., '-03:00') força o SQLite a subtrair 3 horas
    query_detalhe = '''
        SELECT ph.name, l.product_ean, l.action_type, datetime(l.created_at, '-03:00') as created_at
        FROM leads l
        JOIN pharmacies ph ON l.pharmacy_id = ph.id
        ORDER BY l.created_at DESC
        LIMIT 10
    '''
    rows_detalhe = conn.execute(query_detalhe).fetchall()
    conn.close()
    
    totais = {row['name']: row['total'] for row in rows_totais}
    detalhes = []
    for row in rows_detalhe:
        detalhes.append(f"[{row['created_at']}] {row['name']} - {row['product_ean']} ({row['action_type']})")
        
    return jsonify({
        "resumo_mensal": totais,
        "auditoria_ultimos_cliques": detalhes
    })

# --- ROTA 5: Atualização Automática de Estoque ---
@app.route('/update_stock', methods=['POST'])
def update_stock():
    dados = request.get_json()
    farma_id = dados.get('pharmacy_id')
    lista_produtos = dados.get('products')
    
    if not farma_id or not lista_produtos:
        return jsonify({"error": "Dados inválidos"}), 400

    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM stock WHERE pharmacy_id = ?', (farma_id,))
        for item in lista_produtos:
            conn.execute('''
                INSERT INTO stock (pharmacy_id, product_ean, qty, price) 
                VALUES (?, ?, ?, ?)
            ''', (farma_id, item['ean'], item['qty'], item['price']))
            
        conn.commit()
        return jsonify({"status": "sucesso", "msg": f"{len(lista_produtos)} itens atualizados"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
