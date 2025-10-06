from django.db import models
from django.conf import settings

class ChatSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    name = models.CharField(max_length=255, default='New Chat')
    created_at = models.DateTimeField(auto_now_add=True)

class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=20)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)


class TopicWeight(models.Model):
    """Un registro por cada mensaje relevante - peso = 1 por mensaje"""
    message = models.OneToOneField(ChatMessage, on_delete=models.CASCADE, related_name='topic_weight')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE)
    topic = models.ForeignKey('courses.CourseTopics', on_delete=models.CASCADE)
    date = models.DateField()
    
    class Meta:
        indexes = [
            models.Index(fields=['student', 'course', 'date']),
            models.Index(fields=['course', 'topic', 'date']),
            models.Index(fields=['course', 'date']),
        ]
        verbose_name = "Peso de Tema"
        verbose_name_plural = "Pesos de Temas"
    
    def __str__(self):
        return f"{self.student} - {self.topic.name} ({self.date})"
