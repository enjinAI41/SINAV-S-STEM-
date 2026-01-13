import os


class Config:
    """Temel Flask yapılandırma ayarları."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")

    # Örnek MySQL bağlantı dizesi (kullanıcı kendi ortamına göre düzenlemeli)
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "12345678")
    DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
    DB_NAME = os.environ.get("DB_NAME", "university_exam_scheduler")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}


