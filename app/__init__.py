from flask import Flask
from flask_mysqldb import MySQL 

mysql = MySQL()  # Instancia global

def create_app():
    app = Flask(__name__)
    app.config.from_pyfile('config.py')  
    mysql.init_app(app) 
    from .routes import init_routes
    init_routes(app)

    return app