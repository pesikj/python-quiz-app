from datetime import datetime

from django.db.models import Max
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from ..models import Course, Quiz, Question


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
