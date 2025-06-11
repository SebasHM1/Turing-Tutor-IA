from django.db import models
from django.contrib.auth.models import User
from django.conf import settings

class ChatSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=20)  # 'user' o 'bot'
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)