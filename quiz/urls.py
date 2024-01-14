from django.urls import path
from .views import CourseListView, QuizListView, QuestionView, CourseAddView, QuizAddView, QuestionAddView, \
    UserTestReviewView, AdminQuizReviewView, QuestionDeleteView, QuestionUpdateView, QuizFeedbackListView, \
    QuizFeedbackView, CourseFeedbackListView, CourseUpdateView, QuizUpdateView, QuizDeleteView, CourseDeleteView, \
    UserAnswerAIEvaluationView, UserUpdateView, CustomPasswordChangeView, CustomPasswordChangeDoneView, RegisterView, \
    CustomLogoutView

urlpatterns = [
    path("", CourseListView.as_view(), name="course_list"),
    path("courses/<int:course_id>/", QuizListView.as_view(), name="quiz_list"),
    path("question/<int:question_id>/", QuestionView.as_view(), name="question"),
    path("add-course/", CourseAddView.as_view(), name="course_add"),
    path("add-quiz/", QuizAddView.as_view(), name="quiz_add"),
    path("quiz/<int:quiz_id>/add-question/", QuestionAddView.as_view(), name="question_add"),
    path("user-quiz-review/<int:quiz_id>/", UserTestReviewView.as_view(), name="quiz_review"),
    path("quiz/<int:quiz_id>/admin-quiz-review/", AdminQuizReviewView.as_view(), name="admin_quiz_review"),
    path('question/<int:question_id>/delete/', QuestionDeleteView.as_view(), name='question_delete'),
    path('question/<int:question_id>/update/', QuestionUpdateView.as_view(), name='question_update'),
    path("quiz/<int:quiz_id>/admin-quiz-feedback-list/", QuizFeedbackListView.as_view(), name="admin_quiz_list"),
    path("quiz/<int:course_id>/admin-course-feedback-list/", CourseFeedbackListView.as_view(), 
         name="admin_course_feedback_list"),
    path("quiz/<int:quiz_id>/<int:user_id>/admin-feedback/", QuizFeedbackView.as_view(), name="admin_feedback"),
    path('course/update/<int:course_id>/', CourseUpdateView.as_view(), name='course_update'),
    path('quiz/update/<int:quiz_id>/', QuizUpdateView.as_view(), name='quiz_update'),
    path('quiz/delete/<int:quiz_id>/', QuizDeleteView.as_view(), name='quiz_delete'),
    path('course/delete/<int:course_id>/', CourseDeleteView.as_view(), name='course_delete'),
    path("quiz/<int:quiz_id>/<int:user_id>/ai-feedback/", UserAnswerAIEvaluationView.as_view(),
         name="ai_feedback"),
    path('user/update/', UserUpdateView.as_view(), name='user_update'),
    path('user/password_change/', CustomPasswordChangeView.as_view(), name='custom_password_change'),
    path('user/password_change/done/', CustomPasswordChangeDoneView.as_view(), name='custom_password_change_done'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', CustomLogoutView.as_view(), name='custom_logout'),
]
