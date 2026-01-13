"""
Excel dosyalarından veri import etme modülü
- Öğrenci listeleri (SınıfListesi[DERS_KODU].xls)
- Derslik kapasiteleri (kostu_sinav_kapasiteleri.xlsx)
- Derslik yakınlığı (Derslik Yakınlık.xlsx)
"""

import os
import pandas as pd
from typing import List, Dict, Tuple, Optional
from app import db
from models import Course, Student, StudentCourse, Classroom, ClassroomProximity
import re


class ExcelImporter:
    def __init__(self, data_folder: str = "data"):
        self.data_folder = data_folder
        
    def import_student_lists(self) -> Dict[str, int]:
        """
        SınıfListesi[DERS_KODU].xls formatındaki dosyaları okur
        Returns: {course_code: student_count} dictionary
        """
        results = {}
        
        print(f"📁 Data klasörü kontrol ediliyor: {self.data_folder}")
        
        if not os.path.exists(self.data_folder):
            print(f"❌ Veri klasörü bulunamadı: {self.data_folder}")
            return results
        
        print(f"✓ Data klasörü mevcut: {os.path.abspath(self.data_folder)}")
        
        # Klasördeki tüm dosyaları listele
        all_files = os.listdir(self.data_folder)
        print(f"📂 Klasördeki dosyalar ({len(all_files)}):")
        for f in all_files:
            print(f"  - {f}")
            
        # SınıfListesi ile başlayan dosyaları bul
        sinif_listesi_files = [f for f in all_files if f.startswith("SınıfListesi")]
        print(f"\n📋 SınıfListesi dosyaları ({len(sinif_listesi_files)}):")
        for f in sinif_listesi_files:
            print(f"  - {f}")
        
        for filename in all_files:
            if filename.startswith("SınıfListesi") and filename.endswith((".xls", ".xlsx")):
                # Ders kodunu dosya adından çıkar: SınıfListesi[YZM332].xls -> YZM332
                # Farklı formatları destekle: [YZM332], [MAT110] (3), vb.
                match = re.search(r'\[([A-Z]{3}\d{3})\]', filename)
                if not match:
                    print(f"Ders kodu bulunamadı: {filename}")
                    continue
                    
                course_code = match.group(1)
                filepath = os.path.join(self.data_folder, filename)
                
                print(f"İşleniyor: {filename} -> {course_code}")
                
                try:
                    # Excel dosyasını oku
                    df = pd.read_excel(filepath)
                    
                    # Öğrenci No sütununu bul (farklı isimler olabilir)
                    student_no_col = None
                    for col in df.columns:
                        if any(keyword in col.lower() for keyword in ['öğrenci', 'ogrenci', 'no', 'numara']):
                            student_no_col = col
                            break
                    
                    if student_no_col is None:
                        print(f"Öğrenci No sütunu bulunamadı: {filename}")
                        continue
                    
                    # Boş olmayan öğrenci numaralarını al
                    student_numbers = df[student_no_col].dropna().astype(str).tolist()
                    
                    # Veritabanına kaydet
                    course = Course.query.filter_by(code=course_code).first()
                    if not course:
                        print(f"Ders bulunamadı: {course_code}")
                        continue
                    
                    # Mevcut kayıtları temizle
                    StudentCourse.query.filter_by(course_id=course.id).delete()
                    
                    # Yeni kayıtları ekle
                    for student_no in student_numbers:
                        student_no = student_no.strip()
                        if not student_no:
                            continue
                            
                        # Öğrenci kaydını bul veya oluştur
                        student = Student.query.filter_by(student_no=student_no).first()
                        if not student:
                            student = Student(student_no=student_no)
                            db.session.add(student)
                            db.session.flush()  # ID'yi al
                        
                        # Öğrenci-Ders ilişkisini oluştur
                        student_course = StudentCourse(
                            student_id=student.id,
                            course_id=course.id,
                            student_no=student_no,
                            course_code=course_code
                        )
                        db.session.add(student_course)
                    
                    db.session.commit()
                    results[course_code] = len(student_numbers)
                    print(f"✓ {course_code}: {len(student_numbers)} öğrenci")
                    
                except Exception as e:
                    print(f"Hata - {filename}: {str(e)}")
                    db.session.rollback()
                    
        return results
    
    def import_classroom_capacities(self, filename: str = "kostu_sinav_kapasiteleri.xlsx") -> int:
        """
        Derslik kapasite dosyasını okur
        Format: Sınıf | Kontenjan
        Returns: İmport edilen derslik sayısı
        """
        filepath = os.path.join(self.data_folder, filename)
        
        print(f"📊 Derslik kapasiteleri import ediliyor: {filename}")
        print(f"📁 Dosya yolu: {os.path.abspath(filepath)}")
        
        if not os.path.exists(filepath):
            print(f"❌ Dosya bulunamadı: {filepath}")
            return 0
        
        print(f"✓ Dosya mevcut, okunuyor...")
            
        try:
            df = pd.read_excel(filepath)
            
            print(f"📊 {len(df)} satır veri bulundu")
            print(f"📋 Sütunlar: {list(df.columns)}")
            
            # Sütun isimlerini kontrol et
            classroom_col = 'Sınıf'
            capacity_col = 'Kontenjan'
            
            if classroom_col not in df.columns or capacity_col not in df.columns:
                print(f"❌ Gerekli sütunlar bulunamadı. Mevcut sütunlar: {list(df.columns)}")
                return 0
            
            print(f"✓ Derslik sütunu: {classroom_col}")
            print(f"✓ Kapasite sütunu: {capacity_col}")
            
            count = 0
            updated_count = 0
            missing_classrooms = []
            
            for _, row in df.iterrows():
                classroom_name = str(row[classroom_col]).strip()
                capacity = row[capacity_col]
                
                if pd.isna(capacity) or classroom_name == 'nan':
                    continue
                    
                try:
                    capacity = int(float(capacity))
                except:
                    print(f"⚠️ Geçersiz kapasite değeri: {capacity} ({classroom_name})")
                    continue
                
                # Derslik kaydını bul
                classroom = Classroom.query.filter_by(name=classroom_name).first()
                if not classroom:
                    missing_classrooms.append(classroom_name)
                    continue
                
                # Kapasiteyi güncelle
                old_capacity = classroom.capacity
                classroom.capacity = capacity
                
                if old_capacity != capacity:
                    updated_count += 1
                    print(f"✓ {classroom_name}: {old_capacity} -> {capacity}")
                
                count += 1
            
            db.session.commit()
            
            print(f"✅ {count} derslik kapasitesi kontrol edildi")
            print(f"🔄 {updated_count} derslik kapasitesi güncellendi")
            
            if missing_classrooms:
                print(f"⚠️ Bulunamayan derslikler ({len(missing_classrooms)}):")
                for name in missing_classrooms:
                    print(f"  - {name}")
                print("💡 Bu derslikleri önce Classroom tablosuna ekleyin")
            
            return count
            
        except Exception as e:
            print(f"❌ Hata - {filename}: {str(e)}")
            db.session.rollback()
            return 0
    
    def import_classroom_proximity(self, filename: str = "Derslik Yakınlık.xlsx") -> int:
        """
        Derslik yakınlık matrisini okur
        Format: DERSLİK | YAKIN DERSLİK (virgülle ayrılmış liste)
        Returns: İmport edilen yakınlık ilişkisi sayısı
        """
        filepath = os.path.join(self.data_folder, filename)
        
        print(f"🏢 Derslik yakınlık matrisi import ediliyor: {filename}")
        print(f"📁 Dosya yolu: {os.path.abspath(filepath)}")
        
        if not os.path.exists(filepath):
            print(f"❌ Dosya bulunamadı: {filepath}")
            return 0
        
        print(f"✓ Dosya mevcut, okunuyor...")
            
        try:
            # Excel dosyasını oku
            df = pd.read_excel(filepath)
            
            print(f"📊 {len(df)} satır veri bulundu")
            
            # Sütun isimlerini bul
            classroom_col = 'DERSLİK'
            nearby_col = 'YAKIN DERSLİK'
            
            if classroom_col not in df.columns or nearby_col not in df.columns:
                print(f"❌ Gerekli sütunlar bulunamadı. Mevcut sütunlar: {list(df.columns)}")
                return 0
            
            print(f"✓ Ana derslik sütunu: {classroom_col}")
            print(f"✓ Yakın derslik sütunu: {nearby_col}")
            
            # Mevcut yakınlık verilerini temizle
            ClassroomProximity.query.delete()
            
            # Mevcut derslikleri al
            existing_classrooms = {cl.name: cl for cl in Classroom.query.all()}
            print(f"📊 Veritabanında {len(existing_classrooms)} derslik mevcut")
            
            count = 0
            missing_classrooms = set()
            
            for _, row in df.iterrows():
                main_classroom_name = str(row[classroom_col]).strip()
                nearby_classrooms_str = str(row[nearby_col]).strip()
                
                if pd.isna(row[classroom_col]) or pd.isna(row[nearby_col]):
                    continue
                
                # Ana dersliği bul
                if main_classroom_name not in existing_classrooms:
                    missing_classrooms.add(main_classroom_name)
                    continue
                
                main_classroom = existing_classrooms[main_classroom_name]
                
                # Yakın derslikleri parse et (virgülle ayrılmış)
                nearby_names = [name.strip() for name in nearby_classrooms_str.split(',')]
                
                for nearby_name in nearby_names:
                    if not nearby_name:
                        continue
                        
                    if nearby_name not in existing_classrooms:
                        missing_classrooms.add(nearby_name)
                        continue
                    
                    nearby_classroom = existing_classrooms[nearby_name]
                    
                    # Aynı derslik kendisi ile yakınlık kurmasın
                    if main_classroom.id == nearby_classroom.id:
                        continue
                    
                    # Yakınlık kaydı oluştur
                    # Excel'de sıralama yakınlık derecesini gösteriyor (ilk = en yakın)
                    distance_score = (nearby_names.index(nearby_name) + 1) * 0.1  # 0.1, 0.2, 0.3, ...
                    
                    proximity = ClassroomProximity(
                        classroom1_id=main_classroom.id,
                        classroom2_id=nearby_classroom.id,
                        distance_score=min(distance_score, 0.9),  # Max 0.9
                        is_adjacent=(distance_score <= 0.1)  # İlk sıradakiler bitişik
                    )
                    db.session.add(proximity)
                    count += 1
            
            db.session.commit()
            
            print(f"✓ {count} yakınlık ilişkisi eklendi")
            
            if missing_classrooms:
                print(f"⚠️ Bulunamayan derslikler ({len(missing_classrooms)}):")
                for name in sorted(missing_classrooms):
                    print(f"  - {name}")
                print("💡 Bu derslikleri önce Classroom tablosuna ekleyin")
            
            return count
            
        except Exception as e:
            print(f"Hata - {filename}: {str(e)}")
            db.session.rollback()
            return 0
    
    def import_all(self) -> Dict[str, any]:
        """Tüm Excel dosyalarını import et"""
        print("Excel veri import işlemi başlıyor...")
        
        results = {
            'student_lists': self.import_student_lists(),
            'classroom_capacities': self.import_classroom_capacities(),
            'classroom_proximity': self.import_classroom_proximity()
        }
        
        print("Import işlemi tamamlandı!")
        return results


def create_sample_data():
    """Test için örnek Excel dosyaları oluştur"""
    os.makedirs("data", exist_ok=True)
    
    # Örnek öğrenci listesi
    sample_students = pd.DataFrame({
        'Öğrenci No': ['2021001', '2021002', '2021003', '2021004', '2021005'],
        'Ad Soyad': ['Ahmet Yılmaz', 'Ayşe Kaya', 'Mehmet Demir', 'Fatma Şahin', 'Ali Özkan']
    })
    sample_students.to_excel("data/SınıfListesi[YZM332].xlsx", index=False)
    
    # Örnek derslik kapasiteleri
    sample_classrooms = pd.DataFrame({
        'Derslik Adı': ['A101', 'A102', 'B201', 'C301', 'Amfi-1'],
        'Kapasite': [30, 40, 50, 60, 200],
        'Bina': ['A Blok', 'A Blok', 'B Blok', 'C Blok', 'Ana Bina'],
        'Kat': ['1', '1', '2', '3', 'Zemin']
    })
    sample_classrooms.to_excel("data/kostu_sinav_kapasiteleri.xlsx", index=False)
    
    print("Örnek veri dosyaları oluşturuldu!")


if __name__ == "__main__":
    # Test için
    create_sample_data()
    importer = ExcelImporter()
    importer.import_all()