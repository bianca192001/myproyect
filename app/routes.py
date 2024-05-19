# routes.py
from flask import Blueprint, render_template, jsonify, request, current_app
from datetime import datetime
import bcchapi
import uuid  # Importar el módulo uuid
from transbank.webpay.webpay_plus.transaction import Transaction, WebpayOptions
from transbank.common.integration_type import IntegrationType
import config
from flask import Flask, request, jsonify, render_template_string
from transbank.error.transbank_error import TransbankError
from transbank.webpay.webpay_plus.transaction import Transaction


app = Blueprint('app', __name__)

webpay_options = WebpayOptions(
    api_key=config.TBK_API_KEY,
    commerce_code=config.TBK_COMMERCE_CODE,
    integration_type=IntegrationType.TEST  # Usar ambiente de prueba
)

# Inicializar bcchapi con tu nombre de usuario y contraseña de Banco Central
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

    @app.route('/pay', methods=['POST'])
    def pay():
        amount = request.json.get('amount')
        session_id = str(uuid.uuid4())[:25]  # Generar un ID de sesión único y truncarlo a 25 caracteres
        buy_order = str(uuid.uuid4())[:25]   # Generar un ID de orden de compra único y truncarlo a 25 caracteres
        return_url = "http://localhost:5000/commit"  # Cambia esto a tu URL de retorno

        response = Transaction(webpay_options).create(buy_order, session_id, amount, return_url)
        return jsonify({
            "url": response['url'],
            "token": response['token']
        })

    @app.route('/commit', methods=['GET', 'POST'])
    def commit():
        token = request.args.get('token_ws')
        if not token:
            return jsonify({'error': 'Token is required'}), 400

        try:
            # Realiza la lógica de commit con el token
            response = Transaction(webpay_options).commit(token)

            # Información importante
            important_info = {
                "amount": response.get("amount"),
                "authorization_code": response.get("authorization_code"),
                "buy_order": response.get("buy_order"),
                "card_number": response.get("card_detail", {}).get("card_number"),
                "status": response.get("status"),
                "transaction_date": response.get("transaction_date")
            }

            return render_template_string(
                '''
                <!DOCTYPE html>
                <html lang="es">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Comprobante de Transacción</title>
                    <style>
                        body { font-family: Arial, sans-serif; }
                        .container { max-width: 600px; margin: 50px auto; padding: 20px; border: 1px solid #ccc; border-radius: 10px; }
                        h1 { text-align: center; }
                        .details { margin-top: 20px; }
                        .details p { margin: 5px 0; }
                        .details span { font-weight: bold; }
                        .back-button { display: block; width: 100%; text-align: center; margin-top: 20px; }
                        .back-button a { text-decoration: none; color: white; background-color: #007bff; padding: 10px 20px; border-radius: 5px; }
                        .back-button a:hover { background-color: #0056b3; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>Comprobante de Transacción</h1>
                        <div class="details">
                            <p><span>Monto:</span> {{ important_info['amount'] }}</p>
                            <p><span>Código de autorización:</span> {{ important_info['authorization_code'] }}</p>
                            <p><span>Orden de compra:</span> {{ important_info['buy_order'] }}</p>
                            <p><span>Número de tarjeta:</span> **** **** **** {{ important_info['card_number'] }}</p>
                            <p><span>Estado:</span> {{ important_info['status'] }}</p>
                            <p><span>Fecha de transacción:</span> {{ important_info['transaction_date'] }}</p>
                        </div>
                    </div>
                </body>
                </html>
                ''', important_info=important_info
            )

        except TransbankError as e:
            return jsonify({'error': str(e)}), 500