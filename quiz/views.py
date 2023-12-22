from django.contrib.auth.mixins import LoginRequiredMixin
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

    def _get_quiz_questions(self):
        quiz_questions = {}
        for quiz in self.get_queryset():
            answered_questions = (UserAnswer.objects.filter(question__quiz=quiz).filter(user=self.request.user)
                                  .values_list("question__quiz", flat=True))
            if len(answered_questions) == 0:
                quiz_questions[quiz.id] = quiz.question_set.order_by("order").first().pk
                continue
            current_question_query = quiz.question_set.filter(~Q(quiz_id__in=answered_questions))
            if not current_question_query.exists():
                quiz_questions[quiz.id] = None
            else:
                quiz_questions[quiz.id] = current_question_query.order_by("order").first().pk
        return quiz_questions

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["quiz_questions"] = self._get_quiz_questions()
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
            user_answer = UserAnswer.objects.create(question=question, answer_text=post_data["text"],
                                                    user=self.request.user)
            user_answer.save()
            return render(request, self.template_name, {"feedback": "Odpověď byla uložena"})
        elif question.type == Question.MULTIPLE_CHOICE_SINGLE_ANSWER:
            user_answer = int(post_data.get("selected_option"))
            correct_option = question.option_set.filter(is_correct=True).first()
            if user_answer == correct_option.pk:
                return render(request, self.template_name, {"feedback": "Vybral(a) jsi správnou odpověď.",
                                                            "quiz": self._quiz, "question": question,
                                                            "feedback_type": "success"})
            else:
                selected_option = question.option_set.filter(pk=user_answer).first()
                return render(request, self.template_name, {"feedback": selected_option.feedback,
                                                            "quiz": self._quiz, "question": question,
                                                            "feedback_type": "warning"})
        elif question.type == Question.MULTIPLE_CHOICE_MULTIPLE_ANSWER:
            selected_options = {key: value for key, value in post_data.items() if 'option_' in key}


class AddCourseView(LoginRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = 'add_course.html'
    success_url = reverse_lazy('course_list')


class AddQuizView(LoginRequiredMixin, CreateView):
    model = Quiz
    form_class = QuizForm
    template_name = 'add_quiz.html'
    success_url = reverse_lazy('course_list')


class AddQuestionView(LoginRequiredMixin, CreateView):
    model = Question
    form_class = QuestionForm
    template_name = 'add_question.html'
    success_url = reverse_lazy('course_list')

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
