# courses/forms.py
from django import forms
from .models import Course

class CourseForm(forms.ModelForm):
    class Meta:
        model  = Course
        fields = ['name', 'description', 'level', 'schedule']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class JoinByCodeTeacherForm(forms.Form):
    code = forms.CharField(max_length=12)
