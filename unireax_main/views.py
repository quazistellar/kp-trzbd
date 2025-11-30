import csv
import json
import os
import random
import string
import threading
import traceback
import pytz 
from datetime import datetime, timedelta
from io import StringIO
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.models import LogEntry
from django.contrib.auth import (
    authenticate, get_user_model, login, logout, update_session_auth_hash
)

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.db import connection, models, transaction

from django.db.models import (
    Avg, Case, Count, DecimalField, F, Func, IntegerField, Q, Sum, When
)

from django.db.models.functions import Cast
from django.http import HttpResponse, HttpResponseServerError, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST


from reportlab.lib import colors
from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
)

from .forms import (
    CodeVerificationForm, CourseForm, CourseSettingsForm, CourseTeacherForm,
    CustomSetPasswordForm, LectureForm, ListenerRegistrationForm,
    PasswordResetRequestForm, PracticalAssignmentForm, QuestionForm, RoleForm,
    TeacherMethodistRegistrationForm, TestForm, UserCourseForm, UserForm
)
from .models import (
    AnswerType, AssignmentStatus, AssignmentSubmissionFile, Certificate,
    ChoiceOption, Course, CourseCategory, CourseTeacher, CourseType, Feedback,
    Lecture, MatchingPair, PasswordResetCode, PracticalAssignment, Question,
    Review, Role, Test, TestResult, User, UserAnswer, UserCourse,
    UserMatchingAnswer, UserPracticalAssignment, UserSelectedChoice,
    ViewCourseLectures, ViewCoursePracticalAssignments, ViewCourseTests
)

from .payments import YookassaPayment

from .utils.additional_function import (
    add_to_favorites,  
    calculate_course_progress,
    download_receipt_response,
    generate_password,
    generate_username,
    get_favorite_courses,
    remove_from_favorites,  
)

from .utils.email_utils import (
    send_account_approved_email, send_account_rejected_email
)

User = get_user_model()



def test_500_error(request):
    return HttpResponseServerError("тестовая ошибка 500!!!!!")

def custom_403(request, exception=None):
    return render(request, '403.html', status=403)

def custom_404(request, exception=None):
    return render(request, '404.html', status=404)

def custom_500(request):
    return render(request, '500.html', status=500)

def custom_csrf_failure(request, reason=""):
    context = {'csrf_reason': reason}
    return render(request, 'csrf_failure.html', context, status=403)


def main(request):
    """"функция служит для отображения"""
    students_count = User.objects.filter(role__role_name='слушатель курсов').count()
    courses_count = Course.objects.filter(is_active=True).count()  

    courses = Course.objects.filter(is_active=True).annotate(  
        db_rating=Cast(
            Func(F('id'), function='calculate_course_rating'),
            output_field=DecimalField(max_digits=3, decimal_places=2)
        ),
        students_count=Count('usercourse')
    ).order_by('-db_rating', '-students_count')[:10]

    favorite_ids = get_favorite_courses(request)
    
    for course in courses:
        course.is_favorite = course.id in favorite_ids

    context = {
        'stats': {
            'students': students_count,
            'courses': courses_count,
        },
        'courses': courses,
    }

    return render(request, 'main.html', context)

def is_methodist_teacher(user):
    """проверка того, что пользователь - методист/преподаватель и подтверждён"""
    return user.is_authenticated and \
           hasattr(user, 'role') and \
           (user.role.role_name == 'методист' or user.role.role_name == 'преподаватель') and \
           hasattr(user, 'is_verified') and user.is_verified == True

def search_courses(request):
    """"функция поиска курсов"""
    query = request.GET.get('q', '')
    courses = Course.objects.filter(course_name__icontains=query)[:5]

    results = []
    for course in courses:
        results.append({
            'id': course.id,
            'name': course.course_name,
            'image': course.course_photo_path.url if course.course_photo_path else '',
            'url': f'/course/{course.id}/',
        })
    return JsonResponse(results, safe=False)


@require_POST
@csrf_exempt
def update_theme(request):
    """"функция обновления темы приложения"""
    if request.user.is_authenticated:
        try:
            data = json.loads(request.body)
            theme = data.get('theme')
            
            if theme in ['light', 'dark']:
                request.user.profile_theme = theme
                request.user.save()
                return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'error'}, status=400)


def auth_view(request):
    """представление для аутентификации пользователей"""
    if request.user.is_authenticated:
        return redirect('profile')

    if request.method == 'POST':
        email = request.POST.get('email')  
        password = request.POST.get('password')
        
        try:
            user = User.objects.get(email=email)
            user = authenticate(request, username=user.username, password=password)
        except User.DoesNotExist:
            user = None

        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'profile')
            return redirect(next_url)
        else:
            messages.error(request, 'Неверный email или пароль')
    
    return render(request, 'auth.html', {'next': request.GET.get('next', '')})


@login_required
def logout_view(request):
    """выход с очисткой куки-избранного"""
    response = redirect('auth')
    logout(request)
    response.delete_cookie('favorite_courses')
    return response


@login_required
def profile_view(request):
    user = request.user
    context = {'user': user}

    if request.method == 'POST':
        if 'profile_update' in request.POST:
            user.first_name = request.POST.get('first_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.patronymic = request.POST.get('patronymic', '')
            user.username = request.POST.get('username', '')
            user.email = request.POST.get('email', '')
            
            if hasattr(user, 'role') and user.role and user.role.role_name in ['преподаватель', 'методист']:
                user.position = request.POST.get('position', '')
                user.educational_institution = request.POST.get('educational_institution', '')

                if 'certificat_from_the_place_of_work_path' in request.FILES:
                    user.certificat_from_the_place_of_work_path = request.FILES['certificat_from_the_place_of_work_path']
            

            if not user.is_verified:
                user.is_verified = False
                messages.info(request, 'Данные обновлены. Аккаунт отправлен на повторную проверку администратором.')

            try:
                user.save()
                messages.success(request, 'Профиль успешно обновлен!')
                return redirect('profile')
            except Exception as e:
                messages.error(request, f'Ошибка при обновлении профиля: {str(e)}')

        elif 'password_change' in request.POST:
            old_password = request.POST.get('old_password')
            new_password1 = request.POST.get('new_password1')
            new_password2 = request.POST.get('new_password2')

            if user.check_password(old_password):
                if new_password1 == new_password2:
                    if len(new_password1) >= 8:
                        user.set_password(new_password1)
                        user.save()
                        update_session_auth_hash(request, user)
                        messages.success(request, 'Пароль успешно изменен!')
                        return redirect('profile')
                    else:
                        messages.error(request, 'Пароль должен содержать минимум 8 символов')
                else:
                    messages.error(request, 'Новые пароли не совпадают')
            else:
                messages.error(request, 'Неверный текущий пароль')


    if user.is_superuser or user.is_staff:
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        waiting_users = User.objects.filter(is_verified=False).count()
        total_courses = Course.objects.count()
        active_courses = Course.objects.filter(is_active=True).count()
        total_enrollments = UserCourse.objects.count()

        user_roles = User.objects.values('role__role_name').annotate(count=Count('id'))
        role_distribution = [
            {'name': role['role__role_name'], 'count': role['count']}
            for role in user_roles if role['role__role_name']
        ]

        today = timezone.now().date()
        week_activity = []

        for i in range(7):
            date = today - timedelta(days=6 - i)
            logins_count = User.objects.filter(last_login__date=date).count()
            enrollments_count = UserCourse.objects.filter(registration_date=date).count()

            week_activity.append({
                'date': date.strftime('%d.%m'),
                'logins_count': logins_count,
                'enrollments_count': enrollments_count,
            })

        max_logins = max([day['logins_count'] for day in week_activity] + [1])
        max_enrollments = max([day['enrollments_count'] for day in week_activity] + [1])

        for day in week_activity:
            day['logins_percent'] = (day['logins_count'] / max_logins) * 100
            day['enrollments_percent'] = (day['enrollments_count'] / max_enrollments) * 100

        thirty_days_ago = timezone.now().date() - timedelta(days=29)
        daily_activity_labels = []
        daily_activity_data = []

        for i in range(30):
            current_date = thirty_days_ago + timedelta(days=i)
            date_str = current_date.strftime('%d.%m')
            daily_activity_labels.append(date_str)

            activity_count = User.objects.filter(last_login__date=current_date).count()
            daily_activity_data.append(activity_count)

        course_stats = Course.objects.annotate(
            total_students=Count('usercourse')
        ).order_by('-total_students')[:5]

        course_stats_data = []
        for course in course_stats:
            completed_count = UserCourse.objects.filter(
                course=course,
                status_course=True
            ).count()

            course_stats_data.append({
                'course_name': course.course_name,
                'total_students': course.total_students,
                'completed_students': completed_count
            })

        popular_courses_qs = Course.objects.annotate(
            enrollment_count=Count('usercourse')
        ).order_by('-enrollment_count')[:5]

        popular_courses_list = [
            {
                'course_name': course.course_name,
                'enrollment_count': course.enrollment_count
            }
            for course in popular_courses_qs
        ]

        completed_courses_count = UserCourse.objects.filter(status_course=True).count()
        completion_rate = (completed_courses_count / max(total_enrollments, 1)) * 100

        context.update({
            'stats': {
                'total_users': total_users,
                'active_users': active_users,
                'total_courses': total_courses,
                'active_courses': active_courses,
                'waiting_users': waiting_users,
            },
            'role_distribution': role_distribution,
            'week_activity': week_activity,
            'analytics_data': {
                'daily_activity_labels': daily_activity_labels,
                'daily_activity_data': daily_activity_data,
                'course_stats': course_stats_data,
                'popular_courses': popular_courses_list, 
                'total_enrollments': total_enrollments,
                'completion_rate': round(completion_rate, 1),
            }
        })

    elif hasattr(user, 'role') and user.role and user.role.role_name == 'методист' and user.is_verified:
        metodist_courses = Course.objects.filter(created_by=user).annotate(
            student_count=Count('usercourse')
        )
        context['metodist_courses'] = metodist_courses

    elif hasattr(user, 'role') and user.role and user.role.role_name == 'преподаватель' and user.is_verified:
        teacher_courses = CourseTeacher.objects.filter(
            teacher=user,
            is_active=True
        ).select_related('course').annotate(
            student_count=Count('course__usercourse')
        )
        context['teacher_courses'] = teacher_courses

    elif hasattr(user, 'role') and user.role and user.role.role_name == 'слушатель курсов' and user.is_verified:
        student_courses = UserCourse.objects.filter(
            user=user,
            is_active=True
        ).select_related('course')
        
        for user_course in student_courses:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT calculate_course_completion(%s, %s)",
                        [user.id, user_course.course.id]
                    )
                    result = cursor.fetchone()
                    user_course.progress = float(result[0]) if result and result[0] else 0
            except Exception as e:
                user_course.progress = 0
        
        context['student_courses'] = student_courses

    return render(request, 'profile.html', context)



@login_required
def course_study_view(request, course_id):
    """Страница изучения курса"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    
    if not UserCourse.objects.filter(user=user, course=course, is_active=True).exists():
        messages.error(request, 'У вас нет доступа к этому курсу')
        return redirect('catalog')
    
    lectures = Lecture.objects.filter(course=course).order_by('lecture_order')
    practical_works = PracticalAssignment.objects.filter(lecture__course=course).order_by('lecture__lecture_order')
    tests = Test.objects.filter(lecture__course=course).order_by('lecture__lecture_order')
    
    test_last_results = {}
    for test in tests:
        last_result = TestResult.objects.filter(
            user=user, 
            test=test
        ).order_by('-attempt_number').first()
        
        if last_result:
            attempts_used = TestResult.objects.filter(user=user, test=test).count()
            attempts_remaining = test.max_attempts - attempts_used if test.max_attempts else None
            
            if test.grading_form == 'points':
                is_passed = last_result.final_score >= (test.passing_score or 0) if last_result.final_score is not None else False
                display_score = last_result.final_score
                display_status = 'Сдан' if is_passed else 'Не сдан'
            else:  
                is_passed = last_result.is_passed if last_result.is_passed is not None else False
                display_score = None
                display_status = 'Зачёт' if is_passed else 'Незачёт'
            
            test_last_results[test.id] = {
                'result': last_result,
                'attempts_remaining': max(attempts_remaining, 0) if attempts_remaining else 0,
                'is_passed': is_passed,
                'display_score': display_score,
                'display_status': display_status
            }
        else:
            test_last_results[test.id] = None

    progress = calculate_course_progress(user, course)
    
    user_assignments = UserPracticalAssignment.objects.filter(
        user=user,
        practical_assignment__lecture__course=course
    ).select_related('submission_status', 'practical_assignment')
    
    current_time = timezone.now()
    upcoming_deadlines = []
    for practical in practical_works:
        if practical.assignment_deadline and practical.assignment_deadline > current_time:
            upcoming_deadlines.append({
                'type': 'practical',
                'title': practical.practical_assignment_name,
                'lecture': f"Лекция {practical.lecture.lecture_order}",
                'deadline': practical.assignment_deadline
            })

    upcoming_deadlines.sort(key=lambda x: x['deadline'])
    upcoming_deadlines = upcoming_deadlines[:5]
    
    context = {
        'course': course,
        'lectures': lectures,
        'practical_works': practical_works,
        'tests': tests,
        'progress': progress,
        'user_assignments': user_assignments,
        'upcoming_deadlines': upcoming_deadlines,
        'current_time': current_time,
        'test_last_results': test_last_results,
    }
    
    return render(request, 'course_study.html', context)






@require_POST
@login_required
def exit_course(request, course_id):
    """Обработка выхода пользователя из курса (деактивация)"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    
    try:
        user_course = UserCourse.objects.get(user=user, course=course, is_active=True)
        
        user_course.is_active = False
        user_course.save()
        
        messages.success(request, f'Вы успешно вышли из курса "{course.course_name}". Ваш прогресс сохранён.')
        
        return JsonResponse({
            'success': True,
            'redirect_url': reverse('catalog')
        })
        
    except UserCourse.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Вы не записаны на этот курс или уже вышли из него'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Произошла ошибка при выходе из курса: {str(e)}'
        }, status=500)


@login_required
def lecture_detail_view(request, lecture_id):
    """Детальная страница лекции"""
    lecture = get_object_or_404(Lecture, id=lecture_id)
    user = request.user
    
    if not UserCourse.objects.filter(user=user, course=lecture.course, is_active=True).exists():
        messages.error(request, 'У вас нет доступа к этой лекции')
        return redirect('catalog')
    
    next_lecture = Lecture.objects.filter(
        course=lecture.course,
        lecture_order__gt=lecture.lecture_order,
        is_active=True
    ).order_by('lecture_order').first()
    
    prev_lecture = Lecture.objects.filter(
        course=lecture.course,
        lecture_order__lt=lecture.lecture_order,
        is_active=True
    ).order_by('-lecture_order').first()
    
    context = {
        'lecture': lecture,
        'next_lecture': next_lecture,
        'prev_lecture': prev_lecture,
    }
    
    return render(request, 'lecture_detail.html', context)

@login_required
def test_start_view(request, test_id):
    """Страница начала теста"""
    test = get_object_or_404(Test, id=test_id)
    user = request.user
    
    if not UserCourse.objects.filter(user=user, course=test.lecture.course, is_active=True).exists():
        messages.error(request, 'У вас нет доступа к этому тесту')
        return redirect('catalog')
    
    attempt_count = TestResult.objects.filter(user=user, test=test).count()
    if test.max_attempts and attempt_count >= test.max_attempts:
        messages.error(request, 'Вы исчерпали все попытки для этого теста')
        return redirect('course_study', course_id=test.lecture.course.id)
    
    questions = Question.objects.filter(test=test).select_related('answer_type').prefetch_related(
        'choiceoption_set', 'matchingpair_set'
    ).order_by('question_order')
    
    context = {
        'test': test,
        'questions': questions,
        'attempt_number': attempt_count + 1,
    }
    
    return render(request, 'test_start.html', context)

@login_required
def test_submit_view(request, test_id):
    """Обработка отправки теста с  обработкой ошибок"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Метод не разрешен'})
    
    test = get_object_or_404(Test, id=test_id)
    user = request.user
    
    try:
        print(f"Начало обработки теста {test_id} для пользователя {user.id}")
        
        data = json.loads(request.body)
        answers = data.get('answers', {})
        attempt_number = data.get('attempt_number', 1)

        print(f"Получены ответы для {len(answers)} вопросов")
        print(f"Номер попытки: {attempt_number}")

        if not UserCourse.objects.filter(user=user, course=test.lecture.course, is_active=True).exists():
            error_msg = f'Нет доступа к тесту'
            print(error_msg)
            return JsonResponse({'success': False, 'error': error_msg})
        
        attempt_count = TestResult.objects.filter(user=user, test=test).count()
        if test.max_attempts and attempt_count >= test.max_attempts:
            error_msg = f'Исчерпаны все попытки'
            print(error_msg)
            return JsonResponse({'success': False, 'error': error_msg})

        existing_result = TestResult.objects.filter(
            user=user, 
            test=test, 
            attempt_number=attempt_number
        ).first()
        
        if existing_result:
            print(f"Удаляем существующий результат попытки {attempt_number}")
            UserAnswer.objects.filter(
                user=user,
                question__test=test,
                attempt_number=attempt_number
            ).delete()
            existing_result.delete()
        
        total_score = save_user_answers(user, test, answers, attempt_number)
        max_score = calculate_max_score(test)
        
        print(f"Получено баллов: {total_score}, Максимум: {max_score}")

        is_passed = False
        if test.grading_form == 'points':
            is_passed = total_score >= (test.passing_score or 0)
            test_result = TestResult(
                user=user,
                test=test,
                attempt_number=attempt_number,
                final_score=total_score,
                is_passed=None  
            )
        else:  
            is_passed = total_score >= (max_score * 0.7)
            test_result = TestResult(
                user=user,
                test=test,
                attempt_number=attempt_number,
                final_score=None,  
                is_passed=is_passed
            )
        
        test_result.save()
        print(f"Результат теста сохранен: {test_result.id}")
        
        response_data = {
            'success': True,
            'score': total_score,
            'max_score': max_score,
            'passed': is_passed,
            'grading_form': test.grading_form,
            'passing_score': test.passing_score if test.grading_form == 'points' else None,
            'course_id': test.lecture.course.id
        }
        
        print(f"Успешный ответ: {response_data}")
        return JsonResponse(response_data)
        
    except json.JSONDecodeError as e:
        error_msg = f'Ошибка декодирования JSON: {str(e)}'
        print(error_msg)
        return JsonResponse({'success': False, 'error': error_msg})
    except Exception as e:
        error_msg = f'Неизвестная ошибка: {str(e)}'
        print(error_msg)
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'error': error_msg})
    
        
    except json.JSONDecodeError as e:
        error_msg = f'Ошибка декодирования JSON: {str(e)}'
        print(error_msg)
        return JsonResponse({'success': False, 'error': error_msg})
    except Exception as e:
        error_msg = f'Неизвестная ошибка: {str(e)}'
        print(error_msg)
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'error': error_msg})
        
    except json.JSONDecodeError as e:
        error_msg = f'Ошибка декодирования JSON: {str(e)}'
        print(error_msg)
        return JsonResponse({'success': False, 'error': error_msg})
    except Exception as e:
        error_msg = f'Неизвестная ошибка: {str(e)}'
        print(error_msg)
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'error': error_msg})
        
    except json.JSONDecodeError as e:
        error_msg = f'Ошибка декодирования JSON: {str(e)}'
        print(error_msg)
        return JsonResponse({'success': False, 'error': error_msg})
    except Exception as e:
        error_msg = f'Неизвестная ошибка: {str(e)}'
        print(error_msg)
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'error': error_msg})

def save_user_answers(user, test, answers, attempt_number):
    total_score = 0
    questions = Question.objects.filter(test=test).select_related('answer_type').prefetch_related(
        'choiceoption_set', 'matchingpair_set'
    )

    for question in questions:
        question_id_str = str(question.id)
        if question_id_str not in answers:
            continue

        user_answer_data = answers[question_id_str]
        score = 0

        user_answer, _ = UserAnswer.objects.get_or_create(
            user=user,
            question=question,
            attempt_number=attempt_number,
            defaults={'answer_text': None}
        )

        UserSelectedChoice.objects.filter(user_answer=user_answer).delete()
        UserMatchingAnswer.objects.filter(user_answer=user_answer).delete()

        try:
            if question.answer_type.answer_type_name == 'single_choice':
                score = check_single_choice_answer(question, user_answer_data, user_answer)
            elif question.answer_type.answer_type_name == 'multiple_choice':
                score = check_multiple_choice_answer(question, user_answer_data, user_answer)
            elif question.answer_type.answer_type_name == 'text_answer':
                score = check_text_answer(question, user_answer_data)
            elif question.answer_type.answer_type_name == 'matching':
                score = check_matching_answer(question, user_answer_data, user_answer)  
            user_answer.score = score
            user_answer.save()
            total_score += score
        except Exception as e:
            print(f"Ошибка при проверке вопроса {question.id}: {e}")

    return total_score

def check_single_choice_answer(question, user_answer, user_answer_obj):
    """Проверка одиночного выбора"""
    try:
        selected_option_id = int(user_answer)
        correct_option = question.choiceoption_set.filter(is_correct=True).first()
        
        if correct_option and correct_option.id == selected_option_id:
            UserSelectedChoice.objects.create(
                user_answer=user_answer_obj,
                choice_option_id=selected_option_id
            )
            return question.question_score
    except (ValueError, TypeError):
        pass
    return 0

def check_multiple_choice_answer(question, user_answer, user_answer_obj):
    """Проверка множественного выбора"""
    try:
        if not isinstance(user_answer, list):
            return 0
            
        selected_option_ids = [int(opt_id) for opt_id in user_answer]
        correct_options = set(question.choiceoption_set.filter(is_correct=True).values_list('id', flat=True))
        user_options = set(selected_option_ids)
        
        for option_id in selected_option_ids:
            UserSelectedChoice.objects.create(
                user_answer=user_answer_obj,
                choice_option_id=option_id
            )
        
        if correct_options == user_options:
            return question.question_score
    except (ValueError, TypeError):
        pass
    return 0

def check_text_answer(question, user_answer):
    """Проверка текстового ответа (упрощенная - всегда полный балл)"""
    if user_answer and len(str(user_answer).strip()) > 0:
        return question.question_score
    return 0

def check_matching_answer(question, user_answer, user_answer_obj):
    """Проверка сопоставлений — теперь реальная, а не заглушка"""
    if not isinstance(user_answer, dict):
        return 0

    correct_count = 0
    total_pairs = question.matchingpair_set.count()

    for field_name, selected_right_text in user_answer.items():
        try:
            pair_id = int(field_name.split('_')[-1])
            pair = question.matchingpair_set.get(id=pair_id)

            UserMatchingAnswer.objects.create(
                user_answer=user_answer_obj,
                matching_pair=pair,
                user_selected_right_text=selected_right_text
            )

            if selected_right_text.strip() == pair.right_text.strip():
                correct_count += 1
        except (ValueError, MatchingPair.DoesNotExist):
            continue

    return int((correct_count / total_pairs) * question.question_score) if total_pairs > 0 else 0

def calculate_max_score(test):
    """Подсчет максимального балла за тест"""
    result = Question.objects.filter(test=test).aggregate(
        total=Sum('question_score')
    )
    return result['total'] or 0

@login_required
def test_results_view(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    user = request.user

    if not UserCourse.objects.filter(user=user, course=course, is_active=True).exists():
        messages.error(request, 'У вас нет доступа к этому курсу')
        return redirect('catalog')

    test_results = TestResult.objects.filter(
        user=user,
        test__lecture__course=course
    ).select_related('test', 'test__lecture').order_by('-completion_date')

    passed_count = 0
    total_attempts = test_results.count()

    for result in test_results:
        if result.test.grading_form == 'points':
            if (result.final_score is not None or result.test.passing_score is None):
                continue
            if result.final_score >= result.test.passing_score:
                passed_count += 1
        elif result.test.grading_form == 'pass_fail':
            if result.is_passed is True:
                passed_count += 1

    success_rate = round(passed_count / total_attempts * 100, 1) if total_attempts > 0 else 0

    points_results = test_results.filter(test__grading_form='points', final_score__isnull=False)
    avg_score = points_results.aggregate(avg=Avg('final_score'))['avg']
    average_score = round(avg_score, 1) if avg_score is not None else 0

    context = {
        'course': course,
        'test_results': test_results,
        'total_attempts': total_attempts,
        'passed_count': passed_count,
        'success_rate': success_rate,
        'average_score': average_score,
    }
    return render(request, 'courses/test_results.html', context)

@login_required
def practical_submit_view(request, assignment_id):
    """Страница сдачи практической работы"""
    assignment = get_object_or_404(PracticalAssignment, id=assignment_id)
    user = request.user
    
    if not UserCourse.objects.filter(user=user, course=assignment.lecture.course, is_active=True).exists():
        messages.error(request, 'У вас нет доступа к этому заданию')
        return redirect('catalog')
    
    user_assignment = UserPracticalAssignment.objects.filter(
        user=user, 
        practical_assignment=assignment
    ).order_by('-attempt_number').first()
    
    feedback = None
    is_passed = False
    percentage = None
    min_score = None
    
    if user_assignment:
        try:
            feedback = Feedback.objects.get(user_practical_assignment=user_assignment)
            if assignment.grading_type == 'points' and assignment.max_score and feedback.score is not None:
                percentage = (feedback.score / assignment.max_score) * 100
                is_passed = percentage >= 50
                min_score = assignment.max_score * 0.5
            elif assignment.grading_type == 'pass_fail':
                is_passed = feedback.is_passed
        except Feedback.DoesNotExist:
            pass
    
    if request.method == 'POST':
        submitted_files = request.FILES.getlist('submission_files')
        comment = request.POST.get('comment', '')
        
        if not submitted_files:
            messages.error(request, 'Пожалуйста, прикрепите хотя бы один файл')
            return redirect('practical_submit', assignment_id=assignment_id)
        
        try:
            if user_assignment:
                attempt_number = user_assignment.attempt_number + 1
            else:
                attempt_number = 1
            
            checking_status = get_object_or_404(AssignmentStatus, assignment_status_name='на проверке')
            
            new_user_assignment = UserPracticalAssignment.objects.create(
                user=user,
                practical_assignment=assignment,
                submission_date=timezone.now(),
                submission_status=checking_status,
                attempt_number=attempt_number,
                comment=comment
            )
            
            files_saved = 0
            for uploaded_file in submitted_files:
                if uploaded_file.size > 50 * 1024 * 1024:  
                    messages.error(request, f'Файл {uploaded_file.name} слишком большой. Максимальный размер: 50 МБ')
                    new_user_assignment.delete()
                    return redirect('practical_submit', assignment_id=assignment_id)
                
                allowed_extensions = ['.pdf', '.doc', '.docx', '.zip']
                file_extension = os.path.splitext(uploaded_file.name)[1].lower()
                if file_extension not in allowed_extensions:
                    messages.error(request, f'Файл {uploaded_file.name} имеет неподдерживаемый формат')
                    new_user_assignment.delete()
                    return redirect('practical_submit', assignment_id=assignment_id)
                
                AssignmentSubmissionFile.objects.create(
                    user_assignment=new_user_assignment,
                    file=uploaded_file,
                    file_name=uploaded_file.name,
                    file_size=uploaded_file.size
                )
                files_saved += 1
            
            if files_saved == 0:
                new_user_assignment.delete()
                messages.error(request, 'Не удалось сохранить файлы. Попробуйте еще раз.')
                return redirect('practical_submit', assignment_id=assignment_id)
            
            messages.success(request, 'Работа успешно отправлена на проверку!')
            return redirect('practical_submit', assignment_id=assignment_id)
            
        except Exception as e:
            if 'new_user_assignment' in locals() and new_user_assignment.id:
                new_user_assignment.delete()
            messages.error(request, f'Произошла ошибка при отправке работы: {str(e)}')
    
    context = {
        'assignment': assignment,
        'current_time': timezone.now(),
        'user_assignment': user_assignment,
        'feedback': feedback,
        'is_passed': is_passed,
        'percentage': percentage,
        'min_score': min_score, 
    }
    
    return render(request, 'practical_submit.html', context)

@login_required
def student_statistics_view(request, course_id):
    """Статистика слушателя по курсу"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    
    if not UserCourse.objects.filter(user=user, course=course, is_active=True).exists():
        messages.error(request, 'У вас нет доступа к этому курсу')
        return redirect('catalog')
    
    progress = calculate_course_progress(user, course)
    
    test_results = TestResult.objects.filter(
        user=user,
        test__lecture__course=course
    )
    total_tests = Test.objects.filter(lecture__course=course, is_active=True).count()
    
    passed_tests = 0
    test_scores = []
    
    course_tests = Test.objects.filter(lecture__course=course, is_active=True)
    
    for test in course_tests:
        last_result = test_results.filter(test=test).order_by('-attempt_number').first()
        
        if last_result:
            if test.grading_form == 'points':
                is_passed = last_result.final_score >= (test.passing_score or 0) if last_result.final_score is not None else False
            else:  
                is_passed = last_result.is_passed if last_result.is_passed is not None else False
            
            if is_passed:
                passed_tests += 1
            
            if last_result.final_score is not None:
                test_scores.append(last_result.final_score)
    
    practicals = PracticalAssignment.objects.filter(lecture__course=course, is_active=True)
    total_practicals = practicals.count()
    completed_practicals = 0
    practical_scores = []
    
    for practical in practicals:
        user_assignments = UserPracticalAssignment.objects.filter(
            user=user, 
            practical_assignment=practical
        )
        for assignment in user_assignments:
            try:
                feedback = Feedback.objects.get(user_practical_assignment=assignment)
                if feedback.is_passed or (feedback.score and practical.max_score and feedback.score >= practical.max_score * 0.6):
                    completed_practicals += 1
                    if feedback.score:
                        practical_scores.append(feedback.score)
                    break
            except Feedback.DoesNotExist:
                continue
    
    avg_test_score = sum(test_scores) / len(test_scores) if test_scores else 0
    avg_practical_score = sum(practical_scores) / len(practical_scores) if practical_scores else 0
    
    context = {
        'course': course,
        'progress': progress,
        'total_tests': total_tests,
        'passed_tests': passed_tests,
        'total_practicals': total_practicals,
        'completed_practicals': completed_practicals,
        'avg_test_score': avg_test_score,
        'avg_practical_score': avg_practical_score,
        'test_results_count': test_results.count(),
    }
    
    return render(request, 'student_statistics.html', context)

@login_required
def graded_assignments_view(request, course_id):
    """Страница с оцененными практическими работами"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    
    all_statuses = AssignmentStatus.objects.all()
    print("Все статусы в системе:", list(all_statuses.values_list('assignment_status_name', flat=True)))
    
    if not UserCourse.objects.filter(user=user, course=course, is_active=True).exists():
        messages.error(request, 'У вас нет доступа к этому курсу')
        return redirect('catalog')
    
    try:
        completed_status = AssignmentStatus.objects.get(assignment_status_name='завершен')
        print("Найден статус 'завершен':", completed_status.id)
    except AssignmentStatus.DoesNotExist:
        alternative_names = ['завершено', 'проверено', 'оценено', 'completed', 'finished']
        for name in alternative_names:
            try:
                completed_status = AssignmentStatus.objects.get(assignment_status_name=name)
                print(f"Найден альтернативный статус '{name}':", completed_status.id)
                break
            except AssignmentStatus.DoesNotExist:
                continue
        else:
            messages.error(request, 'Не найден статус для завершенных работ')
            return redirect('course_study', course_id=course_id)
    
    all_user_assignments = UserPracticalAssignment.objects.filter(
        user=user,
        practical_assignment__lecture__course=course
    ).select_related('practical_assignment', 'practical_assignment__lecture', 'submission_status')
    
    print(f"Всего работ пользователя по курсу: {all_user_assignments.count()}")
    for assignment in all_user_assignments:
        print(f"Работа: {assignment.practical_assignment.practical_assignment_name}, "
              f"Статус: {assignment.submission_status.assignment_status_name}")
    
    user_assignments = all_user_assignments.filter(
        submission_status=completed_status
    )
    print(f"Завершенных работ: {user_assignments.count()}")
    
    graded_assignments = []
    for assignment in user_assignments:
        try:
            feedback = Feedback.objects.get(user_practical_assignment=assignment)
            
            percentage = None
            if (assignment.practical_assignment.grading_type == 'points' and 
                assignment.practical_assignment.max_score and 
                feedback.score is not None):
                percentage = (feedback.score / assignment.practical_assignment.max_score) * 100
            
            graded_assignments.append({
                'assignment': assignment,
                'feedback': feedback,
                'practical': assignment.practical_assignment,
                'percentage': percentage 
            })
            print(f"Найдена обратная связь для работы: {assignment.practical_assignment.practical_assignment_name}, "
                  f"Оценка: {feedback.score}/{assignment.practical_assignment.max_score}, "
                  f"Процент: {percentage}")
        except Feedback.DoesNotExist:
            print(f"Нет обратной связи для работы: {assignment.practical_assignment.practical_assignment_name}")
            continue
    
    print(f"Итого оцененных работ: {len(graded_assignments)}")
    
    graded_assignments.sort(key=lambda x: x['assignment'].submission_date or timezone.now(), reverse=True)
    
    context = {
        'course': course,
        'graded_assignments': graded_assignments,
    }
    
    return render(request, 'graded_assignments.html', context)

@login_required 
def all_test_results_view(request, course_id):
    """Все результаты тестов пользователя по курсу"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    
    if not UserCourse.objects.filter(user=user, course=course, is_active=True).exists():
        messages.error(request, 'У вас нет доступа к этому курсу')
        return redirect('catalog')
    
    test_results = TestResult.objects.filter(
        user=user,
        test__lecture__course=course
    ).select_related('test', 'test__lecture').order_by('-completion_date')
    
    tests_with_results = {}
    for result in test_results:
        test_id = result.test.id
        if test_id not in tests_with_results:
            tests_with_results[test_id] = {
                'test': result.test,
                'results': [],
                'best_score': 0,
                'best_attempt': None
            }
        
        tests_with_results[test_id]['results'].append(result)
        
        if result.final_score and result.final_score > tests_with_results[test_id]['best_score']:
            tests_with_results[test_id]['best_score'] = result.final_score
            tests_with_results[test_id]['best_attempt'] = result
    
    context = {
        'course': course,
        'tests_with_results': tests_with_results.values(),
        'total_attempts': test_results.count(),
    }
    
    return render(request, 'all_test_results.html', context)


def register_certificate_fonts():
    """регистрация шрифтов Arial Black для сертификата с поддержкой кириллицы"""
    fonts_loaded = False
    
    font_paths = [
        os.path.join(settings.BASE_DIR, 'static', 'fonts', 'arial_black.ttf'),
        os.path.join(settings.BASE_DIR, 'static', 'fonts', 'Arial Black.ttf'),
        os.path.join(settings.BASE_DIR, 'static', 'fonts', 'arial-black.ttf'),
        os.path.join(settings.BASE_DIR, 'static', 'fonts', 'arial.ttf'),  
        '/usr/share/fonts/truetype/msttcorefonts/arialbd.ttf',  
        '/Windows/Fonts/arialbd.ttf', 
        'C:/Windows/Fonts/arialbd.ttf',  
    ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('Arial-Black', font_path))
                fonts_loaded = True
                break
            except Exception as e:
                continue
    
    if not fonts_loaded:
        try:
            pdfmetrics.registerFont(TTFont('Arial-Black', 'arialbd'))
        except:
            pass
    
    return fonts_loaded

CERTIFICATE_FONTS_LOADED = register_certificate_fonts()

def get_certificate_font(font_name='regular'):
    """Получение имени шрифта для сертификата"""
    font_names = pdfmetrics.getRegisteredFontNames()
    
    if 'Arial-Black' in font_names:
        return 'Arial-Black'
    elif 'Arial-Bold' in font_names:
        return 'Arial-Bold'
    elif 'Arial' in font_names:
        return 'Arial'
    else:
        return 'Helvetica-Bold'

@login_required
def check_certificate_eligibility(request, course_id):
    """Проверка возможности получения сертификата"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    
    if not UserCourse.objects.filter(user=user, course=course, is_active=True).exists():
        return JsonResponse({'eligible': False, 'error': 'Вы не записаны на этот курс'})
    
    progress = calculate_course_progress(user, course)
    
    user_course = UserCourse.objects.get(user=user, course=course)
    existing_certificate = Certificate.objects.filter(user_course=user_course).first()
    has_certificate = existing_certificate is not None
    
    eligible = (
        progress >= 100 and 
        course.has_certificate and 
        user_course.status_course and 
        not has_certificate and
        course.is_completed
    )
    
    return JsonResponse({
        'eligible': eligible,
        'progress': progress,
        'has_certificate': has_certificate,
        'certificate_id': existing_certificate.id if existing_certificate else None,
        'course_has_certificate': course.has_certificate,
        'course_completed': user_course.status_course,
        'course_is_completed': course.is_completed,
        'error': None if eligible else get_eligibility_error(progress, course, user_course, has_certificate)
    })

def get_eligibility_error(progress, course, user_course, has_certificate):
    """Получить текст ошибки о невозможности получения сертификата"""
    if progress < 100:
        return f'Для получения сертификата необходимо завершить курс на 100% (текущий прогресс: {progress}%)'
    elif not course.has_certificate:
        return 'Для этого курса не предусмотрены сертификаты'
    elif not user_course.status_course:
        return 'Курс не завершен'
    elif has_certificate:
        return 'Сертификат уже получен'
    elif not course.is_completed:
        return 'Сертификат будет доступен после окончательного завершения курса и прекращения добавления новых материалов'
    else:
        return 'Неизвестная ошибка'

@login_required
def generate_certificate(request, course_id):
    """Генерация сертификата"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    
    if not UserCourse.objects.filter(user=user, course=course, is_active=True).exists():
        messages.error(request, 'Вы не записаны на этот курс')
        return redirect('course_study', course_id=course_id)
    
    progress = calculate_course_progress(user, course)
    user_course = UserCourse.objects.get(user=user, course=course)
    
    if progress < 100:
        messages.error(request, f'Для получения сертификата необходимо завершить курс на 100% (текущий прогресс: {progress}%)')
        return redirect('course_study', course_id=course_id)
    
    if not course.has_certificate:
        messages.error(request, 'Для этого курса не предусмотрены сертификаты')
        return redirect('course_study', course_id=course_id)
    
    if not user_course.status_course:
        messages.error(request, 'Курс не завершен')
        return redirect('course_study', course_id=course_id)
    
    if not course.is_completed:
        messages.error(request, 'Сертификат будет доступен после окончательного завершения курса и прекращения добавления новых материалов')
        return redirect('course_study', course_id=course_id)
    
    existing_certificate = Certificate.objects.filter(user_course=user_course).first()
    if existing_certificate:
        messages.info(request, 'Сертификат уже выдан')
        return redirect('certificate_detail', certificate_id=existing_certificate.id)
    
    try:
        certificate = Certificate.objects.create(
            user_course=user_course,
            issue_date=timezone.now().date()
        )
        
        pdf_path = generate_certificate_pdf(certificate)
        certificate.certificate_file_path = pdf_path
        certificate.save()
        
        messages.success(request, 'Сертификат успешно сгенерирован!')
        return redirect('certificate_detail', certificate_id=certificate.id)
        
    except Exception as e:
        messages.error(request, f'Ошибка при генерации сертификата: {str(e)}')
        return redirect('course_study', course_id=course_id)

def generate_certificate_pdf(certificate):
    """PDF сертификата — финальная версия: весь нижний блок поднят выше, как на предпросмотре"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas
    import os

    cert_dir = os.path.join(settings.MEDIA_ROOT, 'certificates')
    os.makedirs(cert_dir, exist_ok=True)
    
    filename = f"certificate_{certificate.certificate_number}.pdf"
    filepath = os.path.join(cert_dir, filename)
    
    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4

    purple = colors.HexColor('#7B7FD5')
    dark   = colors.HexColor('#2c3e50')
    gray   = colors.HexColor('#555555')

    font = get_certificate_font()  

    c.setFillColor(colors.white)
    c.rect(0, 0, width, height, fill=1, stroke=0)
    c.setStrokeColor(purple)
    c.setLineWidth(3)
    c.rect(30, 30, width-60, height-60, stroke=1, fill=0)

    y = height - 110

    c.setFont(font, 40)
    c.setFillColor(purple)
    c.drawCentredString(width/2, y, "UNIREAX")
    y -= 65

    c.setFont(font, 32)
    c.setFillColor(dark)
    c.drawCentredString(width/2, y, "СЕРТИФИКАТ")
    y -= 80

    c.setFont(font, 16)
    c.setFillColor(gray)
    c.drawCentredString(width/2, y, "Настоящим удостоверяется, что")
    y -= 70

    full_name = f"{certificate.user_course.user.last_name.upper()} {certificate.user_course.user.first_name.upper()}"
    if certificate.user_course.user.patronymic:
        full_name += f" {certificate.user_course.user.patronymic.upper()}"

    c.setFont(font, 32)
    c.setFillColor(purple)
    name_lines = _wrap_text(c, full_name, font, 32, width - 120)
    for line in name_lines:
        c.drawCentredString(width/2, y, line)
        y -= 40
    y -= 35

    c.setFont(font, 16)
    c.setFillColor(gray)
    c.drawCentredString(width/2, y, "успешно завершил(а) курс")
    y -= 55

    course_name = certificate.user_course.course.course_name.upper()
    c.setFont(font, 24)
    c.setFillColor(dark)
    course_lines = _wrap_text(c, course_name, font, 24, width - 100)
    for line in course_lines:
        c.drawCentredString(width/2, y, line)
        y -= 38
    y -= 30  

    c.setFont(font, 13)
    c.setFillColor(gray)
    c.drawCentredString(width/2, y, f"Продолжительность: {certificate.user_course.course.course_hours} часов")
    y -= 28
    c.drawCentredString(width/2, y, f"Дата выдачи: {certificate.issue_date.strftime('%d.%m.%Y')}")
    y -= 28
    c.drawCentredString(width/2, y, f"№ {certificate.certificate_number}")
    y -= 80 

    signature_y = y

    signature_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'write.png')
    if os.path.exists(signature_path):
        c.drawImage(
            signature_path,
            width/2 - 130,
            signature_y + 1,
            width=260,
            height=80,
            preserveAspectRatio=True,
            mask='auto'
        )
        line_y = signature_y + 8
        c.setStrokeColor(colors.HexColor('#333333'))
        c.setLineWidth(1.2)
        c.line(width/2 - 130, line_y, width/2 + 130, line_y)
    else:
        line_y = signature_y + 25
        c.setStrokeColor(colors.HexColor('#333333'))
        c.setLineWidth(1.2)
        c.line(width/2 - 130, line_y, width/2 + 130, line_y)

    c.setFont(font, 16)
    c.setFillColor(colors.HexColor('#333333'))
    c.drawCentredString(width/2, signature_y - 28, "Директор UNIREAX")

    c.save()
    return f'certificates/{filename}'

def _wrap_text(canvas, text, font_name, font_size, max_width):
    """Разбивает текст на строки с переносом по словам"""
    canvas.setFont(font_name, font_size)
    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = f"{current} {word}".strip() if current else word
        if canvas.stringWidth(test, font_name, font_size) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines

@login_required
def certificate_detail(request, certificate_id):
    """Страница просмотра сертификата"""
    certificate = get_object_or_404(Certificate, id=certificate_id)
    
    if certificate.user_course.user != request.user and not request.user.is_admin:
        messages.error(request, 'У вас нет доступа к этому сертификату')
        return redirect('profile')
    
    context = {
        'certificate': certificate,
    }
    
    return render(request, 'certificate_detail.html', context)

@login_required
def download_certificate(request, certificate_id):
    """Скачивание сертификата"""
    certificate = get_object_or_404(Certificate, id=certificate_id)
    
    if certificate.user_course.user != request.user and not request.user.is_admin:
        messages.error(request, 'У вас нет доступа к этому сертификату')
        return redirect('profile')
    
    if not certificate.certificate_file_path:
        try:
            pdf_path = generate_certificate_pdf(certificate)
            certificate.certificate_file_path = pdf_path
            certificate.save()
        except Exception as e:
            messages.error(request, f'Ошибка при генерации сертификата: {str(e)}')
            return redirect('certificate_detail', certificate_id=certificate_id)
    
    file_path = os.path.join(settings.MEDIA_ROOT, certificate.certificate_file_path)
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="certificate_{certificate.certificate_number}.pdf"'
            return response
    else:
        messages.error(request, 'Файл сертификата не найден на сервере')
        return redirect('certificate_detail', certificate_id=certificate_id)

@login_required
def my_certificates(request):
    """Страница со всеми сертификатами пользователя"""
    user_courses = UserCourse.objects.filter(user=request.user, is_active=True)
    certificates = Certificate.objects.filter(
        user_course__in=user_courses
    ).select_related('user_course', 'user_course__course')
    
    eligible_courses = []
    for user_course in user_courses:
        if (user_course.course.has_certificate and 
            user_course.status_course and
            not Certificate.objects.filter(user_course=user_course).exists()):
            
            progress = calculate_course_progress(request.user, user_course.course)
            if progress >= 100:
                eligible_courses.append({
                    'course': user_course.course,
                    'user_course': user_course,
                    'progress': progress
                })
    
    context = {
        'certificates': certificates,
        'eligible_courses': eligible_courses,
    }
    
    return render(request, 'my_certificates.html', context)


def forgot_password_view(request):
    return render(request, 'forgot_password.html')


def teacher_methodist_view(request):
    return render(request, 'teacher_methodist.html')


def site_policy(request):
    return render(request, 'policies/site_policy.html')


def privacy_notice(request):
    return render(request, 'policies/privacy_notice.html')


def cookies_policy(request):
    return render(request, 'policies/cookies_policy.html')

class FeedbackEmailThread(threading.Thread):
    """Поток для асинхронной отправки email с обратной связью"""
    def __init__(self, subject, message, recipient_list, html_message=None):
        self.subject = subject
        self.message = message
        self.recipient_list = recipient_list
        self.html_message = html_message
        threading.Thread.__init__(self)

    def run(self):
        send_mail(
            self.subject,
            self.message,
            settings.DEFAULT_FROM_EMAIL,
            self.recipient_list,
            html_message=self.html_message,
            fail_silently=False,
        )

def send_feedback_email(name, email, message):
    subject = f'Обратная связь от {name} - Unireax'
    
    html_message = render_to_string('emails/feedback_email.html', {
        'name': name,
        'email': email,
        'message': message,
        'date': timezone.now().strftime('%d.%m.%Y %H:%M'),
        'site_name': 'UNIREAX'
    })
    
    text_message = f"""
Обратная связь от пользователя - Unireax

Имя: {name}
Email: {email}
Дата: {timezone.now().strftime('%d.%m.%Y %H:%M')}

Сообщение:
{message}

---
Это письмо отправлено автоматически через форму обратной связи на сайте Unireax.
"""
    
    try:
        FeedbackEmailThread(
            subject=subject,
            message=text_message,
            recipient_list=[settings.DEFAULT_FROM_EMAIL],
            html_message=html_message
        ).start()
        return True
    except Exception as e:
        print(f"Ошибка отправки email: {e}")
        return False

def about_us(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        message = request.POST.get('message', '').strip()
        
        if not name or not email or not message:
            messages.error(request, 'Все поля обязательны для заполнения')
            return render(request, 'about_us.html')
        
        if len(message) < 10:
            messages.error(request, 'Сообщение должно содержать не менее 10 символов')
            return render(request, 'about_us.html')
        
        if send_feedback_email(name, email, message):
            messages.success(request, 'Ваше сообщение успешно отправлено! Мы ответим вам в ближайшее время.')
        else:
            messages.error(request, 'Произошла ошибка при отправке сообщения. Пожалуйста, попробуйте позже.')
        
        return redirect('about_us')
    
    return render(request, 'about_us.html')



def catalog(request):
    courses = Course.objects.annotate(
        db_rating=Cast(
            Func(F('id'), function='calculate_course_rating'),
            output_field=DecimalField(max_digits=3, decimal_places=2)
        )
    ).filter(is_active=True)

    query = request.GET.get('q', '')
    if query:
        courses = courses.filter(Q(course_name__icontains=query) | Q(course_description__icontains=query))

    category_id = request.GET.get('category')
    if category_id:
        courses = courses.filter(course_category_id=category_id)

    type_id = request.GET.get('type')
    if type_id:
        courses = courses.filter(course_type_id=type_id)

    price_min = request.GET.get('price_min')
    if price_min:
        courses = courses.filter(course_price__gte=price_min)

    price_max = request.GET.get('price_max')
    if price_max:
        courses = courses.filter(course_price__lte=price_max)

    has_cert = request.GET.get('has_cert')
    if has_cert == 'yes':
        courses = courses.filter(has_certificate=True)
    elif has_cert == 'no':
        courses = courses.filter(has_certificate=False)

    free_only = request.GET.get('free_only')
    if free_only == 'yes':
        courses = courses.filter(Q(course_price=0) | Q(course_price__isnull=True))

    sort = request.GET.get('sort', '')
    if sort == 'name_asc':
        courses = courses.order_by('course_name')
    elif sort == 'name_desc':
        courses = courses.order_by('-course_name')
    elif sort == 'price_asc':
        courses = courses.order_by('course_price')
    elif sort == 'price_desc':
        courses = courses.order_by('-course_price')
    elif sort == 'rating_desc':
        courses = courses.order_by('-db_rating')
    elif sort == 'hours_asc':
        courses = courses.order_by('course_hours')
    elif sort == 'hours_desc':
        courses = courses.order_by('-course_hours')

    categories = CourseCategory.objects.all()
    types = CourseType.objects.all()

    context = {
        'courses': courses,
        'categories': categories,
        'types': types,
        'current_query': query,
        'current_category': category_id,
        'current_type': type_id,
        'current_price_min': price_min,
        'current_price_max': price_max,
        'current_has_cert': has_cert,
        'current_free_only': free_only,
        'current_sort': sort,
    }

    favorite_ids = get_favorite_courses(request)
    for course in courses:
        course.is_favorite = course.id in favorite_ids

    return render(request, 'catalog.html', context)

@login_required
def return_to_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    try:
        user_course = UserCourse.objects.get(user=request.user, course=course)
        
        if user_course.is_active:
            messages.info(request, 'Вы уже записаны на этот курс.')
            return redirect('course_enroll_detail', course_id=course_id)
        else:
            user_course.is_active = True
            user_course.save()
            messages.success(request, 'Вы снова записаны на курс! Добро пожаловать обратно!')
            return redirect('course_enroll_detail', course_id=course_id)
            
    except UserCourse.DoesNotExist:
        messages.error(request, 'Запись на курс не найдена.')
        return redirect('course_enroll_detail', course_id=course_id)

def course_enroll_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    rating = course.rating
    reviews = Review.objects.filter(course=course)
    teachers = CourseTeacher.objects.filter(course=course)
    lectures = Lecture.objects.filter(course=course).order_by('lecture_order')
    
    students_in_course_count = UserCourse.objects.filter(course=course, is_active=True).count()

    enrolled = False
    was_enrolled_before = False
    completion_percentage = 0
    
    if request.user.is_authenticated:
        active_enrollment = UserCourse.objects.filter(
            user=request.user, 
            course=course, 
            is_active=True
        ).first()
        
        any_enrollment = UserCourse.objects.filter(
            user=request.user, 
            course=course
        ).first()
        
        enrolled = active_enrollment is not None
        was_enrolled_before = any_enrollment is not None and not enrolled
        
        if enrolled:
            completion_percentage = course.get_completion(request.user.id)

    context = {
        'course': course,
        'rating': rating,
        'reviews': reviews,
        'teachers': teachers,
        'lectures': lectures,
        'enrolled': enrolled,
        'was_enrolled_before': was_enrolled_before,
        'completion_percentage': completion_percentage,
        'students_in_course_count': students_in_course_count, 
    }

    favorite_ids = get_favorite_courses(request)
    course.is_favorite = course.id in favorite_ids

    return render(request, 'course_enroll_detail.html', context)

@login_required
def enroll_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    try:
        user_course = UserCourse.objects.get(user=request.user, course=course)
        
        if user_course.is_active:
            messages.info(request, 'Вы уже записаны на этот курс.')
            return redirect('course_enroll_detail', course_id=course_id)
        else:
            user_course.is_active = True
            user_course.registration_date = timezone.now().date()
            user_course.save()
            messages.success(request, 'Вы снова записаны на курс! Добро пожаловать обратно!')
            return redirect('course_enroll_detail', course_id=course_id)
            
    except UserCourse.DoesNotExist:
        pass
    
    if course.course_max_places and course.course_max_places > 0:
        enrolled_count = UserCourse.objects.filter(course=course, is_active=True).count()
        if enrolled_count >= course.course_max_places:
            messages.error(request, 'На этот курс нет свободных мест.')
            return redirect('course_enroll_detail', course_id=course_id)
    
    try:
        user_course = UserCourse(
            user=request.user,
            course=course,
            course_price=course.course_price,
            status_course=False,
            is_active=True,
            registration_date=timezone.now().date()
        )
        user_course.save()
        
        messages.success(request, 'Вы успешно записались на курс!')
        return redirect('course_enroll_detail', course_id=course_id)
    
    except Exception as e:
        messages.error(request, f'Произошла ошибка при записи на курс: {str(e)}')
        return redirect('course_enroll_detail', course_id=course_id)

@login_required
def create_payment(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    if UserCourse.objects.filter(user=request.user, course=course).exists():
        messages.error(request, 'Вы уже записаны на этот курс.')
        return redirect('course_enroll_detail', course_id=course_id)
    
    if course.course_price <= 0:
        messages.error(request, 'Этот курс бесплатный.')
        return redirect('course_enroll_detail', course_id=course_id)
    
    try:
        payment_processor = YookassaPayment()
        return_url = request.build_absolute_uri(f'/course/{course_id}/payment/success/')
        
        payment = payment_processor.create_payment(course, request.user, return_url)
        
        request.session['yookassa_payment_id'] = payment.id
        request.session['payment_course_id'] = course_id
        
        return redirect(payment.confirmation.confirmation_url)
        
    except Exception as e:
        messages.error(request, f'Ошибка при создании платежа: {str(e)}')
        return redirect('course_enroll_detail', course_id=course_id)
    

@login_required
def download_receipt(request, course_id, payment_id):
    course = get_object_or_404(Course, id=course_id)
    user = request.user

    user_course = get_object_or_404(
        UserCourse,
        user=user,
        course=course,
        payment_date__isnull=False
    )

    desired_tz = pytz.timezone(timezone.get_current_timezone_name()) 
    local_payment_date = user_course.payment_date.astimezone(desired_tz)


    payment_data = {
        'payment_id': payment_id,
        'payment_date': local_payment_date, 
        'course_name': course.course_name,
        'course_category': course.course_category.course_category_name,
        'course_type': course.course_type.course_type_name,
        'course_hours': course.course_hours,
        'user_name': f"{request.user.last_name} {request.user.first_name}",
        'user_email': request.user.email,
        'amount': str(course.course_price),
    }

    return download_receipt_response(payment_data)


@login_required
def payment_success(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    payment_id = request.session.get('yookassa_payment_id')
    
    if payment_id:
        try:
            payment_processor = YookassaPayment()
            payment_status = payment_processor.check_payment_status(payment_id)
            
            if payment_status == 'succeeded':
                success = payment_processor.process_successful_payment(payment_id)
                
                if success:
                    if 'yookassa_payment_id' in request.session:
                        del request.session['yookassa_payment_id']
                    if 'payment_course_id' in request.session:
                        del request.session['payment_course_id']
                    
                    user_course = UserCourse.objects.get(user=request.user, course=course)
                    
                    return render(request, 'payment_success.html', {
                        'course': course,
                        'payment_id': payment_id,
                        'user_course': user_course
                    })
                else:
                    messages.error(request, 'Ошибка при записи на курс после оплаты.')
            else:
                messages.warning(request, f'Статус платежа: {payment_status}')
                
        except Exception as e:
            messages.error(request, f'Ошибка при подтверждении платежа: {str(e)}')
    
    return redirect('course_enroll_detail', course_id=course_id)

@login_required
def payment_cancel(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    
    if 'yookassa_payment_id' in request.session:
        del request.session['yookassa_payment_id']
    if 'payment_course_id' in request.session:
        del request.session['payment_course_id']
    
    messages.info(request, 'Оплата отменена.')
    return redirect('course_enroll_detail', course_id=course_id)

@csrf_exempt
def yookassa_webhook(request):
    if request.method == 'POST':
        try:
            event_json = json.loads(request.body)
            
            if event_json.get('event') == 'payment.succeeded':
                payment_id = event_json['object']['id']
                payment_processor = YookassaPayment()
                payment_processor.process_successful_payment(payment_id)
            
            return HttpResponse(status=200)
            
        except Exception as e:
            return HttpResponse(status=400)
    
    return HttpResponse(status=405)

@login_required
def submit_review(request, course_id):
    if request.method == 'POST':
        course = get_object_or_404(Course, id=course_id)
        
        if not UserCourse.objects.filter(user=request.user, course=course).exists():
            messages.error(request, 'Вы не записаны на этот курс.')
            return redirect('course_enroll_detail', course_id=course_id)
        
        completion_percentage = course.get_completion(request.user.id)
        if completion_percentage < 50:
            messages.error(request, 'Вы можете оставить отзыв только после завершения 50% курса.')
            return redirect('course_enroll_detail', course_id=course_id)
        
        if Review.objects.filter(user=request.user, course=course).exists():
            messages.error(request, 'Вы уже оставляли отзыв на этот курс.')
            return redirect('course_enroll_detail', course_id=course_id)
        
        rating = request.POST.get('rating')
        review_text = request.POST.get('review_text')
        
        if not rating or not review_text:
            messages.error(request, 'Пожалуйста, заполните все поля.')
            return redirect('course_enroll_detail', course_id=course_id)
        
        try:
            review = Review(
                course=course,
                user=request.user,
                review_text=review_text,
                rating=int(rating)
            )
            review.save()
            
            messages.success(request, 'Ваш отзыв успешно добавлен!')
            return redirect('course_enroll_detail', course_id=course_id)
        
        except Exception as e:
            messages.error(request, f'Произошла ошибка при добавлении отзыва: {str(e)}')
            return redirect('course_enroll_detail', course_id=course_id)
    
    return redirect('course_enroll_detail', course_id=course_id)


@login_required
def submit_review(request, course_id):
    if request.method == 'POST':
        course = get_object_or_404(Course, id=course_id)
        
        if not UserCourse.objects.filter(user=request.user, course=course).exists():
            messages.error(request, 'Вы не записаны на этот курс.')
            return redirect('course_enroll_detail', course_id=course_id)
        
        completion_percentage = course.get_completion(request.user.id)
        if completion_percentage < 50:
            messages.error(request, 'Вы можете оставить отзыв только после завершения 50% курса.')
            return redirect('course_enroll_detail', course_id=course_id)
        
        if Review.objects.filter(user=request.user, course=course).exists():
            messages.error(request, 'Вы уже оставляли отзыв на этот курс.')
            return redirect('course_enroll_detail', course_id=course_id)
        
        rating = request.POST.get('rating')
        review_text = request.POST.get('review_text')
        
        if not rating or not review_text:
            messages.error(request, 'Пожалуйста, заполните все поля.')
            return redirect('course_enroll_detail', course_id=course_id)
        
        try:
            review = Review(
                course=course,
                user=request.user,
                review_text=review_text,
                rating=int(rating)
            )
            review.save()
            
            messages.success(request, 'Ваш отзыв успешно добавлен!')
            return redirect('course_enroll_detail', course_id=course_id)
        
        except Exception as e:
            messages.error(request, f'Произошла ошибка при добавлении отзыва: {str(e)}')
            return redirect('course_enroll_detail', course_id=course_id)
    
    return redirect('course_enroll_detail', course_id=course_id)



@login_required
def admin_panel(request):
    return render(request, 'admin/admin_page.html')


@login_required
def logs_page(request):
    """Отображает страницу с логами с фильтрацией и сортировкой."""
    logs_list = LogEntry.objects.all()

    logs_list = logs_list.exclude(
        Q(change_message__startswith='[{"added":') |
        Q(change_message__startswith='[{"changed":') |
        Q(change_message__startswith='[{"deleted":') |
        Q(change_message='')
    ).exclude(
        Q(content_type__app_label='sessions') |
        Q(content_type__app_label='admin', content_type__model='logentry')
    )

    action_filter = request.GET.get('action_filter')
    if action_filter and action_filter != 'all':
        logs_list = logs_list.filter(action_flag=action_filter)

    time_sort = request.GET.get('time_sort')
    if time_sort == 'oldest':
        logs_list = logs_list.order_by('action_time')
    else:
        logs_list = logs_list.order_by('-action_time')

    date_filter = request.GET.get('date_filter')
    if date_filter:
        try:
            date_obj = timezone.datetime.strptime(date_filter, '%Y-%m-%d').date()
            logs_list = logs_list.filter(action_time__date=date_obj)
        except ValueError:
            pass
    
    paginator = Paginator(logs_list, 10)
    page_number = request.GET.get('page')
    logs = paginator.get_page(page_number)

    return render(request, 'admin/logs_page.html', {
        'logs': logs,
        'action_filter': action_filter,
        'time_sort': time_sort,
        'date_filter': date_filter,
    })


def is_admin(user):
    """Проверка, является ли пользователь администратором"""
    return user.is_authenticated and user.is_admin


@user_passes_test(is_admin)
def user_list(request):
    """Список всех пользователей с фильтрацией и поиском"""
    users = User.objects.all().select_related('role')
    
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(username__icontains=search_query)
        )

    role_filter = request.GET.get('role_filter', '')
    if role_filter:
        users = users.filter(role_id=role_filter)

    verified_filter = request.GET.get('verified_filter', '')
    if verified_filter == 'verified':
        users = users.filter(is_verified=True)
    elif verified_filter == 'not_verified':
        users = users.filter(is_verified=False)

    roles = Role.objects.all()

    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'users': page_obj,
        'roles': roles,
        'search_query': search_query,
        'role_filter': role_filter,
        'verified_filter': verified_filter,
    }

    return render(request, 'admin/users/user_list.html', context)


@user_passes_test(is_admin)
def user_detail(request, user_id):
    """Детальная информация о пользователе"""
    user_obj = get_object_or_404(User, id=user_id)

    context = {
        'user_obj': user_obj,
    }

    return render(request, 'admin/users/user_detail.html', context)


@user_passes_test(is_admin)
def create_update_user(request, user_id=None):
    """Создание или обновление пользователя"""
    user_obj = None
    if user_id:
        user_obj = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES, instance=user_obj)
        if form.is_valid():
            try:
                user = form.save()
                action = "обновлен" if user_id else "создан"
                messages.success(request, f"Пользователь {user.last_name} {user.first_name} успешно {action}.")
                return redirect('user_detail', user_id=user.id)
            except Exception as e:
                messages.error(request, f"Произошла ошибка при сохранении: {str(e)}")
    else:
        form = UserForm(instance=user_obj)

    context = {
        'user_obj': user_obj,
        'form': form,
    }

    return render(request, 'admin/users/create_update_user.html', context)


@user_passes_test(is_admin)
@login_required
def delete_user(request, user_id):
    """Удаление пользователя"""
    user_obj = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        try:
            user_name = f"{user_obj.last_name} {user_obj.first_name}"
            user_obj.delete()
            messages.success(request, f"Пользователь {user_name} успешно удален.")
            return redirect('user_list')
        except Exception as e:
            messages.error(request, f"Произошла ошибка при удалении пользователя: {str(e)}")
            return redirect('user_detail', user_id=user_id)

    context = {
        'user_obj': user_obj,
    }

    return render(request, 'admin/users/delete_user.html', context)


def can_manage_courses(user):
    """Проверка, может ли пользователь управлять курсами"""
    return user.is_authenticated and (user.is_admin or user.is_staff)

@user_passes_test(can_manage_courses)
def course_list(request):
    """Список всех курсов с фильтрацией и поиском"""
    courses = Course.objects.all().select_related('course_category', 'course_type', 'created_by')

    search_query = request.GET.get('search', '')
    if search_query:
        courses = courses.filter(
            Q(course_name__icontains=search_query) |
            Q(course_description__icontains=search_query) |
            Q(code_room__icontains=search_query)
        )

    category_filter = request.GET.get('category_filter', '')
    if category_filter:
        courses = courses.filter(course_category_id=category_filter)

    type_filter = request.GET.get('type_filter', '')
    if type_filter:
        courses = courses.filter(course_type_id=type_filter)

    active_filter = request.GET.get('active_filter', '')
    if active_filter == 'active':
        courses = courses.filter(is_active=True)
    elif active_filter == 'inactive':
        courses = courses.filter(is_active=False)

    categories = CourseCategory.objects.all()
    types = CourseType.objects.all()

    paginator = Paginator(courses, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'courses': page_obj,
        'categories': categories,
        'types': types,
        'search_query': search_query,
        'category_filter': category_filter,
        'type_filter': type_filter,
        'active_filter': active_filter,
    }

    return render(request, 'admin/courses/course_list.html', context)


@user_passes_test(can_manage_courses)
def course_detail(request, course_id):
    """Детальная информация о курсе"""
    course = get_object_or_404(Course, id=course_id)

    context = {
        'course': course,
    }

    return render(request, 'admin/courses/course_detail.html', context)


@user_passes_test(can_manage_courses)
def create_update_course(request, course_id=None):
    """Создание или обновление курса"""
    course_obj = None
    if course_id:
        course_obj = get_object_or_404(Course, id=course_id)

    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course_obj)
        if form.is_valid():
            try:
                course = form.save()
                action = "обновлен" if course_id else "создан"
                messages.success(request, f"Курс '{course.course_name}' успешно {action}.")
                return redirect('course_detail', course_id=course.id)
            except Exception as e:
                messages.error(request, f"Произошла ошибка при сохранении: {str(e)}")
    else:
        form = CourseForm(instance=course_obj)

    context = {
        'course_obj': course_obj,
        'form': form,
    }

    return render(request, 'admin/courses/create_update_course.html', context)


@user_passes_test(can_manage_courses)
def delete_course(request, course_id):
    """Удаление курса"""
    course_obj = get_object_or_404(Course, id=course_id)

    if request.method == 'POST':
        try:
            course_name = course_obj.course_name
            course_obj.delete()
            messages.success(request, f"Курс '{course_name}' успешно удален.")
            return redirect('course_list')
        except Exception as e:
            messages.error(request, f"Произошла ошибка при удалении курса: {str(e)}")
            return redirect('course_detail', course_id=course_id)

    context = {
        'course_obj': course_obj,
    }

    return render(request, 'admin/courses/delete_course.html', context)

@user_passes_test(is_admin)
def role_list(request):
    """Список всех ролей с фильтрацией и поиском"""
    roles = Role.objects.all()

    search_query = request.GET.get('search', '')
    if search_query:
        roles = roles.filter(role_name__icontains=search_query)

    paginator = Paginator(roles, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'roles': page_obj,
        'search_query': search_query,
    }

    return render(request, 'admin/roles/role_list.html', context)


@user_passes_test(is_admin)
def role_detail(request, role_id):
    """Детальная информация о роли"""
    role_obj = get_object_or_404(Role, id=role_id)

    users_count = User.objects.filter(role=role_obj).count()

    context = {
        'role_obj': role_obj,
        'users_count': users_count,
    }

    return render(request, 'admin/roles/role_detail.html', context)


@user_passes_test(is_admin)
def create_update_role(request, role_id=None):
    """Создание или обновление роли"""
    role_obj = None
    if role_id:
        role_obj = get_object_or_404(Role, id=role_id)

    if request.method == 'POST':
        form = RoleForm(request.POST, instance=role_obj)
        if form.is_valid():
            try:
                role = form.save()
                action = "обновлена" if role_id else "создана"
                messages.success(request, f"Роль '{role.role_name}' успешно {action}.")
                return redirect('role_detail', role_id=role.id)
            except Exception as e:
                messages.error(request, f"Произошла ошибка при сохранении: {str(e)}")
    else:
        form = RoleForm(instance=role_obj)

    context = {
        'role_obj': role_obj,
        'form': form,
    }

    return render(request, 'admin/roles/create_update_role.html', context)


@user_passes_test(is_admin)
def delete_role(request, role_id):
    """Удаление роли"""
    role_obj = get_object_or_404(Role, id=role_id)

    users_with_role = User.objects.filter(role=role_obj).exists()

    if request.method == 'POST':
        try:
            role_name = role_obj.role_name
            role_obj.delete()
            messages.success(request, f"Роль '{role_name}' успешно удалена.")
            return redirect('role_list')
        except Exception as e:
            messages.error(request, f"Произошла ошибка при удалении роли: {str(e)}")
            return redirect('role_detail', role_id=role_id)

    context = {
        'role_obj': role_obj,
        'users_with_role': users_with_role,
    }

    return render(request, 'admin/roles/delete_role.html', context)


@user_passes_test(can_manage_courses)
def user_course_list(request):
    """Список всех записей слушателей на курсы"""
    user_courses = UserCourse.objects.all().select_related('user', 'course', 'user__role')

    search_query = request.GET.get('search', '')
    if search_query:
        user_courses = user_courses.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__patronymic__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(course__course_name__icontains=search_query)
        )

    course_filter = request.GET.get('course_filter', '')
    if course_filter:
        user_courses = user_courses.filter(course_id=course_filter)

    status_filter = request.GET.get('status_filter', '')
    if status_filter == 'active':
        user_courses = user_courses.filter(is_active=True)
    elif status_filter == 'inactive':
        user_courses = user_courses.filter(is_active=False)

    completion_filter = request.GET.get('completion_filter', '')
    if completion_filter == 'completed':
        user_courses = user_courses.filter(status_course=True)
    elif completion_filter == 'not_completed':
        user_courses = user_courses.filter(status_course=False)

    courses = Course.objects.all()

    paginator = Paginator(user_courses, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'user_courses': page_obj,
        'courses': courses,
        'search_query': search_query,
        'course_filter': course_filter,
        'status_filter': status_filter,
        'completion_filter': completion_filter,
    }

    return render(request, 'admin/user_courses/user_course_list.html', context)


@user_passes_test(can_manage_courses)
def user_course_detail(request, user_course_id):
    """Детальная информация о записи слушателя на курс"""
    user_course_obj = get_object_or_404(UserCourse, id=user_course_id)

    context = {
        'user_course_obj': user_course_obj,
    }

    return render(request, 'admin/user_courses/user_course_detail.html', context)


@user_passes_test(can_manage_courses)
def create_update_user_course(request, user_course_id=None):
    """Создание или обновление записи слушателя на курс"""
    user_course_obj = None
    if user_course_id:
        user_course_obj = get_object_or_404(UserCourse, id=user_course_id)

    listeners = User.objects.filter(role__role_name='слушатель курсов')
    courses = Course.objects.all()

    if request.method == 'POST':
        user_id = request.POST.get('user')
        course_id = request.POST.get('course')
        registration_date = request.POST.get('registration_date')
        payment_date = request.POST.get('payment_date')
        completion_date = request.POST.get('completion_date')
        course_price = request.POST.get('course_price')
        status_course = request.POST.get('status_course') == 'on'
        is_active = request.POST.get('is_active') == 'on'

        errors = []

        if not user_id:
            errors.append("Поле 'Пользователь' обязательно для заполнения.")
        if not course_id:
            errors.append("Поле 'Курс' обязательно для заполнения.")

        if user_id and course_id:
            existing = UserCourse.objects.filter(user_id=user_id, course_id=course_id)
            if user_course_obj:
                existing = existing.exclude(id=user_course_obj.id)

            if existing.exists():
                errors.append("Этот пользователь уже записан на данный курс.")

        if not errors:
            try:
                if user_course_obj:
                    user_course = user_course_obj
                else:
                    user_course = UserCourse()

                user_course.user_id = user_id
                user_course.course_id = course_id
                user_course.status_course = status_course
                user_course.is_active = is_active

                if registration_date:
                    user_course.registration_date = registration_date
                elif not user_course_obj:
                    user_course.registration_date = timezone.now().date()

                if payment_date:
                    user_course.payment_date = payment_date

                if completion_date:
                    user_course.completion_date = completion_date

                if course_price:
                    user_course.course_price = course_price
                elif not user_course_obj:
                    course = Course.objects.get(id=course_id)
                    user_course.course_price = course.course_price

                user_course.save()

                action = "обновлена" if user_course_id else "создана"
                messages.success(request, f"Запись пользователя на курс успешно {action}.")
                return redirect('user_course_detail', user_course_id=user_course.id)

            except Exception as e:
                errors.append(f"Произошла ошибка при сохранении: {str(e)}")

        context = {
            'user_course_obj': user_course_obj,
            'listeners': listeners,
            'courses': courses,
            'errors': errors,
            'form': {
                'user': {'value': user_id},
                'course': {'value': course_id},
                'registration_date': {'value': registration_date},
                'payment_date': {'value': payment_date},
                'completion_date': {'value': completion_date},
                'course_price': {'value': course_price},
                'status_course': {'value': status_course},
                'is_active': {'value': is_active},
            }
        }

        return render(request, 'admin/user_courses/create_update_user_course.html', context)

    else:
        form_data = {}
        if user_course_obj:
            form_data = {
                'user': {'value': user_course_obj.user_id},
                'course': {'value': user_course_obj.course_id},
                'registration_date': {'value': user_course_obj.registration_date},
                'payment_date': {'value': user_course_obj.payment_date},
                'completion_date': {'value': user_course_obj.completion_date},
                'course_price': {'value': user_course_obj.course_price},
                'status_course': {'value': user_course_obj.status_course},
                'is_active': {'value': user_course_obj.is_active},
            }

        context = {
            'user_course_obj': user_course_obj,
            'listeners': listeners,
            'courses': courses,
            'form': form_data,
            'errors': [],
        }

        return render(request, 'admin/user_courses/create_update_user_course.html', context)


@user_passes_test(can_manage_courses)
def delete_user_course(request, user_course_id):
    """Удаление записи слушателя на курс"""
    user_course_obj = get_object_or_404(UserCourse, id=user_course_id)

    if request.method == 'POST':
        try:
            user_name = f"{user_course_obj.user.last_name} {user_course_obj.user.first_name}"
            course_name = user_course_obj.course.course_name
            user_course_obj.delete()
            messages.success(request, f"Запись пользователя {user_name} на курс '{course_name}' успешно удалена.")
            return redirect('user_course_list')
        except Exception as e:
            messages.error(request, f"Произошла ошибка при удалении записи: {str(e)}")
            return redirect('user_course_detail', user_course_id=user_course_id)

    context = {
        'user_course_obj': user_course_obj,
    }

    return render(request, 'admin/user_courses/delete_user_course.html', context)


@user_passes_test(can_manage_courses)
def course_teacher_list(request):
    """Список всех назначений преподавателей на курсы"""
    course_teachers = CourseTeacher.objects.all().select_related('teacher', 'course', 'teacher__role')

    search_query = request.GET.get('search', '')
    if search_query:
        course_teachers = course_teachers.filter(
            Q(teacher__first_name__icontains=search_query) |
            Q(teacher__last_name__icontains=search_query) |
            Q(teacher__email__icontains=search_query) |
            Q(course__course_name__icontains=search_query)
        )

    course_filter = request.GET.get('course_filter', '')
    if course_filter:
        course_teachers = course_teachers.filter(course_id=course_filter)

    status_filter = request.GET.get('status_filter', '')
    if status_filter == 'active':
        course_teachers = course_teachers.filter(is_active=True)
    elif status_filter == 'inactive':
        course_teachers = course_teachers.filter(is_active=False)

    courses = Course.objects.all()

    paginator = Paginator(course_teachers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'course_teachers': page_obj,
        'courses': courses,
        'search_query': search_query,
        'course_filter': course_filter,
        'status_filter': status_filter,
    }

    return render(request, 'admin/course_teachers/course_teacher_list.html', context)


@user_passes_test(can_manage_courses)
def course_teacher_detail(request, course_teacher_id):
    """Детальная информация о назначении преподавателя на курс"""
    course_teacher_obj = get_object_or_404(CourseTeacher, id=course_teacher_id)

    context = {
        'course_teacher_obj': course_teacher_obj,
    }

    return render(request, 'admin/course_teachers/course_teacher_detail.html', context)



@user_passes_test(can_manage_courses)
def create_update_course_teacher(request, course_teacher_id=None):
    """Создание или обновление назначения преподавателя на курс"""
    course_teacher_obj = None
    if course_teacher_id:
        course_teacher_obj = get_object_or_404(CourseTeacher, id=course_teacher_id)

    if request.method == 'POST':
        form = CourseTeacherForm(request.POST, instance=course_teacher_obj)
        if form.is_valid():
            try:
                course_teacher = form.save(commit=False)

                if course_teacher.start_date is None:
                    course_teacher.start_date = timezone.now().date()

                course_teacher.save()

                action = "обновлено" if course_teacher_id else "создано"
                messages.success(request, f"Назначение преподавателя на курс успешно {action}.")
                return redirect('course_teacher_detail', course_teacher_id=course_teacher.id)
            except Exception as e:
                messages.error(request, f"Произошла ошибка при сохранении: {str(e)}")
    else:
        initial_data = {}
        if not course_teacher_obj:
            initial_data['start_date'] = timezone.now().date() 
        
        form = CourseTeacherForm(instance=course_teacher_obj, initial=initial_data)

    context = {
        'course_teacher_obj': course_teacher_obj,
        'form': form,
    }

    return render(request, 'admin/course_teachers/create_update_course_teacher.html', context)


@user_passes_test(can_manage_courses)
def delete_course_teacher(request, course_teacher_id):
    """Удаление назначения преподавателя на курс"""
    course_teacher_obj = get_object_or_404(CourseTeacher, id=course_teacher_id)

    if request.method == 'POST':
        try:
            teacher_name = f"{course_teacher_obj.teacher.last_name} {course_teacher_obj.teacher.first_name}"
            course_name = course_teacher_obj.course.course_name
            course_teacher_obj.delete()
            messages.success(request, f"Назначение преподавателя {teacher_name} на курс '{course_name}' успешно удалено.")
            return redirect('course_teacher_list')
        except Exception as e:
            messages.error(request, f"Произошла ошибка при удалении назначения: {str(e)}")
            return redirect('course_teacher_detail', course_teacher_id=course_teacher_id)

    context = {
        'course_teacher_obj': course_teacher_obj,
    }

    return render(request, 'admin/course_teachers/delete_course_teacher.html', context)


def register_teacher_methodist(request):
    """View для регистрации преподавателя/методиста."""
    if request.user.is_authenticated:
        return redirect('profile')

    if request.method == 'POST':
        form = TeacherMethodistRegistrationForm(request.POST, request.FILES)
        
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно! Ваш аккаунт будет активирован после проверки документов.')
            return redirect('profile')
    else:
        form = TeacherMethodistRegistrationForm()

    return render(request, 'registration_teacher_methodist.html', {'form': form})


def register_listener(request):
    """View для регистрации слушателя."""
    if request.user.is_authenticated:
        return redirect('profile')

    if request.method == 'POST':
        form = ListenerRegistrationForm(request.POST)
        
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect('profile')
    else:
        form = ListenerRegistrationForm()

    return render(request, 'registration_listener.html', {'form': form})


def is_methodist(user):
    """Проверка, что пользователь - методист и подтверждён"""
    return user.is_authenticated and \
           hasattr(user, 'role') and user.role.role_name == 'методист' and \
           hasattr(user, 'is_verified') and user.is_verified == True

@user_passes_test(is_methodist)
def methodist_dashboard(request):
    """Дашборд методиста"""
    courses = Course.objects.filter(created_by=request.user, is_active=True)
    
    total_lectures = Lecture.objects.filter(course__created_by=request.user).count()
    total_tests = Test.objects.filter(lecture__course__created_by=request.user).count()
    total_assignments = PracticalAssignment.objects.filter(lecture__course__created_by=request.user).count()
    
    context = {
        'courses': courses,
        'total_lectures': total_lectures,
        'total_tests': total_tests,
        'total_assignments': total_assignments,
    }
    return render(request, 'methodist/dashboard.html', context)

@user_passes_test(is_methodist)
def create_course(request):
    """Создание нового курса"""
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save(commit=False)
            course.created_by = request.user
            course.is_active = True
            course.save()
            messages.success(request, f'Курс "{course.course_name}" успешно создан!')
            return redirect('methodist_course_constructor', course_id=course.id)
        else:
            messages.error(request, 'Ошибка при создании курса. Проверьте поля.')
    else:
        form = CourseForm()

    categories = CourseCategory.objects.all()
    course_types = CourseType.objects.all()
    
    context = {
        'form': form,
        'categories': categories,
        'course_types': course_types,
    }
    return render(request, 'methodist/create_course.html', context)

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q

@user_passes_test(is_methodist_teacher)
def course_constructor_main(request, course_id):
    """Главная страница конструктора курса"""

    is_request_user_teacher = False
    if hasattr(request.user, 'role') and request.user.role.role_name == 'преподаватель':
        is_request_user_teacher = True

    if is_request_user_teacher:
        course = get_object_or_404(
            Course, 
            Q(created_by=request.user) | Q(created_by__isnull=True), 
            id=course_id                                          
        )
    else:
        course = get_object_or_404(Course, id=course_id, created_by=request.user)
    
    lectures = Lecture.objects.filter(course=course).order_by('lecture_order')
    tests = Test.objects.filter(lecture__course=course).select_related('lecture')
    practical_assignments = PracticalAssignment.objects.filter(lecture__course=course).select_related('lecture')
    total_questions = Question.objects.filter(test__lecture__course=course).count()
    
    context = {
        'course': course,
        'lectures': lectures,
        'tests': tests,
        'practical_assignments': practical_assignments,
        'total_questions': total_questions,
    }
    return render(request, 'methodist/course_constructor/main.html', context)





@user_passes_test(is_methodist_teacher)
def lecture_management(request, course_id):
    """Управление лекциями"""

    is_request_user_teacher = False
    if hasattr(request.user, 'role') and request.user.role.role_name == 'преподаватель':
        is_request_user_teacher = True

    if is_request_user_teacher:

        course = get_object_or_404(
            Course, 
            Q(created_by=request.user) | Q(created_by__isnull=True), 
            id=course_id                                            
        )
    else:
        course = get_object_or_404(Course, id=course_id, created_by=request.user)
  
    
    lectures = Lecture.objects.filter(course=course).order_by('lecture_order')
    
    next_order = 1
    if lectures.exists():
        next_order = lectures.last().lecture_order + 1
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_lecture':
            form = LectureForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    with transaction.atomic():
                        lecture = form.save(commit=False)
                        lecture.course = course
                        lecture.lecture_order = form.cleaned_data.get('lecture_order', next_order)
                        lecture.is_active = True  
                        lecture.save()
                        messages.success(request, 'Лекция успешно добавлена!')
                except Exception as e:
                    messages.error(request, f'Ошибка при добавлении лекции: {str(e)}')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
        
        elif action == 'update_lecture':
            lecture_id = request.POST.get('lecture_id')
            lecture = get_object_or_404(Lecture, id=lecture_id, course=course)
            form = LectureForm(request.POST, request.FILES, instance=lecture)
            if form.is_valid():
                try:
                    form.save()
                    messages.success(request, 'Лекция успешно обновлена!')
                except Exception as e:
                    messages.error(request, f'Ошибка при обновлении лекции: {str(e)}')
            else:
                messages.error(request, 'Ошибка при обновлении лекции. Проверьте поля.')
        
        elif action == 'delete_lecture':
            lecture_id = request.POST.get('lecture_id')
            lecture = get_object_or_404(Lecture, id=lecture_id, course=course)
            lecture_name = lecture.lecture_name
            
            has_tests = Test.objects.filter(lecture=lecture).exists()
            has_assignments = PracticalAssignment.objects.filter(lecture=lecture).exists()
            
            if has_tests or has_assignments:
                messages.error(request, f'Нельзя удалить лекцию "{lecture_name}", так как к ней привязаны тесты или задания!')
            else:
                lecture.delete()
                messages.success(request, f'Лекция "{lecture_name}" удалена!')
        
        return redirect('methodist_lecture_management', course_id=course_id)
    
    lectures_with_documents = lectures.filter(lecture_document_path__isnull=False).count()
    
    context = {
        'course': course,
        'lectures': lectures,
        'next_order': next_order,
        'lectures_with_documents': lectures_with_documents,
    }
    return render(request, 'methodist/course_constructor/lecture_management.html', context)




@user_passes_test(is_methodist_teacher)
def test_constructor(request, course_id):
    """Конструктор тестов - список тестов"""

    is_request_user_teacher = False
    if hasattr(request.user, 'role') and request.user.role.role_name == 'преподаватель':
        is_request_user_teacher = True

 
    if is_request_user_teacher:

        course = get_object_or_404(
            Course, 
            Q(created_by=request.user) | Q(created_by__isnull=True), 
            id=course_id                                       
        )
    else:
        course = get_object_or_404(Course, id=course_id, created_by=request.user)
    lectures = Lecture.objects.filter(course=course, is_active=True).order_by('lecture_order')
    tests = Test.objects.filter(lecture__course=course).select_related('lecture').prefetch_related('question_set')
    
    final_tests_count = tests.filter(is_final=True).count()
    points_tests_count = tests.filter(grading_form='points').count()
    
    context = {
        'course': course,
        'lectures': lectures,
        'tests': tests,
        'final_tests_count': final_tests_count,
        'points_tests_count': points_tests_count,
    }
    return render(request, 'methodist/course_constructor/test_constructor.html', context)



@user_passes_test(is_methodist_teacher)
@require_POST
def create_test(request, course_id):
    """Создание нового теста"""
    
    is_request_user_teacher = False
    if hasattr(request.user, 'role') and request.user.role.role_name == 'преподаватель':
        is_request_user_teacher = True

    if is_request_user_teacher:
        course = get_object_or_404(
            Course, 
            Q(created_by=request.user) | Q(created_by__isnull=True), 
            id=course_id                                            
        )
    else:
        course = get_object_or_404(Course, id=course_id, created_by=request.user)
    
    form = TestForm(request.POST, course_id=course_id)
    
    if form.is_valid():
        try:
            with transaction.atomic():
                test = form.save(commit=False)
                test.lecture = form.cleaned_data['lecture']
                test.is_active = True  
                test.save()
                messages.success(request, f'Тест "{test.test_name}" успешно создан!')
                return redirect('methodist_test_editor', course_id=course_id, test_id=test.id)
        except Exception as e:
            messages.error(request, f'Ошибка при создании теста: {str(e)}')
    else:
        messages.error(request, 'Ошибка при создании теста. Проверьте поля.')
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
    
    return redirect('methodist_test_constructor', course_id=course_id)


@user_passes_test(is_methodist_teacher)
def test_editor(request, course_id, test_id):
    """Редактор теста с вопросами"""
    
    is_request_user_teacher = False
    if hasattr(request.user, 'role') and request.user.role.role_name == 'преподаватель':
        is_request_user_teacher = True

    if is_request_user_teacher:
        course = get_object_or_404(
            Course, 
            Q(created_by=request.user) | Q(created_by__isnull=True), 
            id=course_id                                            
        )
    else:
        course = get_object_or_404(Course, id=course_id, created_by=request.user)
    
    test = get_object_or_404(Test, id=test_id, lecture__course=course)
    questions = Question.objects.filter(test=test).order_by('question_order').prefetch_related(
        'choiceoption_set', 'matchingpair_set'
    )
    answer_types = AnswerType.objects.all()

    if not answer_types.exists():
        messages.warning(request, 'Типы ответов не найдены!')

    answer_types_with_russian = [
        {'id': 1, 'name': 'Один или несколько вариантов ответа'},
        {'id': 3, 'name': 'Краткий текстовый ответ'},
        {'id': 4, 'name': 'Развернутый текстовый ответ'},
        {'id': 5, 'name': 'Сопоставление'},
    ]

    total_score = sum(question.question_score for question in questions)
    choice_questions_count = questions.filter(answer_type__answer_type_name__icontains='choice').count()
    matching_questions_count = questions.filter(answer_type__answer_type_name__icontains='matching').count()
    text_questions_count = questions.filter(answer_type__answer_type_name__icontains='text').count()

    context = {
        'course': course,
        'test': test,
        'questions': questions,
        'answer_types': answer_types_with_russian,  
        'total_score': total_score,
        'choice_questions_count': choice_questions_count,
        'matching_questions_count': matching_questions_count,
        'text_questions_count': text_questions_count,
    }
    return render(request, 'methodist/course_constructor/test_editor.html', context)


@user_passes_test(is_methodist_teacher)
@require_POST
def add_question(request, course_id, test_id):
    """Добавление вопроса к тесту"""
    
    is_request_user_teacher = False
    if hasattr(request.user, 'role') and request.user.role.role_name == 'преподаватель':
        is_request_user_teacher = True

    if is_request_user_teacher:
        course = get_object_or_404(
            Course, 
            Q(created_by=request.user) | Q(created_by__isnull=True), 
            id=course_id                                            
        )
    else:
        course = get_object_or_404(Course, id=course_id, created_by=request.user)
    
    test = get_object_or_404(Test, id=test_id, lecture__course=course)

    try:
        with transaction.atomic():
            question_text = request.POST.get('question_text', '').strip()
            answer_type_id = request.POST.get('answer_type')
            
            question_score_str = request.POST.get('question_score', '1')
            try:
                question_score = int(question_score_str)
                if question_score < 1:
                    question_score = 1
            except (ValueError, TypeError):
                question_score = 1
            
            if not question_text:
                messages.error(request, 'Введите текст вопроса')
                return redirect('methodist_test_editor', course_id=course_id, test_id=test_id)
            
            if not answer_type_id:
                messages.error(request, 'Выберите тип ответа')
                return redirect('methodist_test_editor', course_id=course_id, test_id=test_id)

            try:
                answer_type = AnswerType.objects.get(id=int(answer_type_id))
            except (AnswerType.DoesNotExist, ValueError):
                messages.error(request, 'Выбран неверный тип ответа')
                return redirect('methodist_test_editor', course_id=course_id, test_id=test_id)

            type_name = answer_type.answer_type_name.lower()

            last_question = Question.objects.filter(test=test).order_by('-question_order').first()
            question_order = last_question.question_order + 1 if last_question else 1

            question = Question.objects.create(
                test=test,
                question_text=question_text,
                answer_type=answer_type,
                question_score=question_score,
                question_order=question_order
            )

            if 'single_choice' in type_name:
                option_texts = request.POST.getlist('option_text')
                is_corrects = request.POST.getlist('is_correct')
                
                valid_options = [text.strip() for text in option_texts if text.strip()]
                if len(valid_options) < 2:
                    question.delete()
                    messages.error(request, 'Добавьте хотя бы 2 варианта ответа')
                    return redirect('methodist_test_editor', course_id=course_id, test_id=test_id)
                
                correct_count = is_corrects.count('on')
                if correct_count != 1:
                    question.delete()
                    messages.error(request, 'Для вопроса с одиночным выбором должен быть ровно один правильный вариант')
                    return redirect('methodist_test_editor', course_id=course_id, test_id=test_id)
                
                for i, option_text in enumerate(option_texts):
                    if option_text.strip(): 
                        is_correct = i < len(is_corrects) and is_corrects[i] == 'on'
                        ChoiceOption.objects.create(
                            question=question,
                            option_text=option_text.strip(),
                            is_correct=is_correct
                        )

            elif 'multiple_choice' in type_name:
                option_texts = request.POST.getlist('option_text')
                is_corrects = request.POST.getlist('is_correct')
                
                valid_options = [text.strip() for text in option_texts if text.strip()]
                if len(valid_options) < 2:
                    question.delete()
                    messages.error(request, 'Добавьте хотя бы 2 варианта ответа')
                    return redirect('methodist_test_editor', course_id=course_id, test_id=test_id)
                
                correct_count = is_corrects.count('on')
                if correct_count < 1:
                    question.delete()
                    messages.error(request, 'Для вопроса с множественным выбором должен быть хотя бы один правильный вариант')
                    return redirect('methodist_test_editor', course_id=course_id, test_id=test_id)
                
                for i, option_text in enumerate(option_texts):
                    if option_text.strip(): 
                        is_correct = i < len(is_corrects) and is_corrects[i] == 'on'
                        ChoiceOption.objects.create(
                            question=question,
                            option_text=option_text.strip(),
                            is_correct=is_correct
                        )

            elif 'matching' in type_name:
                left_texts = request.POST.getlist('left_text')
                right_texts = request.POST.getlist('right_text')
                
                valid_pairs = []
                for i in range(min(len(left_texts), len(right_texts))):
                    left_text = left_texts[i].strip()
                    right_text = right_texts[i].strip()
                    if left_text and right_text:
                        valid_pairs.append((left_text, right_text))
                
                if len(valid_pairs) < 2:
                    question.delete()
                    messages.error(request, 'Добавьте хотя бы 2 пары соответствия')
                    return redirect('methodist_test_editor', course_id=course_id, test_id=test_id)
                
                for left_text, right_text in valid_pairs:
                    MatchingPair.objects.create(
                        question=question,
                        left_text=left_text,
                        right_text=right_text
                    )

            elif 'text' in type_name:
                correct_text = request.POST.get('correct_text', '').strip()
                if not correct_text:
                    question.delete()
                    messages.error(request, 'Для текстового вопроса укажите правильный ответ')
                    return redirect('methodist_test_editor', course_id=course_id, test_id=test_id)
                
                question.correct_text = correct_text
                question.save()

            else:
                question.delete()
                messages.error(request, f'Неизвестный тип вопроса: {type_name}')
                return redirect('methodist_test_editor', course_id=course_id, test_id=test_id)

            messages.success(request, 'Вопрос успешно добавлен!')
            
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error adding question: {str(e)}", exc_info=True)
        
        messages.error(request, f'Ошибка при добавлении вопроса: {str(e)}')

    return redirect('methodist_test_editor', course_id=course_id, test_id=test_id)


@user_passes_test(is_methodist_teacher)
@require_POST
def delete_question(request, course_id, test_id, question_id):
    """Удаление вопроса"""
    
    is_request_user_teacher = False
    if hasattr(request.user, 'role') and request.user.role.role_name == 'преподаватель':
        is_request_user_teacher = True

    if is_request_user_teacher:
        course = get_object_or_404(
            Course, 
            Q(created_by=request.user) | Q(created_by__isnull=True), 
            id=course_id                                            
        )
    else:
        course = get_object_or_404(Course, id=course_id, created_by=request.user)
    
    test = get_object_or_404(Test, id=test_id, lecture__course=course)
    question = get_object_or_404(Question, id=question_id, test=test)

    try:
        with transaction.atomic():
            ChoiceOption.objects.filter(question=question).delete()
            MatchingPair.objects.filter(question=question).delete()
            UserAnswer.objects.filter(question=question).delete()
            
            question.delete()
            messages.success(request, 'Вопрос удален!')
    except Exception as e:
        messages.error(request, f'Ошибка при удалении вопроса: {str(e)}')

    return redirect('methodist_test_editor', course_id=course_id, test_id=test_id)


@user_passes_test(is_methodist_teacher)
def practical_assignment_management(request, course_id):
    """Управление практическими заданиями"""
    
    is_request_user_teacher = False
    if hasattr(request.user, 'role') and request.user.role.role_name == 'преподаватель':
        is_request_user_teacher = True

    if is_request_user_teacher:
        course = get_object_or_404(
            Course, 
            Q(created_by=request.user) | Q(created_by__isnull=True), 
            id=course_id                                            
        )
    else:
        course = get_object_or_404(Course, id=course_id, created_by=request.user)
    
    lectures = Lecture.objects.filter(course=course, is_active=True).order_by('lecture_order')
    assignments = PracticalAssignment.objects.filter(lecture__course=course).select_related('lecture')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_assignment':
            form = PracticalAssignmentForm(request.POST, request.FILES, course_id=course.id)
            if form.is_valid():
                try:
                    with transaction.atomic():
                        assignment = form.save(commit=False)
                        assignment.is_active = True  
                        assignment.save()
                        messages.success(request, 'Практическое задание успешно создано!')
                except Exception as e:
                    messages.error(request, f'Ошибка при создании задания: {str(e)}')
            else:
                messages.error(request, 'Ошибка при создании задания. Проверьте поля.')
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")

        elif action == 'update_assignment':
            assignment_id = request.POST.get('assignment_id')
            assignment = get_object_or_404(PracticalAssignment, id=assignment_id, lecture__course=course)
            form = PracticalAssignmentForm(request.POST, request.FILES, instance=assignment, course_id=course.id)
            if form.is_valid():
                try:
                    form.save()
                    messages.success(request, 'Практическое задание успешно обновлено!')
                except Exception as e:
                    messages.error(request, f'Ошибка при обновлении задания: {str(e)}')
            else:
                messages.error(request, 'Ошибка при обновлении задания. Проверьте поля.')
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")

        elif action == 'delete_assignment':
            assignment_id = request.POST.get('assignment_id')
            assignment = get_object_or_404(PracticalAssignment, id=assignment_id, lecture__course=course)
            assignment_name = assignment.practical_assignment_name
            
            from .models import UserPracticalAssignment
            has_submissions = UserPracticalAssignment.objects.filter(practical_assignment=assignment).exists()
            
            if has_submissions:
                messages.error(request, f'Нельзя удалить задание "{assignment_name}", так как к нему уже есть сданные работы!')
            else:
                assignment.delete()
                messages.success(request, f'Задание "{assignment_name}" удалено!')

        return redirect('methodist_assignment_management', course_id=course_id)

    assignments_with_files = assignments.filter(assignment_document_path__isnull=False).count()
    overdue_assignments = assignments.filter(
        assignment_deadline__lt=timezone.now()
    ).count()

    context = {
        'course': course,
        'lectures': lectures,
        'assignments': assignments,
        'today': timezone.now().date(),
        'now_datetime': timezone.now().strftime('%Y-%m-%dT%H:%M'),
        'assignments_with_files': assignments_with_files,
        'overdue_assignments': overdue_assignments,
    }
    return render(request, 'methodist/course_constructor/practical_assignment_management.html', context)


@user_passes_test(is_methodist_teacher)
def course_settings(request, course_id):
    """Настройки курса"""
    course = get_object_or_404(Course, id=course_id, created_by=request.user)

    if request.method == 'POST':
        form = CourseSettingsForm(request.POST, request.FILES, instance=course)
        action = request.POST.get('action')

        if action == 'update_settings':
            if form.is_valid():
                try:
                    form.save()
                    messages.success(request, 'Настройки курса успешно обновлены!')
                except Exception as e:
                    messages.error(request, f'Ошибка при обновлении настроек: {str(e)}')
            else:
                messages.error(request, 'Ошибка в форме. Проверьте поля.')
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{form.fields[field].label or field}: {error}")

        elif action == 'complete_course':
            try:
                with transaction.atomic():
                    course.is_completed = True
                    course.save()
                    
                    Lecture.objects.filter(course=course).update(is_active=True)
                    Test.objects.filter(lecture__course=course).update(is_active=True)
                    PracticalAssignment.objects.filter(lecture__course=course).update(is_active=True)
                    
                    messages.success(request, f'Курс "{course.course_name}" завершён! Все материалы активированы и пользователи будут уверены в том, что курс больше не пополняется новым.')
            except Exception as e:
                messages.error(request, f'Ошибка при завершении курса: {str(e)}')

        elif action == 'archive_course':
            try:
                course.is_active = False
                course.save()
                messages.success(request, f'Курс "{course.course_name}" архивирован!')
            except Exception as e:
                messages.error(request, f'Ошибка при архивации курса: {str(e)}')

        elif action == 'unarchive_course':
            try:
                course.is_active = True
                course.save()
                messages.success(request, f'Курс "{course.course_name}" разархивирован!')
            except Exception as e:
                messages.error(request, f'Ошибка при разархивации курса: {str(e)}')

        return redirect('methodist_course_settings', course_id=course_id)

    form = CourseSettingsForm(instance=course)
    total_lectures = course.lecture_set.count()
    total_tests = Test.objects.filter(lecture__course=course).count()
    total_assignments = PracticalAssignment.objects.filter(lecture__course=course).count()
    total_students = UserCourse.objects.filter(course=course, is_active=True).count()

    context = {
        'course': course,
        'form': form,
        'total_lectures': total_lectures,
        'total_tests': total_tests,
        'total_assignments': total_assignments,
        'total_students': total_students,
    }
    return render(request, 'methodist/course_constructor/course_settings.html', context)


@user_passes_test(is_methodist_teacher)
@require_POST
def add_choice_option(request, course_id, test_id, question_id):
    """Добавление варианта ответа (AJAX)"""
    
    is_request_user_teacher = False
    if hasattr(request.user, 'role') and request.user.role.role_name == 'преподаватель':
        is_request_user_teacher = True

    if is_request_user_teacher:
        course = get_object_or_404(
            Course, 
            Q(created_by=request.user) | Q(created_by__isnull=True), 
            id=course_id                                            
        )
    else:
        course = get_object_or_404(Course, id=course_id, created_by=request.user)
    
    test = get_object_or_404(Test, id=test_id, lecture__course=course)
    question = get_object_or_404(Question, id=question_id, test=test)

    option_text = request.POST.get('option_text', '').strip()
    is_correct = request.POST.get('is_correct') == 'on'

    if not option_text:
        return JsonResponse({'success': False, 'error': 'Заполните текст варианта'})

    try:
        option = ChoiceOption.objects.create(
            question=question,
            option_text=option_text,
            is_correct=is_correct,
        )
        return JsonResponse({
            'success': True,
            'option_id': option.id,
            'option_text': option.option_text,
            'is_correct': option.is_correct
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@user_passes_test(is_methodist_teacher)
@require_POST
def add_matching_pair(request, course_id, test_id, question_id):
    """Добавление пары соответствия (AJAX)"""
    
    is_request_user_teacher = False
    if hasattr(request.user, 'role') and request.user.role.role_name == 'преподаватель':
        is_request_user_teacher = True

    if is_request_user_teacher:
        course = get_object_or_404(
            Course, 
            Q(created_by=request.user) | Q(created_by__isnull=True), 
            id=course_id                                            
        )
    else:
        course = get_object_or_404(Course, id=course_id, created_by=request.user)
    
    test = get_object_or_404(Test, id=test_id, lecture__course=course)
    question = get_object_or_404(Question, id=question_id, test=test)

    left_text = request.POST.get('left_text', '').strip()
    right_text = request.POST.get('right_text', '').strip()

    if not left_text or not right_text:
        return JsonResponse({'success': False, 'error': 'Заполните оба текста пары'})

    try:
        pair = MatchingPair.objects.create(
            question=question,
            left_text=left_text,
            right_text=right_text,
        )
        return JsonResponse({
            'success': True,
            'pair_id': pair.id,
            'left_text': pair.left_text,
            'right_text': pair.right_text
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@user_passes_test(is_methodist_teacher)
@require_POST
def delete_choice_option(request, option_id):
    """Удаление варианта ответа (AJAX)"""
    
    option = get_object_or_404(ChoiceOption, id=option_id)
    
    is_request_user_teacher = False
    if hasattr(request.user, 'role') and request.user.role.role_name == 'преподаватель':
        is_request_user_teacher = True

    if is_request_user_teacher:
        if not (option.question.test.lecture.course.created_by == request.user or 
                option.question.test.lecture.course.created_by is None):
            return JsonResponse({'success': False, 'error': 'Доступ запрещён'}, status=403)
    else:
        if option.question.test.lecture.course.created_by != request.user:
            return JsonResponse({'success': False, 'error': 'Доступ запрещён'}, status=403)

    try:
        option.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@user_passes_test(is_methodist_teacher)
@require_POST
def delete_matching_pair(request, pair_id):
    """Удаление пары соответствия (AJAX)"""
    
    pair = get_object_or_404(MatchingPair, id=pair_id)
    
    is_request_user_teacher = False
    if hasattr(request.user, 'role') and request.user.role.role_name == 'преподаватель':
        is_request_user_teacher = True

    if is_request_user_teacher:
        if not (pair.question.test.lecture.course.created_by == request.user or 
                pair.question.test.lecture.course.created_by is None):
            return JsonResponse({'success': False, 'error': 'Доступ запрещён'}, status=403)
    else:
        if pair.question.test.lecture.course.created_by != request.user:
            return JsonResponse({'success': False, 'error': 'Доступ запрещён'}, status=403)

    try:
        pair.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})




def register_custom_fonts():
    font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'arial_black.ttf')
    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont('Arial-Black', font_path))
            return True
        except Exception as e:
            print(f"Ошибка загрузки шрифта: {e}")
    print("Шрифт не найден → используется стандартный Helvetica")
    return False

HAS_CUSTOM_FONT = register_custom_fonts()


@login_required
def methodist_statistics(request):
    if not hasattr(request.user, 'role') or request.user.role.role_name != 'методист':
        return render(request, '403.html', status=403)

    today = timezone.now().date()

    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')

    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = today - timedelta(days=30)
            end_date = today
    else:
        start_date = today - timedelta(days=30)
        end_date = today

    course_students_stats = []
    for course in Course.objects.filter(created_by=request.user):
        enrollments = UserCourse.objects.filter(
            course=course,
            registration_date__range=[start_date, end_date]
        )
        completed = enrollments.filter(status_course=True)
        in_progress = enrollments.filter(status_course=False)

        avg_rating = Review.objects.filter(
            course=course,
            publish_date__range=[start_date, end_date]
        ).aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0

        completion_rate = (completed.count() / enrollments.count() * 100) if enrollments.count() > 0 else 0

        course_students_stats.append({
            'course': course,
            'total_enrollments': enrollments.count(),
            'completed': completed.count(),
            'in_progress': in_progress.count(),
            'completion_rate': round(completion_rate, 1),
            'avg_rating': round(avg_rating, 2)
        })

    popular_courses = Course.objects.annotate(
        total_students=Count('usercourse', filter=Q(usercourse__registration_date__range=[start_date, end_date])),
        avg_rating=Avg('review__rating', filter=Q(review__publish_date__range=[start_date, end_date]))
    ).filter(total_students__gt=0).order_by('-avg_rating', '-total_students')[:10]

    context = {
        'course_students_stats': course_students_stats,
        'popular_courses': popular_courses,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'methodist_statistics.html', context)


@login_required
def export_statistics_csv(request, export_type):
    if not hasattr(request.user, 'role') or request.user.role.role_name != 'методист':
        return HttpResponse('Доступ запрещён', status=403)

    today = timezone.now().date()
    start = request.GET.get('start_date')
    end = request.GET.get('end_date')

    try:
        start_date = datetime.strptime(start, '%Y-%m-%d').date() if start else today - timedelta(days=30)
        end_date = datetime.strptime(end, '%Y-%m-%d').date() if end else today
    except:
        start_date = today - timedelta(days=30)
        end_date = today

    if export_type == 'students':
        filename = f"статистика_слушателей_{start_date}_по_{end_date}.csv"
    else:
        filename = f"популярные_курсы_{start_date}_по_{end_date}.csv"
    
    encoded_filename = quote(filename)
    
    response = HttpResponse(
        content_type='text/csv; charset=utf-8-sig',
        headers={
            'Content-Disposition': f'attachment; filename="{encoded_filename}"',
        }
    )
    
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    writer.writerow(["Статистика курсов"])
    writer.writerow([f"Период: {start_date} — {end_date}"])
    writer.writerow([f"Сгенерировано: {today}"])
    writer.writerow([])

    if export_type == 'students':
        writer.writerow(['Курс', 'Всего записей', 'Завершено', 'В процессе', 'Процент завершения', 'Средний рейтинг'])
        for c in Course.objects.filter(created_by=request.user):
            enr = UserCourse.objects.filter(course=c, registration_date__range=[start_date, end_date])
            total = enr.count()
            completed = enr.filter(status_course=True).count()
            avg = Review.objects.filter(course=c, publish_date__range=[start_date, end_date]).aggregate(Avg('rating'))['rating__avg'] or 0
            rate = (completed / total * 100) if total else 0
            writer.writerow([
                c.course_name, 
                total, 
                completed, 
                total-completed, 
                f"{rate:.1f}%", 
                f"{avg:.2f}"
            ])
    else:
        writer.writerow(['Курс', 'Категория', 'Слушателей', 'Рейтинг', 'Тип курса', 'Часы'])
        courses = Course.objects.annotate(
            s=Count('usercourse', filter=Q(usercourse__registration_date__range=[start_date, end_date])),
            r=Avg('review__rating', filter=Q(review__publish_date__range=[start_date, end_date]))
        ).filter(s__gt=0).order_by('-r', '-s')[:10]
        for c in courses:
            writer.writerow([
                c.course_name,
                getattr(c.course_category, 'course_category_name', '—'),
                c.s,
                f"{c.r or 0:.2f}",
                getattr(c.course_type, 'course_type_name', '—'),
                c.course_hours or '—'
            ])
    
    writer.writerow([])
    writer.writerow(["Отчет сгенерирован автоматически системой управления курсами"])

    return response


@login_required
def export_statistics_pdf(request, export_type):
    if not hasattr(request.user, 'role') or request.user.role.role_name != 'методист':
        return HttpResponse('Доступ запрещён', status=403)

    today = timezone.now().date()
    start = request.GET.get('start_date')
    end = request.GET.get('end_date')

    try:
        start_date = datetime.strptime(start, '%Y-%m-%d').date() if start else today - timedelta(days=30)
        end_date = datetime.strptime(end, '%Y-%m-%d').date() if end else today
    except:
        start_date = today - timedelta(days=30)
        end_date = today

    if export_type == 'students':
        filename = f"статистика_слушателей_{start_date}_по_{end_date}.pdf"
    else:
        filename = f"популярные_курсы_{start_date}_по_{end_date}.pdf"
    
    encoded_filename = quote(filename)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{encoded_filename}"'
    response['Content-Type'] = 'application/pdf'
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'

    try:
        doc = SimpleDocTemplate(
            response, 
            pagesize=landscape(A4), 
            topMargin=18*mm, 
            leftMargin=12*mm, 
            rightMargin=12*mm,
            title=filename.replace('.pdf', '')
        )
        elements = []

        title_font = 'Arial-Black' if HAS_CUSTOM_FONT else 'Helvetica-Bold'
        text_font = 'Arial-Black' if HAS_CUSTOM_FONT else 'Helvetica'

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name='BigTitle', 
            fontName=title_font, 
            fontSize=22, 
            textColor=colors.HexColor('#8A6BB1'), 
            alignment=1, 
            spaceAfter=20
        ))
        styles.add(ParagraphStyle(
            name='Info', 
            fontName=text_font, 
            fontSize=12, 
            textColor=colors.HexColor('#6B4E9B'), 
            spaceAfter=8
        ))
        styles.add(ParagraphStyle(
            name='Cell', 
            fontName=text_font, 
            fontSize=9.5, 
            leading=11, 
            alignment=0
        ))
        styles.add(ParagraphStyle(
            name='CellCenter', 
            fontName=text_font, 
            fontSize=9.5, 
            leading=11, 
            alignment=1
        ))

        elements.append(Paragraph(
            "СТАТИСТИКА СЛУШАТЕЛЕЙ" if export_type == 'students' else "ТОП ПОПУЛЯРНЫХ КУРСОВ", 
            styles['BigTitle']
        ))
        elements.append(Paragraph(
            f"<b>Период:</b> {start_date} — {end_date}", 
            styles['Info']
        ))
        elements.append(Paragraph(
            f"<b>Сгенерировано:</b> {today}", 
            styles['Info']
        ))
        elements.append(Spacer(1, 12))

        if export_type == 'students':
            data = [['Курс', 'Всего', 'Завершено', 'В процессе', 'Процент\nзавершения', 'Рейтинг']]
            col_widths = [180, 65, 75, 75, 85, 65]
            
            for c in Course.objects.filter(created_by=request.user):
                enr = UserCourse.objects.filter(course=c, registration_date__range=[start_date, end_date])
                total = enr.count()
                completed = enr.filter(status_course=True).count()
                avg = Review.objects.filter(
                    course=c, 
                    publish_date__range=[start_date, end_date]
                ).aggregate(Avg('rating'))['rating__avg'] or 0
                rate = (completed / total * 100) if total else 0
                
                data.append([
                    Paragraph(c.course_name, styles['Cell']),
                    Paragraph(str(total), styles['CellCenter']),
                    Paragraph(str(completed), styles['CellCenter']),
                    Paragraph(str(total-completed), styles['CellCenter']),
                    Paragraph(f"{rate:.1f}%", styles['CellCenter']),
                    Paragraph(f"{avg:.2f}", styles['CellCenter']),
                ])
        else:
            data = [['Курс', 'Категория', 'Слушателей', 'Рейтинг', 'Тип', 'Часы']]
            col_widths = [200, 120, 75, 70, 90, 60]
            
            courses = Course.objects.annotate(
                s=Count('usercourse', filter=Q(usercourse__registration_date__range=[start_date, end_date])),
                r=Avg('review__rating', filter=Q(review__publish_date__range=[start_date, end_date]))
            ).filter(s__gt=0).order_by('-r', '-s')[:10]
            
            for c in courses:
                data.append([
                    Paragraph(c.course_name, styles['Cell']),
                    Paragraph(getattr(c.course_category, 'course_category_name', '—'), styles['Cell']),
                    Paragraph(str(c.s), styles['CellCenter']),
                    Paragraph(f"{c.r or 0:.2f}", styles['CellCenter']),
                    Paragraph(getattr(c.course_type, 'course_type_name', '—'), styles['Cell']),
                    Paragraph(str(c.course_hours or '—'), styles['CellCenter']),
                ])

        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#9B7BB8')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTNAME', (0,0), (-1,0), title_font),
            ('FONTNAME', (0,1), (-1,-1), text_font),
            ('FONTSIZE', (0,0), (-1,0), 11),
            ('FONTSIZE', (0,1), (-1,-1), 9.5),
            ('GRID', (0,0), (-1,-1), 0.7, colors.HexColor('#D8BFD8')),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#FAF5FF')),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ]))
        
        elements.append(table)
        doc.build(elements)
        
    except Exception as e:
        return HttpResponse(f"Ошибка при создании PDF: {str(e)}", status=500)

    return response


def is_admin(user):
    return user.is_authenticated and user.is_admin


@user_passes_test(is_admin)
def admin_user_verification_list(request):

    metodist_role = Role.objects.filter(role_name="методист").first()
    teacher_role = Role.objects.filter(role_name="преподаватель").first()
    
    if not metodist_role:
        metodist_role = Role.objects.create(role_name="методист")
    if not teacher_role:
        teacher_role = Role.objects.create(role_name="преподаватель")
    
    users = User.objects.filter(
        Q(role=metodist_role) | Q(role=teacher_role)
    ).select_related('role').order_by('-date_joined')
    
    status_filter = request.GET.get('status_filter', '')
    if status_filter == 'verified':
        users = users.filter(is_verified=True)
    elif status_filter == 'not_verified':
        users = users.filter(is_verified=False)
    
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(patronymic__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(position__icontains=search_query) |
            Q(educational_institution__icontains=search_query)
        )
    
    role_filter = request.GET.get('role_filter', '')
    if role_filter == 'metodist':
        users = users.filter(role=metodist_role)
    elif role_filter == 'teacher':
        users = users.filter(role=teacher_role)
    
    paginator = Paginator(users, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'users': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'role_filter': role_filter,
        'page_obj': page_obj,
    }
    
    return render(request, 'admin/admin_user_verification_list.html', context)


@user_passes_test(is_admin)
def admin_user_verification_detail(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    metodist_role = Role.objects.filter(role_name="методист").first()
    teacher_role = Role.objects.filter(role_name="преподаватель").first()
    
    if user.role not in [metodist_role, teacher_role]:
        messages.error(request, 'У пользователя неподходящая роль')
        return redirect('admin_user_verification_list')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        comment = request.POST.get('comment', '').strip()
        
        if action == 'approve':
            user.is_verified = True
            user.save()
            email_sent = send_account_approved_email(user, comment)
            if email_sent:
                messages.success(request, f'Аккаунт пользователя {user.get_full_name()} подтвержден. Уведомление отправлено на почту.')
            else:
                messages.warning(request, f'Аккаунт пользователя {user.get_full_name()} подтвержден, но не удалось отправить почту.')
            
        elif action == 'reject':
            user.is_verified = False
            user.save()
            email_sent = send_account_rejected_email(user, comment)

            if email_sent:
                messages.success(request, f'Аккаунт пользователя {user.get_full_name()} отклонен. Уведомление отправлено на почту.')
            else:
                messages.warning(request, f'Аккаунт пользователя {user.get_full_name()} отклонен, но не удалось отправить почту.')
        
        return redirect('admin_user_verification_list')
    
    context = {
        'user_obj': user,
    }
    
    return render(request, 'admin/admin_user_verification_detail.html', context)


@require_POST
@csrf_exempt
def toggle_favorite(request, course_id):
    """Добавить/удалить курс из избранного"""
    course = get_object_or_404(Course, id=course_id)
    favorites = get_favorite_courses(request)
    
    if course_id in favorites:
        response_data = remove_from_favorites(request, course_id)
        is_fav = False
    else:
        response_data = add_to_favorites(request, course_id)
        is_fav = True
    
    updated_favorites = get_favorite_courses(request)
    
    json_response = JsonResponse({
        'is_favorite': is_fav,
        'favorites_count': len(updated_favorites)
    })
    
    if hasattr(response_data, 'cookies'):
        for cookie in response_data.cookies.values():
            json_response.set_cookie(
                cookie.key,
                cookie.value,
                max_age=cookie.get('max_age'),
                httponly=cookie.get('httponly', True)
            )
    
    return json_response



def favorites_page(request):
    """Страница с избранными курсами"""
    favorite_ids = get_favorite_courses(request)
    favorite_courses = Course.objects.filter(
        id__in=favorite_ids, 
        is_active=True
    ).select_related('course_category', 'course_type')
    
    for course in favorite_courses:
        course.db_rating = course.rating  
    
    context = {
        'favorite_courses': favorite_courses,
        'favorites_count': len(favorite_ids)
    }
    return render(request, 'favorites.html', context)


class EmailThread(threading.Thread):
    """Поток для асинхронной отправки email"""
    def __init__(self, subject, message, recipient_list, html_message=None):
        self.subject = subject
        self.message = message
        self.recipient_list = recipient_list
        self.html_message = html_message
        threading.Thread.__init__(self)

    def run(self):
        send_mail(
            self.subject,
            self.message,
            settings.DEFAULT_FROM_EMAIL,
            self.recipient_list,
            html_message=self.html_message,
            fail_silently=False,
        )

def send_reset_code_email(user, code, request):
    subject = 'Код восстановления пароля - UNIREAX'
    
    html_message = render_to_string('emails/password_reset_email.html', {
        'user': user,
        'code': code,
        'site_name': 'UNIREAX',
        'domain': request.get_host(),
        'protocol': 'https' if request.is_secure() else 'http'
    })
    
    text_message = f"""
Здравствуйте, {user.first_name} {user.last_name}!

Вы запросили восстановление пароля для вашего аккаунта на UNIREAX.

Ваш код подтверждения: {code}

Код действителен в течение 15 минут.

Если вы не запрашивали восстановление пароля, проигнорируйте это письмо.

С уважением,
Команда UNIREAX
"""
    
    EmailThread(subject, text_message, [user.email], html_message).start()

def password_reset_request(request):
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].lower()
            
            try:
                user = User.objects.get(email=email)
                
                PasswordResetCode.objects.filter(user=user, is_used=False).update(is_used=True)
                
                code = ''.join(random.choices(string.digits, k=6))
                reset_code = PasswordResetCode.objects.create(
                    user=user,
                    code=code
                )
                
                send_reset_code_email(user, code, request)                
                request.session['reset_email'] = email
                request.session['reset_code_id'] = reset_code.id
                
                messages.success(request, f'Код подтверждения отправлен на email {email}')
                return redirect('password_reset_verify')
                
            except User.DoesNotExist:
                messages.success(request, 'Если email зарегистрирован, код подтверждения будет отправлен')
                return redirect('password_reset_verify')
    else:
        form = PasswordResetRequestForm()
    
    return render(request, 'password_reset_request.html', {'form': form})

def password_reset_verify(request):
    if 'reset_email' not in request.session:
        messages.error(request, 'Сначала укажите ваш email')
        return redirect('password_reset_request')
    
    if request.method == 'POST':
        form = CodeVerificationForm(request.POST)
        email = request.session['reset_email']
        code_id = request.session['reset_code_id']
        
        if form.is_valid():
            entered_code = form.cleaned_data['code']
            
            try:
                reset_code = PasswordResetCode.objects.get(
                    id=code_id,
                    user__email=email,
                    code=entered_code
                )
                
                if not reset_code.is_valid():
                    messages.error(request, 'Код недействителен или истек срок действия')
                    return render(request, 'password_reset_verify.html', {'form': form, 'email': email})
                
                reset_code.mark_as_used()
                
                request.session['verified_user_id'] = reset_code.user.id
                if 'reset_code_id' in request.session:
                    del request.session['reset_code_id']
                
                messages.success(request, 'Код подтвержден. Теперь установите новый пароль.')
                return redirect('password_reset_confirm')
                
            except PasswordResetCode.DoesNotExist:
                messages.error(request, 'Неверный код подтверждения')
    else:
        form = CodeVerificationForm()
    
    email = request.session.get('reset_email', '')
    return render(request, 'password_reset_verify.html', {'form': form, 'email': email})

def password_reset_confirm(request):
    if 'verified_user_id' not in request.session:
        messages.error(request, 'Сначала подтвердите ваш email')
        return redirect('password_reset_request')
    
    try:
        user = User.objects.get(id=request.session['verified_user_id'])
        
        if request.method == 'POST':
            form = CustomSetPasswordForm(user, request.POST)
            
            if form.is_valid():
                form.save()
                
                session_keys = ['reset_email', 'verified_user_id', 'reset_code_id']
                for key in session_keys:
                    if key in request.session:
                        del request.session[key]
                
                messages.success(request, 'Пароль успешно изменен! Теперь вы можете войти с новым паролем.')
                return redirect('password_reset_complete')
        else:
            form = CustomSetPasswordForm(user)
        
        return render(request, 'password_reset_confirm.html', {'form': form})
            
    except User.DoesNotExist:
        messages.error(request, 'Пользователь не найден')
        return redirect('password_reset_request')

def password_reset_complete(request):
    return render(request, 'password_reset_complete.html')



@login_required
def course_teach(request, course_id):
    """Страница преподавания для преподавателя"""
    course = get_object_or_404(Course, id=course_id)
    
    is_teacher = CourseTeacher.objects.filter(
        course=course, 
        teacher=request.user, 
        is_active=True
    ).exists()
    
    if not is_teacher:
        return redirect('profile')
    
    students = UserCourse.objects.filter(
        course=course, 
        is_active=True
    ).select_related('user')
    
    assignments = PracticalAssignment.objects.filter(
        lecture__course=course,
        is_active=True
    ).select_related('lecture')
    
    submissions = UserPracticalAssignment.objects.filter(
        practical_assignment__lecture__course=course
    ).select_related(
        'user', 
        'practical_assignment',
        'practical_assignment__lecture',
        'submission_status'
    ).prefetch_related('assignmentsubmissionfile_set', 'feedback')
    
    students_count = students.count()
    assignments_to_review = submissions.filter(
        submission_status__assignment_status_name='на проверке'
    ).count()
    
    students_details = []
    total_progress = 0
    
    for student_course in students:
        student = student_course.user
        progress = calculate_student_progress_python(student.id, course.id)
        total_progress += progress
        
        student_submissions = submissions.filter(user=student)
        completed_assignments = student_submissions.filter(
            submission_status__assignment_status_name='завершен'
        ).count()
        
        avg_score = Feedback.objects.filter(
            user_practical_assignment__user=student,
            user_practical_assignment__practical_assignment__lecture__course=course,
            score__isnull=False
        ).aggregate(avg_score=Avg('score'))['avg_score'] or 0
        
        students_details.append({
            'user_id': student.id,
            'user__last_name': student.last_name,
            'user__first_name': student.first_name,
            'user__email': student.email,
            'progress': progress,
            'completed_assignments': completed_assignments,
            'average_score': avg_score
        })
    
    average_progress = total_progress / students_count if students_count > 0 else 0
    
    active_students = submissions.values('user').distinct().count()
    
    recent_submissions = submissions.filter(
        submission_status__assignment_status_name='на проверке'
    ).order_by('-submission_date')[:5]
    
    upcoming_deadlines = PracticalAssignment.objects.filter(
        lecture__course=course,
        assignment_deadline__isnull=False,
        assignment_deadline__gt=timezone.now(),
        is_active=True
    ).select_related('lecture').order_by('assignment_deadline')[:5]
    
    deadline_list = []
    for assignment in upcoming_deadlines:
        submitted_count = submissions.filter(
            practical_assignment=assignment,
            submission_date__isnull=False
        ).count()
        
        deadline_list.append({
            'assignment_name': assignment.practical_assignment_name,
            'lecture_name': assignment.lecture.lecture_name,
            'deadline': assignment.assignment_deadline,
            'submitted_count': submitted_count,
            'total_students': students_count
        })
    
    lectures = Lecture.objects.filter(
        course=course,
        is_active=True
    ).order_by('lecture_order')
    
    context = {
        'course': course,
        'students_count': students_count,
        'assignments_to_review': assignments_to_review,
        'average_progress': average_progress,
        'active_students': active_students,
        'recent_submissions': recent_submissions,
        'students_details': students_details,
        'upcoming_deadlines': deadline_list,
        'lectures': lectures,
        'assignments': assignments,
        'submissions': submissions,
    }
    
    return render(request, 'course_teach.html', context)



from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction 
from django.contrib.auth.decorators import login_required
from .models import UserPracticalAssignment, CourseTeacher, Feedback, AssignmentStatus, PracticalAssignment, Course

@login_required
def grade_assignment(request, submission_id):
    """
    Страница оценивания работы слушателя.
    Выставляет статус "Завершен", если работа соответствует критериям (зачет/проходной балл),
    иначе выставляет статус "На доработке".
    """
    submission = get_object_or_404(UserPracticalAssignment, id=submission_id)
    course = submission.practical_assignment.lecture.course
    
    if not CourseTeacher.objects.filter(course=course, teacher=request.user, is_active=True).exists():
        messages.error(request, 'У вас нет прав для оценивания работ в этом курсе.')
        return redirect('profile') 

    try:
        feedback = Feedback.objects.get(user_practical_assignment=submission)
    except Feedback.DoesNotExist:
        feedback = Feedback(user_practical_assignment=submission)
    
    if request.method == 'POST':
        assignment = submission.practical_assignment 
        
        completed_status = get_object_or_404(AssignmentStatus, assignment_status_name='завершен')
        on_rework_status = get_object_or_404(AssignmentStatus, assignment_status_name='на доработке') 
        
        try:
            with transaction.atomic(): 
                if assignment.grading_type == 'points':
                    score_str = request.POST.get('score')
                    if not score_str:
                        messages.error(request, 'Для бальной системы необходимо указать количество баллов.')
                        return render(request, 'grade_assignment.html', {'submission': submission, 'feedback': feedback, 'course': course})
                    
                    try:
                        score = int(score_str)
                        if score < 0 or score > assignment.max_score:
                            messages.error(request, f'Баллы должны быть в диапазоне от 0 до {assignment.max_score}.')
                            return render(request, 'grade_assignment.html', {'submission': submission, 'feedback': feedback, 'course': course})
                    except ValueError:
                        messages.error(request, 'Баллы должны быть числом.')
                        return render(request, 'grade_assignment.html', {'submission': submission, 'feedback': feedback, 'course': course})
                    
                    feedback.score = score
                    feedback.is_passed = None 
                    
                    if score >= assignment.max_score * 0.5:
                        submission.submission_status = completed_status
                    else:
                        submission.submission_status = on_rework_status
                    
                else: 
                    is_passed_str = request.POST.get('is_passed')
                    if is_passed_str not in ['true', 'false']:
                        messages.error(request, 'Для системы "зачёт/незачёт" необходимо выбрать оценку.')
                        return render(request, 'grade_assignment.html', {'submission': submission, 'feedback': feedback, 'course': course})
                    
                    is_passed = (is_passed_str == 'true')
                    feedback.is_passed = is_passed
                    feedback.score = None  
                    
                    if is_passed:
                        submission.submission_status = completed_status
                    else:
                        submission.submission_status = on_rework_status
                
                feedback.comment_feedback = request.POST.get('comment_feedback', '')
                feedback.save()
                submission.save() 
                
                messages.success(request, f'Оценка успешно сохранена. Статус работы: "{submission.submission_status.assignment_status_name}".')
                return redirect('course_teach', course_id=course.id)
                
        except PracticalAssignment.DoesNotExist:
            messages.error(request, 'Ошибка: Практическое задание не найдено.')
            return redirect('course_teach', course_id=course.id)
        except AssignmentStatus.DoesNotExist:
            messages.error(request, 'Ошибка: Не найдены необходимые статусы работы ("завершен" или "на доработке"). Обратитесь к администратору.')
            return redirect('course_teach', course_id=course.id)
        except Exception as e:
            messages.error(request, f'Ошибка при сохранении оценки: {str(e)}')
            return render(request, 'grade_assignment.html', {'submission': submission, 'feedback': feedback, 'course': course})
    
    context = {
        'submission': submission,
        'feedback': feedback,
        'course': course,
        'max_score': submission.practical_assignment.max_score if submission.practical_assignment.grading_type == 'points' else None
    }
    
    return render(request, 'grade_assignment.html', context)




@login_required
def student_progress(request, course_id, student_id):
    """Детальный прогресс слушателя"""
    course = get_object_or_404(Course, id=course_id)
    student = get_object_or_404(User, id=student_id)
    
    is_teacher = CourseTeacher.objects.filter(
        course=course, 
        teacher=request.user, 
        is_active=True
    ).exists()
    
    if not is_teacher:
        return redirect('profile')
    
    submissions = UserPracticalAssignment.objects.filter(
        user=student,
        practical_assignment__lecture__course=course
    ).select_related(
        'practical_assignment',
        'practical_assignment__lecture',
        'submission_status'
    ).prefetch_related('assignmentsubmissionfile_set', 'feedback')
    
    from django.db.models import Max
    latest_test_attempts = TestResult.objects.filter(
        user=student,
        test__lecture__course=course
    ).values('test').annotate(
        latest_attempt=Max('attempt_number')
    )
    
    test_results = []
    for attempt in latest_test_attempts:
        test_id = attempt['test']
        latest_attempt_num = attempt['latest_attempt']
        
        last_result = TestResult.objects.filter(
            user=student,
            test_id=test_id,
            attempt_number=latest_attempt_num
        ).select_related('test', 'test__lecture').first()
        
        if last_result:
            test_results.append(last_result)
    
    progress = calculate_student_progress_python(student.id, course.id)
    
    completed_assignments_count = submissions.filter(
        submission_status__assignment_status_name='завершен'
    ).count()
    
    pending_assignments_count = submissions.filter(
        submission_status__assignment_status_name='на проверке'
    ).count()
    
    context = {
        'course': course,
        'student': student,
        'submissions': submissions,
        'test_results': test_results,
        'progress': progress,
        'completed_assignments_count': completed_assignments_count,
        'pending_assignments_count': pending_assignments_count,
        'current_time': timezone.now(),
    }
    
    return render(request, 'student_progress.html', context)

from django.db import connection

def calculate_student_progress_python(student_id, course_id):
    """Расчет прогресса слушателя через вызов PostgreSQL функции"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT calculate_course_completion(%s, %s)",
                [student_id, course_id]
            )
            result = cursor.fetchone()
            return float(result[0]) if result and result[0] else 0.00
    except Exception as e:
        print(f"Error calculating progress: {e}")
        return 0.00

def calculate_course_average_progress_python(course_id):
    """Расчет среднего прогресса по курсу через вызов PostgreSQL функции"""
    try:
        students = UserCourse.objects.filter(
            course_id=course_id,
            is_active=True
        )
        
        if not students.exists():
            return 0.00
        
        total_progress = 0
        for student_course in students:
            progress = calculate_student_progress_python(student_course.user_id, course_id)
            total_progress += progress
        
        return round(total_progress / students.count(), 2)
    except Exception as e:
        print(f"Error calculating average progress: {e}")
        return 0.00
    


@login_required
def create_course_teacher(request):
    """Создание курса (только тип 'Классная комната')"""
    if request.method == 'POST':
        try:
            classroom_type = CourseType.objects.get(course_type_name="Классная комната")
            
            course = Course(
                course_name=request.POST['course_name'],
                course_description=request.POST.get('course_description', ''),
                course_category_id=request.POST['course_category'],
                course_hours=request.POST['course_hours'],
                course_max_places=request.POST.get('course_max_places'),
                course_price=request.POST.get('course_price'),
                course_type=classroom_type,
                created_by=None, 
                is_active=True
            )
            
            if 'course_photo_path' in request.FILES:
                course.course_photo_path = request.FILES['course_photo_path']
            
            course.has_certificate = 'has_certificate' in request.POST
            
            course.save()
            
            from .models import CourseTeacher
            CourseTeacher.objects.create(
                course=course,
                teacher=request.user,
                start_date=timezone.now().date(),
                is_active=True
            )
            
            messages.success(request, 'Курс успешно создан!')
            return redirect('course_study', course_id=course.id)
            
        except Exception as e:
            messages.error(request, f'Ошибка при создании курса: {str(e)}')
    
    categories = CourseCategory.objects.all()
    classroom_type = CourseType.objects.get(course_type_name="Классная комната")
    
    return render(request, 'course_create.html', {
        'categories': categories,
        'classroom_type': classroom_type
    })


@login_required
def course_students_management(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if not course.courseteacher_set.filter(teacher=request.user, is_active=True).exists():
        messages.error(request, 'У вас нет доступа к управлению этим курсом')
        return redirect('profile')

    students = UserCourse.objects.filter(course=course, is_active=True).select_related('user')
    students_count = students.count()

    return render(request, 'course_students_management.html', {
        'course': course,
        'students': students,
        'students_count': students_count,
    })


@login_required
def upload_students_csv(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if not course.courseteacher_set.filter(teacher=request.user, is_active=True).exists():
        messages.error(request, 'Доступ запрещён')
        return redirect('profile')

    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']

        if not csv_file.name.lower().endswith('.csv'):
            messages.error(request, 'Файл должен иметь расширение .csv')
            return redirect('course_students_management', course_id=course_id)

        try:
            decoded_file = csv_file.read().decode('utf-8-sig')  
            reader = csv.DictReader(StringIO(decoded_file))

            required_fields = {'first_name', 'last_name', 'email'}
            if not required_fields.issubset(set(reader.fieldnames or [])):
                messages.error(request, f'CSV должен содержать колонки: {", ".join(required_fields)}')
                return redirect('course_students_management', course_id=course_id)

            student_role = Role.objects.get(role_name='слушатель курсов')
            created_count = 0
            errors = []

            with transaction.atomic():
                for row_num, row in enumerate(reader, start=2):
                    email = row['email'].strip().lower()
                    first_name = row['first_name'].strip()
                    last_name = row['last_name'].strip()
                    patronymic = row.get('patronymic', '').strip()

                    if not (email and first_name and last_name):
                        errors.append(f"Строка {row_num}: не заполнены обязательные поля")
                        continue

                    try:
                        validate_email(email)
                    except ValidationError:
                        errors.append(f"Строка {row_num}: неверный email {email}")
                        continue

                    try:
                        user, created = User.objects.get_or_create(
                            email=email,
                            defaults={
                                'username': email,
                                'first_name': first_name,
                                'last_name': last_name,
                                'patronymic': patronymic or None,
                                'role': student_role,
                                'is_verified': True,
                                'is_active': True,
                            }
                        )

                        if created:
                            password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                            user.set_password(password)
                            user.save()

                        UserCourse.objects.get_or_create(
                            user=user,
                            course=course,
                            defaults={
                                'registration_date': timezone.now().date(),
                                'status_course': False,
                                'course_price': course.course_price or 0,
                                'is_active': True,
                            }
                        )
                        if created:
                            created_count += 1

                    except Exception as e:
                        errors.append(f"Строка {row_num}: {str(e)}")

            if created_count:
                messages.success(request, f'Добавлено/обновлено слушателей: {created_count}')
            if errors:
                messages.warning(request, 'Ошибки в некоторых строках: ' + ' | '.join(errors[:7]))

        except Exception as e:
            messages.error(request, f'Ошибка обработки файла: {str(e)}')

    return redirect('course_students_management', course_id=course_id)



@login_required
def generate_students_csv(request, course_id):
    """"функция для генерации csv-файла со студентами"""
    course = get_object_or_404(Course, id=course_id)

    if not course.courseteacher_set.filter(teacher=request.user, is_active=True).exists():
        messages.error(request, 'Доступ запрещён')
        return redirect('profile')

    if request.method == 'POST':
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="students_with_passwords_{course_id}.csv"'
        response.write('\ufeff')  

        writer = csv.writer(response)
        writer.writerow(['first_name', 'last_name', 'patronymic', 'email', 'password', 'login_info'])

        student_role = Role.objects.get(role_name='слушатель курсов')
        generated_count = 0

        with transaction.atomic():
            i = 0
            while True:
                first_name = request.POST.get(f'first_name_{i}')
                if first_name is None:
                    break

                last_name = request.POST.get(f'last_name_{i}', '').strip()
                patronymic = request.POST.get(f'patronymic_{i}', '').strip()
                email = request.POST.get(f'email_{i}', '').strip().lower()

                if not (first_name and last_name and email):
                    i += 1
                    continue

                password_plain = ''.join(random.choices(string.ascii_letters + string.digits, k=12))

                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        'username': email,
                        'first_name': first_name.strip(),
                        'last_name': last_name,
                        'patronymic': patronymic or None,
                        'role': student_role,
                        'is_verified': True,
                        'is_active': True,
                    }
                )


                if created:
                    user.set_password(password_plain)
                    user.save()
                    generated_count += 1

                UserCourse.objects.get_or_create(
                    user=user,
                    course=course,
                    defaults={
                        'registration_date': timezone.now().date(),
                        'status_course': False,
                        'course_price': course.course_price or 0,
                        'is_active': True,
                    }
                )

                login_info = f"Логин: {email} | Пароль: {password_plain if created else '(уже был создан)'}"
                writer.writerow([
                    first_name.strip(),
                    last_name,
                    patronymic,
                    email,
                    password_plain if created else '(существующий пользователь)',
                    login_info
                ])

                i += 1

        if generated_count:
            messages.success(request, f'Успешно создано {generated_count} новых аккаунтов. CSV с паролями скачан.')
        else:
            messages.info(request, 'Новые пользователи не созданы (возможно, все уже существуют). CSV сформирован.')

        return response

    return redirect('course_students_management', course_id=course_id)


@login_required
def teacher_courses(request):
    """страница со списком курсов преподавателя"""
    if request.user.role.role_name != 'преподаватель':
        messages.error(request, 'Доступ запрещен')
        return redirect('profile')
    
    teacher_courses = CourseTeacher.objects.filter(
        teacher=request.user, 
        is_active=True
    ).select_related('course')
    
    return render(request, 'teacher_courses.html', {
        'teacher_courses': teacher_courses
    })



@login_required
@require_POST
def delete_account(request):
    user = request.user
    
    if user.is_admin:
        messages.error(request, "Администраторы не могут удалять свои аккаунты")
        return redirect('profile')
    
    try:
        if user.role.role_name == 'слушатель курсов':
            UserCourse.objects.filter(user=user).delete()
            UserPracticalAssignment.objects.filter(user=user).delete()
            TestResult.objects.filter(user=user).delete()
            UserAnswer.objects.filter(user=user).delete()
            Review.objects.filter(user=user).delete()

            PasswordResetCode.objects.filter(user=user).delete()
            logout(request)
            user.delete()
            
            messages.success(request, "Ваш аккаунт и все связанные данные были успешно удалены")
            return redirect('main')
            
        elif user.role.role_name == 'преподаватель':
            user.is_active = False
            user.save()
            
            CourseTeacher.objects.filter(teacher=user).update(is_active=False)
            
            logout(request)
            messages.success(request, "Ваш аккаунт был успешно деактивирован. Вы больше не являетесь преподавателем на курсах.")
            return redirect('main')
            
        elif user.role.role_name == 'методист':
            user.is_active = False
            user.save()
            
            courses_created = Course.objects.filter(created_by=user)
            
            for course in courses_created:
                course.is_active = False
                course.save()
                Lecture.objects.filter(course=course).update(is_active=False)
                PracticalAssignment.objects.filter(lecture__course=course).update(is_active=False)
                Test.objects.filter(lecture__course=course).update(is_active=False)
                UserCourse.objects.filter(course=course).update(is_active=False)
                CourseTeacher.objects.filter(course=course).update(is_active=False)
            
            logout(request)
            messages.success(request, "Ваш аккаунт и все созданные вами курсы были деактивированы. Курсы больше недоступны для обучения.")
            return redirect('main')
        
    except Exception as e:
        messages.error(request, f"Произошла ошибка при обработке запроса: {str(e)}")
        return redirect('profile')