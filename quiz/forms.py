from django import forms
from .models import Course, Quiz, Question


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description']


class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ['title', 'deadline', "course"]


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ["text", "type"]
