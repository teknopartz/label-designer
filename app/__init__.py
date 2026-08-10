from flask import Flask


def create_app(config):
    app = Flask(__name__)
    app.config.update(config)

    from .routes import bp
    app.register_blueprint(bp)

    return app
