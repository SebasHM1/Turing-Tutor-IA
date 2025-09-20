from django import forms
from .models import PromptConfig
from courses.models import TeacherCourse

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

class TutoringDetailsForm(forms.ModelForm):
    class Meta:
        model = TeacherCourse
        fields = ['tutoring_details']
        widgets = {
            'tutoring_details': forms.Textarea(attrs={
                'rows': 5, 
                'placeholder': 'Ej: Lunes y Miércoles de 10am a 12pm.\nOficina: 301\nEnlace Zoom: https://...'
            }),
        }
