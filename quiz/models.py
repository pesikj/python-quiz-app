import decimal
import os
from typing import Optional

from django.contrib.auth.models import User
from django.db import models
from django.db.models import QuerySet, Q, JSONField, Max


class Course(models.Model):
    CHATGPT_MODEL_35_TURBO = "gpt-4"

    CHATGPT_MODEL_CHOICES = [
        (CHATGPT_MODEL_35_TURBO, "gpt-4"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    ai_prompt_format = models.TextField(null=True, blank=True)
    ai_api_key = models.CharField(max_length=200, null=True, blank=True)
    ai_model = models.CharField(max_length=20, choices=CHATGPT_MODEL_CHOICES, default=CHATGPT_MODEL_35_TURBO,
                                blank=True)
    attachment = models.FileField(upload_to='attachments/', null=True, blank=True)

    @property
    def filename(self):
        return os.path.basename(self.attachment.path)

    def get_quiz_question_counts(self, user: User) -> dict:
        quiz_questions_counts = {}
        for quiz in self.quiz_set.all():
            quiz: Quiz
            finished_questions_ids = quiz.quiz_completed_questions_ids(user)
            finished_questions_ids = list(set(finished_questions_ids))
            if quiz.question_set.count() == 0:
                quiz_questions_counts[quiz.id] = None
            elif len(finished_questions_ids) == 0:
                quiz_questions_counts[quiz.id] = quiz.question_set.order_by("order").first().pk
            else:
                current_question_query = quiz.question_set.filter(~Q(pk__in=finished_questions_ids))
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

    @property
    def has_answers(self) -> bool:
        for quiz in self.quiz_set.all():
            if quiz.has_answers:
                return True
        return False

    def __str__(self):
        return self.title


class Quiz(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    deadline = models.DateTimeField(null=True, blank=True)
    ai_prompt_quiz_text = models.CharField(max_length=200, null=True, blank=True)
    attachment = models.FileField(upload_to='attachments/', null=True, blank=True)

    @property
    def filename(self):
        return os.path.basename(self.attachment.path)

    def quiz_completed(self, user):
        questions_ids = set(self.question_set.values_list("id", flat=True))
        user_answers_completed_questions_ids = self.quiz_completed_questions_ids(user)
        return questions_ids == user_answers_completed_questions_ids and len(questions_ids) > 0

    def quiz_completed_questions_ids(self, user: User):
        questions_ids = set(self.question_set.values_list("id", flat=True))
        user_answers_text_questions_ids = list(UserAnswer.objects.filter(question__quiz=self, user=user,
                                                                         question__type__in=[Question.SHORT_TEXT,
                                                                                             Question.LONG_TEXT])
                                               .values_list("question_id", flat=True))
        user_answers_correct_questions_ids = list(UserAnswer.objects.filter(question__quiz=self, user=user,
                                                                            question__type__in=[
                                                                                Question.MULTIPLE_CHOICE_SINGLE_ANSWER,
                                                                                Question.MULTIPLE_CHOICE_MULTIPLE_ANSWER],
                                                                            points__exact=1)
                                                  .values_list("question_id", flat=True))
        user_answers_incorrect_questions = (UserAnswer.objects.filter(question__quiz=self, user=user,
                                                                      question__type__in=[
                                                                          Question.MULTIPLE_CHOICE_SINGLE_ANSWER,
                                                                          Question.MULTIPLE_CHOICE_MULTIPLE_ANSWER],
                                                                      ).filter(Q(points__isnull=True)
                                                                               | Q(points__lt=1)))
        user_answers_incorrect_questions_ids = []
        for item in user_answers_incorrect_questions:
            item: UserAnswer
            max_attempt = UserAnswer.get_attempt_number_for_user_question(user.pk, item.question.pk)
            if max_attempt >= item.question.max_attempts + 1:
                user_answers_incorrect_questions_ids.append(item.question.id)
        user_answers_completed_questions_ids = set(user_answers_text_questions_ids + user_answers_correct_questions_ids
                                                   + user_answers_incorrect_questions_ids)
        return user_answers_completed_questions_ids

    @property
    def has_answers(self) -> bool:
        for question in self.question_set.all():
            if question.useranswer_set.exists():
                return True
        return False

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
    text = models.TextField(verbose_name="Text otázky")
    type = models.CharField(max_length=2, choices=QUESTION_TYPES, default=SHORT_TEXT, verbose_name="Příklad otázky")
    order = models.IntegerField(default=0)
    example_answer = models.TextField(null=True, blank=True, verbose_name="Příklad odpovědi")
    ai_feedback_enabled = models.BooleanField(default=False, null=True, blank=True)
    attachment_1 = models.FileField(upload_to='attachments/', null=True, blank=True)
    attachment_2 = models.FileField(upload_to='attachments/', null=True, blank=True)
    attachment_3 = models.FileField(upload_to='attachments/', null=True, blank=True)
    max_attempts = models.IntegerField(default=2, verbose_name="Počet pokusů")

    class Meta:
        ordering = ["order"]

    @property
    def question_attachments(self):
        from quiz.templatetags.custom_filters import is_image

        attachment_list = [x for x in [self.attachment_1, self.attachment_2, self.attachment_3] if x]
        ordered_attachments = ([x for x in attachment_list if is_image(x.path)] +
                               [x for x in attachment_list if not is_image(x.path)])
        return ordered_attachments

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

    @staticmethod
    def __calculate_points(selected_options_set: set, correct_option_set: set) -> float:
        max_points = 1.0
        min_points = 0.0

        correctly_chosen = len(selected_options_set.intersection(correct_option_set))
        incorrectly_chosen = len(selected_options_set.difference(correct_option_set))
        total_correct_options = len(correct_option_set)
        if total_correct_options > 0:
            points_for_correct = correctly_chosen / total_correct_options
        else:
            points_for_correct = 0
        penalty_per_incorrect = 1 / (len(correct_option_set) + len(correct_option_set.difference(selected_options_set)))
        penalty = incorrectly_chosen * penalty_per_incorrect
        total_points = max_points * points_for_correct - penalty
        return max(min_points, total_points)

    def evaluate_response(self, post_data, user):
        is_correct = True
        selected_options = None
        missing = 0
        selected_options_queryset = []
        points = 0
        if self.type == self.MULTIPLE_CHOICE_SINGLE_ANSWER:
            user_answer = int(post_data.get("selected_option"))
            selected_options_queryset = self.option_set.filter(pk=user_answer)
            is_correct = selected_options_queryset.first().is_correct
        elif self.type == self.MULTIPLE_CHOICE_MULTIPLE_ANSWER:
            selected_options = {key: value for key, value in post_data.items() if 'option_' in key}
            selected_options_queryset = Option.objects.filter(id__in=selected_options.values())
            selected_options_set = set(selected_options_queryset.values_list("id", flat=True))
            correct_option_set = set(self.option_set.filter(is_correct=True).values_list("id", flat=True))
            points = self.__calculate_points(selected_options_set, correct_option_set)
            is_correct = selected_options_set == correct_option_set
            missing = len(correct_option_set) - len(selected_options_set)
        user_answer = UserAnswer(question=self, user=user)
        if self.type == self.MULTIPLE_CHOICE_SINGLE_ANSWER:
            user_answer.points = is_correct
        elif self.type == self.MULTIPLE_CHOICE_MULTIPLE_ANSWER:
            user_answer.points = points
        user_answer.save()
        user_answer.selected_options.set(selected_options_queryset)
        return user_answer


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
    points = models.DecimalField(null=True, blank=True, max_digits=3, decimal_places=2)
    admin_feedback_on = models.DateTimeField(null=True, blank=True)
    ai_feedback_on = models.DateTimeField(null=True, blank=True)
    admin_feedback_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name="feedback_set")
    attempt_number = models.IntegerField(default=1)
    missing_answers = models.IntegerField(default=0)

    @property
    def points_formatted(self):
        return decimal.Decimal(str(self.points)).normalize()

    @property
    def is_last_attempt(self):
        return self.attempt_number == self.get_attempt_number_for_user_question(self.user.pk, self.question.pk)

    @staticmethod
    def get_attempt_number_for_queryset(query_set):
        value = query_set.aggregate(Max('attempt_number'))['attempt_number__max']
        return value if value else 1

    @classmethod
    def get_attempt_number_for_user_question(cls, user_id: int, question_id: int) -> int:
        query_set = cls.objects.filter(user_id=user_id, question_id=question_id)
        return cls.get_attempt_number_for_queryset(query_set)

    @classmethod
    def get_user_answers_single_question(cls, user_id: int, quiz_id: int, question_id: Optional[int] = None,
                                         question_type_list: Optional[list] = None,
                                         ai_feedback_enabled: Optional[bool] = None):
        result = cls.objects.filter(question__quiz=user_id, user__id=quiz_id)
        if question_id:
            result = result.filter(question_id=question_id)
        max_attempt_number = cls.get_attempt_number_for_queryset(result)
        result = result.filter(attempt_number=max_attempt_number)
        if question_type_list:
            result = result.filter(question__type__in=question_type_list)
        if ai_feedback_enabled is not None:
            result = result.filter(question__ai_feedback_enabled=ai_feedback_enabled)
        return result

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
        elif self.question.type in (Question.MULTIPLE_CHOICE_SINGLE_ANSWER, Question.MULTIPLE_CHOICE_MULTIPLE_ANSWER):
            return "<ol><li>" "</li><li>".join([f"<b>{x.text}</b>: {x.calculated_feedback}"
                                                for x in self.selected_options.all()]) + "</li></ol>"

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
        unique_together = ('user', 'question', 'attempt_number')


class ChatGPTLog(models.Model):
    message = models.TextField(null=True, blank=True)
    response = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField("Created At", auto_now_add=True)
    user_answer = models.ForeignKey(UserAnswer, on_delete=models.CASCADE, null=True, blank=True)

    @classmethod
    def send_request(cls, user_answer: UserAnswer):
        client = OpenAI(api_key=user_answer.question.quiz.course.ai_api_key)
        message_content = user_answer.question.quiz.course.ai_prompt_format
        message_content = (message_content.replace("[question_text]", user_answer.question.text)
                           .replace("[answer_text]", user_answer.answer_text))
        if user_answer.question.example_answer:
            message_content = message_content.replace("[example_answer]", user_answer.answer_text)
        stream = client.chat.completions.create(
            model=user_answer.question.quiz.course.ai_model,
            messages=[{"role": "user", "content": message_content}],
            stream=True,
        )
        response = "".join([part.choices[0].delta.content or "" for part in stream])
        print(response)
        log_item = cls(message=message_content, response=response, user_answer=user_answer)
        log_item.save()
        user_answer.ai_feedback = response
        user_answer.ai_feedback_on = log_item.created_at
        user_answer.save()

