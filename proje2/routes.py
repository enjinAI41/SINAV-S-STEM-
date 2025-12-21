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
)

from app import db
from models import Course, Classroom, Exam, User, Role, InstructorAvailability
from scheduler import generate_exam_schedule

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
        if not user or user.password_hash != password:
            # Not: Gerçek bir projede burada hash kontrolü yapılmalı
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
        faculty = request.form.get("faculty")
        department = request.form.get("department")
        instructor = request.form.get("instructor")
        student_count = request.form.get("student_count", type=int)
        exam_duration = request.form.get("exam_duration", type=int)
        exam_type = request.form.get("exam_type")
        has_exam = request.form.get("has_exam") == "on"
        special_case = request.form.get("special_case") or None

        if not all(
            [name, faculty, department, instructor, student_count, exam_duration, exam_type]
        ):
            flash("Lütfen tüm zorunlu alanları doldurun.", "warning")
            return redirect(url_for("main.create_course"))

        # Bölüm yetkilisinin fakülte/bölüm dışına ders eklemesini engelle
        if user.role == Role.DEPARTMENT_OFFICER:
            faculty = user.faculty
            department = user.department

        course = Course(
            name=name,
            faculty=faculty,
            department=department,
            instructor=instructor,
            student_count=student_count,
            exam_duration=exam_duration,
            exam_type=exam_type,
            has_exam=has_exam,
            special_case=special_case,
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
    classrooms = query.all()
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
        exam_allowed = request.form.get("exam_allowed") == "on"
        nearby_classrooms = request.form.get("nearby_classrooms") or None

        if not name or not capacity:
            flash("Derslik adı ve kapasite zorunludur.", "warning")
            return redirect(url_for("main.create_classroom"))

        classroom = Classroom(
            name=name,
            capacity=capacity,
            exam_allowed=exam_allowed,
            nearby_classrooms=nearby_classrooms,
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
        classroom.name = request.form.get("name")
        classroom.capacity = request.form.get("capacity", type=int)
        classroom.exam_allowed = request.form.get("exam_allowed") == "on"
        classroom.nearby_classrooms = request.form.get("nearby_classrooms") or None
        db.session.commit()
        flash("Derslik güncellendi.", "success")
        return redirect(url_for("main.list_classrooms"))

    return render_template("classroom_form.html", classroom=classroom, user=current_user())


@main_bp.route("/classrooms/<int:classroom_id>/delete", methods=["POST"])
@login_required(roles=[Role.ADMIN, Role.DEPARTMENT_OFFICER])
def delete_classroom(classroom_id: int):
    classroom = Classroom.query.get_or_404(classroom_id)
    db.session.delete(classroom)
    db.session.commit()
    flash("Derslik silindi.", "info")
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
    if not faculty and not department and user and user.faculty:
        faculty = user.faculty
    if not department and user and user.department:
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


@main_bp.route("/admin/run_scheduler", methods=["POST"])
@login_required(roles=[Role.ADMIN])
def run_scheduler():
    """Admin için otomatik planlama tetikleme endpoint'i."""
    # Basit örnek: tüm anahtar parametreleri içerde belirleyip algoritmayı çağırıyoruz.
    all_courses = Course.query.filter_by(has_exam=True).all()
    all_classrooms = Classroom.query.filter_by(exam_allowed=True).all()

    # Örnek: sınav günlerini 5 günlük bir aralık olarak varsayalım
    schedule = generate_exam_schedule(all_courses, all_classrooms)

    if not schedule.success:
        flash("Planlama başarısız: " + schedule.message, "danger")
        return redirect(url_for("main.index"))

    # Eski sınavları temizleyelim
    Exam.query.delete()

    for exam_info in schedule.exams:
        exam = Exam(
            course_id=exam_info.course_id,
            classroom_id=exam_info.classroom_id,
            date=exam_info.date,
            start_time=exam_info.start_time,
            end_time=exam_info.end_time,
        )
        db.session.add(exam)

    db.session.commit()
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
    """Sınav programını basit bir tablo halinde PDF olarak indir.

    Not: Türkçe karakterlerin düzgün çıkması için
    `static/fonts/DejaVuSans.ttf` benzeri bir UTF-8 destekli TTF fontu
    projeye eklenmeli.
    """
    from io import BytesIO
    from flask import send_file
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

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

    buffer = BytesIO()

    # Unicode (Türkçe) destekleyen font kaydı
    try:
        pdfmetrics.registerFont(TTFont("DejaVu", "static/fonts/DejaVuSans.ttf"))
        base_font = "DejaVu"
    except Exception:
        # Font bulunamazsa yedek olarak Helvetica kullanılacak (Türkçe kısıtlı olabilir)
        base_font = "Helvetica"
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 40
    # Başlık için de aynı fontu kullan (ayrı bir -Bold fontu kaydetmedik)
    p.setFont(base_font, 14)
    p.drawString(40, y, "Üniversite Sınav Programı")
    y -= 25

    p.setFont(base_font, 8)
    headers = [
        "Ders",
        "Öğr. Üyesi",
        "Fak/Bölüm",
        "Derslikler",
        "Tarih",
        "Saat",
        "Tür",
    ]
    # Derslik sütunu genişletildi, diğer sütunlar optimize edildi
    col_x = [40, 140, 220, 300, 420, 480, 540]
    for x, h_text in zip(col_x, headers):
        p.drawString(x, y, h_text)
    y -= 12
    p.line(40, y, width - 40, y)
    y -= 14

    # Satırlar için daha küçük font (daha fazla bilgi sığması için)
    p.setFont(base_font, 7)

    for group in grouped_exams.values():
        if y < 60:  # Daha fazla boşluk bırak (iki satırlı derslikler için)
            p.showPage()
            y = height - 40
            p.setFont(base_font, 7)
        
        e = group['exam']
        classrooms = group['classrooms']
        
        # Derslik isimlerini akıllıca kısalt
        if len(classrooms) == 1:
            classroom_text = classrooms[0].name
        elif len(classrooms) <= 3:
            classroom_text = ", ".join([cl.name for cl in classrooms])
        else:
            # 3'ten fazla derslik varsa ilk 2'sini göster + "..."
            classroom_text = f"{classrooms[0].name}, {classrooms[1].name}... (+{len(classrooms)-2})"
        
        # Derslik metnini sütun genişliğine göre kısalt (yaklaşık 25 karakter)
        if len(classroom_text) > 25:
            classroom_text = classroom_text[:22] + "..."
        
        row = [
            e.course.name[:15],
            e.course.instructor[:12],
            f"{e.course.faculty.split()[0][:8]}/{e.course.department.split()[0][:8]}",
            classroom_text,
            e.date.strftime("%d.%m.%Y"),
            f"{e.start_time.strftime('%H:%M')}-{e.end_time.strftime('%H:%M')}",
            e.course.exam_type[:6],
        ]
        # Satırı çiz
        for i, (x, text) in enumerate(zip(col_x, row)):
            # Derslik sütunu için özel işlem (index 3)
            if i == 3 and len(text) > 25:
                # Uzun derslik isimlerini iki satıra böl
                lines = []
                words = text.split(", ")
                current_line = ""
                for word in words:
                    if len(current_line + word) <= 25:
                        current_line += (", " if current_line else "") + word
                    else:
                        if current_line:
                            lines.append(current_line)
                        current_line = word
                if current_line:
                    lines.append(current_line)
                
                # İlk satırı çiz
                p.drawString(x, y, lines[0] if lines else text[:25])
                # İkinci satır varsa alt satıra çiz
                if len(lines) > 1:
                    p.drawString(x, y - 8, lines[1][:25])
            else:
                p.drawString(x, y, str(text))
        
        # Derslik sütunu iki satır kullandıysa ekstra boşluk bırak
        if len(classrooms) > 2:
            y -= 20
        else:
            y -= 12

    p.showPage()
    p.save()
    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="sinav_programi.pdf",
    )


