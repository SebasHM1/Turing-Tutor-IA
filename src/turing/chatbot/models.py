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
    """Un registro por cada palabra clave detectada en un mensaje"""
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='topic_weights')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.ForeignKey('courses.Course', on_delete=models.CASCADE)
    topic = models.ForeignKey('courses.CourseTopics', on_delete=models.CASCADE)
    keyword = models.ForeignKey('courses.TopicKeyword', on_delete=models.CASCADE, related_name='weights')
    date = models.DateField()
    
    class Meta:
        # Un mensaje puede tener múltiples keywords del mismo o diferentes topics
        unique_together = ['message', 'keyword']
        indexes = [
            models.Index(fields=['student', 'course', 'date']),
            models.Index(fields=['course', 'topic', 'date']),
            models.Index(fields=['course', 'date']),
            models.Index(fields=['keyword', 'date']),
        ]
        verbose_name = "Peso de Tema"
        verbose_name_plural = "Pesos de Temas"
    
    def __str__(self):
        return f"{self.student} - {self.keyword.keyword} ({self.topic.name}) - {self.date}"
