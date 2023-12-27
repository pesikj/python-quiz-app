from django import forms
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
