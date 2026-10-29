from django.shortcuts import render
from django.http import HttpResponseRedirect
# Import models
from .models import Course, Enrollment, Question, Choice, Submission

from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)
# Create your views here.


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


# Helper method to collect selected choices from the exam form
def extract_answers(request):
    submitted_answers = []
    for key, value in request.POST.items():
        if key.startswith('choice'):
            try:
                submitted_answers.append(int(value))
            except ValueError:
                pass
    return submitted_answers


# Submit view to create an exam submission record
def submit(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user
    if not user.is_authenticated:
        return redirect('onlinecourse:login')

    enrollment = Enrollment.objects.filter(user=user, course=course).first()
    if not enrollment:
        enrollment = Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    submission = Submission.objects.create(enrollment=enrollment)
    selected_choice_ids = extract_answers(request)
    choices = Choice.objects.filter(id__in=selected_choice_ids)
    submission.choices.set(choices)

    return redirect('onlinecourse:show_exam_result', course_id=course.id, submission_id=submission.id)


# Exam result view to check if learner passed and show results
def show_exam_result(request, course_id, submission_id):
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(Submission, pk=submission_id)

    # Get questions for this course
    questions = course.question_set.all()
    if not questions.exists():
        questions = Question.objects.filter(lesson__course=course).distinct()

    total_score = 0
    total_possible_score = 0
    selected_choices = submission.choices.all()
    selected_choice_ids = list(selected_choices.values_list('id', flat=True))

    for question in questions:
        total_possible_score += question.grade
        if question.is_get_score(selected_choice_ids):
            total_score += question.grade

    if total_possible_score > 0:
        grade = round((total_score / total_possible_score) * 100, 1)
        if grade.is_integer():
            grade = int(grade)
    else:
        grade = 0

    context = {
        'course': course,
        'submission': submission,
        'grade': grade,
        'questions': questions,
        'selected_choices': selected_choices,
        'selected_ids': selected_choice_ids,
    }
    return render(request, 'onlinecourse/exam_result_bootstrap.html', context)




