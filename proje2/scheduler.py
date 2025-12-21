"""
Sınav planlama algoritması.

Bu projede temel olarak iki aşamalı bir yaklaşım kullanıyoruz:
1) Greedy (açgözlü) yerleştirme:
   - Dersleri öğrenci sayısına göre azalan sırada sıralıyoruz.
   - Her ders için uygun gün/saat aralığı ve derslik arıyoruz.
   - Önce tek bir derslik yetiyorsa en uygun dersliği seçiyoruz.
   - Kapasite yetmezse, yakın derslikler veya başka derslikler ile birleştirerek kapasiteyi karşılıyoruz.

2) Basit backtracking:
   - Greedy yerleştirme sırasında çıkmaz bir duruma girersek
     (hiçbir uygun slot bulunamıyorsa), son birkaç yerleştirmeyi geri alıp
     alternatif kombinasyonlar deniyoruz.

Avantajlar:
    - Greedy adım hızlı ve büyük çoğunlukla yeterli.
    - Backtracking sayesinde zor durumlarda alternatifler denenebilir.

Dezavantajlar:
    - Çok büyük veri setlerinde backtracking maliyetli olabilir.
    - Tüm mümkün kombinasyonları garantili olarak gezmez, ama pratikte
      üniversite düzeyindeki tipik boyutlarda yeterlidir.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time, timedelta
from typing import List, Dict, Tuple, Optional

from models import Course, Classroom, InstructorAvailability


@dataclass
class ExamAssignment:
    course_id: int
    classroom_id: int
    date: date
    start_time: time
    end_time: time


@dataclass
class ScheduleResult:
    success: bool
    message: str
    exams: List[ExamAssignment]


def generate_time_slots(
    start_hour: int = 9,
    end_hour: int = 18,
    slot_minutes: int = 30,
) -> List[time]:
    """Belirli bir gün için potansiyel başlangıç saatleri üretir."""
    slots: List[time] = []
    current = time(hour=start_hour, minute=0)
    while current < time(hour=end_hour, minute=0):
        slots.append(current)
        # datetime.time doğrudan timedelta ile toplanamadığı için küçük bir yardımcı kullanabiliriz
        dummy_datetime = timedelta(hours=current.hour, minutes=current.minute) + timedelta(
            minutes=slot_minutes
        )
        hours = dummy_datetime.seconds // 3600
        minutes = (dummy_datetime.seconds % 3600) // 60
        current = time(hour=hours, minute=minutes)
    return slots


def is_instructor_available(course: Course, exam_date: date, start: time, end: time) -> bool:
    """İlgili hocanın belirtilen zaman aralığında müsait olup olmadığını kontrol eder."""
    availabilities = InstructorAvailability.query.filter_by(
        instructor_name=course.instructor, date=exam_date
    ).all()
    if not availabilities:
        # Müsaitlik tanımı yoksa, basitçe müsait kabul edelim (aksi isteniyorsa değiştirilebilir)
        return True

    for avail in availabilities:
        if avail.start_time <= start and avail.end_time >= end:
            return True
    return False


def has_student_conflict(
    existing_exams: List[ExamAssignment],
    new_exam: ExamAssignment,
    course_lookup: Dict[int, Course],
) -> bool:
    """
    Bir öğrencinin aynı saatte iki sınavı olmaması kısıtı.
    Bu örnekte öğrenci listeleri yerine öğrenci sayıları ile çalışıyoruz,
    bu yüzden "aynı bölüm/fakülte ve aynı sınıf düzeyi" gibi kaba bir kontrol
    üzerinden çakışma kontrolü yapılabilir. Basit olması için:
    - Aynı bölüm ve fakültede, aynı anda iki farklı ders sınavı olmasın.
    """
    new_course = course_lookup[new_exam.course_id]
    for exam in existing_exams:
        if exam.date != new_exam.date:
            continue
        # Zaman çakışması kontrolü
        if not (exam.end_time <= new_exam.start_time or exam.start_time >= new_exam.end_time):
            existing_course = course_lookup[exam.course_id]
            if (
                existing_course.department == new_course.department
                and existing_course.faculty == new_course.faculty
            ):
                return True
    return False


def classroom_has_conflict(
    existing_exams: List[ExamAssignment],
    classroom_id: int,
    exam_date: date,
    start: time,
    end: time,
) -> bool:
    """Aynı derslikte aynı anda iki sınav olmaması kısıtı."""
    for exam in existing_exams:
        if exam.classroom_id != classroom_id or exam.date != exam_date:
            continue
        if not (exam.end_time <= start or exam.start_time >= end):
            return True
    return False


def generate_exam_schedule(
    courses: List[Course],
    classrooms: List[Classroom],
    days: int = 5,
    start_date: Optional[date] = None,
) -> ScheduleResult:
    """Temel greedy + sınırlı backtracking ile sınav programı üretir."""
    if start_date is None:
        start_date = date.today()

    # Sadece sınavı olan dersler
    target_courses = [c for c in courses if c.has_exam]
    if not target_courses:
        return ScheduleResult(success=False, message="Planlanacak ders bulunamadı.", exams=[])

    # Dersleri öğrenci sayısına göre azalan sırada sırala
    target_courses.sort(key=lambda c: c.student_count, reverse=True)

    # Derslikleri kapasiteye göre artan sırada tutmak, küçük sınıfları verimli kullanmaya yardım eder
    classrooms_sorted = sorted(classrooms, key=lambda cl: cl.capacity)

    course_lookup: Dict[int, Course] = {c.id: c for c in target_courses}
    assignments: List[ExamAssignment] = []

    time_slots = generate_time_slots()

    def backtrack(course_index: int) -> bool:
        if course_index >= len(target_courses):
            return True

        course = target_courses[course_index]
        duration_minutes = course.exam_duration
        duration_delta = timedelta(minutes=duration_minutes)

        for day_offset in range(days):
            exam_date = start_date + timedelta(days=day_offset)

            for start_slot in time_slots:
                start_dt = timedelta(hours=start_slot.hour, minutes=start_slot.minute)
                end_dt = start_dt + duration_delta
                end_slot = time(
                    hour=end_dt.seconds // 3600, minute=(end_dt.seconds % 3600) // 60
                )

                # Sınav süresi dışına çıkmıyoruz (örnek olarak 18:00'dan sonra bitmesin)
                if end_slot > time(hour=18, minute=0):
                    continue

                # Hoca müsait mi?
                if not is_instructor_available(course, exam_date, start_slot, end_slot):
                    continue

                # Öğrenci çakışma kontrolü için geçici atamalar listesi
                # Kapasite yetecek şekilde bir veya daha fazla derslik birleştirmemiz gerekiyor
                remaining_students = course.student_count
                combined_classrooms: List[Classroom] = []

                for classroom in classrooms_sorted:
                    # Bu zaman aralığında dersliğin uygunluğu
                    if classroom_has_conflict(
                        assignments, classroom.id, exam_date, start_slot, end_slot
                    ):
                        continue
                    if remaining_students <= 0:
                        break
                    # Her derslik için bir assignment düşüneceğiz,
                    # fakat öğrenci çakışması dersi/saat üzerinden kontrol edildiği için
                    # sınıf bazında ek bir çakışma yok.
                    combined_classrooms.append(classroom)
                    remaining_students -= classroom.capacity

                if remaining_students > 0:
                    # Kapasite yetmedi, bu slotu geç
                    continue

                # Bu slot için tüm derslik kombinasyonu hazır,
                # önce öğrenci çakışmasını tek bir "örnek" sınıf üstünden kontrol edelim.
                tentative_exam = ExamAssignment(
                    course_id=course.id,
                    classroom_id=combined_classrooms[0].id,
                    date=exam_date,
                    start_time=start_slot,
                    end_time=end_slot,
                )

                if has_student_conflict(assignments, tentative_exam, course_lookup):
                    continue

                # Uygun slot bulundu: tüm derslikleri için atama ekle
                added_indices: List[int] = []
                for cl in combined_classrooms:
                    assignment = ExamAssignment(
                        course_id=course.id,
                        classroom_id=cl.id,
                        date=exam_date,
                        start_time=start_slot,
                        end_time=end_slot,
                    )
                    assignments.append(assignment)
                    added_indices.append(len(assignments) - 1)

                # Sıradaki dersi yerleştirmeye çalış
                if backtrack(course_index + 1):
                    return True

                # Olmadıysa eklenen atamaları geri al (backtrack)
                for idx in reversed(added_indices):
                    assignments.pop(idx)

        # Bu ders için hiç uygun yer bulunamadıysa başarısız
        return False

    if not backtrack(0):
        return ScheduleResult(
            success=False,
            message="Tüm kısıtlar altında geçerli bir program üretilemedi.",
            exams=[],
        )

    return ScheduleResult(success=True, message="Başarılı", exams=assignments)


