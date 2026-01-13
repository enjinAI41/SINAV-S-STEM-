from datetime import datetime

from app import db


class Role:
    """Uygulama içi basit rol sabitleri."""

    ADMIN = "admin"
    DEPARTMENT_OFFICER = "department_officer"
    INSTRUCTOR = "instructor"
    STUDENT = "student"


class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column("ders_id", db.Integer, primary_key=True)
    code = db.Column("ders_kodu", db.String(20), nullable=False, unique=True)  # YZM332, BLM331 vb.
    name = db.Column("ders_adi", db.String(200), nullable=False)
    department = db.Column("bolum", db.String(200), nullable=False)
    faculty = db.Column("fakulte", db.String(200), nullable=False)
    instructor = db.Column("ogretim_uyesi", db.String(200), nullable=False)
    student_count = db.Column("ogrenci_sayisi", db.Integer, nullable=False)
    exam_duration = db.Column("sinav_suresi", db.Integer, nullable=False)  # 30,60,90,120,240,360,480 (4,6,8 saat)
    exam_type = db.Column("sinav_turu", db.String(50), nullable=False)  # ara/final
    has_exam = db.Column("sinav_var_mi", db.Boolean, default=True)
    special_case = db.Column("ozel_durum", db.String(255))  # Lab/Uygulama vb.
    requires_special_room = db.Column("ozel_mekan_gerekli", db.Boolean, default=False)

    exams = db.relationship("Exam", back_populates="course", cascade="all, delete-orphan")
    student_courses = db.relationship("StudentCourse", back_populates="course", cascade="all, delete-orphan")


class Student(db.Model):
    __tablename__ = "students"
    
    id = db.Column(db.Integer, primary_key=True)
    student_no = db.Column("ogrenci_no", db.String(20), nullable=False, unique=True)
    name = db.Column("ad_soyad", db.String(200))
    department = db.Column("bolum", db.String(200))
    faculty = db.Column("fakulte", db.String(200))
    
    student_courses = db.relationship("StudentCourse", back_populates="student", cascade="all, delete-orphan")


class StudentCourse(db.Model):
    """Öğrenci-Ders ilişki tablosu (Excel'den gelecek veriler)"""
    __tablename__ = "student_courses"
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.ders_id"), nullable=False)
    student_no = db.Column("ogrenci_no", db.String(20), nullable=False)  # Hızlı erişim için
    course_code = db.Column("ders_kodu", db.String(20), nullable=False)  # Hızlı erişim için
    
    student = db.relationship("Student", back_populates="student_courses")
    course = db.relationship("Course", back_populates="student_courses")
    
    __table_args__ = (db.UniqueConstraint('student_id', 'course_id', name='unique_student_course'),)


class Classroom(db.Model):
    __tablename__ = "classrooms"

    id = db.Column("derslik_id", db.Integer, primary_key=True)
    name = db.Column("derslik_adi", db.String(100), nullable=False, unique=True)
    capacity = db.Column("kapasite", db.Integer, nullable=False)
    exam_allowed = db.Column("sinav_uygun_mu", db.Boolean, default=True)
    building = db.Column("bina", db.String(100))  # Excel'den gelecek
    floor = db.Column("kat", db.String(10))  # Excel'den gelecek
    room_type = db.Column("oda_tipi", db.String(50))  # Normal, Lab, Amfi vb.

    exams = db.relationship("Exam", back_populates="classroom")
    proximity_from = db.relationship("ClassroomProximity", foreign_keys="ClassroomProximity.classroom1_id", back_populates="classroom1")
    proximity_to = db.relationship("ClassroomProximity", foreign_keys="ClassroomProximity.classroom2_id", back_populates="classroom2")


class ClassroomProximity(db.Model):
    """Derslik yakınlık matrisi (Excel'den gelecek)"""
    __tablename__ = "classroom_proximities"
    
    id = db.Column(db.Integer, primary_key=True)
    classroom1_id = db.Column(db.Integer, db.ForeignKey("classrooms.derslik_id"), nullable=False)
    classroom2_id = db.Column(db.Integer, db.ForeignKey("classrooms.derslik_id"), nullable=False)
    distance_score = db.Column("uzaklik_skoru", db.Float, nullable=False)  # 0-1 arası, 0=çok yakın, 1=çok uzak
    is_adjacent = db.Column("bitisik_mi", db.Boolean, default=False)  # Bitişik derslikler
    
    classroom1 = db.relationship("Classroom", foreign_keys=[classroom1_id], back_populates="proximity_from")
    classroom2 = db.relationship("Classroom", foreign_keys=[classroom2_id], back_populates="proximity_to")
    
    __table_args__ = (db.UniqueConstraint('classroom1_id', 'classroom2_id', name='unique_classroom_pair'),)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # admin, department_officer, instructor, student
    department = db.Column(db.String(200))
    faculty = db.Column(db.String(200))
    # Öğrenci/Hoca için ek bilgiler
    student_no = db.Column("ogrenci_no", db.String(20))  # Öğrenci ise
    instructor_name = db.Column("ogretim_uyesi_adi", db.String(200))  # Hoca ise

    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    def is_department_officer(self) -> bool:
        return self.role == Role.DEPARTMENT_OFFICER

    def is_instructor(self) -> bool:
        return self.role == Role.INSTRUCTOR

    def is_student(self) -> bool:
        return self.role == Role.STUDENT


class InstructorAvailability(db.Model):
    __tablename__ = "instructor_availabilities"

    id = db.Column(db.Integer, primary_key=True)
    instructor_name = db.Column(db.String(200), nullable=False)
    # Basitlik için sadece tarih ve saat aralığı tutuyoruz
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_available = db.Column("musait_mi", db.Boolean, default=True)  # False ise müsait değil


class Exam(db.Model):
    __tablename__ = "exams"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.ders_id"), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey("classrooms.derslik_id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Birden fazla derslik kullanılıyorsa grup bilgisi
    exam_group_id = db.Column("sinav_grup_id", db.String(50))  # Aynı sınavın farklı dersliklerini gruplar

    course = db.relationship("Course", back_populates="exams")
    classroom = db.relationship("Classroom", back_populates="exams")


