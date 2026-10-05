"""
Application factory for Flask backend with CORS and blueprint registration.
"""

from pathlib import Path
from flask import Flask
from flask_cors import CORS
from backend.api.routes import api_bp


def create_app() -> Flask:
    root_dir = Path(__file__).resolve().parent.parent.parent

    app = Flask(
        __name__,
        template_folder=str(root_dir / 'templates'),
        static_folder=str(root_dir / 'static'),
    )

    CORS(app, resources={r'/*': {'origins': '*'}})
    app.register_blueprint(api_bp)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000, host='0.0.0.0')
