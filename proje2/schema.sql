-- MySQL tablo oluşturma sorguları

CREATE DATABASE IF NOT EXISTS university_exam_scheduler
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_turkish_ci;

USE university_exam_scheduler;

-- Kullanıcılar
CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(80) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(50) NOT NULL, -- admin, department_officer, instructor, student
  department VARCHAR(200),
  faculty VARCHAR(200)
);

-- Dersler
CREATE TABLE courses (
  ders_id INT AUTO_INCREMENT PRIMARY KEY,
  ders_adi VARCHAR(200) NOT NULL,
  bolum VARCHAR(200) NOT NULL,
  fakulte VARCHAR(200) NOT NULL,
  ogretim_uyesi VARCHAR(200) NOT NULL,
  ogrenci_sayisi INT NOT NULL,
  sinav_suresi INT NOT NULL, -- 30,60,90,120
  sinav_turu VARCHAR(50) NOT NULL, -- ara/final
  sinav_var_mi TINYINT(1) NOT NULL DEFAULT 1,
  ozel_durum VARCHAR(255)
);

-- Derslikler
CREATE TABLE classrooms (
  derslik_id INT AUTO_INCREMENT PRIMARY KEY,
  derslik_adi VARCHAR(100) NOT NULL UNIQUE,
  kapasite INT NOT NULL,
  sinav_uygun_mu TINYINT(1) NOT NULL DEFAULT 1,
  yakin_derslikler VARCHAR(255)
);

-- Hoca müsaitlikleri
CREATE TABLE instructor_availabilities (
  id INT AUTO_INCREMENT PRIMARY KEY,
  instructor_name VARCHAR(200) NOT NULL,
  date DATE NOT NULL,
  start_time TIME NOT NULL,
  end_time TIME NOT NULL
);

-- Sınavlar
CREATE TABLE exams (
  id INT AUTO_INCREMENT PRIMARY KEY,
  course_id INT NOT NULL,
  classroom_id INT NOT NULL,
  date DATE NOT NULL,
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_exam_course FOREIGN KEY (course_id) REFERENCES courses (ders_id),
  CONSTRAINT fk_exam_classroom FOREIGN KEY (classroom_id) REFERENCES classrooms (derslik_id)
);


