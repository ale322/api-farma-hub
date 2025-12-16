from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import math
import os

app = Flask(__name__)
CORS(app)

# --- CONFIGURAÇÃO DO BANCO (COLE SUA URL DO NEON AQUI) ---
# Ex: "postgres://usuario:senha@endpoint.neon.tech/neondb?sslmode=require"
DATABASE_URL = 'postgresql://neondb_owner:npg_MInKa3EA8CRF@ep-empty-water-aha5djpi-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'

def get_db_connection():
    # Conecta no Neon (PostgreSQL)
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

# --- CRIAÇÃO DAS TABELAS (Rodar uma vez) ---
def inicializar_banco():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Postgres usa SERIAL para auto-incremento, não INTEGER PRIMARY KEY AUTOINCREMENT
        cur.execute('''
            CREATE TABLE IF NOT EXISTS pharmacies (
                id SERIAL PRIMARY KEY, 
                name TEXT, 
                address TEXT, 
                latitude REAL, 
                longitude REAL
            );
        ''')
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS stock (
                id SERIAL PRIMARY KEY, 
                pharmacy_id INTEGER, 
                product_ean TEXT, 
                qty INTEGER, 
                price REAL
            );
        ''')
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id SERIAL PRIMARY KEY, 
                pharmacy_id INTEGER, 
                product_ean TEXT, 
                action_type TEXT, 
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        
        # Cria a farmácia padrão se não existir
        cur.execute("SELECT id FROM pharmacies WHERE id = 2")
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO pharmacies (id, name, address, latitude, longitude) 
                VALUES (2, 'Farmácia Pelourinho (BA)', 'Largo do Pelourinho, Salvador - BA', -12.9711, -38.5108)
            """)
            
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Banco de Dados Neon Inicializado com Sucesso!")
    except Exception as e:
        print(f"❌ Erro ao iniciar banco: {e}")

# --- RODA NA INICIALIZAÇÃO ---
# No Render, isso roda toda vez que o servidor sobe
inicializar_banco()

# --- FUNÇÕES AUXILIARES ---
def calcular_distancia(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# --- ROTAS ---

@app.route('/')
def home():
    return jsonify({"status": "online", "banco": "PostgreSQL (Neon)", "msg": "Sistema Profissional Ativo"})

@app.route('/search', methods=['GET'])
def search_product():
    ean_buscado = request.args.get('ean')
    user_lat = request.args.get('lat', type=float)
    user_lon = request.args.get('lon', type=float)
    
    if not ean_buscado: return jsonify({"error": "Informe o EAN"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Sintaxe Postgres usa %s
        query = '''
            SELECT ph.id, ph.name as farmacia, ph.address, ph.latitude, ph.longitude,
                st.qty as quantidade, st.price as preco
            FROM stock st
            JOIN pharmacies ph ON st.pharmacy_id = ph.id
            WHERE st.product_ean = %s AND st.qty > 0
        '''
        cur.execute(query, (ean_buscado,))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        resultados = []
        for row in rows:
            distancia_km = 0
            tempo_estimado = "A calcular"
            if user_lat is not None and user_lon is not None:
                dist = calcular_distancia(user_lat, user_lon, row['latitude'], row['longitude'])
                tempo = int((dist / 20) * 60) + 10
                distancia_km = dist
                tempo_estimado = f"{tempo} min"

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

        if user_lat: resultados.sort(key=lambda x: x['distancia_raw'])
        return jsonify(resultados)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/log_action', methods=['POST'])
def log_action():
    dados = request.get_json()
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO leads (pharmacy_id, product_ean, action_type) VALUES (%s, %s, %s)', 
                    (dados.get('pharmacy_id'), dados.get('ean'), dados.get('action')))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status": "logged"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/dashboard', methods=['GET'])
def dashboard():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        query_totais = '''
            SELECT ph.name, COUNT(l.id) as total 
            FROM leads l
            JOIN pharmacies ph ON l.pharmacy_id = ph.id 
            GROUP BY ph.name
        '''
        cur.execute(query_totais)
        rows_totais = cur.fetchall()
        
        # No Postgres, para ajustar fuso horário usamos AT TIME ZONE ou intervalo
        # Vamos simplificar subtraindo 3 horas direto
        query_detalhe = '''
            SELECT ph.name, l.product_ean, l.action_type, 
                   (l.created_at - INTERVAL '3 hours')::text as created_at
            FROM leads l JOIN pharmacies ph ON l.pharmacy_id = ph.id
            ORDER BY l.created_at DESC LIMIT 10
        '''
        cur.execute(query_detalhe)
        rows_detalhe = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return jsonify({
            "resumo_mensal": {row['name']: row['total'] for row in rows_totais},
            "auditoria_ultimos_cliques": [f"[{r['created_at'][:19]}] {r['name']} - {r['product_ean']} ({r['action_type']})" for r in rows_detalhe]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/update_stock', methods=['POST'])
def update_stock():
    dados = request.get_json()
    farma_id = dados.get('pharmacy_id')
    lista = dados.get('products')
    
    if not farma_id or not lista: return jsonify({"error": "Dados inválidos"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Limpa estoque antigo
        cur.execute('DELETE FROM stock WHERE pharmacy_id = %s', (farma_id,))
        
        # Insere novo
        for item in lista:
            cur.execute('INSERT INTO stock (pharmacy_id, product_ean, qty, price) VALUES (%s, %s, %s, %s)', 
                         (farma_id, item['ean'], item['qty'], item['price']))
        
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status": "sucesso", "msg": f"{len(lista)} itens atualizados"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
