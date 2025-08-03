from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class Materia(models.Model):
    nombre        = models.CharField(max_length=120)
    descripcion   = models.TextField(blank=True)
    nivel         = models.CharField(max_length=20) 
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    responsable   = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='materias_creadas',
        limit_choices_to={'role': 'Teacher'} 
    )

    def __str__(self):
        return self.nombre


class ProfesorMateria(models.Model):
    """Tabla intermedia para soportar muchos-a-muchos profesor ↔ materia."""
    profesor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='materias'
    )
    materia  = models.ForeignKey(
        Materia,
        on_delete=models.CASCADE,
        related_name='profesores'
    )
    fecha_union = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('profesor', 'materia') 

    def __str__(self):
        return f'{self.profesor.email} ↔ {self.materia.nombre}'
