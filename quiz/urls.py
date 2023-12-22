from django.urls import path
from .views import CourseListView, QuizListView, QuestionView, AddCourseView, AddQuizView, AddQuestionView

urlpatterns = [
    path("", CourseListView.as_view(), name="course_list"),
    path("courses/<int:course_id>/", QuizListView.as_view(), name="quiz_list"),
    path("quiz/<int:pk>/", QuestionView.as_view(), name="question"),
    path("add-course/", AddCourseView.as_view(), name="course_add"),
    path("add-quiz/", AddQuizView.as_view(), name="quiz_add"),
    path("quiz/<int:quiz_id>/add-question/", AddQuestionView.as_view(), name="question_add"),
]
