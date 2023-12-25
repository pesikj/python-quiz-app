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
            if quiz.question_set.count() == 0:
                quiz_questions_counts[quiz.id] = None
            elif len(answered_questions) == 0:
                quiz_questions_counts[quiz.id] = quiz.question_set.order_by("order").first().pk
            else:
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

    def last_question(self, user):
        return self.next_question(user) is None

    def next_question(self, user):
        user_answers = UserAnswer.objects.filter(question__quiz=self.quiz).values_list("question_id", flat=True)
        return (self.quiz.question_set.filter(order__gt=self.order).filter(~Q(id__in=user_answers)).order_by("order")
                .first())

    def previous_question(self, user):
        user_answers = UserAnswer.objects.filter(question__quiz=self.quiz).values_list("question_id", flat=True)
        return (self.quiz.question_set.filter(order__lt=self.order).filter(~Q(id__in=user_answers)).order_by("order")
                .last())

    def __str__(self):
        return self.text

    def save_question_options(self, options_texts, post_data):
        if self.type in (Question.SHORT_TEXT, Question.LONG_TEXT):
            self.option_set.all().delete()
        else:
            for key, value in options_texts.items():
                if value:
                    option_number = int(key.replace('option_text_', ''))
                    feedback = post_data.get(f"feedback_{option_number}")
                    if self.type == Question.MULTIPLE_CHOICE_SINGLE_ANSWER:
                        is_correct = option_number == 1
                    else:
                        is_correct = f"is_correct_{option_number}" in post_data
                    if f"option_id_{option_number}" in post_data:
                        option = Option.objects.get(pk=post_data[f"option_id_{option_number}"])
                    else:
                        option = Option(question=self)
                    option.text = value
                    option.feedback = feedback
                    option.is_correct = is_correct
                    option.save()

    def evaluate_response(self, post_data, user):
        is_correct = True
        selected_options = None
        missing = 0
        if self.type == self.MULTIPLE_CHOICE_SINGLE_ANSWER:
            user_answer = int(post_data.get("selected_option"))
            selected_options_queryset = self.option_set.filter(pk=user_answer)
            is_correct = selected_options_queryset.first().is_correct
        elif self.type == self.MULTIPLE_CHOICE_MULTIPLE_ANSWER:
            selected_options = {key: value for key, value in post_data.items() if 'option_' in key}
            selected_options_queryset = Option.objects.filter(id__in=selected_options.values())
            selected_options_set = set(selected_options_queryset.values_list("id", flat=True))
            correct_option_set = set(self.option_set.filter(is_correct=True).values_list("id", flat=True))
            is_correct = selected_options_set == correct_option_set
            missing = len(correct_option_set) - len(selected_options_set)
        if is_correct:
            user_answer_record = UserAnswer(question=self, user=user)
            user_answer_record.save()
            user_answer_record.selected_options.set(selected_options_queryset)
        return selected_options_queryset, is_correct, missing


class Option(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    text = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)
    feedback = models.TextField(null=True, blank=True)
    option_order = models.IntegerField(null=True, blank=True)

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

    class Meta:
        unique_together = ('question', 'text',)


class UserAnswer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.RESTRICT)
    selected_options = models.ManyToManyField(Option)
    answered_on = models.DateTimeField(auto_now_add=True)
    answer_text = models.TextField(null=True, blank=True)
    admin_feedback = models.TextField(null=True, blank=True)
    ai_feedback = models.TextField(null=True, blank=True)
    points = models.IntegerField(null=True, blank=True)
    admin_feedback_on = models.DateTimeField(null=True, blank=True)
    ai_feedback_on = models.DateTimeField(null=True, blank=True)
    admin_feedback_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name="feedback_set")
    @property
    def user_answer(self):
        if self.question.type in (Question.SHORT_TEXT, Question.LONG_TEXT):
            return self.answer_text
        return self.__get_option_attrs("text")

    @property
    def answer_feedback(self):
        if self.question.type in (Question.SHORT_TEXT, Question.LONG_TEXT):
            if self.admin_feedback:
                return self.admin_feedback
            if self.ai_feedback:
                return self.ai_feedback

    def __get_option_attrs(self, attr):
        if self.question.type == Question.MULTIPLE_CHOICE_SINGLE_ANSWER:
            selected_option: Option = self.selected_options.first()
            return getattr(selected_option, attr)
        if self.question.type == Question.MULTIPLE_CHOICE_MULTIPLE_ANSWER:
            selected_options: QuerySet = self.selected_options.all()
            return f"<ul><li>{'</li><li>'.join([getattr(x, attr) for x in selected_options])}</li></ul>"

    def __str__(self):
        return f"{self.user.username}'s answer to {self.question.text}"

    class Meta:
        unique_together = ('user', 'question',)

