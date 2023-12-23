from django.contrib.auth.models import User
from django.db import models
from django.db.models import QuerySet, Q


class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()

    def get_quiz_question_counts(self, user: User) -> dict:
        quiz_questions_counts = {}
        for quiz in self.quiz_set.all():
            answered_questions = (UserAnswer.objects.filter(question__quiz=quiz).filter(user=user)
                                  .filter(question__quiz__course=self)
                                  .values_list("question__id", flat=True))
            answered_questions = list(set(answered_questions))
            if len(answered_questions) == 0:
                quiz_questions_counts[quiz.id] = quiz.question_set.order_by("order").first().pk
                continue
            current_question_query = quiz.question_set.filter(~Q(pk__in=answered_questions))
            if not current_question_query.exists():
                quiz_questions_counts[quiz.id] = None
            else:
                quiz_questions_counts[quiz.id] = current_question_query.order_by("order").first().pk
        return quiz_questions_counts

    def quiz_completion_info(self, user: User) -> dict:
        quiz_completion_info = {}
        for quiz in self.quiz_set.all():
            quiz_completion_info[quiz.id] = quiz.quiz_completed(user)
        return quiz_completion_info

    def __str__(self):
        return self.title


class Quiz(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    deadline = models.DateTimeField(null=True, blank=True)

    def quiz_completed(self, user):
        questions_ids = set(self.question_set.values_list("id", flat=True))
        user_answers_questions_id = (
            set(UserAnswer.objects.filter(question__quiz=self, user=user).values_list("question_id", flat=True)))
        return questions_ids == user_answers_questions_id and len(questions_ids) > 0

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

    @property
    def last_question(self):
        return self.quiz.question_set.filter(order__gt=self.order).order_by("order").count() == 0

    @property
    def next_question(self):
        return self.quiz.question_set.filter(order__gt=self.order).order_by("order").first()

    def __str__(self):
        return self.text


class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    text = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)
    feedback = models.TextField(null=True, blank=True)

    @property
    def calculated_feedback(self):
        if self.feedback:
            return self.feedback
        if self.is_correct:
            return "Správná odpověď"
        else:
            return "Nesprávná odpověď"

    def __str__(self):
        return self.text


class UserAnswer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_options = models.ManyToManyField(Option)
    answered_on = models.DateTimeField(auto_now_add=True)
    answer_text = models.TextField(null=True, blank=True)
    admin_feedback = models.TextField(null=True, blank=True)
    ai_feedback = models.TextField(null=True, blank=True)
    points = models.IntegerField(null=True, blank=True)

    @property
    def user_answer(self):
        if self.question.type in (Question.SHORT_TEXT, Question.LONG_TEXT):
            return self.answer_text
        if self.question.type == Question.MULTIPLE_CHOICE_SINGLE_ANSWER:
            selected_option: Option = self.selected_options.first()
            return selected_option.text
        if self.question.type == Question.MULTIPLE_CHOICE_MULTIPLE_ANSWER:
            selected_options: QuerySet = self.selected_options.all()
            return "\n".join([x.text for x in selected_options])

    @property
    def answer_feedback(self):
        if self.question.type in (Question.SHORT_TEXT, Question.LONG_TEXT):
            if self.admin_feedback:
                return self.admin_feedback
            if self.ai_feedback:
                return self.ai_feedback
        if self.question.type == Question.MULTIPLE_CHOICE_SINGLE_ANSWER:
            selected_option: Option = self.selected_options.first()
            return selected_option.calculated_feedback
        if self.question.type == Question.MULTIPLE_CHOICE_MULTIPLE_ANSWER:
            selected_options: QuerySet = self.selected_options.all()
            return "\n".join([x.calculated_feedback for x in selected_options])

    def __str__(self):
        return f"{self.user.username}'s answer to {self.question.text}"

