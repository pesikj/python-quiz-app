from django.contrib.auth.models import User
from django.db import models


class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()

    def __str__(self):
        return self.title


class Quiz(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    deadline = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title


class Question(models.Model):
    SHORT_TEXT = 'ST'
    LONG_TEXT = 'LT'
    MULTIPLE_CHOICE_SINGLE_ANSWER = 'MC'
    MULTIPLE_CHOICE_MULTIPLE_ANSWER = 'MM'

    QUESTION_TYPES = [
        (SHORT_TEXT, 'Short Text'),
        (LONG_TEXT, 'Long Text'),
        (MULTIPLE_CHOICE_SINGLE_ANSWER, 'Multiple Choice - Single Answer'),
        (MULTIPLE_CHOICE_MULTIPLE_ANSWER, 'Multiple Choice - Multiple Answers'),
    ]

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, blank=True)
    text = models.TextField()
    type = models.CharField(max_length=2, choices=QUESTION_TYPES, default=SHORT_TEXT)
    order = models.IntegerField(default=0)

    def __str__(self):
        return self.text


class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    text = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)
    feedback = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.text


class UserAnswer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_options = models.ManyToManyField(Option)
    answered_on = models.DateTimeField(auto_now_add=True)
    answer_text = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s answer to {self.question.text}"

