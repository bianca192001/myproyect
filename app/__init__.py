from flask import Flask
from flask_mysqldb import MySQL

mysql = MySQL()  # Instancia global

def create_app():
    app = Flask(__name__)

    # Cargar configuración desde un archivo de configuración
    app.config.from_pyfile('config.py')

    # Inicializar MySQL con la aplicación
    mysql.init_app(app)

    with app.app_context():
        from .routes import init_routes
        init_routes(app, mysql)

    return app
