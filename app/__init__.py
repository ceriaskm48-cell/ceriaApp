from flask import Flask
from .config import COLOR_PRIMARY, COLOR_SECONDARY

def create_app():
    app = Flask(__name__)

    from .views import bp
    app.register_blueprint(bp)

    @app.context_processor
    def inject_colors():
        return dict(COLOR_PRIMARY=COLOR_PRIMARY, COLOR_SECONDARY=COLOR_SECONDARY)

    return app
