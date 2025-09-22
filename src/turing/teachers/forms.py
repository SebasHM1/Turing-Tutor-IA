from django import forms
from .models import PromptConfig

class PromptForm(forms.ModelForm):
    class Meta:
        model = PromptConfig
        fields = ['content']
        labels = {'content': 'System Prompt (compartido)'}
        widgets = {'content': forms.Textarea(attrs={'rows': 12, 'placeholder': 'Instrucciones del profe...'})}
