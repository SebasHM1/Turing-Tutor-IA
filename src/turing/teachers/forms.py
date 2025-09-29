from django import forms
from .models import PromptConfig
from courses.models import TeacherCourse, TutoringSlot

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
