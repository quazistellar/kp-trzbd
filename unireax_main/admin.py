from django.contrib import admin
from django.contrib.admin.models import LogEntry, CHANGE, ADDITION, DELETION
from django.utils.html import format_html
from django.utils.translation import gettext as _
from django.contrib.auth.admin import UserAdmin
from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.http import urlencode
import json
from django.db.models import Q

from .models import (
    Role,
    User,
    CourseCategory,
    CourseType,
    AssignmentStatus,
    Course,
    CourseTeacher,
    Lecture,
    PracticalAssignment,
    UserPracticalAssignment,
    UserCourse,
    Feedback,
    Review,
    AnswerType,
    Test,
    Question,
    ChoiceOption,
    MatchingPair,
    UserAnswer,
    UserSelectedChoice,
    UserMatchingAnswer,
    TestResult,
    Certificate,
    AssignmentSubmissionFile,  
    ViewCoursePracticalAssignments,  
    ViewCourseLectures,
    ViewCourseTests,
    ViewAssignmentSubmissions,
    PasswordResetCode
)

# 1. роли пользователей
@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('role_name',)
    search_fields = ('role_name',)
    ordering = ('role_name',)

class UserAdminForm(forms.ModelForm):
    class Meta:
        model = User
        fields = '__all__'
    
    def clean_certificat_from_the_place_of_work_path(self):
        file = self.cleaned_data.get('certificat_from_the_place_of_work_path')
        if file:
            if file.size > 10 * 1024 * 1024:
                raise ValidationError('Файл слишком большой. Максимальный размер: 10 МБ')
            ext = file.name.split('.')[-1].lower()
            allowed_extensions = ['jpg', 'jpeg', 'png', 'pdf']
            if ext not in allowed_extensions:
                raise ValidationError(f'Допустимые форматы: {", ".join(allowed_extensions)}')
        
        return file

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    form = UserAdminForm
    
    list_display = ('id', 'username', 'email', 'last_name', 'first_name', 'patronymic', 'is_verified', 'role', 'is_staff', 'date_joined')
    list_filter = ('is_verified', 'role', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'patronymic', 'email')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('last_name', 'first_name', 'patronymic', 'email')}),
        (_('Дополнительная информация'), {'fields': (
            'is_verified', 
            'role', 
            'profile_theme', 
            'position', 
            'educational_institution', 
            'certificat_from_the_place_of_work_path'
        )}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 
                'email', 
                'password1', 
                'password2', 
                'last_name', 
                'first_name', 
                'patronymic'
            ),
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj and obj.certificat_from_the_place_of_work_path:
            return readonly_fields + ('certificat_file_link',)
        return readonly_fields
    
    def certificat_file_link(self, obj):
        if obj.certificat_from_the_place_of_work_path:
            return format_html(
                '<a href="{}" target="_blank">📎 Посмотреть справку</a>',
                obj.certificat_from_the_place_of_work_path.url
            )
        return "—"
    
    certificat_file_link.short_description = "Справка с места работы"
    
    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj and obj.certificat_from_the_place_of_work_path:
            for fieldset in fieldsets:
                if fieldset[0] is not None and 'Дополнительная информация' in fieldset[0]:
                    fields = list(fieldset[1]['fields'])
                    if 'certificat_from_the_place_of_work_path' in fields:
                        fields[fields.index('certificat_from_the_place_of_work_path')] = 'certificat_file_link'
                    fieldset[1]['fields'] = tuple(fields)
        return fieldsets

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'certificat_from_the_place_of_work_path' in form.base_fields:
            form.base_fields['certificat_from_the_place_of_work_path'].help_text = (
                'Форматы: JPG, PNG, PDF. Максимальный размер: 10 МБ'
            )
        return form

# 3. категории курсов
@admin.register(CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    list_display = ('course_category_name',)
    search_fields = ('course_category_name',)
    ordering = ('course_category_name',)

# 4. типы курсов
@admin.register(CourseType)
class CourseTypeAdmin(admin.ModelAdmin):
    list_display = ('course_type_name', 'course_type_description')
    search_fields = ('course_type_name',)
    ordering = ('course_type_name',)

# 5. статусы заданий
@admin.register(AssignmentStatus)
class AssignmentStatusAdmin(admin.ModelAdmin):
    list_display = ('assignment_status_name',)
    search_fields = ('assignment_status_name',)
    ordering = ('assignment_status_name',)

# 6. курсы
@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('course_name', 'course_category', 'course_price', 'course_type', 'created_by', 'is_active')
    list_filter = ('course_category', 'course_type', 'has_certificate', 'is_completed')
    search_fields = ('course_name', 'course_description')
    ordering = ('course_name',)

# 7. курсы_преподаватели
@admin.register(CourseTeacher)
class CourseTeacherAdmin(admin.ModelAdmin):
    list_display = ('course', 'teacher', 'start_date', 'is_active')
    list_filter = ('start_date',)
    search_fields = ('course__course_name', 'teacher__username')
    ordering = ('start_date',)

# 8. лекции
@admin.register(Lecture)
class LectureAdmin(admin.ModelAdmin):
    list_display = ('lecture_name', 'course', 'lecture_order', 'is_active')
    list_filter = ('course',)
    search_fields = ('lecture_name', 'lecture_content', 'is_active')
    ordering = ('lecture_order',)

# 9. практические задания
@admin.register(PracticalAssignment)
class PracticalAssignmentAdmin(admin.ModelAdmin):
    list_display = ('practical_assignment_name', 'lecture', 'assignment_deadline', 'grading_type', 'max_score')
    list_filter = ('lecture', 'assignment_deadline', 'grading_type')
    search_fields = ('practical_assignment_name', 'practical_assignment_description')
    ordering = ('assignment_deadline',)

# 10. пользователи_практические_задания
@admin.register(UserPracticalAssignment)
class UserPracticalAssignmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'practical_assignment', 'submission_date', 'submission_status', 'attempt_number')
    list_filter = ('submission_status', 'submission_date')
    search_fields = ('user__username', 'practical_assignment__practical_assignment_name')
    ordering = ('submission_date',)

# 11. пользователи_курсы
@admin.register(UserCourse)
class UserCourseAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'registration_date', 'status_course', 'payment_date', 'completion_date', 'course_price', 'is_active')
    list_filter = ('status_course', 'registration_date', 'payment_date', 'completion_date')
    search_fields = ('user__username', 'course__course_name')
    ordering = ('registration_date',)

# 12. обратная связь
@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('user_practical_assignment', 'score', 'is_passed', 'comment_feedback')
    list_filter = ('is_passed',)
    search_fields = ('user_practical_assignment__user__username', 'user_practical_assignment__practical_assignment__practical_assignment_name')
    ordering = ('user_practical_assignment',)

# 13. отзывы
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('course', 'user', 'rating', 'publish_date')
    list_filter = ('rating', 'publish_date')
    search_fields = ('course__course_name', 'user__username', 'review_text')
    ordering = ('publish_date',)

# 14. типы ответов
@admin.register(AnswerType)
class AnswerTypeAdmin(admin.ModelAdmin):
    list_display = ('answer_type_name', 'answer_type_description')
    search_fields = ('answer_type_name',)
    ordering = ('answer_type_name',)

# 15. тесты
@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('test_name', 'lecture', 'is_final', 'grading_form', 'passing_score', 'is_active')
    list_filter = ('is_final', 'grading_form')
    search_fields = ('test_name', 'test_description')
    ordering = ('test_name',)

# 16. вопросы
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'test', 'answer_type', 'question_score', 'question_order')
    list_filter = ('test', 'answer_type')
    search_fields = ('question_text',)
    ordering = ('question_order',)

# 17. варианты ответов
@admin.register(ChoiceOption)
class ChoiceOptionAdmin(admin.ModelAdmin):
    list_display = ('option_text', 'question', 'is_correct')
    list_filter = ('is_correct',)
    search_fields = ('option_text',)

# 18. пары соответствий
@admin.register(MatchingPair)
class MatchingPairAdmin(admin.ModelAdmin):
    list_display = ('left_text', 'right_text', 'question')
    search_fields = ('left_text', 'right_text')

# 19. ответы пользователей
@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ('user', 'question', 'answer_date', 'attempt_number', 'score')
    list_filter = ('answer_date',)
    search_fields = ('user__username', 'question__question_text')
    ordering = ('answer_date',)

# 20. выбранные варианты для single_choice и multiple_choice
@admin.register(UserSelectedChoice)
class UserSelectedChoiceAdmin(admin.ModelAdmin):
    list_display = ('user_answer', 'choice_option')

# 21. пользовательские сопоставления для matching
@admin.register(UserMatchingAnswer)
class UserMatchingAnswerAdmin(admin.ModelAdmin):
    list_display = ('user_answer', 'matching_pair', 'user_selected_right_text')

# 22. результаты тестов
@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ('user', 'test', 'completion_date', 'final_score', 'is_passed', 'attempt_number')
    list_filter = ('is_passed', 'completion_date')
    search_fields = ('user__username', 'test__test_name')
    ordering = ('completion_date',)

# 23. сертификаты
@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('user_course', 'certificate_number', 'issue_date')
    search_fields = ('certificate_number', 'user_course__user__username', 'user_course__course__course_name')
    ordering = ('issue_date',)

def is_duplicate_log_entry(message):
    """Проверяет, является ли сообщение дубликатом (JSON формата Django)."""
    try:
        data = json.loads(message)
        if isinstance(data, list):
            for item in data:
                if 'added' in item or 'changed' in item or 'deleted' in item:
                    return True
        return False
    except (json.JSONDecodeError, TypeError, IndexError):
        return False

# логирование пользовательских действий для администатора
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('action_time', 'user', 'content_type_display', 'object_repr', 'action_flag_display', 'change_message_display')
    list_filter = ('action_flag', 'user', 'content_type')
    search_fields = ('object_id', 'change_message', 'object_repr')
    readonly_fields = ('action_time', 'user', 'content_type', 'object_id', 'object_repr', 'action_flag_display', 'change_message_display')
    date_hierarchy = 'action_time'
    ordering = ('-action_time',)

    def get_queryset(self, request):
        """Функция исключения логов с JSON-дубликатами и системных моделей"""
        qs = super().get_queryset(request)
        return qs.exclude(
            Q(change_message__startswith='[{"added":') |
            Q(change_message__startswith='[{"changed":') |
            Q(change_message__startswith='[{"deleted":') |
            Q(change_message='Была удалена запись:') |
            Q(change_message='')
        ).exclude(
            Q(content_type__app_label='sessions') |  
            Q(content_type__app_label='admin', content_type__model='logentry')  
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def action_flag_display(self, obj):
        if obj.action_flag == ADDITION:
            return _("Добавлено")
        elif obj.action_flag == CHANGE:
            return _("Изменено")
        elif obj.action_flag == DELETION:
            return _("Удалено")
        return ""
    action_flag_display.short_description = _("Действие")

    def content_type_display(self, obj):
        """Функция для корректного отображение типа контента без ссылок"""
        return f"{obj.content_type.app_label}.{obj.content_type.model}"
    content_type_display.short_description = _('Модель')

    def change_message_display(self, obj):
        """Функция, которая отображает читаемое сообщение об изменении, фильтруя JSON-дубликаты."""
        if is_duplicate_log_entry(obj.change_message) or obj.change_message == 'Была удалена запись:' or obj.change_message == '':
            return "—"
        return obj.change_message
    change_message_display.short_description = _('Сообщение об изменении')


admin.site.register(LogEntry, LogEntryAdmin)



# 24. Файлы сдачи заданий
@admin.register(AssignmentSubmissionFile)
class AssignmentSubmissionFileAdmin(admin.ModelAdmin):
    list_display = ('user_assignment', 'file_name', 'file_size', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('file_name', 'user_assignment__user__username')
    readonly_fields = ('uploaded_at', 'file_name', 'file_size')
    ordering = ('-uploaded_at',)
    
    def has_add_permission(self, request):
        return False

# 25. представления 
@admin.register(ViewCoursePracticalAssignments)
class ViewCoursePracticalAssignmentsAdmin(admin.ModelAdmin):
    list_display = ('course_name', 'lecture_name', 'practical_assignment_name', 'assignment_deadline', 'grading_type', 'is_active')
    list_filter = ('course_name', 'grading_type', 'is_active')
    search_fields = ('course_name', 'lecture_name', 'practical_assignment_name')
    ordering = ('course_name', 'lecture_order')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(ViewCourseLectures)
class ViewCourseLecturesAdmin(admin.ModelAdmin):
    list_display = ('course_name', 'lecture_name', 'lecture_order', 'is_active')
    list_filter = ('course_name', 'is_active')
    search_fields = ('course_name', 'lecture_name')
    ordering = ('course_name', 'lecture_order')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(ViewCourseTests)
class ViewCourseTestsAdmin(admin.ModelAdmin):
    list_display = ('course_name', 'lecture_name', 'test_name', 'is_final', 'grading_form', 'is_active')
    list_filter = ('course_name', 'is_final', 'grading_form', 'is_active')
    search_fields = ('course_name', 'lecture_name', 'test_name')
    ordering = ('course_name', 'lecture_order')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(ViewAssignmentSubmissions)
class ViewAssignmentSubmissionsAdmin(admin.ModelAdmin):
    list_display = ('user_name', 'practical_assignment_name', 'course_name', 'submission_date', 'status', 'file_count', 'total_size')
    list_filter = ('status', 'submission_date', 'course_name')
    search_fields = ('user_name', 'practical_assignment_name', 'course_name')
    ordering = ('-submission_date',)
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False