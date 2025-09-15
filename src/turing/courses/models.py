# courses/models.py
from django.db import models
from django.conf import settings
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
        upload_to='tutoring_schedules/',
        verbose_name="Archivo de Monitorías (PDF)"
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

    def __str__(self):
        return f"Horario de monitorías para {self.course.name}"

    class Meta:
        verbose_name = "Horario de Monitoría"
        verbose_name_plural = "Horarios de Monitorías"