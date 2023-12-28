from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django_recaptcha.fields import ReCaptchaField

from .models import Course, Quiz, Question


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["title", "description", "ai_prompt_format", "ai_api_key", "ai_model", "attachment"]


class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ['title', 'deadline', "course", "ai_prompt_quiz_text", "attachment"]


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ["text", "type", "example_answer", "ai_feedback_enabled", "attachment_1", "attachment_2",
                  "attachment_3"]


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]


class CustomUserCreationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super(CustomUserCreationForm, self).__init__(*args, **kwargs)
        if hasattr(settings, "RECAPTCHA_PRIVATE_KEY") and settings.RECAPTCHA_PRIVATE_KEY:
            self.fields["captcha"] = ReCaptchaField()
