from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Max, Q
from django.http import HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import DetailView, CreateView
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
        return context

    def post(self, request, *args, **kwargs):
        post_data = request.POST.copy()
        question_id = post_data['question_id']
        question = Question.objects.get(pk=int(question_id))
        if question.type in (Question.SHORT_TEXT, Question.LONG_TEXT):
            user_answer = UserAnswer.objects.create(question=question, answer_text=post_data["answer_text"],
                                                    user=self.request.user)
            user_answer.save()
            context = {"feedback": "Odpověď byla uložena"}
        elif question.type == Question.MULTIPLE_CHOICE_SINGLE_ANSWER:
            user_answer = int(post_data.get("selected_option"))
            correct_option = question.option_set.filter(is_correct=True).first()
            selected_option = question.option_set.get(pk=user_answer)
            feedback = selected_option.feedback
            context = {"feedback": selected_option.feedback, "quiz": self._quiz, "question": question,
                       "selected_option": selected_option}
            if user_answer == correct_option.pk:
                feedback = feedback if feedback else "Správná odpověď."
                context["feedback"] = feedback
                context["feedback_type"] = "success"
                context["continue"] = True
                user_answer_record = UserAnswer(question=question, user=request.user)
                user_answer_record.save()
                user_answer_record.selected_options.set([user_answer])
            else:
                context["feedback_type"] = "warning"
        elif question.type == Question.MULTIPLE_CHOICE_MULTIPLE_ANSWER:
            selected_options = {key: value for key, value in post_data.items() if 'option_' in key}
            context = {"quiz": self._quiz}
        return render(request, self.template_name, context)


class AddCourseView(UserPassesTestMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'add_course.html'
    success_url = reverse_lazy('course_list')

    def test_func(self):
        return self.request.user.is_superuser


class AddQuizView(UserPassesTestMixin, CreateView):
    model = Quiz
    form_class = QuizForm
    template_name = 'add_quiz.html'
    success_url = reverse_lazy('course_list')

    def test_func(self):
        return self.request.user.is_superuser


class AddQuestionView(UserPassesTestMixin, CreateView):
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
            question = form.save(commit=False)
            question.quiz = self._quiz
            max_order_value = Question.objects.filter(quiz=self._quiz).aggregate(Max('order'))['order__max']
            question.order = max_order_value + 1 if max_order_value else 1
            question.save()
            options_texts = {key: value for key, value in post_data.items() if 'option_text' in key}
            for key, value in options_texts.items():
                if value:
                    option_number = int(key.replace('option_text_', ''))
                    feedback = post_data.get(f"feedback_{option_number}")
                    option = Option(question=question, text=value, feedback=feedback,
                                    is_correct=f"is_correct_{option_number}" in post_data)
                    option.save()
            return redirect(reverse_lazy("quiz_list", kwargs={"course_id": self._quiz.course.pk}))
        else:
            return render(request, self.template_name, {'form': form})


class UserTestReviewView(LoginRequiredMixin, ListView):
    model = UserAnswer
    context_object_name = 'answers'
    template_name = 'user_test_review.html'

    @property
    def _quiz(self):
        return Quiz.objects.get(id=self.kwargs['quiz_id'])

    def get_queryset(self):
        quiz = self._quiz
        return UserAnswer.objects.filter(question__quiz=quiz).filter(user=self.request.user).order_by("question__order")

