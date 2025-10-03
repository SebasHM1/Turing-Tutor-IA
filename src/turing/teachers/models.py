from django.db import models
from django.conf import settings


class PromptConfig(models.Model):
    key = models.CharField(max_length=50, unique=True, default="global")
    content = models.TextField("Prompt del profesor", default="", blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="updated_prompts"
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración de Prompt"
        verbose_name_plural = "Configuraciones de Prompt"

    def __str__(self):
        return f"{self.key} (actualizado {self.updated_at:%Y-%m-%d %H:%M})"