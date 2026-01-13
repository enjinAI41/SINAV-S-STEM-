"""
Üniversite Sınav Programı Hazırlama Sistemi - Route (Yönlendirme) Dosyası
Bu dosya tüm web sayfası yönlendirmelerini ve iş mantığını içerir.
"""

from datetime import date

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    request,
    flash,
    session,
    jsonify,
)
from sqlalchemy.orm import joinedload
from werkzeug.security import check_password_hash

from app import db
from models import Course, Classroom, Exam, User, Role, InstructorAvailability, Student, StudentCourse, ClassroomProximity
from scheduler import generate_exam_schedule
from excel_importer import ExcelImporter

# Ana blueprint (yönlendirme grubu) oluştur
main_bp = Blueprint("main", __name__)

# Türkçe gün isimleri için Jinja2 filtresi
@main_bp.app_template_filter('turkish_day')
def turkish_day_filter(date_obj):
    """
    Tarihi Türkçe gün ismi ile döndürür.
    Örnek: Monday -> Pazartesi
    """
    turkish_days = {
        'Monday': 'Pazartesi',
        'Tuesday': 'Salı', 
        'Wednesday': 'Çarşamba',
        'Thursday': 'Perşembe',
        'Friday': 'Cuma',
        'Saturday': 'Cumartesi',
        'Sunday': 'Pazar'
    }
    english_day = date_obj.strftime('%A')
    return turkish_days.get(english_day, english_day)


def current_user():
    """
    Oturumdaki kullanıcıyı döndürür (basit session tabanlı kimlik doğrulama).
    Returns:
        User: Giriş yapmış kullanıcı nesnesi veya None
    """
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.get(user_id)


def login_required(roles=None):
    """
    Rol bazlı yetkilendirme için decorator fonksiyonu.
    Args:
        roles: İzin verilen roller listesi (opsiyonel)
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            user = current_user()
            # Kullanıcı giriş yapmamışsa login sayfasına yönlendir
            if not user:
                flash("Bu işlemi yapmak için giriş yapmalısınız.", "warning")
                return redirect(url_for("main.login"))
            # Kullanıcının rolü yetkilendirilmiş roller arasında değilse ana sayfaya yönlendir
            if roles and user.role not in roles:
                flash("Bu işlem için yetkiniz yok.", "danger")
                return redirect(url_for("main.index"))
            return func(*args, **kwargs)

        # Flask'ın endpoint ismi için fonksiyon adını koru
        wrapper.__name__ = func.__name__
        return wrapper

    return decorator


# ==================== ANA SAYFA ROUTE'LARI ====================

@main_bp.route("/")
def index():
    """
    Ana sayfa görüntüleme fonksiyonu.
    Kullanıcı durumuna göre farklı içerik gösterir.
    """
    return render_template("index.html", user=current_user())


# ==================== KİMLİK DOĞRULAMA ROUTE'LARI ====================

@main_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Kullanıcı giriş sayfası ve giriş işlemi.
    GET: Giriş formunu göster
    POST: Giriş bilgilerini kontrol et ve oturum başlat
    """
    if request.method == "POST":
        # Form verilerini al
        username = request.form.get("username")
        password = request.form.get("password")

        # Kullanıcıyı veritabanında ara
        user = User.query.filter_by(username=username).first()
        if not user:
            flash("Kullanıcı adı veya şifre hatalı.", "danger")
            return redirect(url_for("main.login"))
        
        # Şifre kontrolü - hem hash'li hem düz metin destekle
        password_correct = False
        
        # Önce hash'li şifre kontrolü dene
        if user.password_hash.startswith('scrypt:'):
            password_correct = check_password_hash(user.password_hash, password)
        else:
            # Düz metin şifre kontrolü (eski kullanıcılar için)
            password_correct = (user.password_hash == password)
        
        if not password_correct:
            flash("Kullanıcı adı veya şifre hatalı.", "danger")
            return redirect(url_for("main.login"))

        # Oturum başlat
        session["user_id"] = user.id
        flash("Başarıyla giriş yaptınız.", "success")
        return redirect(url_for("main.index"))

    # GET isteği: Giriş formunu göster
    return render_template("login.html")


@main_bp.route("/logout")
def logout():
    """
    Kullanıcı çıkış işlemi.
    Oturumu temizler ve ana sayfaya yönlendirir.
    """
    session.clear()
    flash("Çıkış yapıldı.", "info")
    return redirect(url_for("main.index"))


# ==================== DERS YÖNETİMİ ROUTE'LARI ====================

@main_bp.route("/courses")
@login_required(roles=[Role.ADMIN, Role.DEPARTMENT_OFFICER])
def list_courses():
    """
    Ders listesi görüntüleme fonksiyonu.
    Sadece admin ve bölüm yetkilileri erişebilir.
    Bölüm yetkilileri sadece kendi fakülte/bölüm derslerini görür.
    """
    user = current_user()
    query = Course.query
    # Bölüm yetkilisi sadece kendi fakülte/bölüm derslerini görür
    if user.role == Role.DEPARTMENT_OFFICER:
        query = query.filter(
            Course.faculty == user.faculty,
            Course.department == user.department,
        )
    courses = query.all()
    return render_template("courses.html", courses=courses, user=user)


@main_bp.route("/courses/new", methods=["GET", "POST"])
@login_required(roles=[Role.ADMIN, Role.DEPARTMENT_OFFICER])
def create_course():
    user = current_user()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        faculty = request.form.get("faculty")
        department = request.form.get("department")
        instructor = request.form.get("instructor")
        student_count = request.form.get("student_count", type=int)
        exam_duration = request.form.get("exam_duration", type=int)
        exam_type = request.form.get("exam_type")
        has_exam = request.form.get("has_exam") == "on"
        special_case = request.form.get("special_case") or None
        requires_special_room = request.form.get("requires_special_room") == "on"

        if not all([name, code, faculty, department, instructor, student_count, exam_duration, exam_type]):
            flash("Lütfen tüm zorunlu alanları doldurun.", "warning")
            return redirect(url_for("main.create_course"))

        # Ders kodu benzersizliği kontrolü
        existing_course = Course.query.filter_by(code=code).first()
        if existing_course:
            flash(f"Bu ders kodu zaten mevcut: {code}", "warning")
            return redirect(url_for("main.create_course"))

        # Bölüm yetkilisinin fakülte/bölüm dışına ders eklemesini engelle
        if user.role == Role.DEPARTMENT_OFFICER:
            faculty = user.faculty
            department = user.department

        course = Course(
            name=name,
            code=code,
            faculty=faculty,
            department=department,
            instructor=instructor,
            student_count=student_count,
            exam_duration=exam_duration,
            exam_type=exam_type,
            has_exam=has_exam,
            special_case=special_case,
            requires_special_room=requires_special_room,
        )
        db.session.add(course)
        db.session.commit()
        flash("Ders başarıyla eklendi.", "success")
        return redirect(url_for("main.list_courses"))

    # Mevcut öğretim üyelerini al
    existing_instructors = db.session.query(Course.instructor).distinct().all()
    instructors = [instructor[0] for instructor in existing_instructors if instructor[0]]
    
    return render_template("course_form.html", user=user, instructors=instructors)


@main_bp.route("/courses/<int:course_id>/edit", methods=["GET", "POST"])
@login_required(roles=[Role.ADMIN, Role.DEPARTMENT_OFFICER])
def edit_course(course_id: int):
    user = current_user()
    course = Course.query.get_or_404(course_id)

    # Bölüm yetkilisi başka fakülte/bölüm dersini düzenleyemesin
    if user.role == Role.DEPARTMENT_OFFICER and not (
        course.faculty == user.faculty and course.department == user.department
    ):
        flash("Bu derste değişiklik yapma yetkiniz yok.", "danger")
        return redirect(url_for("main.list_courses"))

    if request.method == "POST":
        course.name = request.form.get("name")
        # Admin fakülte/bölüm güncelleyebilir, bölüm yetkilisi kendi bölümüne kilitlidir
        if user.role == Role.ADMIN:
            course.faculty = request.form.get("faculty")
            course.department = request.form.get("department")
        course.instructor = request.form.get("instructor")
        course.student_count = request.form.get("student_count", type=int)
        course.exam_duration = request.form.get("exam_duration", type=int)
        course.exam_type = request.form.get("exam_type")
        course.has_exam = request.form.get("has_exam") == "on"
        course.special_case = request.form.get("special_case") or None

        db.session.commit()
        flash("Ders güncellendi.", "success")
        return redirect(url_for("main.list_courses"))

    # Mevcut öğretim üyelerini al
    existing_instructors = db.session.query(Course.instructor).distinct().all()
    instructors = [instructor[0] for instructor in existing_instructors if instructor[0]]
    
    return render_template("course_form.html", course=course, user=user, instructors=instructors)


@main_bp.route("/courses/<int:course_id>/delete", methods=["POST"])
@login_required(roles=[Role.ADMIN, Role.DEPARTMENT_OFFICER])
def delete_course(course_id: int):
    user = current_user()
    course = Course.query.get_or_404(course_id)

    if user.role == Role.DEPARTMENT_OFFICER and not (
        course.faculty == user.faculty and course.department == user.department
    ):
        flash("Bu dersi silme yetkiniz yok.", "danger")
        return redirect(url_for("main.list_courses"))

    db.session.delete(course)
    db.session.commit()
    flash("Ders silindi.", "info")
    return redirect(url_for("main.list_courses"))


@main_bp.route("/classrooms")
@login_required(roles=[Role.ADMIN, Role.DEPARTMENT_OFFICER])
def list_classrooms():
    user = current_user()
    only_exam = request.args.get("only_exam") == "1"
    query = Classroom.query
    if only_exam:
        query = query.filter_by(exam_allowed=True)
    
    # Yakınlık verilerini de yükle - basit yaklaşım
    classrooms = query.all()
    
    # Derslikleri baş harflerine göre sırala (A, D, E, K, M, S, AMFİ)
    def sort_key(classroom):
        name = classroom.name
        if name.startswith('AMFİ'):
            return ('Z', name)  # AMFİ'leri en sona koy
        else:
            return (name[0], name)  # İlk harfe göre sırala
    
    classrooms.sort(key=sort_key)
    
    # Her derslik için yakınlık verilerini manuel yükle
    for classroom in classrooms:
        classroom._nearby_classrooms = []
        # Tüm yakın derslikleri al (sadece ilk 3'ü değil)
        proximities = ClassroomProximity.query.filter_by(classroom1_id=classroom.id).order_by(ClassroomProximity.distance_score).all()
        
        for prox in proximities:
            nearby_classroom = Classroom.query.get(prox.classroom2_id)
            if nearby_classroom:
                classroom._nearby_classrooms.append({
                    'classroom': nearby_classroom,
                    'distance': prox.distance_score,
                    'is_adjacent': prox.is_adjacent
                })
    
    return render_template(
        "classrooms.html",
        classrooms=classrooms,
        only_exam=only_exam,
        user=user,
    )


@main_bp.route("/classrooms/new", methods=["GET", "POST"])
@login_required(roles=[Role.ADMIN, Role.DEPARTMENT_OFFICER])
def create_classroom():
    if request.method == "POST":
        name = request.form.get("name")
        capacity = request.form.get("capacity", type=int)
        building = request.form.get("building") or None
        floor = request.form.get("floor") or None
        room_type = request.form.get("room_type") or "Normal"
        exam_allowed = request.form.get("exam_allowed") == "on"

        if not name or not capacity:
            flash("Derslik adı ve kapasite zorunludur.", "warning")
            return redirect(url_for("main.create_classroom"))

        # Derslik adı benzersizliği kontrolü
        existing_classroom = Classroom.query.filter_by(name=name).first()
        if existing_classroom:
            flash(f"Bu derslik adı zaten mevcut: {name}", "warning")
            return redirect(url_for("main.create_classroom"))

        classroom = Classroom(
            name=name,
            capacity=capacity,
            building=building,
            floor=floor,
            room_type=room_type,
            exam_allowed=exam_allowed,
        )
        db.session.add(classroom)
        db.session.commit()
        flash("Derslik başarıyla eklendi.", "success")
        return redirect(url_for("main.list_classrooms"))

    return render_template("classroom_form.html", user=current_user())


@main_bp.route("/classrooms/<int:classroom_id>/edit", methods=["GET", "POST"])
@login_required(roles=[Role.ADMIN, Role.DEPARTMENT_OFFICER])
def edit_classroom(classroom_id: int):
    classroom = Classroom.query.get_or_404(classroom_id)
    if request.method == "POST":
        # Derslik adı benzersizliği kontrolü (kendisi hariç)
        new_name = request.form.get("name")
        if new_name != classroom.name:
            existing_classroom = Classroom.query.filter_by(name=new_name).first()
            if existing_classroom:
                flash(f"Bu derslik adı zaten mevcut: {new_name}", "warning")
                return redirect(url_for("main.edit_classroom", classroom_id=classroom_id))
        
        classroom.name = new_name
        classroom.capacity = request.form.get("capacity", type=int)
        classroom.building = request.form.get("building") or None
        classroom.floor = request.form.get("floor") or None
        classroom.room_type = request.form.get("room_type") or "Normal"
        classroom.exam_allowed = request.form.get("exam_allowed") == "on"
        
        db.session.commit()
        flash("Derslik güncellendi.", "success")
        return redirect(url_for("main.list_classrooms"))

    return render_template("classroom_form.html", classroom=classroom, user=current_user())


@main_bp.route("/classrooms/<int:classroom_id>/delete", methods=["POST"])
@login_required(roles=[Role.ADMIN, Role.DEPARTMENT_OFFICER])
def delete_classroom(classroom_id: int):
    classroom = Classroom.query.get_or_404(classroom_id)
    
    # Önce bu derslikle ilgili sınavları kontrol et
    exam_count = Exam.query.filter_by(classroom_id=classroom_id).count()
    if exam_count > 0:
        flash(f"Bu derslik {exam_count} sınavda kullanılıyor. Önce sınavları temizleyin.", "warning")
        return redirect(url_for("main.list_classrooms"))
    
    # Yakınlık verilerini temizle
    ClassroomProximity.query.filter(
        (ClassroomProximity.classroom1_id == classroom_id) |
        (ClassroomProximity.classroom2_id == classroom_id)
    ).delete()
    
    # Dersliği sil
    db.session.delete(classroom)
    db.session.commit()
    flash(f"Derslik '{classroom.name}' silindi.", "info")
    return redirect(url_for("main.list_classrooms"))


@main_bp.route("/instructor_availability", methods=["GET", "POST"])
@login_required(roles=[Role.ADMIN, Role.DEPARTMENT_OFFICER])
def manage_instructor_availability():
    if request.method == "POST":
        instructor_name = request.form.get("instructor_name")
        date_str = request.form.get("date")
        start_time = request.form.get("start_time")
        end_time = request.form.get("end_time")
        if not all([instructor_name, date_str, start_time, end_time]):
            flash("Lütfen tüm alanları doldurun.", "warning")
            return redirect(url_for("main.manage_instructor_availability"))

        availability = InstructorAvailability(
            instructor_name=instructor_name,
            date=date.fromisoformat(date_str),
            start_time=start_time,
            end_time=end_time,
        )
        db.session.add(availability)
        db.session.commit()
        flash("Müsaitlik bilgisi eklendi.", "success")
        return redirect(url_for("main.manage_instructor_availability"))

    availabilities = InstructorAvailability.query.order_by(
        InstructorAvailability.instructor_name, InstructorAvailability.date
    ).all()
    return render_template(
        "instructor_availability.html",
        availabilities=availabilities,
        user=current_user(),
    )


@main_bp.route("/exams")
@login_required(
    roles=[Role.ADMIN, Role.DEPARTMENT_OFFICER, Role.INSTRUCTOR, Role.STUDENT]
)
def list_exams():
    user = current_user()
    faculty = request.args.get("faculty")
    department = request.args.get("department")
    day = request.args.get("day")

    query = Exam.query.join(Course).join(Classroom).distinct()

    # Varsayılan olarak: bölüm yetkilisi / hoca / öğrenci kendi fakülte-bölümünü görsün
    # Admin tüm sınavları görebilir
    if not faculty and not department and user and user.faculty and user.role != Role.ADMIN:
        faculty = user.faculty
    if not department and user and user.department and user.role != Role.ADMIN:
        department = user.department

    if faculty:
        query = query.filter(Course.faculty == faculty)
    if department:
        query = query.filter(Course.department == department)
    if day:
        query = query.filter(Exam.date == date.fromisoformat(day))

    exams = query.order_by(Exam.date, Exam.start_time).all()
    
    # Aynı dersin birden fazla dersliği olabileceği için unique course sayısını hesapla
    unique_courses = set()
    unique_dates = set()
    total_students = 0
    processed_courses = set()
    
    for exam in exams:
        course_key = f"{exam.course.id}_{exam.date}_{exam.start_time}"
        if course_key not in processed_courses:
            unique_courses.add(exam.course.id)
            unique_dates.add(exam.date)
            total_students += exam.course.student_count
            processed_courses.add(course_key)
    
    # İstatistikler için ek bilgiler
    stats = {
        'unique_courses_count': len(unique_courses),
        'unique_dates_count': len(unique_dates),
        'total_students': total_students,
        'total_classrooms': len(set(exam.classroom.id for exam in exams))
    }
    
    return render_template("exams.html", exams=exams, user=user, stats=stats)


@main_bp.route("/admin/debug_classrooms")
@login_required(roles=[Role.ADMIN])
def debug_classrooms():
    """Debug: Tüm derslikleri ve durumlarını göster."""
    all_classrooms = Classroom.query.all()
    exam_allowed_classrooms = Classroom.query.filter_by(exam_allowed=True).all()
    
    debug_info = {
        'total_classrooms': len(all_classrooms),
        'exam_allowed_classrooms': len(exam_allowed_classrooms),
        'classrooms': []
    }
    
    for classroom in all_classrooms:
        debug_info['classrooms'].append({
            'name': classroom.name,
            'capacity': classroom.capacity,
            'exam_allowed': classroom.exam_allowed
        })
    
    return f"<pre>{debug_info}</pre>"


@main_bp.route("/admin/import_excel", methods=["GET", "POST"])
@login_required(roles=[Role.ADMIN])
def import_excel():
    """Excel dosyalarından veri import et"""
    if request.method == "POST":
        try:
            importer = ExcelImporter()
            results = importer.import_all()
            
            flash(f"Import başarılı! Öğrenci listeleri: {len(results['student_lists'])}, "
                  f"Derslik kapasiteleri: {results['classroom_capacities']}, "
                  f"Yakınlık ilişkileri: {results['classroom_proximity']}", "success")
        except Exception as e:
            flash(f"Import hatası: {str(e)}", "danger")
        
        return redirect(url_for("main.import_excel"))
    
    return render_template("import_excel.html", user=current_user())


@main_bp.route("/my_schedule")
@login_required()
def my_schedule():
    """Kişisel sınav takvimi - Öğrenci veya Hoca için"""
    user = current_user()
    exams = []
    
    if user.is_student() and user.student_no:
        # Öğrenci için: Kayıtlı olduğu derslerin sınavları
        student_courses = StudentCourse.query.filter_by(student_no=user.student_no).all()
        course_ids = [sc.course_id for sc in student_courses]
        
        if course_ids:
            exams = (Exam.query
                    .join(Course)
                    .join(Classroom)
                    .filter(Course.id.in_(course_ids))
                    .order_by(Exam.date, Exam.start_time)
                    .all())
    
    elif user.is_instructor() and user.instructor_name:
        # Hoca için: Verdiği derslerin sınavları
        exams = (Exam.query
                .join(Course)
                .join(Classroom)
                .filter(Course.instructor == user.instructor_name)
                .order_by(Exam.date, Exam.start_time)
                .all())
    
    return render_template("my_schedule.html", exams=exams, user=user)


@main_bp.route("/admin/run_scheduler", methods=["POST"])
@login_required(roles=[Role.ADMIN])
def run_scheduler():
    """Gelişmiş otomatik planlama tetikleme endpoint'i."""
    all_courses = Course.query.filter_by(has_exam=True).all()
    all_classrooms = Classroom.query.filter_by(exam_allowed=True).all()

    # Debug: Kaç derslik bulundu?
    print(f"DEBUG: {len(all_classrooms)} derslik bulundu:")
    for classroom in all_classrooms:
        print(f"  - {classroom.name} (kapasite: {classroom.capacity}, sınava uygun: {classroom.exam_allowed})")
    
    print(f"DEBUG: {len(all_courses)} ders bulundu:")
    for course in all_courses:
        print(f"  - {course.name} (öğrenci: {course.student_count})")

    # Gelişmiş scheduler'ı çağır
    schedule = generate_exam_schedule(all_courses, all_classrooms, days=10)

    if not schedule.success:
        flash("Planlama başarısız: " + schedule.message, "danger")
        return redirect(url_for("main.index"))

    # Eski sınavları temizle
    Exam.query.delete()

    # Yeni sınavları ekle
    for exam_info in schedule.exams:
        exam = Exam(
            course_id=exam_info.course_id,
            classroom_id=exam_info.classroom_id,
            date=exam_info.date,
            start_time=exam_info.start_time,
            end_time=exam_info.end_time,
            exam_group_id=exam_info.exam_group_id
        )
        db.session.add(exam)

    db.session.commit()
    
    # İstatistikleri flash mesajında göster
    stats = schedule.statistics
    flash(f"Sınav programı oluşturuldu! {stats['scheduled_courses']}/{stats['total_courses']} ders planlandı. "
          f"{stats['total_classrooms_used']} derslik kullanıldı.", "success")
    
    if stats['failed_courses']:
        flash(f"Planlanamayan dersler: {', '.join(stats['failed_courses'])}", "warning")
    
    return redirect(url_for("main.list_exams"))
    flash("Sınav programı başarıyla oluşturuldu.", "success")
    return redirect(url_for("main.list_exams"))


@main_bp.route("/admin/clear_schedule", methods=["POST"])
@login_required(roles=[Role.ADMIN])
def clear_schedule():
    """Tüm sınav programını temizler (yeniden planlama öncesi veya sıfırlama için)."""
    Exam.query.delete()
    db.session.commit()
    flash("Tüm sınav programı temizlendi.", "info")
    return redirect(url_for("main.list_exams"))


@main_bp.route("/exams/export/csv")
@login_required(
    roles=[Role.ADMIN, Role.DEPARTMENT_OFFICER, Role.INSTRUCTOR, Role.STUDENT]
)
def export_exams_csv():
    """Sınav programını CSV (Excel ile açılabilir) olarak indir."""
    import csv
    from io import StringIO
    from flask import Response

    faculty = request.args.get("faculty")
    department = request.args.get("department")
    day = request.args.get("day")

    query = Exam.query.join(Course).join(Classroom).distinct()
    if faculty:
        query = query.filter(Course.faculty == faculty)
    if department:
        query = query.filter(Course.department == department)
    if day:
        query = query.filter(Exam.date == date.fromisoformat(day))

    exams = query.order_by(Exam.date, Exam.start_time).all()

    # Aynı dersin birden fazla dersliğini grupla
    grouped_exams = {}
    for exam in exams:
        key = f"{exam.course.id}_{exam.date.strftime('%Y%m%d')}_{exam.start_time.strftime('%H%M')}"
        if key not in grouped_exams:
            grouped_exams[key] = {'exam': exam, 'classrooms': []}
        grouped_exams[key]['classrooms'].append(exam.classroom)

    output = StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(
        [
            "Ders",
            "Öğretim Üyesi",
            "Fakülte",
            "Bölüm",
            "Derslikler",
            "Toplam Kapasite",
            "Öğrenci Sayısı",
            "Tarih",
            "Başlangıç",
            "Bitiş",
            "Süre (dk)",
            "Sınav Türü",
        ]
    )
    for group in grouped_exams.values():
        e = group['exam']
        classrooms = group['classrooms']
        classroom_names = ", ".join([cl.name for cl in classrooms])
        total_capacity = sum([cl.capacity for cl in classrooms])
        
        writer.writerow(
            [
                e.course.name,
                e.course.instructor,
                e.course.faculty,
                e.course.department,
                classroom_names,
                total_capacity,
                e.course.student_count,
                e.date.strftime("%d.%m.%Y"),
                e.start_time.strftime("%H:%M"),
                e.end_time.strftime("%H:%M"),
                e.course.exam_duration,
                e.course.exam_type,
            ]
        )

    # Excel'in Türkçe karakterleri doğru algılaması için UTF-8 BOM ekleyelim
    bom = "\ufeff"
    csv_text = bom + output.getvalue()

    response = Response(csv_text, mimetype="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = "attachment; filename=sinav_programi.csv"
    return response


@main_bp.route("/exams/export/pdf")
@login_required(
    roles=[Role.ADMIN, Role.DEPARTMENT_OFFICER, Role.INSTRUCTOR, Role.STUDENT]
)
def export_exams_pdf():
    """Sınav programını profesyonel PDF formatında indir - ReportLab Table kullanarak."""
    from io import BytesIO
    from flask import send_file
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # Filtre parametreleri
    faculty = request.args.get("faculty")
    department = request.args.get("department")
    day = request.args.get("day")

    # Veritabanı sorgusu
    query = Exam.query.join(Course).join(Classroom).distinct()
    if faculty:
        query = query.filter(Course.faculty == faculty)
    if department:
        query = query.filter(Course.department == department)
    if day:
        query = query.filter(Exam.date == date.fromisoformat(day))

    exams = query.order_by(Exam.date, Exam.start_time).all()

    # Aynı dersin birden fazla dersliğini grupla
    grouped_exams = {}
    for exam in exams:
        key = f"{exam.course.id}_{exam.date.strftime('%Y%m%d')}_{exam.start_time.strftime('%H%M')}"
        if key not in grouped_exams:
            grouped_exams[key] = {'exam': exam, 'classrooms': []}
        grouped_exams[key]['classrooms'].append(exam.classroom)

    buffer = BytesIO()

    # Türkçe font kaydı
    try:
        # DejaVu Sans fontunu kaydet
        pdfmetrics.registerFont(TTFont('DejaVuSans', 'static/fonts/DejaVuSans.ttf'))
        base_font = 'DejaVuSans'
        bold_font = 'DejaVuSans'  # Bold yoksa normal kullan
    except Exception as e:
        print(f"Font yükleme hatası: {e}")
        # Font bulunamazsa Helvetica kullan
        base_font = 'Helvetica'
        bold_font = 'Helvetica-Bold'

    # PDF dokümanı oluştur (Landscape - Yatay)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )

    # Stil tanımlamaları
    styles = getSampleStyleSheet()
    
    # Başlık stili
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=bold_font,
        fontSize=16,
        spaceAfter=12,
        alignment=1,  # Ortala
        textColor=colors.darkblue
    )
    
    # Alt başlık stili
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontName=base_font,
        fontSize=10,
        spaceAfter=12,
        alignment=1,  # Ortala
        textColor=colors.grey
    )

    # Hücre içi metin stili
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontName=base_font,
        fontSize=8,
        leading=10,
        alignment=0  # Sola hizala
    )

    # Ortalanmış hücre stili
    cell_center_style = ParagraphStyle(
        'CellCenterStyle',
        parent=styles['Normal'],
        fontName=base_font,
        fontSize=8,
        leading=10,
        alignment=1  # Ortala
    )

    # PDF içeriği
    story = []

    # Başlık
    title = Paragraph("Üniversite Sınav Programı", title_style)
    story.append(title)

    # Filtre bilgileri
    if faculty or department or day:
        filter_info = []
        if faculty:
            filter_info.append(f"Fakülte: {faculty}")
        if department:
            filter_info.append(f"Bölüm: {department}")
        if day:
            filter_info.append(f"Tarih: {day}")
        
        subtitle = Paragraph(" | ".join(filter_info), subtitle_style)
        story.append(subtitle)
    
    story.append(Spacer(1, 12))

    # Tablo verilerini hazırla
    table_data = []
    
    # Başlık satırı
    headers = [
        "Ders Adı",
        "Ders Kodu", 
        "Öğretim Üyesi",
        "Fakülte",
        "Bölüm",
        "Derslikler",
        "Tarih",
        "Saat",
        "Süre",
        "Tür"
    ]
    
    # Başlık satırını ekle
    header_row = []
    for header in headers:
        header_row.append(Paragraph(f"<b>{header}</b>", cell_center_style))
    table_data.append(header_row)

    # Veri satırlarını ekle
    for group in grouped_exams.values():
        e = group['exam']
        classrooms = group['classrooms']
        
        # Derslik listesini formatla - TÜM derslikler görünsün
        classroom_text = ", ".join([cl.name for cl in classrooms])
        
        # Fakülte ve bölüm isimlerini akıllıca kısalt
        def smart_truncate(text, max_words=2, max_chars=20):
            words = text.split()
            if len(words) <= max_words:
                result = " ".join(words)
            else:
                result = " ".join(words[:max_words]) + "..."
            
            if len(result) > max_chars:
                result = result[:max_chars-3] + "..."
            return result

        row = [
            Paragraph(e.course.name, cell_style),  # Ders Adı - tam metin, word wrap
            Paragraph(e.course.code, cell_center_style),  # Ders Kodu
            Paragraph(e.course.instructor, cell_style),  # Öğretim Üyesi - tam isim
            Paragraph(e.course.faculty, cell_style),  # Fakülte - tam isim
            Paragraph(e.course.department, cell_style),  # Bölüm - tam isim
            Paragraph(classroom_text, cell_style),  # Derslikler
            Paragraph(e.date.strftime("%d.%m.%Y"), cell_center_style),  # Tarih
            Paragraph(f"{e.start_time.strftime('%H:%M')}<br/>{e.end_time.strftime('%H:%M')}", cell_center_style),  # Saat
            Paragraph(f"{e.course.exam_duration}dk", cell_center_style),  # Süre
            Paragraph(e.course.exam_type, cell_center_style)  # Tür
        ]
        table_data.append(row)

    # Sütun genişlikleri (landscape A4 için optimize edilmiş)
    col_widths = [
        1.6*inch,  # Ders Adı - biraz daha daraltıldı
        0.6*inch,  # Ders Kodu - daraltıldı
        1.4*inch,  # Öğretim Üyesi - biraz daraltıldı
        1.2*inch,  # Fakülte - GENİŞLETİLDİ
        1.4*inch,  # Bölüm - GENİŞLETİLDİ
        1.2*inch,  # Derslikler - biraz daraltıldı
        0.7*inch,  # Tarih - daraltıldı
        0.7*inch,  # Saat
        0.5*inch,  # Süre
        0.6*inch   # Tür
    ]

    # Tablo oluştur
    table = Table(table_data, colWidths=col_widths, repeatRows=1)

    # Tablo stilini ayarla
    table_style = TableStyle([
        # Başlık satırı stili
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.darkblue),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), bold_font),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        
        # Veri satırları stili
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), base_font),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        
        # Hücre padding
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        
        # Dikey hizalama
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        
        # Alternatif satır renkleri (zebra pattern)
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        
        # Belirli sütunları ortala
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),  # Ders Kodu
        ('ALIGN', (6, 1), (6, -1), 'CENTER'),  # Tarih
        ('ALIGN', (7, 1), (7, -1), 'CENTER'),  # Saat
        ('ALIGN', (8, 1), (8, -1), 'CENTER'),  # Süre
        ('ALIGN', (9, 1), (9, -1), 'CENTER'),  # Tür
    ])

    table.setStyle(table_style)
    story.append(table)

    # Sayfa altı bilgi
    story.append(Spacer(1, 12))
    footer_text = f"Toplam {len(grouped_exams)} sınav • Oluşturulma: {date.today().strftime('%d.%m.%Y')}"
    footer = Paragraph(footer_text, subtitle_style)
    story.append(footer)

    # PDF'i oluştur
    doc.build(story)
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="sinav_programi.pdf",
    )


