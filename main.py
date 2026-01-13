"""
Üniversite Sınav Programı Hazırlama Sistemi - Ana Uygulama Dosyası
Bu dosya Flask uygulamasını başlatır ve çalıştırır.
"""

from app import create_app


app = create_app()


if __name__ == "__main__":
    app.run()


