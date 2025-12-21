USE university_exam_scheduler;

-- Örnek kullanıcılar
INSERT INTO users (username, password_hash, role, faculty, department) VALUES
  ('admin1', 'admin123', 'admin', NULL, NULL),
  ('bolum_bilgisayar', 'bolum123', 'department_officer', 'Mühendislik Fakültesi', 'Bilgisayar Mühendisliği'),
  ('bolum_isletme', 'bolum123', 'department_officer', 'İktisadi ve İdari Bilimler Fakültesi', 'İşletme'),
  ('hoca_alg', 'hoca123', 'instructor', 'Mühendislik Fakültesi', 'Bilgisayar Mühendisliği'),
  ('hoca_prog', 'hoca123', 'instructor', 'Mühendislik Fakültesi', 'Bilgisayar Mühendisliği'),
  ('hoca_istat', 'hoca123', 'instructor', 'İktisadi ve İdari Bilimler Fakültesi', 'İşletme'),
  ('ogr_bilgi_1', 'ogr123', 'student', 'Mühendislik Fakültesi', 'Bilgisayar Mühendisliği'),
  ('ogr_bilgi_2', 'ogr123', 'student', 'Mühendislik Fakültesi', 'Bilgisayar Mühendisliği'),
  ('ogr_isletme_1', 'ogr123', 'student', 'İktisadi ve İdari Bilimler Fakültesi', 'İşletme');

-- Örnek dersler (Bilgisayar Mühendisliği)
INSERT INTO courses (ders_adi, bolum, fakulte, ogretim_uyesi, ogrenci_sayisi, sinav_suresi, sinav_turu, sinav_var_mi, ozel_durum) VALUES
  ('Algoritmalar', 'Bilgisayar Mühendisliği', 'Mühendislik Fakültesi', 'Dr. Ahmet Alg', 120, 90, 'vize', 1, NULL),
  ('Veri Yapıları', 'Bilgisayar Mühendisliği', 'Mühendislik Fakültesi', 'Dr. Ahmet Alg', 110, 90, 'final', 1, NULL),
  ('Programlama I', 'Bilgisayar Mühendisliği', 'Mühendislik Fakültesi', 'Dr. Ayşe Prog', 150, 120, 'vize', 1, NULL),
  ('Programlama II', 'Bilgisayar Mühendisliği', 'Mühendislik Fakültesi', 'Dr. Ayşe Prog', 140, 120, 'final', 1, NULL),
  ('Sayısal Analiz', 'Bilgisayar Mühendisliği', 'Mühendislik Fakültesi', 'Dr. Kemal Sayısal', 80, 60, 'vize', 1, 'Çift ekran gerekir');

-- Örnek dersler (İşletme)
INSERT INTO courses (ders_adi, bolum, fakulte, ogretim_uyesi, ogrenci_sayisi, sinav_suresi, sinav_turu, sinav_var_mi, ozel_durum) VALUES
  ('Muhasebe I', 'İşletme', 'İktisadi ve İdari Bilimler Fakültesi', 'Dr. Elif İstat', 90, 60, 'vize', 1, NULL),
  ('Muhasebe II', 'İşletme', 'İktisadi ve İdari Bilimler Fakültesi', 'Dr. Elif İstat', 85, 60, 'final', 1, NULL),
  ('İstatistik', 'İşletme', 'İktisadi ve İdari Bilimler Fakültesi', 'Dr. Elif İstat', 100, 90, 'vize', 1, NULL),
  ('Pazarlama', 'İşletme', 'İktisadi ve İdari Bilimler Fakültesi', 'Dr. Can Paz', 70, 60, 'vize', 0, 'Bu dönem sınav yok');  -- sinav_var_mi = 0

-- Örnek derslikler
INSERT INTO classrooms (derslik_adi, kapasite, sinav_uygun_mu, yakin_derslikler) VALUES
  ('A101', 60, 1, 'A102,A103'),
  ('A102', 60, 1, 'A101,A103'),
  ('A103', 80, 1, 'A101,A102'),
  ('B201', 40, 1, 'B202'),
  ('B202', 40, 0, 'B201'), -- sınava uygun olmayan küçük derslik
  ('C301', 120, 1, NULL);

-- Örnek hoca müsaitlikleri (algoritmanın kullanacağı veriler)
INSERT INTO instructor_availabilities (instructor_name, date, start_time, end_time) VALUES
  ('Dr. Ahmet Alg',       DATE_ADD(CURDATE(), INTERVAL 1 DAY), '09:00:00', '17:00:00'),
  ('Dr. Ayşe Prog',       DATE_ADD(CURDATE(), INTERVAL 1 DAY), '10:00:00', '18:00:00'),
  ('Dr. Kemal Sayısal',   DATE_ADD(CURDATE(), INTERVAL 2 DAY), '09:00:00', '15:00:00'),
  ('Dr. Elif İstat',      DATE_ADD(CURDATE(), INTERVAL 1 DAY), '09:00:00', '13:00:00'),
  ('Dr. Elif İstat',      DATE_ADD(CURDATE(), INTERVAL 2 DAY), '13:00:00', '18:00:00'),
  ('Dr. Can Paz',         DATE_ADD(CURDATE(), INTERVAL 3 DAY), '09:00:00', '12:00:00');


