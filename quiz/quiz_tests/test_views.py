from datetime import datetime

from django.db.models import Max
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from ..models import Course, Quiz, Question, UserAnswer


class AddCourseViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create an admin user for testing
        cls.admin_user = User.objects.create_superuser(username='adminuser', password='12345',
                                                       email='admin@example.com')
        cls.client = Client()

    def test_redirect_if_not_logged_in(self):
        response = self.client.get(reverse('course_add'))
        self.assertRedirects(response, '/accounts/login/?next=/add-course/')  # Adjust the redirect URL as needed

    def test_forbidden_if_logged_in_not_admin(self):
        # Create a non-admin user
        user = User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')
        response = self.client.get(reverse('course_add'))
        self.assertEqual(response.status_code, 403)  # Forbidden access

    def test_logged_in_admin_uses_correct_template(self):
        self.client.login(username='adminuser', password='12345')
        response = self.client.get(reverse('course_add'))

        self.assertEqual(str(response.context['user']), 'adminuser')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'add_course.html')

    def test_form_course_creation_by_admin(self):
        self.client.login(username='adminuser', password='12345')
        response = self.client.post(reverse('course_add'),
                                    {'title': 'New Course', 'description': 'New Course Description'})

        self.assertEqual(response.status_code, 302)  # Redirects after successful post
        self.assertTrue(Course.objects.filter(title='New Course').exists())


class AddQuizViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a superuser and a regular user for testing
        cls.superuser = User.objects.create_superuser(username='admin', password='admin123')
        cls.user = User.objects.create_user(username='user', password='user123')

        # Create a course for the quiz
        cls.course = Course.objects.create(title="Sample Course", description="Course Description")

        cls.client = Client()

    def test_access_denied_to_non_superuser(self):
        self.client.login(username='user', password='user123')
        response = self.client.get(reverse('quiz_add'))
        self.assertEqual(response.status_code, 403)  # Forbidden for non-superusers

    def test_access_granted_to_superuser(self):
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('quiz_add'))
        self.assertEqual(response.status_code, 200)  # Accessible for superusers

    def test_add_quiz_using_form(self):
        self.client.login(username='admin', password='admin123')
        response = self.client.post(reverse('quiz_add'), {
            'title': 'New Quiz',
            'deadline': datetime.now(),
            'course': self.course.id
        })
        self.assertEqual(response.status_code, 302)  # Redirect on success
        self.assertTrue(Quiz.objects.filter(title='New Quiz').exists())  # Quiz created


class AddQuestionViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Create a superuser and a regular user for testing
        cls.superuser = User.objects.create_superuser(username='admin', password='admin123')
        cls.user = User.objects.create_user(username='user', password='user123')

        # Create a course and a quiz for the question
        cls.course = Course.objects.create(title="Sample Course", description="Course Description")
        cls.quiz = Quiz.objects.create(course=cls.course, title="Sample Quiz")

        cls.client = Client()

    def test_access_denied_to_non_superuser(self):
        self.client.login(username='user', password='user123')
        response = self.client.get(reverse('question_add', kwargs={'quiz_id': self.quiz.id}))
        self.assertEqual(response.status_code, 403)  # Forbidden for non-superusers

    def test_access_granted_to_superuser(self):
        self.client.login(username='admin', password='admin123')
        response = self.client.get(reverse('question_add', kwargs={'quiz_id': self.quiz.id}))
        self.assertEqual(response.status_code, 200)  # Accessible for superusers

    def test_add_question_using_form(self):
        self.client.login(username='admin', password='admin123')
        response = self.client.post(reverse('question_add', kwargs={'quiz_id': self.quiz.id}), {
            'text': 'New Question',
            'type': Question.SHORT_TEXT
        })
        self.assertEqual(response.status_code, 302)  # Redirect on success
        self.assertTrue(Question.objects.filter(text='New Question').exists())  # Question created

        # Test for question order
        max_order = Question.objects.filter(quiz=self.quiz).aggregate(Max('order'))['order__max']
        new_question = Question.objects.get(text='New Question')
        self.assertEqual(new_question.order, max_order)


class QuestionViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a user
        cls.user = User.objects.create_user(username='user', password='password')

        # Create course, quiz, and question
        cls.course = Course.objects.create(title="Sample Course", description="Course Description")
        cls.quiz = Quiz.objects.create(course=cls.course, title="Sample Quiz")
        cls.question = Question.objects.create(quiz=cls.quiz, text="Sample Question", type=Question.SHORT_TEXT)

        cls.client = Client()

    def test_question_view_get(self):
        self.client.login(username='user', password='password')
        response = self.client.get(reverse('question', kwargs={'pk': self.question.id}))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'question.html')
        self.assertEqual(response.context['question'], self.question)

    def test_question_view_post_short_text(self):
        self.client.login(username='user', password='password')
        post_data = {'question_id': self.question.id, 'answer_text': 'Sample Answer'}
        response = self.client.post(reverse('question', kwargs={'pk': self.question.id}), post_data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(UserAnswer.objects.filter(question=self.question, user=self.user).exists())


class UserTestReviewViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a user
        cls.user = User.objects.create_user(username='user', password='password')
        cls.other_user = User.objects.create_user(username='other_user', password='password')

        # Create course, quiz, question, and user answers
        cls.course = Course.objects.create(title="Sample Course", description="Course Description")
        cls.quiz = Quiz.objects.create(course=cls.course, title="Sample Quiz")
        cls.question1 = Question.objects.create(quiz=cls.quiz, text="Sample Question 1", type=Question.SHORT_TEXT)
        cls.question2 = Question.objects.create(quiz=cls.quiz, text="Sample Question 2", type=Question.LONG_TEXT)

        UserAnswer.objects.create(user=cls.user, question=cls.question1, answer_text="Answer 1")
        UserAnswer.objects.create(user=cls.user, question=cls.question2, answer_text="Answer 2")
        cls.client = Client()

    def test_review_page_context(self):
        self.client.login(username='user', password='password')
        response = self.client.get(reverse('quiz_review', kwargs={'quiz_id': self.quiz.id}))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user_quiz_review.html')
        self.assertTrue('answers' in response.context)
        self.assertEqual(len(response.context['answers']), 2)

        # Check if answers belong to the correct user and quiz
        for answer in response.context['answers']:
            self.assertEqual(answer.user, self.user)
            self.assertEqual(answer.question.quiz, self.quiz)

    def test_review_page_no_access_other_user(self):
        self.client.login(username='other_user', password='password')
        response = self.client.get(reverse('quiz_review', kwargs={'quiz_id': self.quiz.id}))

        # Assuming other users should not see this user's answers
        self.assertEqual(len(response.context['answers']), 0)


class QuestionDeleteViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Create users
        cls.admin_user = User.objects.create_superuser(username='admin', password='adminpass')
        cls.regular_user = User.objects.create_user(username='user', password='userpass')

        # Create a course, a quiz, and a question
        cls.course = Course.objects.create(title="Sample Course", description="Course Description")
        cls.quiz = Quiz.objects.create(course=cls.course, title="Sample Quiz")
        cls.question1 = Question.objects.create(quiz=cls.quiz, text="Sample Question")
        cls.question2 = Question.objects.create(quiz=cls.quiz, text="Sample Question")
        cls.client = Client()

    def test_delete_question_by_admin(self):
        self.client.login(username='admin', password='adminpass')
        response = self.client.post(reverse('question_delete', kwargs={'question_id': self.question1.id}))

        self.assertRedirects(response, reverse('admin_quiz_review', kwargs={'quiz_id': self.quiz.id}))
        self.assertFalse(Question.objects.filter(id=self.question1.id).exists())

    def test_delete_question_access_denied_regular_user(self):
        self.client.login(username='user', password='userpass')
        response = self.client.post(reverse('question_delete', kwargs={'question_id': self.question2.id}))
        self.assertTrue(Question.objects.filter(id=self.question2.id).exists())


class QuestionUpdateViewTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Create users
        cls.superuser = User.objects.create_superuser(username='admin', password='adminpass')
        cls.regular_user = User.objects.create_user(username='user', password='userpass')

        # Create course, quiz, and question
        cls.course = Course.objects.create(title="Sample Course", description="Course Description")
        cls.quiz = Quiz.objects.create(course=cls.course, title="Sample Quiz")
        cls.question = Question.objects.create(quiz=cls.quiz, text="Sample Question", type='ST')

        cls.client = Client()

    def test_update_question_by_admin(self):
        self.client.login(username='admin', password='adminpass')
        response = self.client.post(reverse('question_update', kwargs={'question_id': self.question.id}),
                                    {'text': 'Updated Question', 'type': 'LT'})

        self.assertRedirects(response, reverse('admin_quiz_review', kwargs={'quiz_id': self.quiz.id}))
        updated_question = Question.objects.get(id=self.question.id)
        self.assertEqual(updated_question.text, 'Updated Question')
        self.assertEqual(updated_question.type, 'LT')

    def test_update_question_access_denied_regular_user(self):
        self.client.login(username='user', password='userpass')
        response = self.client.post(reverse('question_update', kwargs={'question_id': self.question.id}),
                                    {'text': 'Updated Question', 'type': 'LT'})

        self.assertEqual(response.status_code, 403)  # Assuming regular users are forbidden
        self.assertEqual(Question.objects.get(id=self.question.id).text, 'Sample Question')  # Unchanged


class QuizAndCourseFeedbackListViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a superuser
        cls.superuser = User.objects.create_superuser(username='admin', password='adminpass')

        # Create test data for course, quiz, question, and user answer
        cls.course = Course.objects.create(title="Test Course")
        cls.quiz = Quiz.objects.create(course=cls.course, title="Test Quiz")
        cls.question = Question.objects.create(quiz=cls.quiz, text="Test Question", type=Question.SHORT_TEXT)
        cls.user_answer = UserAnswer.objects.create(user=cls.superuser, question=cls.question,
                                                    answer_text="Test Answer")

        cls.client = Client()

    def test_admin_quiz_list_view_access(self):
        # Test access control
        self.client.login(username='admin', password='adminpass')
        response = self.client.get(reverse('admin_quiz_list', kwargs={'quiz_id': self.quiz.id}))
        self.assertEqual(response.status_code, 200)

        # Test template used
        self.assertTemplateUsed(response, "admin_quiz_answers_feedback_list.html")

        # Test context data
        self.assertIn('user_quizzes', response.context)

    def test_admin_course_feedback_list_view_access(self):
        # Test access control
        self.client.login(username='admin', password='adminpass')
        response = self.client.get(reverse('admin_course_feedback_list', kwargs={'course_id': self.course.id}))
        self.assertEqual(response.status_code, 200)

        # Test template used
        self.assertTemplateUsed(response, "admin_course_answers_feedback_list.html")

        # Test context data
        self.assertIn('user_quizzes', response.context)


class QuizFeedbackViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create a superuser and a regular user
        cls.superuser = User.objects.create_superuser(username='admin', password='adminpass')
        cls.regular_user = User.objects.create_user(username='user', password='userpass')

        # Create test data for course, quiz, question, and user answer
        cls.course = Course.objects.create(title="Test Course")
        cls.quiz = Quiz.objects.create(course=cls.course, title="Test Quiz")
        cls.question = Question.objects.create(quiz=cls.quiz, text="Test Question", type=Question.SHORT_TEXT)
        cls.user_answer = UserAnswer.objects.create(user=cls.regular_user, question=cls.question,
                                                    answer_text="Test Answer")

        cls.client = Client()

    def test_quiz_feedback_view_access_superuser(self):
        # Test access control for superuser
        self.client.login(username='admin', password='adminpass')
        response = self.client.get(
            reverse('admin_feedback', kwargs={'quiz_id': self.quiz.id, 'user_id': self.regular_user.id}))
        self.assertEqual(response.status_code, 200)

        # Test template used
        self.assertTemplateUsed(response, "admin_quiz_answers_feedback.html")

        # Test context data
        self.assertIn('user_answers', response.context)

    def test_quiz_feedback_view_access_regular_user(self):
        # Test access control for non-superuser
        self.client.login(username='user', password='userpass')
        response = self.client.get(
            reverse('admin_feedback', kwargs={'quiz_id': self.quiz.id, 'user_id': self.regular_user.id}))
        self.assertEqual(response.status_code, 403)  # or 302 for redirect to login page

    def test_quiz_feedback_view_post(self):
        # Test POST request handling
        self.client.login(username='admin', password='adminpass')
        post_data = {'feedback_1': 'New feedback'}
        response = self.client.post(
            reverse('admin_feedback', kwargs={'quiz_id': self.quiz.id, 'user_id': self.regular_user.id}), post_data)

        # Fetch the updated user_answer
        updated_user_answer = UserAnswer.objects.get(id=self.user_answer.id)
        self.assertEqual(updated_user_answer.admin_feedback, 'New feedback')
        self.assertIsNotNone(updated_user_answer.admin_feedback_on)
        self.assertEqual(updated_user_answer.admin_feedback_by, self.superuser)

        # Test redirection after post
        self.assertRedirects(response, reverse('admin_quiz_list', kwargs={'quiz_id': self.quiz.id}))
