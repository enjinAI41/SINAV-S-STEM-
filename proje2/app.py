from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import config_map

db = SQLAlchemy()
migrate = Migrate()


def create_app(config_name: str = "development") -> Flask:
    """Flask uygulamasını oluşturan fabrika fonksiyonu."""
    app = Flask(__name__)
    app.config.from_object(config_map[config_name])

    db.init_app(app)
    migrate.init_app(app, db)

    # Modellerin importu (db.create_all için gerekli)
    from models import Course, Classroom, User, Exam, InstructorAvailability  # noqa: F401

    # Blueprint kayıtları
    from routes import main_bp

    app.register_blueprint(main_bp)

    return app


if __name__ == "__main__":
    application = create_app()
    application.run()


