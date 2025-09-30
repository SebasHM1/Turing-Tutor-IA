# courses/models.py
import os
import uuid
from unidecode import unidecode
from django.utils.text import slugify
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator
import secrets
import string

User = settings.AUTH_USER_MODEL

def _gen_course_code(n=6):
    alnum = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alnum) for _ in range(n))

class Course(models.Model):
    name        = models.CharField(max_length=120, db_column='nombre')
    description = models.TextField(blank=True, db_column='descripcion')
    level       = models.CharField(max_length=20, db_column='nivel')
    created_at  = models.DateTimeField(auto_now_add=True, db_column='fecha_creacion')
    owner       = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_courses',
        limit_choices_to={'role': 'Teacher'},
        db_column='responsable'
    )
    code     = models.CharField(max_length=12, unique=True, db_index=True, db_column='codigo', blank=True)
    schedule = models.CharField(max_length=60, db_column='horario', blank=True)

    def save(self, *args, **kwargs):
        # genera un código si viene vacío
        if not self.code:
            new_code = _gen_course_code()
            while Course.objects.filter(code=new_code).exists():
                new_code = _gen_course_code()
            self.code = new_code
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class TeacherCourse(models.Model):
    """Relación muchos-a-muchos profesor ↔ course."""
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='courses',
        db_column='profesor'
    )
    course  = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='teachers',
        db_column='materia'
    )

    joined_at = models.DateTimeField(auto_now_add=True, db_column='fecha_union')

    class Meta:
        unique_together = ('teacher', 'course')
        db_table = 'courses_profesor_materia'

    def __str__(self):
        return f'{self.teacher.email} ↔ {self.course.name}'

class TutoringSlot(models.Model):
    """Representa una única franja horaria de monitoría."""
    
    class DaysOfWeek(models.TextChoices):
        MONDAY = 'MON', _('Lunes')
        TUESDAY = 'TUE', _('Martes')
        WEDNESDAY = 'WED', _('Miércoles')
        THURSDAY = 'THU', _('Jueves')
        FRIDAY = 'FRI', _('Viernes')
        SATURDAY = 'SAT', _('Sábado')
        SUNDAY = 'SUN', _('Domingo')

    teacher_course = models.ForeignKey(
        TeacherCourse, 
        on_delete=models.CASCADE, 
        related_name='tutoring_slots'
    )
    day = models.CharField(
        max_length=3,
        choices=DaysOfWeek.choices,
        verbose_name="Día de la semana"
    )
    start_time = models.TimeField(verbose_name="Hora de inicio")
    end_time = models.TimeField(verbose_name="Hora de finalización")
    location = models.CharField(
        max_length=255, 
        verbose_name="Ubicación o Enlace",
        help_text="Ej: Oficina 301, Laboratorio B, o enlace de Zoom/Meet"
    )

    class Meta:
        # Asegura que no haya dos horarios idénticos para el mismo profesor/curso
        unique_together = ('teacher_course', 'day', 'start_time')
        ordering = ['day', 'start_time']

    def __str__(self):
        return f"{self.get_day_display()}: {self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')}"

class Enrollment(models.Model):
    """Relación estudiante ↔ course."""
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='enrollments',
        limit_choices_to={'role': 'Student'},
        db_column='estudiante'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='enrollments',
        db_column='materia'
    )
    joined_at = models.DateTimeField(auto_now_add=True, db_column='fecha_union')

    class Meta:
        unique_together = ('student', 'course')
        db_table = 'courses_inscripcion'

    def __str__(self):
        return f'{self.student.email} ↔ {self.course.name}'

class CoursePrompt(models.Model):
    course = models.OneToOneField(Course, on_delete=models.CASCADE, related_name='prompt')
    content = models.TextField("Prompt del profesor", default="", blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="updated_course_prompts"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Prompt de Curso"
        verbose_name_plural = "Prompts de Curso"

    def __str__(self):
        return f"Prompt de {self.course.name} (actualizado {self.updated_at:%Y-%m-%d %H:%M})"
    

class KnowledgeBaseFile(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='knowledge_files')
    file = models.FileField(upload_to='knowledge_base/', max_length=500)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=255, blank=True)
    extracted_text = models.TextField(blank=True, help_text="Text extracted from PDF")
    text_chunks = models.JSONField(default=list, blank=True, help_text="Text chunks for RAG")
    embeddings = models.JSONField(default=list, blank=True, help_text="Vector embeddings for chunks")
    processed = models.BooleanField(default=False, help_text="Whether the file has been processed for RAG")
    processing_error = models.TextField(blank=True, help_text="Error message if processing failed")

    def __str__(self):
        return self.name or self.file.name
    

def sanitized_upload_to(instance, filename):
    """
    Renombra el archivo subido a un formato seguro y único.
    Ej: 'Monitorías del 20%.pdf' -> 'monitorias-del-20-a1b2c3d4.pdf'
    """
    path, extension = os.path.splitext(filename)
    
    ascii_name = unidecode(path)
    
    slug_name = slugify(ascii_name)
    
    unique_id = uuid.uuid4().hex[:8]
    
    safe_filename = f"{slug_name}-{unique_id}{extension}"
    
    return os.path.join('tutoring_schedules', safe_filename)

class TutoringSchedule(models.Model):
    """
    Almacena el archivo PDF con el horario de monitorías para un curso.
    """
    course = models.OneToOneField(
        Course,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='tutoring_schedule'
    )
    file = models.FileField(
        upload_to=sanitized_upload_to,
        verbose_name="Archivo de Monitorías (PDF)",
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])]
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de subida"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Última actualización"
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+'
    )

    def save(self, *args, **kwargs):
        # Primero, verifica si este objeto ya existe en la base de datos.
        if self.pk:
            try:
                # Obtiene la instancia antigua de la base de datos.
                old_instance = TutoringSchedule.objects.get(pk=self.pk)
                # Si el archivo ha cambiado, elimina el antiguo.
                if old_instance.file and old_instance.file != self.file:
                    old_instance.file.delete(save=False)
            except TutoringSchedule.DoesNotExist:
                # Esto no debería ocurrir si self.pk está definido, pero es bueno manejarlo.
                pass
        
        # Llama al método save original para guardar la nueva instancia (y el nuevo archivo).
        super().save(*args, **kwargs)


    def __str__(self):
        return f"Horario de monitorías para {self.course.name}"

    class Meta:
        verbose_name = "Horario de Monitoría"
        verbose_name_plural = "Horarios de Monitorías"
