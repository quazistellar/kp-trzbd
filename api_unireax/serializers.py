from rest_framework import serializers
from unireax_main.models import *

from django.contrib.auth.models import AbstractUser

# 1. роли пользователей
class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'role_name']

# 2. пользователи
class UserSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source='role.role_name', read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'patronymic',
            'is_verified', 'role', 'role_name', 'profile_theme', 'position',
            'educational_institution', 'certificat_from_the_place_of_work_path',
            'is_active', 'date_joined'
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User.objects.create(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

# 3. категории курсов
class CourseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseCategory
        fields = ['id', 'course_category_name']

# 4. типы курсов
class CourseTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseType
        fields = ['id', 'course_type_name', 'course_type_description']

# 5. статусы заданий
class AssignmentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssignmentStatus
        fields = ['id', 'assignment_status_name']

# 6. курсы
class CourseSerializer(serializers.ModelSerializer):
    rating = serializers.ReadOnlyField()
    
    class Meta:
        model = Course
        fields = [
            'id', 'course_name', 'course_description', 'course_price',
            'course_category', 'course_photo_path', 'has_certificate',
            'course_max_places', 'course_hours', 'is_completed', 'code_room',
            'course_type', 'created_by', 'is_active', 'rating'
        ]

class CourseDetailSerializer(serializers.ModelSerializer):
    rating = serializers.ReadOnlyField()
    course_category_name = serializers.CharField(source='course_category.course_category_name', read_only=True)
    course_type_name = serializers.CharField(source='course_type.course_type_name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = Course
        fields = [
            'id', 'course_name', 'course_description', 'course_price',
            'course_category', 'course_category_name', 'course_photo_path', 
            'has_certificate', 'course_max_places', 'course_hours', 
            'is_completed', 'code_room', 'course_type', 'course_type_name',
            'created_by', 'created_by_name', 'is_active', 'rating'
        ]

# 7. курсы-преподаватели
class CourseTeacherSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    course_name = serializers.CharField(source='course.course_name', read_only=True)
    
    class Meta:
        model = CourseTeacher
        fields = [
            'id', 'course', 'course_name', 'teacher', 'teacher_name',
            'start_date', 'is_active'
        ]

# 8. лекции
class LectureSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.course_name', read_only=True)
    
    class Meta:
        model = Lecture
        fields = [
            'id', 'lecture_name', 'lecture_content', 'lecture_document_path',
            'lecture_order', 'course', 'course_name', 'is_active'
        ]

# 9. практические задания
class PracticalAssignmentSerializer(serializers.ModelSerializer):
    lecture_name = serializers.CharField(source='lecture.lecture_name', read_only=True)
    course_name = serializers.CharField(source='lecture.course.course_name', read_only=True)
    
    class Meta:
        model = PracticalAssignment
        fields = [
            'id', 'practical_assignment_name', 'practical_assignment_description',
            'assignment_document_path', 'assignment_criteria', 'lecture', 
            'lecture_name', 'assignment_deadline', 'grading_type', 'max_score',
            'is_active', 'course_name'
        ]

# 10. пользователи и их практические работы
class UserPracticalAssignmentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    assignment_name = serializers.CharField(source='practical_assignment.practical_assignment_name', read_only=True)
    status_name = serializers.CharField(source='submission_status.assignment_status_name', read_only=True)
    
    class Meta:
        model = UserPracticalAssignment
        fields = [
            'id', 'user', 'user_name', 'practical_assignment', 'assignment_name',
            'submission_date', 'submission_status', 'status_name', 'attempt_number',
            'comment'
        ]

class UserPracticalAssignmentDetailSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    assignment_name = serializers.CharField(source='practical_assignment.practical_assignment_name', read_only=True)
    status_name = serializers.CharField(source='submission_status.assignment_status_name', read_only=True)
    files = serializers.SerializerMethodField()
    
    class Meta:
        model = UserPracticalAssignment
        fields = [
            'id', 'user', 'user_name', 'practical_assignment', 'assignment_name',
            'submission_date', 'submission_status', 'status_name', 'attempt_number',
            'comment', 'files'
        ]
    
    def get_files(self, obj):
        files = obj.assignmentsubmissionfile_set.all()
        return AssignmentSubmissionFileSerializer(files, many=True).data

# 11. пользователи-курсы
class UserCourseSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    course_name = serializers.CharField(source='course.course_name', read_only=True)
    
    class Meta:
        model = UserCourse
        fields = [
            'id', 'user', 'user_name', 'course', 'course_name',
            'registration_date', 'status_course', 'payment_date',
            'completion_date', 'course_price', 'is_active'
        ]

# 12. обратная связь
class FeedbackSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user_practical_assignment.user.get_full_name', read_only=True)
    assignment_name = serializers.CharField(source='user_practical_assignment.practical_assignment.practical_assignment_name', read_only=True)
    
    class Meta:
        model = Feedback
        fields = [
            'id', 'user_practical_assignment', 'user_name', 'assignment_name',
            'score', 'is_passed', 'comment_feedback'
        ]

# 13. отзывы
class ReviewSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    course_name = serializers.CharField(source='course.course_name', read_only=True)
    
    class Meta:
        model = Review
        fields = [
            'id', 'course', 'course_name', 'user', 'user_name',
            'review_text', 'rating', 'publish_date', 'comment_review'
        ]

# 14. типы ответов
class AnswerTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerType
        fields = ['id', 'answer_type_name', 'answer_type_description']

# 15. тесты
class TestSerializer(serializers.ModelSerializer):
    lecture_name = serializers.CharField(source='lecture.lecture_name', read_only=True)
    course_name = serializers.CharField(source='lecture.course.course_name', read_only=True)
    
    class Meta:
        model = Test
        fields = [
            'id', 'test_name', 'test_description', 'is_final', 'lecture',
            'lecture_name', 'max_attempts', 'grading_form', 'passing_score',
            'is_active', 'course_name'
        ]

# 16. вопросы
class QuestionSerializer(serializers.ModelSerializer):
    test_name = serializers.CharField(source='test.test_name', read_only=True)
    answer_type_name = serializers.CharField(source='answer_type.answer_type_name', read_only=True)
    
    class Meta:
        model = Question
        fields = [
            'id', 'test', 'test_name', 'question_text', 'answer_type',
            'answer_type_name', 'question_score', 'correct_text', 'question_order'
        ]

# 17. варианты ответов
class ChoiceOptionSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.question_text', read_only=True)
    
    class Meta:
        model = ChoiceOption
        fields = ['id', 'question', 'question_text', 'option_text', 'is_correct']

# 18. пары соответствий
class MatchingPairSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.question_text', read_only=True)
    
    class Meta:
        model = MatchingPair
        fields = ['id', 'question', 'question_text', 'left_text', 'right_text']

# 19. ответы пользователей
class UserAnswerSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    question_text = serializers.CharField(source='question.question_text', read_only=True)
    
    class Meta:
        model = UserAnswer
        fields = [
            'id', 'user', 'user_name', 'question', 'question_text',
            'answer_text', 'answer_date', 'attempt_number', 'score'
        ]

# 20. выбранные варианты
class UserSelectedChoiceSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user_answer.user.get_full_name', read_only=True)
    question_text = serializers.CharField(source='user_answer.question.question_text', read_only=True)
    option_text = serializers.CharField(source='choice_option.option_text', read_only=True)
    
    class Meta:
        model = UserSelectedChoice
        fields = [
            'id', 'user_answer', 'user_name', 'choice_option', 'option_text',
            'question_text'
        ]

# 21. пользовательские сопоставления
class UserMatchingAnswerSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user_answer.user.get_full_name', read_only=True)
    question_text = serializers.CharField(source='user_answer.question.question_text', read_only=True)
    left_text = serializers.CharField(source='matching_pair.left_text', read_only=True)
    correct_right_text = serializers.CharField(source='matching_pair.right_text', read_only=True)
    
    class Meta:
        model = UserMatchingAnswer
        fields = [
            'id', 'user_answer', 'user_name', 'matching_pair', 'left_text',
            'user_selected_right_text', 'correct_right_text', 'question_text'
        ]

# 22. результаты тестов
class TestResultSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    test_name = serializers.CharField(source='test.test_name', read_only=True)
    
    class Meta:
        model = TestResult
        fields = [
            'id', 'user', 'user_name', 'test', 'test_name', 'completion_date',
            'final_score', 'is_passed', 'attempt_number'
        ]

# 23. сертификаты
class CertificateSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user_course.user.get_full_name', read_only=True)
    course_name = serializers.CharField(source='user_course.course.course_name', read_only=True)
    
    class Meta:
        model = Certificate
        fields = [
            'id', 'user_course', 'user_name', 'course_name',
            'certificate_number', 'issue_date', 'certificate_file_path'
        ]

# 24. файлы сдачи заданий
class AssignmentSubmissionFileSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user_assignment.user.get_full_name', read_only=True)
    assignment_name = serializers.CharField(source='user_assignment.practical_assignment.practical_assignment_name', read_only=True)
    
    class Meta:
        model = AssignmentSubmissionFile
        fields = [
            'id', 'user_assignment', 'user_name', 'assignment_name', 'file',
            'uploaded_at', 'file_name', 'file_size'
        ]

# 25. коды восстановления пароля
class PasswordResetCodeSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = PasswordResetCode
        fields = ['id', 'user', 'user_email', 'code', 'created_at', 'is_used']


class ViewCoursePracticalAssignmentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ViewCoursePracticalAssignments
        fields = '__all__'

class ViewCourseLecturesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ViewCourseLectures
        fields = '__all__'

class ViewCourseTestsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ViewCourseTests
        fields = '__all__'

class ViewAssignmentSubmissionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ViewAssignmentSubmissions
        fields = '__all__'

class CourseProgressSerializer(serializers.Serializer):
    course_id = serializers.IntegerField()
    course_name = serializers.CharField()
    progress = serializers.FloatField()
    total_points = serializers.IntegerField()
    user_points = serializers.IntegerField()

class TestSubmissionSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    test_id = serializers.IntegerField()
    answers = serializers.JSONField()

class AssignmentSubmissionSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    assignment_id = serializers.IntegerField()
    files = serializers.ListField(
        child=serializers.FileField(max_length=100000, allow_empty_file=False)
    )
    comment = serializers.CharField(required=False, allow_blank=True)

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm', 'first_name',
            'last_name', 'patronymic', 'role'
        ]
    
    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Пароли не совпадают")
        return data
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6)
    new_password = serializers.CharField()
    new_password_confirm = serializers.CharField()
    
    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError("Пароли не совпадают")
        return data