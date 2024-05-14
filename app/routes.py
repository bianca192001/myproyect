from flask import jsonify
from . import mysql

def init_routes(app):
    @app.route('/')
    def home():
        return "Iniciando flask con los compas del duoc."
    
    @app.route('/productos', methods=['GET'])
    
    def obtener_productos():
        try:
            cursor = mysql.connection.cursor()
            consulta_sql = "SELECT id_producto,id_marca,nombre,precio FROM productos"
            cursor.execute(consulta_sql)
            productos = cursor.fetchall()
            cursor.close()
        except Exception as e:
            return jsonify({"error": str(e)}), 500

        lista_productos = []
        for producto in productos:
            lista_productos.append({
                'id': producto[0],
                'nombre': producto[1],
                'marca': producto[2],
                'precio': float(producto[3]) if producto[3] else None
            })

        return jsonify(lista_productos)


