# courses/forms.py
from django import forms
from .models import Course, CoursePrompt, KnowledgeBaseFile

class CourseForm(forms.ModelForm):
    class Meta:
        model  = Course
        fields = ['name', 'description', 'level', 'schedule']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class JoinByCodeTeacherForm(forms.Form):
    code = forms.CharField(max_length=12)


class CoursePromptForm(forms.ModelForm):
    class Meta:
        model = CoursePrompt
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 6, 'placeholder': 'Escribe el prompt para este curso...'}),
        }


class KnowledgeBaseFileForm(forms.ModelForm):
    class Meta:
        model = KnowledgeBaseFile
        fields = ['file', 'name']