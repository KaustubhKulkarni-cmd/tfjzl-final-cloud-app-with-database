from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Course, Lesson, Question, Choice, Enrollment, Submission


class AssessmentFeatureTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='teststudent', password='password123', first_name='Test')
        self.client = Client()
        self.course = Course.objects.create(name='Test Course', description='Test Description')
        self.lesson = Lesson.objects.create(title='Test Lesson', course=self.course, content='Test Content')
        self.question = Question.objects.create(course=self.course, lesson=self.lesson, question_text='What is Django?', grade=50)
        self.choice1 = Choice.objects.create(question=self.question, choice_text='A Python web framework', is_correct=True)
        self.choice2 = Choice.objects.create(question=self.question, choice_text='A database', is_correct=False)

    def test_question_choice_relationship(self):
        self.assertEqual(self.question.choice_set.count(), 2)
        self.assertEqual(self.choice1.question, self.question)

    def test_is_get_score_correct(self):
        self.assertTrue(self.question.is_get_score([self.choice1.id]))

    def test_is_get_score_incorrect(self):
        self.assertFalse(self.question.is_get_score([self.choice2.id]))
        self.assertFalse(self.question.is_get_score([self.choice1.id, self.choice2.id]))
        self.assertFalse(self.question.is_get_score([]))

    def test_submission_and_exam_result(self):
        self.client.login(username='teststudent', password='password123')
        # Submit correct choice
        submit_url = reverse('onlinecourse:submit', args=[self.course.id])
        response = self.client.post(submit_url, {f'choice_{self.choice1.id}': self.choice1.id})
        self.assertEqual(response.status_code, 302)

        # Verify submission created
        submission = Submission.objects.filter(enrollment__user=self.user, enrollment__course=self.course).first()
        self.assertIsNotNone(submission)
        self.assertIn(self.choice1, submission.choices.all())

        # Test exam result page
        result_url = reverse('onlinecourse:show_exam_result', args=[self.course.id, submission.id])
        res = self.client.get(result_url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Congratulations')
        self.assertContains(res, '100/100')

