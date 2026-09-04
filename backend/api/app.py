'''
app.py is responsible for application infrastructure: 
- loading environment variables, 
- setting up CORS, 
- registering error handlers
- establishing database connections.
'''

from pathlib import Path
from flask import Flask
from backend.api.routes import api_bp


def create_app() -> Flask:
    # Resolve the project root (baseball/)
    root_dir = Path(__file__).resolve().parent.parent.parent

    app = Flask(
        __name__,
        template_folder=str(root_dir / "templates"),
        static_folder=str(root_dir / "static"),
    )

    # Register all endpoints
    app.register_blueprint(api_bp)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)