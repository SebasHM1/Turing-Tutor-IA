from django import forms
from .models import PromptConfig
from courses.models import Group, TutoringSlot

class PromptForm(forms.ModelForm):
    class Meta:
        model = PromptConfig
        fields = ["content"]
        labels = {"content": "Prompt del profesor"}
        widgets = {
            "content": forms.Textarea(attrs={
                "rows": 18,
                "style": "width:100%;font-family:monospace;font-size:14px;"
            })
        }

class TutoringSlotForm(forms.ModelForm):
    class Meta:
        model = TutoringSlot
        fields = ['day', 'start_time', 'end_time', 'location']
        widgets = {
            # Usamos widgets de HTML5 para una mejor experiencia de usuario
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }

class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name', 'schedule'] # El profesor y el curso se asignan en la vista
        # Puedes añadir widgets para que se vea mejor
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Ej: Grupo 1, Cálculo Avanzado (Tarde)'}),
            'schedule': forms.TextInput(attrs={'placeholder': 'Ej: Lunes y Miércoles 14:00 - 16:00'}),
        }
