## Üniversite Sınav Programı Hazırlama Uygulaması

Python (Flask) ve MySQL kullanarak geliştirilen bu projede; üniversitedeki tüm fakülte, bölüm ve MYO’ların ara sınav / final sınavları belirli kısıtlar altında otomatik olarak planlanır ve dersliklere yerleştirilir.

### Teknolojiler

- **Backend**: Python, Flask, Flask-SQLAlchemy, Flask-Migrate
- **Veritabanı**: MySQL
- **Frontend**: HTML, Bootstrap, basit CSS/JS
- **Mimari**: MVC benzeri (model, view, controller/route, scheduler)

### Klasör Yapısı

- `app.py`: Flask uygulama fabrikası ve `db` nesnesi
- `main.py`: Uygulamayı çalıştırmak için giriş noktası
- `config.py`: Geliştirme/üretim ortamı ayarları ve MySQL bağlantı bilgileri
- `models.py`: `Course`, `Classroom`, `User`, `InstructorAvailability`, `Exam` modelleri
- `scheduler.py`: Kısıt tabanlı sınav planlama algoritması
- `routes.py`: Rol bazlı yetkilendirme içeren Flask blueprint ve endpoint'ler
- `templates/`: HTML şablonları (`base.html`, `index.html`, `login.html`, `courses.html`, `classrooms.html`, `exams.html`)
- `static/main.css`: Basit modern görünüm için CSS
- `schema.sql`: MySQL tablo oluşturma sorguları

### Veritabanı Kurulumu

1. MySQL sunucusunda bir kullanıcı ve şifre belirleyin.
2. `config.py` içinde `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_NAME` değerlerini kendi ortamınıza göre güncelleyin.
3. Aşağıdaki komutlarla şemayı yükleyin:

```bash
mysql -u root -p < schema.sql
```

veya önce veritabanını oluşturup:

```bash
mysql -u root -p
> SOURCE /tam/yol/schema.sql;
```

4. İsterseniz Flask-Migrate yerine doğrudan:

```python
from app import create_app, db
from models import *

app = create_app()
with app.app_context():
    db.create_all()
```

ile tabloları da üretebilirsiniz.

### Örnek Kullanıcılar

`users` tablosuna elle örnek kayıtlar ekleyebilirsiniz (basitlik için şifreler düz metin tutulmuştur, gerçek projede hash kullanın):

```sql
INSERT INTO users (username, password_hash, role, faculty, department)
VALUES
  ('admin1', 'admin123', 'admin', NULL, NULL),
  ('bolum1', 'bolum123', 'department_officer', 'Mühendislik Fakültesi', 'Bilgisayar Müh.'),
  ('hoca1', 'hoca123', 'instructor', 'Mühendislik Fakültesi', 'Bilgisayar Müh.'),
  ('ogr1', 'ogr123', 'student', 'Mühendislik Fakültesi', 'Bilgisayar Müh.');
```

### Uygulamayı Çalıştırma

1. Sanal ortam oluşturun ve bağımlılıkları yükleyin:

```bash
python -m venv venv
venv\Scripts\activate  # Windows
pip install flask flask_sqlalchemy flask_migrate pymysql
```

2. Gerekirse veritabanı tablolarını `db.create_all()` ile veya `schema.sql` ile oluşturun.
3. Uygulamayı çalıştırın:

```bash
python main.py
```

4. Tarayıcıdan `http://localhost:5000` adresine gidin.

### Rol Bazlı Yetkilendirme

- **Admin**:
  - Tüm sistemi görür.
  - `index` sayfasından "Otomatik Planlamayı Başlat" butonuyla planlamayı tetikler.
  - Dersler ve derslikler sayfasını görebilir.
- **Bölüm Yetkilisi**:
  - Kendi bölümündeki dersleri ve derslikleri görüntüleyebilir (örnek projede form ekleme/silme kısımı sade tutulmuştur).
- **Hoca**:
  - Sadece sınav programını görüntüler.
- **Öğrenci**:
  - Sadece kendi sınav programını görüntülemesi için altyapı uygundur, örnek proje tüm sınavları listeler (geliştirme ödevi olarak filtre eklenebilir).

### Algoritmanın Çalışma Mantığı (Kısa Rapor)

`scheduler.py` içinde **greedy + sınırlı backtracking** yaklaşımı kullanılmıştır:

- **Girdi**: Sınavı olan dersler (`Course`), sınav yapılabilen derslikler (`Classroom`), hoca müsaitlikleri (`InstructorAvailability`).
- **Kısıtlar**:
  - Aynı ders için birden fazla sınav saati olamaz.
  - Aynı derslikte aynı anda iki sınav olamaz.
  - Bir öğrencinin aynı saatte iki sınavı olamaz (modelde gerçek öğrenci listesi olmadığı için aynı fakülte/bölüm derslerinde çakışma engellenir).
  - Derslik kapasitesi aşılmaz; yetmezse birden fazla derslik birleştirilir.
  - Hoca sadece tanımlı olduğu müsait gün ve saat aralıklarında sınava girebilir.
  - Sınavlar, belirlenen çalışma saatleri dışına taşmaz (örnekte 09:00–18:00).

**Adımlar**:

1. Planlanacak dersler, `ogrenci_sayisi` azalan sırada sıralanır (en zoru önce yerleştir).
2. Belirli bir başlangıç tarihinden itibaren (örneğin bugün) `days` parametresi kadar gün ve her gün için 30 dakikalık zaman dilimleri (`generate_time_slots`) oluşturulur.
3. Her ders için sırayla:
   - Gün ve zaman dilimleri içinde gezilir.
   - Dersin sınav süresine göre bitiş saati hesaplanır; çalışma saatleri dışına taşmaması sağlanır.
   - İlgili hocanın bu gün/saat aralığında `InstructorAvailability` tablosuna göre müsait olup olmadığı kontrol edilir.
   - Kapasite yetecek şekilde bir veya daha fazla derslik birleştirilir; her derslik için aynı tarih/saatte çakışan başka bir sınav olup olmadığı kontrol edilir.
   - Bölüm/fakülte bazlı öğrenci çakışması kontrol edilir; aynı anda aynı bölüm/fakülte için iki farklı dersin sınavı konmaz.
4. Tüm kontrolleri geçen ilk uygun kombinasyon **greedy** olarak seçilir ve atama listesine eklenir.
5. Bazı dersler için uygun kombinasyon bulunamazsa, son eklenen atamalar geri alınarak (**backtracking**) alternatif gün/saat/derslik kombinasyonları denenir.

**Neden Bu Algoritma?**

- Tam kapsamlı bir kısıt programlama/ILP çözümü (ör. MILP solver) kullanımına göre:
  - Üniversite projesi seviyesi için daha anlaşılır ve kodu takip etmesi kolaydır.
  - Python ile direkt uygulanabilir, ek kütüphane gerektirmez.
  - Greedy kısım hızlı; backtracking ise zor durumlarda esneklik sağlar.

**Avantajlar**:

- Kısıtların çoğunu açıkça kod seviyesinde görebilirsiniz (eğitsel).
- Veri seti orta büyüklükteyken performansı tatmin edicidir.
- Kapasite yetersizliğinde otomatik derslik birleştirme yapar.

**Dezavantajlar**:

- Çok büyük sayıdaki ders/derslik kombinasyonlarında backtracking maliyeti artabilir.
- Teorik olarak her zaman çözüm garantisi vermez; ama çözüm varsa çoğu pratik durumda bulur.


