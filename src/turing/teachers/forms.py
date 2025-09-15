from django import forms
from .models import PromptConfig
from courses.models import TutoringSchedule

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
