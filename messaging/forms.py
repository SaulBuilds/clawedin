from django import forms
from django.contrib.auth import get_user_model

from .models import DirectMessage, GroupMessage, GroupThread, InMail


class DirectMessageForm(forms.ModelForm):
    class Meta:
        model = DirectMessage
        fields = ("recipient", "subject", "body")
        widgets = {
            "body": forms.Textarea(attrs={"rows": 6}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["recipient"].queryset = get_user_model().objects.exclude(
                id=user.id
            )


class InMailForm(forms.ModelForm):
    class Meta:
        model = InMail
        fields = ("recipient", "subject", "body")
        widgets = {
            "body": forms.Textarea(attrs={"rows": 6}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["recipient"].queryset = get_user_model().objects.exclude(
                id=user.id
            )


class GroupThreadForm(forms.ModelForm):
    members = forms.ModelMultipleChoiceField(
        queryset=get_user_model().objects.none(),
        widget=forms.SelectMultiple,
        help_text="Choose the members to add to the group.",
    )

    class Meta:
        model = GroupThread
        fields = ("name", "members")

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = get_user_model().objects.all()
        if user is not None:
            queryset = queryset.exclude(id=user.id)
        self.fields["members"].queryset = queryset


class GroupMessageForm(forms.ModelForm):
    class Meta:
        model = GroupMessage
        fields = ("body",)
        widgets = {
            "body": forms.Textarea(attrs={"rows": 4, "placeholder": "Write a message..."}),
        }
