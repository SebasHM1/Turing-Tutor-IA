# courses/models.py
from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

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
