from django.urls import path
from .views import CourseListView, QuizListView, QuestionView, CourseAddView, QuizAddView, QuestionAddView, \
    UserTestReviewView, AdminQuizReviewView, QuestionDeleteView, QuestionUpdateView, QuizFeedbackListView, \
    QuizFeedbackView, CourseFeedbackListView

urlpatterns = [
    path("", CourseListView.as_view(), name="course_list"),
    path("courses/<int:course_id>/", QuizListView.as_view(), name="quiz_list"),
    path("question/<int:pk>/", QuestionView.as_view(), name="question"),
    path("add-course/", CourseAddView.as_view(), name="course_add"),
    path("add-quiz/", QuizAddView.as_view(), name="quiz_add"),
    path("quiz/<int:quiz_id>/add-question/", QuestionAddView.as_view(), name="question_add"),
    path("user-test-review/<int:quiz_id>/", UserTestReviewView.as_view(), name="quiz_review"),
    path("quiz/<int:quiz_id>/admin-test-review/", AdminQuizReviewView.as_view(), name="admin_quiz_review"),
    path('question/<int:question_id>/delete/', QuestionDeleteView.as_view(), name='question_delete'),
    path('question/<int:question_id>/update/', QuestionUpdateView.as_view(), name='question_update'),
    path("quiz/<int:quiz_id>/admin-quiz-feedback-list/", QuizFeedbackListView.as_view(), name="admin_quiz_list"),
    path("quiz/<int:course_id>/admin-course-feedback-list/", CourseFeedbackListView.as_view(), 
         name="admin_course_feedback_list"),
    path("quiz/<int:quiz_id>/<int:user_id>/admin-feedback/", QuizFeedbackView.as_view(), name="admin_feedback"),

]
