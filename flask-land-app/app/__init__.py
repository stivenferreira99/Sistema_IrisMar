from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:1234@localhost/irismar'
    # Es crucial configurar un SECRET_KEY para las sesiones y los mensajes flash.
    # ¡Asegúrate de cambiar 'tu_clave_secreta_aqui' por una cadena aleatoria y segura!
    app.config['SECRET_KEY'] = 'prueba123'
    db.init_app(app)
# En app/__init__.py
# ...
    with app.app_context():
        from .routes import main, filtrar_propiedades
        app.register_blueprint(main)
        db.create_all()
# ...


    return app