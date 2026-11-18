"""
Application factory for Flask backend with CORS and blueprint registration.
"""

import os
from flask import Flask
from flask_cors import CORS
from backend.api.routes import api_bp
from backend.database.roster_store import roster_store


def create_app() -> Flask:
    app = Flask(__name__)

    # Eagerly warm up in-memory roster store so live routes make zero SQL queries
    roster_store.warmup()

    CORS(app, resources={r'/*': {'origins': '*'}})
    app.register_blueprint(api_bp)

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=int(os.environ.get('PORT', '5050')), host='0.0.0.0')
