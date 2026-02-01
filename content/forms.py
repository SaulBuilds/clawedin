from django import forms

from .models import Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ("title", "body")
        widgets = {
            "body": forms.Textarea(attrs={"rows": 8}),
        }
