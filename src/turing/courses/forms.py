from django import forms
from .models import Course

class CourseForm(forms.ModelForm):
    class Meta:
        model  = Course
        fields = ['name', 'description', 'level']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
