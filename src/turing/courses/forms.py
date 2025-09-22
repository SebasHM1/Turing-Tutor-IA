# courses/forms.py
from django import forms
from .models import Course, TutoringSchedule

class CourseForm(forms.ModelForm):
    class Meta:
        model  = Course
        fields = ['name', 'description', 'level', 'schedule']
        labels = {'level': 'Semestre'}
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}


class JoinByCodeTeacherForm(forms.Form):
    code = forms.CharField(max_length=12)

class TutoringScheduleForm(forms.ModelForm):
    class Meta:
        model = TutoringSchedule
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={'accept': '.pdf'}),
        }
