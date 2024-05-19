from flask import Flask,  jsonify, request
from datetime import datetime
import json 
import bcchapi

app = Flask(__name__)

# Inicializar bcchapi con tu nombre de usuario y contraseña de Bancocentra
siete = bcchapi.Siete("fr.saezm@duocuc.cl", "Cuenta.2024")

def obtener_tipo_cambio_hoy():
    # Obtener la fecha y hora actual
    hoy = datetime.now().strftime('%Y-%m-%d')

    # Obtener el tipo de cambio CLP a USD de hoy
    serie = siete.get("F073.TCO.PRE.Z.D", hoy, hoy)

    # Verificar si hay datos en la lista de observaciones
    if serie.Series.get('Obs'):
        # Obtener el tipo de cambio CLP a USD de hoy
        clp_to_usd = float(serie.Series['Obs'][0]['value'])
        return clp_to_usd
    else:
        return None

def obtener_ultimo_tipo_cambio():
    # Obtener el último valor disponible de la serie de tipo de cambio CLP a USD
    serie = siete.get("F073.TCO.PRE.Z.D")

    # Verificar si hay datos en la lista de observaciones
    if serie.Series.get('Obs'):
        # Obtener el último tipo de cambio CLP a USD
        clp_to_usd = float(serie.Series['Obs'][-1]['value'])
        return clp_to_usd
    else:
        return None

@app.route('/', methods=['GET', 'POST'])
def obtener_tipo_cambio():
    if request.method == 'POST':
        # Obtener el valor ingresado en pesos chilenos
        clp_amount = float(request.form['clp_amount'])

        # Intentar obtener el valor del dólar para el día de hoy
        clp_to_usd = obtener_tipo_cambio_hoy()

        # Si no hay datos disponibles para el día de hoy, obtener el último valor disponible
        if clp_to_usd is None:
            clp_to_usd = obtener_ultimo_tipo_cambio()

        if clp_to_usd is not None:
            # Calcular el valor en dólares
            usd_amount = clp_amount / clp_to_usd

            # Formatear el valor en dólares con el símbolo de la unidad monetaria y dos decimales
            formatted_usd_amount = "${:.2f}".format(usd_amount)

            # Devolver el valor en dólares formateado como respuesta en formato JSON
            return jsonify({"Dolar": formatted_usd_amount})
        else:
            # Manejar el caso donde no se encuentran datos de la serie
            return jsonify({"error": "No se encontraron datos de la serie para la fecha actual ni datos disponibles en la serie."}), 404
    else:
        # Renderizar el formulario para ingresar el valor en pesos chilenos
        return '''
            <form method="post">
                <label for="clp_amount">Ingrese el valor en pesos chilenos sin puntos:</label><br>
                <input type="text" id="clp_amount" name="clp_amount"><br>
                <input type="submit" value="Convertir a USD">
            </form>
        '''

if __name__ == '__main__':
    app.run(debug=True)