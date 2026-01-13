"""
Gelişmiş Sınav Planlama Algoritması - Profesyonel Versiyon

Bu algoritma şu özellikleri destekler:
1) Öğrenci bazlı çakışma kontrolü (Excel verilerinden)
2) Yakınlık tabanlı derslik ataması
3) Hoca müsaitlik kontrolü
4) 4, 6, 8 saatlik özel sınav süreleri
5) Lab/Uygulama gibi özel mekan gereksinimleri
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time, timedelta
from typing import List, Dict, Tuple, Optional, Set
import uuid

from models import Course, Classroom, InstructorAvailability, StudentCourse, ClassroomProximity
from app import db


@dataclass
class ExamAssignment:
    course_id: int
    classroom_id: int
    date: date
    start_time: time
    end_time: time
    exam_group_id: str  # Aynı sınavın farklı dersliklerini gruplar


@dataclass
class ScheduleResult:
    success: bool
    message: str
    exams: List[ExamAssignment]
    statistics: Dict[str, any]


class AdvancedScheduler:
    def __init__(self):
        self.student_course_cache: Dict[int, Set[str]] = {}  # course_id -> student_no_set
        self.classroom_proximity_cache: Dict[int, List[Tuple[int, float]]] = {}  # classroom_id -> [(nearby_id, distance)]
        
    def _build_student_course_cache(self):
        """Öğrenci-ders ilişkilerini cache'e al (performans için)"""
        print("Öğrenci-ders cache'i oluşturuluyor...")
        
        student_courses = db.session.query(StudentCourse.course_id, StudentCourse.student_no).all()
        
        for course_id, student_no in student_courses:
            if course_id not in self.student_course_cache:
                self.student_course_cache[course_id] = set()
            self.student_course_cache[course_id].add(student_no)
        
        print(f"✓ {len(self.student_course_cache)} ders için öğrenci cache'i hazır")
    
    def _build_proximity_cache(self):
        """Derslik yakınlık verilerini cache'e al"""
        print("Derslik yakınlık cache'i oluşturuluyor...")
        
        proximities = db.session.query(
            ClassroomProximity.classroom1_id,
            ClassroomProximity.classroom2_id,
            ClassroomProximity.distance_score
        ).all()
        
        for classroom1_id, classroom2_id, distance in proximities:
            if classroom1_id not in self.classroom_proximity_cache:
                self.classroom_proximity_cache[classroom1_id] = []
            self.classroom_proximity_cache[classroom1_id].append((classroom2_id, distance))
        
        # Yakınlık skoruna göre sırala (en yakından en uzağa)
        for classroom_id in self.classroom_proximity_cache:
            self.classroom_proximity_cache[classroom_id].sort(key=lambda x: x[1])
        
        print(f"✓ {len(self.classroom_proximity_cache)} derslik için yakınlık cache'i hazır")
    
    def _has_student_conflict(self, existing_exams: List[ExamAssignment], new_exam: ExamAssignment) -> bool:
        """
        Öğrenci bazlı çakışma kontrolü
        Aynı öğrencinin aynı saatte iki farklı sınavı olamaz
        """
        new_course_students = self.student_course_cache.get(new_exam.course_id, set())
        if not new_course_students:
            return False
        
        for exam in existing_exams:
            if exam.date != new_exam.date:
                continue
                
            # Zaman çakışması var mı?
            if not (exam.end_time <= new_exam.start_time or exam.start_time >= new_exam.end_time):
                existing_course_students = self.student_course_cache.get(exam.course_id, set())
                
                # Ortak öğrenci var mı?
                common_students = new_course_students.intersection(existing_course_students)
                if common_students:
                    print(f"DEBUG: Öğrenci çakışması - {len(common_students)} ortak öğrenci")
                    return True
        
        return False
    
    def _is_instructor_available(self, course: Course, exam_date: date, start: time, end: time) -> bool:
        """Hoca müsaitlik kontrolü - %100 uyum"""
        availabilities = InstructorAvailability.query.filter_by(
            instructor_name=course.instructor, 
            date=exam_date,
            is_available=True
        ).all()
        
        if not availabilities:
            # Müsaitlik tanımı yoksa varsayılan olarak müsait kabul et
            return True
        
        for avail in availabilities:
            if avail.start_time <= start and avail.end_time >= end:
                return True
        
        return False
    
    def _classroom_has_conflict(self, existing_exams: List[ExamAssignment], classroom_id: int, 
                              exam_date: date, start: time, end: time) -> bool:
        """Derslik çakışma kontrolü"""
        for exam in existing_exams:
            if exam.classroom_id != classroom_id or exam.date != exam_date:
                continue
            if not (exam.end_time <= start or exam.start_time >= end):
                return True
        return False
    
    def _get_nearby_classrooms(self, main_classroom_id: int, required_capacity: int, 
                              available_classrooms: List[Classroom]) -> List[Classroom]:
        """
        Ana dersliğe yakın derslikleri kapasite sırasına göre döndür
        """
        nearby_classrooms = []
        
        # Yakınlık cache'inden yakın derslikleri al
        nearby_ids = self.classroom_proximity_cache.get(main_classroom_id, [])
        
        # Mevcut derslikler arasından yakın olanları filtrele
        available_dict = {cl.id: cl for cl in available_classrooms}
        
        for nearby_id, distance in nearby_ids:
            if nearby_id in available_dict:
                nearby_classrooms.append(available_dict[nearby_id])
        
        # Yakınlık cache'inde olmayan derslikleri de ekle (uzak kabul et)
        for classroom in available_classrooms:
            if classroom.id not in [cl.id for cl in nearby_classrooms]:
                nearby_classrooms.append(classroom)
        
        return nearby_classrooms
    
    def _find_optimal_classroom_combination(self, course: Course, available_classrooms: List[Classroom]) -> List[Classroom]:
        """
        Ders için EN OPTIMAL derslik kombinasyonunu bul
        VERİMLİLİK + YAKINLIK dengeli yaklaşım
        """
        required_capacity = course.student_count
        
        # Özel mekan gereksinimi kontrolü
        if course.requires_special_room:
            # Lab/Uygulama dersleri için özel derslikler
            special_classrooms = [cl for cl in available_classrooms 
                                if cl.room_type and 'lab' in cl.room_type.lower()]
            if special_classrooms:
                available_classrooms = special_classrooms
        
        # 1. Tek derslik yeterli mi?
        suitable_single = [cl for cl in available_classrooms if cl.capacity >= required_capacity]
        if suitable_single:
            # EN KÜÇÜK uygun dersliği seç (MINIMUM İSRAF)
            best_single = min(suitable_single, key=lambda cl: cl.capacity)
            waste = best_single.capacity - required_capacity
            print(f"DEBUG: {course.name} -> Tek derslik: {best_single.name} ({best_single.capacity}) - İsraf: {waste}")
            return [best_single]
        
        # 2. Birden fazla derslik gerekli - VERİMLİLİK + YAKINLIK
        print(f"DEBUG: {course.name} için çoklu derslik gerekli ({required_capacity} kişi)")
        
        best_combination = None
        best_score = float('inf')
        
        # Tüm olası 2'li kombinasyonları dene
        for i, classroom1 in enumerate(available_classrooms):
            for j, classroom2 in enumerate(available_classrooms[i+1:], i+1):
                total_capacity = classroom1.capacity + classroom2.capacity
                
                if total_capacity >= required_capacity:
                    waste = total_capacity - required_capacity
                    
                    # Yakınlık bonusu hesapla
                    proximity_bonus = 0
                    if classroom1.id in self.classroom_proximity_cache:
                        for nearby_id, distance in self.classroom_proximity_cache[classroom1.id]:
                            if nearby_id == classroom2.id:
                                # Yakın derslikler için bonus (0-20 puan arası)
                                proximity_bonus = (1.0 - distance) * 20
                                break
                    
                    # TOPLAM SKOR = İsraf - Yakınlık Bonusu (düşük skor daha iyi)
                    score = waste - proximity_bonus
                    
                    if score < best_score:
                        best_score = score
                        best_combination = [classroom1, classroom2]
                        print(f"DEBUG: Yeni en iyi: {classroom1.name}({classroom1.capacity}) + {classroom2.name}({classroom2.capacity}) = {total_capacity} (İsraf: {waste}, Yakınlık: {proximity_bonus:.1f}, Skor: {score:.1f})")
        
        if best_combination:
            classroom_info = ", ".join([f"{cl.name}({cl.capacity})" for cl in best_combination])
            total_capacity = sum(cl.capacity for cl in best_combination)
            waste = total_capacity - required_capacity
            print(f"DEBUG: {course.name} -> OPTIMAL kombinasyon: {classroom_info} (toplam: {total_capacity}, israf: {waste})")
            return best_combination
        
        # 3. 2'li kombinasyon bulunamazsa, 3'lü dene
        print(f"DEBUG: {course.name} için 3'lü kombinasyon deneniyor...")
        
        best_3_combination = None
        best_3_score = float('inf')
        
        # Tüm olası 3'lü kombinasyonları dene
        for i, cl1 in enumerate(available_classrooms):
            for j, cl2 in enumerate(available_classrooms[i+1:], i+1):
                for k, cl3 in enumerate(available_classrooms[j+1:], j+1):
                    total_capacity = cl1.capacity + cl2.capacity + cl3.capacity
                    
                    if total_capacity >= required_capacity:
                        waste = total_capacity - required_capacity
                        
                        # 3'lü için yakınlık bonusu (daha karmaşık)
                        proximity_bonus = 0
                        
                        # cl1-cl2 yakınlığı
                        if cl1.id in self.classroom_proximity_cache:
                            for nearby_id, distance in self.classroom_proximity_cache[cl1.id]:
                                if nearby_id == cl2.id:
                                    proximity_bonus += (1.0 - distance) * 10
                                    break
                        
                        # cl1-cl3 yakınlığı
                        if cl1.id in self.classroom_proximity_cache:
                            for nearby_id, distance in self.classroom_proximity_cache[cl1.id]:
                                if nearby_id == cl3.id:
                                    proximity_bonus += (1.0 - distance) * 10
                                    break
                        
                        # cl2-cl3 yakınlığı
                        if cl2.id in self.classroom_proximity_cache:
                            for nearby_id, distance in self.classroom_proximity_cache[cl2.id]:
                                if nearby_id == cl3.id:
                                    proximity_bonus += (1.0 - distance) * 10
                                    break
                        
                        score = waste - proximity_bonus
                        
                        if score < best_3_score:
                            best_3_score = score
                            best_3_combination = [cl1, cl2, cl3]
                            print(f"DEBUG: Yeni en iyi 3'lü: {cl1.name}({cl1.capacity}) + {cl2.name}({cl2.capacity}) + {cl3.name}({cl3.capacity}) = {total_capacity} (İsraf: {waste}, Yakınlık: {proximity_bonus:.1f}, Skor: {score:.1f})")
        
        if best_3_combination:
            classroom_info = ", ".join([f"{cl.name}({cl.capacity})" for cl in best_3_combination])
            total_capacity = sum(cl.capacity for cl in best_3_combination)
            waste = total_capacity - required_capacity
            print(f"DEBUG: {course.name} -> OPTIMAL 3'lü: {classroom_info} (toplam: {total_capacity}, israf: {waste})")
            return best_3_combination
        
        # 4. Son çare: 4'lü kombinasyon (yakınlık gözetmeden)
        print(f"DEBUG: {course.name} için 4'lü kombinasyon deneniyor...")
        
        # Kapasiteye göre sırala (büyükten küçüğe)
        sorted_classrooms = sorted(available_classrooms, key=lambda cl: cl.capacity, reverse=True)
        
        selected_classrooms = []
        remaining_capacity = required_capacity
        
        for classroom in sorted_classrooms:
            if remaining_capacity <= 0:
                break
            selected_classrooms.append(classroom)
            remaining_capacity -= classroom.capacity
        
        if remaining_capacity > 0:
            print(f"DEBUG: {course.name} için kapasite yetersiz: {remaining_capacity} kişi daha gerekli")
            return []
        
        classroom_info = ", ".join([f"{cl.name}({cl.capacity})" for cl in selected_classrooms])
        total_capacity = sum(cl.capacity for cl in selected_classrooms)
        waste = total_capacity - required_capacity
        print(f"DEBUG: {course.name} -> Çoklu derslik: {classroom_info} (toplam: {total_capacity}, israf: {waste})")
        
        return selected_classrooms
    
    def generate_time_slots(self, start_hour: int = 8, end_hour: int = 18, slot_minutes: int = 30) -> List[time]:
        """Zaman dilimlerini oluştur"""
        slots = []
        current_hour = start_hour
        current_minute = 0
        
        while current_hour < end_hour:
            slots.append(time(hour=current_hour, minute=current_minute))
            current_minute += slot_minutes
            if current_minute >= 60:
                current_hour += 1
                current_minute = 0
        
        return slots
    
    def generate_exam_schedule(self, courses: List[Course], classrooms: List[Classroom], 
                             days: int = 7, start_date: Optional[date] = None) -> ScheduleResult:
        """
        Gelişmiş sınav programı oluştur
        """
        if start_date is None:
            start_date = date.today()
        
        # Cache'leri oluştur
        self._build_student_course_cache()
        self._build_proximity_cache()
        
        # Sadece sınavı olan dersler
        target_courses = [c for c in courses if c.has_exam]
        if not target_courses:
            return ScheduleResult(
                success=False, 
                message="Planlanacak ders bulunamadı.", 
                exams=[], 
                statistics={}
            )
        
        # Dersleri öğrenci sayısına göre azalan sırada sırala (büyük dersler önce)
        target_courses.sort(key=lambda c: c.student_count, reverse=True)
        
        print(f"SCHEDULER: {len(target_courses)} ders planlanacak")
        print(f"SCHEDULER: {len(classrooms)} derslik mevcut")
        
        assignments: List[ExamAssignment] = []
        time_slots = self.generate_time_slots()
        
        statistics = {
            'total_courses': len(target_courses),
            'scheduled_courses': 0,
            'failed_courses': [],
            'total_classrooms_used': 0,
            'average_classroom_utilization': 0
        }
        
        def backtrack(course_index: int) -> bool:
            if course_index >= len(target_courses):
                return True
            
            course = target_courses[course_index]
            duration_minutes = course.exam_duration
            
            print(f"SCHEDULER: Planlama -> {course.name} ({course.student_count} öğrenci, {duration_minutes} dk)")
            
            for day_offset in range(days):
                exam_date = start_date + timedelta(days=day_offset)
                
                for start_slot in time_slots:
                    # Bitiş saatini hesapla
                    start_dt = timedelta(hours=start_slot.hour, minutes=start_slot.minute)
                    end_dt = start_dt + timedelta(minutes=duration_minutes)
                    
                    # Gün sınırını aşmasın
                    if end_dt.total_seconds() > timedelta(hours=18).total_seconds():
                        continue
                    
                    end_slot = time(
                        hour=int(end_dt.total_seconds() // 3600),
                        minute=int((end_dt.total_seconds() % 3600) // 60)
                    )
                    
                    # Hoca müsait mi?
                    if not self._is_instructor_available(course, exam_date, start_slot, end_slot):
                        continue
                    
                    # Mevcut derslikleri filtrele
                    available_classrooms = [
                        cl for cl in classrooms
                        if not self._classroom_has_conflict(assignments, cl.id, exam_date, start_slot, end_slot)
                    ]
                    
                    if not available_classrooms:
                        continue
                    
                    # Optimal derslik kombinasyonunu bul
                    selected_classrooms = self._find_optimal_classroom_combination(course, available_classrooms)
                    
                    if not selected_classrooms:
                        continue
                    
                    # Geçici atamalar oluştur
                    exam_group_id = str(uuid.uuid4())[:8]
                    temp_assignments = []
                    
                    for classroom in selected_classrooms:
                        temp_assignment = ExamAssignment(
                            course_id=course.id,
                            classroom_id=classroom.id,
                            date=exam_date,
                            start_time=start_slot,
                            end_time=end_slot,
                            exam_group_id=exam_group_id
                        )
                        temp_assignments.append(temp_assignment)
                    
                    # Öğrenci çakışması kontrolü (sadece bir kez, ilk derslik için)
                    if self._has_student_conflict(assignments, temp_assignments[0]):
                        continue
                    
                    # Uygun slot bulundu - atamaları ekle
                    assignments.extend(temp_assignments)
                    
                    # Sıradaki dersi dene
                    if backtrack(course_index + 1):
                        statistics['scheduled_courses'] += 1
                        return True
                    
                    # Geri al (backtrack)
                    for _ in temp_assignments:
                        assignments.pop()
            
            # Bu ders için uygun slot bulunamadı
            statistics['failed_courses'].append(course.name)
            print(f"SCHEDULER: BAŞARISIZ -> {course.name}")
            return False
        
        # Planlama başlat
        success = backtrack(0)
        
        # İstatistikleri tamamla
        used_classrooms = set(exam.classroom_id for exam in assignments)
        statistics['total_classrooms_used'] = len(used_classrooms)
        
        if success:
            message = f"Tüm dersler başarıyla planlandı! {len(assignments)} sınav ataması yapıldı."
        else:
            scheduled_count = statistics['scheduled_courses']
            failed_count = len(statistics['failed_courses'])
            message = f"Kısmi başarı: {scheduled_count}/{len(target_courses)} ders planlandı. {failed_count} ders planlanamadı."
        
        return ScheduleResult(
            success=success,
            message=message,
            exams=assignments,
            statistics=statistics
        )


# Eski fonksiyon ile uyumluluk için wrapper
def generate_exam_schedule(courses: List[Course], classrooms: List[Classroom], 
                         days: int = 7, start_date: Optional[date] = None) -> ScheduleResult:
    """Eski API ile uyumluluk için wrapper fonksiyon"""
    scheduler = AdvancedScheduler()
    return scheduler.generate_exam_schedule(courses, classrooms, days, start_date)