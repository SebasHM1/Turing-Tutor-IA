from django import forms
from .models import Materia

class MateriaForm(forms.ModelForm):
    class Meta:
        model  = Materia
        fields = ['nombre', 'descripcion', 'nivel']
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
        }
