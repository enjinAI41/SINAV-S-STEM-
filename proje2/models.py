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
    name = db.Column("ders_adi", db.String(200), nullable=False)
    department = db.Column("bolum", db.String(200), nullable=False)
    faculty = db.Column("fakulte", db.String(200), nullable=False)
    instructor = db.Column("ogretim_uyesi", db.String(200), nullable=False)
    student_count = db.Column("ogrenci_sayisi", db.Integer, nullable=False)
    exam_duration = db.Column("sinav_suresi", db.Integer, nullable=False)  # 30,60,90,120
    exam_type = db.Column("sinav_turu", db.String(50), nullable=False)  # ara/final
    has_exam = db.Column("sinav_var_mi", db.Boolean, default=True)
    special_case = db.Column("ozel_durum", db.String(255))

    exams = db.relationship("Exam", back_populates="course", cascade="all, delete-orphan")


class Classroom(db.Model):
    __tablename__ = "classrooms"

    id = db.Column("derslik_id", db.Integer, primary_key=True)
    name = db.Column("derslik_adi", db.String(100), nullable=False, unique=True)
    capacity = db.Column("kapasite", db.Integer, nullable=False)
    exam_allowed = db.Column("sinav_uygun_mu", db.Boolean, default=True)
    nearby_classrooms = db.Column("yakin_derslikler", db.String(255))  # virgülle ayrılmış liste

    exams = db.relationship("Exam", back_populates="classroom")


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # admin, department_officer, instructor, student
    department = db.Column(db.String(200))
    faculty = db.Column(db.String(200))

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


class Exam(db.Model):
    __tablename__ = "exams"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.ders_id"), nullable=False)
    classroom_id = db.Column(db.Integer, db.ForeignKey("classrooms.derslik_id"), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    course = db.relationship("Course", back_populates="exams")
    classroom = db.relationship("Classroom", back_populates="exams")


