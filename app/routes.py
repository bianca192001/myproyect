from flask import render_template, jsonify, request, current_app
from datetime import datetime
import bcchapi

# Inicializar bcchapi con tu nombre de usuario y contraseña de Bancocentral
siete = bcchapi.Siete("fr.saezm@duocuc.cl", "Cuenta.2024")

def obtener_tipo_cambio_hoy():
    try:
        hoy = datetime.now().strftime('%Y-%m-%d')
        serie = siete.get("F073.TCO.PRE.Z.D", hoy, hoy)
        if serie.Series.get('Obs'):
            clp_to_usd = float(serie.Series['Obs'][0]['value'])
            return clp_to_usd
        else:
            return None
    except Exception as e:
        print(f"Error al obtener el tipo de cambio: {e}")
        return None

def obtener_ultimo_tipo_cambio():
    try:
        serie = siete.get("F073.TCO.PRE.Z.D")
        if serie.Series.get('Obs'):
            clp_to_usd = float(serie.Series['Obs'][-1]['value'])
            return clp_to_usd
        else:
            return None
    except Exception as e:
        print(f"Error al obtener el último tipo de cambio: {e}")
        return None

def init_routes(app, mysql):
    @app.route('/')
    def home():
        return render_template('productos.html')

    @app.route('/productos', methods=['GET'])
    def obtener_productos():
        try:
            cursor = mysql.connection.cursor()
            consulta_sql = """
                SELECT p.ID_Producto, m.Nombre, t.Descripcion, p.Nombre, p.Precio
                FROM productos p
                JOIN marcas m ON p.ID_Marca = m.ID_Marca
                JOIN tiposproducto t ON p.ID_TipoProducto = t.ID_TipoProducto
            """
            cursor.execute(consulta_sql)
            productos = cursor.fetchall()
            cursor.close()
        except Exception as e:
            current_app.logger.error(f"Error al obtener productos: {e}")
            return jsonify({"error": str(e)}), 500

        tipo_cambio = obtener_tipo_cambio_hoy()
        if tipo_cambio is None:
            tipo_cambio = obtener_ultimo_tipo_cambio()

        if tipo_cambio is None:
            return jsonify({"error": "No se pudo obtener el tipo de cambio"}), 500

        lista_productos = []
        for producto in productos:
            if producto[4] is not None:
                try:
                    precio_usd = float(producto[4]) / tipo_cambio
                except (TypeError, ValueError) as e:
                    current_app.logger.error(f"Error al convertir el precio: {e}")
                    precio_usd = None
            else:
                precio_usd = None
            lista_productos.append({
                'id': producto[0],
                'marca': producto[1],
                'tipo': producto[2],
                'nombre': producto[3],
                'precio': float(producto[4]) if producto[4] else None,
                'precio_usd': precio_usd
            })

        return jsonify(lista_productos)

    @app.route('/tipo_cambio', methods=['POST'])
    def obtener_tipo_cambio():
        data = request.get_json()
        clp_amount = float(data['clp_amount'])

        clp_to_usd = obtener_tipo_cambio_hoy()
        if clp_to_usd is None:
            clp_to_usd = obtener_ultimo_tipo_cambio()

        if clp_to_usd is not None:
            usd_amount = clp_amount / clp_to_usd
            formatted_usd_amount = "${:.2f}".format(usd_amount)
            return jsonify({"Dolar": formatted_usd_amount})
        else:
            return jsonify({"error": "No se encontraron datos de la serie para la fecha actual ni datos disponibles en la serie."}), 404
