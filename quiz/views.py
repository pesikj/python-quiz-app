from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Max, Q, Count, Case, When, IntegerField
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import DetailView, CreateView, DeleteView, UpdateView, TemplateView
from django.views.generic.list import ListView

from .forms import CourseForm, QuizForm, QuestionForm
from .models import Course, Question, Quiz, Option, UserAnswer


class CourseListView(ListView):
    model = Course
    context_object_name = 'courses'
    template_name = 'course_list.html'


class QuizListView(LoginRequiredMixin, ListView):
    model = Quiz
    context_object_name = 'quizzes'
    template_name = 'quiz_list.html'

    def _get_course(self):
        return Course.objects.get(pk=self.kwargs["course_id"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["quiz_questions"] = self._get_course().get_quiz_question_counts(self.request.user)
        context["quiz_completion"] = self._get_course().quiz_completion_info(self.request.user)
        return context

    def get_queryset(self):
        return Quiz.objects.filter(course_id=self.kwargs['course_id'])


class QuestionView(LoginRequiredMixin, DetailView):
    model = Question
    template_name = 'question.html'
    context_object_name = 'question'

    @property
    def _quiz(self):
        return self.get_object().quiz

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["quiz"] = self._quiz
        context["next_question"] = self.object.next_question(self.request.user)
        context["previous_question"] = self.object.previous_question(self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        post_data = request.POST.copy()
        question_id = post_data['question_id']
        question = Question.objects.get(pk=int(question_id))
        context = {"quiz": self._quiz, "question": question, "next_question": question.next_question(self.request.user),
                   "previous_question": question.previous_question(self.request.user)}
        if question.type in (Question.SHORT_TEXT, Question.LONG_TEXT):
            user_answer = UserAnswer.objects.create(question=question, answer_text=post_data["answer_text"],
                                                    user=self.request.user)
            user_answer.save()
            context.update({"feedback": [["", "Odpověď byla uložena"]], "continue": True})
        elif question.type in (Question.MULTIPLE_CHOICE_SINGLE_ANSWER, Question.MULTIPLE_CHOICE_MULTIPLE_ANSWER):
            selected_options, is_correct, missing = question.evaluate_response(post_data, request.user)
            context.update({"missing": missing})
            if is_correct:
                context["feedback_type"] = "success"
                context["continue"] = True
            else:
                context["feedback_type"] = "warning"
            if question.type == Question.MULTIPLE_CHOICE_SINGLE_ANSWER:
                context["feedback"] = [[selected_options.first().text, selected_options.first().calculated_feedback]]
                context["selected_option"] = selected_options.first()
            else:
                context["feedback"] = [[x.text, x.calculated_feedback] for x in selected_options]
                context["selected_options_ids"] = [selected_option.id for selected_option in selected_options]
        return render(request, self.template_name, context)


class CourseAddView(UserPassesTestMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'add_course.html'
    success_url = reverse_lazy('course_list')

    def test_func(self):
        return self.request.user.is_superuser


class QuizAddView(UserPassesTestMixin, CreateView):
    model = Quiz
    form_class = QuizForm
    template_name = 'add_quiz.html'
    success_url = reverse_lazy('course_list')

    def test_func(self):
        return self.request.user.is_superuser


class QuestionAddView(UserPassesTestMixin, CreateView):
    model = Question
    form_class = QuestionForm
    template_name = 'add_question.html'
    success_url = reverse_lazy('course_list')

    def test_func(self):
        return self.request.user.is_superuser

    @property
    def _quiz(self):
        return Quiz.objects.get(id=self.kwargs['quiz_id'])

    def post(self, request, *args, **kwargs):
        form = QuestionForm(request.POST)
        post_data = request.POST.copy()
        if form.is_valid():
            question: Question = form.save(commit=False)
            question.quiz = self._quiz
            max_order_value = Question.objects.filter(quiz=self._quiz).aggregate(Max('order'))['order__max']
            question.order = max_order_value + 1 if max_order_value else 1
            question.save()
            options_texts = {key: value for key, value in post_data.items() if 'option_text' in key}
            question.save_question_options(options_texts, post_data)
            return redirect(reverse_lazy("quiz_list", kwargs={"course_id": self._quiz.course.pk}))
        else:
            return render(request, self.template_name, {'form': form})


class UserTestReviewView(LoginRequiredMixin, ListView):
    model = UserAnswer
    context_object_name = 'answers'
    template_name = 'user_quiz_review.html'

    @property
    def _quiz(self):
        return Quiz.objects.get(id=self.kwargs['quiz_id'])

    def get_queryset(self):
        quiz = self._quiz
        return UserAnswer.objects.filter(question__quiz=quiz).filter(user=self.request.user).order_by("question__order")


class AdminQuizReviewView(UserPassesTestMixin, ListView):
    model = Question
    context_object_name = 'questions'
    template_name = 'admin_quiz_review.html'

    def test_func(self):
        return self.request.user.is_superuser


class QuestionDeleteView(UserPassesTestMixin, DeleteView):
    model = Question
    template_name = "question_confirm_delete.html"
    pk_url_kwarg = 'question_id'

    def get_success_url(self):
        return reverse_lazy('admin_quiz_review', kwargs={'quiz_id': self.object.quiz.id})

    def test_func(self):
        return self.request.user.is_superuser


class QuestionUpdateView(UserPassesTestMixin, UpdateView):
    model = Question
    form_class = QuestionForm
    template_name = 'update_question.html'
    pk_url_kwarg = 'question_id'

    @property
    def _quiz(self):
        return self.get_object().quiz

    def get_success_url(self):
        return reverse_lazy('admin_quiz_review', kwargs={'quiz_id': self.get_object().quiz.id})

    def test_func(self):
        return self.request.user.is_superuser

    def post(self, request, *args, **kwargs):
        form = QuestionForm(request.POST, instance=self.get_object())
        post_data = request.POST.copy()
        if form.is_valid():
            question: Question = form.save(commit=False)
            question.quiz = self._quiz
            question.save()
            options_texts = {key: value for key, value in post_data.items() if 'option_text' in key}
            question.save_question_options(options_texts, post_data)
            return redirect(self.get_success_url())
        else:
            return render(request, self.template_name, {'form': form})


class QuizFeedbackBaseListView(UserPassesTestMixin, TemplateView):
    def test_func(self):
        return self.request.user.is_superuser

    def _get_user_answers_query(self):
        return UserAnswer.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_answers_query = self._get_user_answers_query()
        context["user_quizzes"] = (self._get_user_answers_query()
                                   .filter(question__type__in=[Question.SHORT_TEXT, Question.LONG_TEXT])
                                   .values('user__id', 'user__username', "question__quiz__id", "question__quiz__title")
                                   .annotate(total=Count('question__id', distinct=True),
                                             feedback_missing=Count(Case(When(admin_feedback__isnull=True, then=1),
                                                                         output_field=IntegerField()), distinct=True)
                                             ))
        return context


class QuizFeedbackListView(QuizFeedbackBaseListView):
    template_name = "admin_quiz_answers_feedback_list.html"

    def _get_user_answers_query(self):
        return UserAnswer.objects.filter(question__quiz=self.kwargs["quiz_id"])
    
    
class CourseFeedbackListView(QuizFeedbackBaseListView):
    template_name = "admin_course_answers_feedback_list.html"

    def _get_user_answers_query(self):
        return UserAnswer.objects.filter(question__quiz__course=self.kwargs["course_id"])


class QuizFeedbackView(UserPassesTestMixin, ListView):
    model = UserAnswer
    context_object_name = 'user_answers'
    template_name = 'admin_quiz_answers_feedback.html'

    @property
    def _quiz(self):
        return Quiz.objects.get(id=self.kwargs['quiz_id'])

    def test_func(self):
        return self.request.user.is_superuser

    def get_queryset(self):
        return UserAnswer.objects.filter(question__quiz=self.kwargs["quiz_id"], user__id=self.kwargs["user_id"],
                                         question__type__in=[Question.SHORT_TEXT, Question.LONG_TEXT])

    def get_success_url(self):
        return reverse_lazy("admin_quiz_list", kwargs={'quiz_id': self._quiz.id})

    def post(self, request, *args, **kwargs):
        post_data = request.POST.copy()
        feedback_texts = {key: value for key, value in post_data.items() if 'feedback_' in key}
        for key, value in feedback_texts.items():
            user_answer = UserAnswer.objects.get(pk=int(key.replace("feedback_", "")))
            if value:
                user_answer.admin_feedback = value
                user_answer.admin_feedback_on = timezone.now()
                user_answer.admin_feedback_by = self.request.user
                user_answer.save()
            else:
                user_answer.admin_feedback = None
                user_answer.admin_feedback_on = None
                user_answer.admin_feedback_by = None
                user_answer.save()
        return redirect(self.get_success_url())
