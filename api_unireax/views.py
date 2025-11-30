from django.shortcuts import render
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Sum, Q, Avg
from django.utils import timezone
from .serializers import *
from .permission import *
from .api_exceptions import *

# 1. роли пользователей
class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage

# 2. пользователи
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage
    
    @action(detail=False, methods=['post'], permission_classes=[])
    @handle_api_exceptions
    def register(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'success': True,
                'message': 'Пользователь успешно зарегистрирован',
                'user_id': user.id
            }, status=status.HTTP_201_CREATED)
        raise ValidationError(detail=serializer.errors)
    
    @action(detail=False, methods=['post'], permission_classes=[])
    @handle_api_exceptions
    def login(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            return Response({
                'success': True,
                'message': 'Вход выполнен успешно'
            })
        raise ValidationError(detail=serializer.errors)

# 3. категории курсов
class CourseCategoryViewSet(viewsets.ModelViewSet):
    queryset = CourseCategory.objects.all()
    serializer_class = CourseCategorySerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage

# 4. типы курсов
class CourseTypeViewSet(viewsets.ModelViewSet):
    queryset = CourseType.objects.all()
    serializer_class = CourseTypeSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage

# 5. статусы заданий
class AssignmentStatusViewSet(viewsets.ModelViewSet):
    queryset = AssignmentStatus.objects.all()
    serializer_class = AssignmentStatusSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage

# 6. Курсы
class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CourseDetailSerializer
        return CourseSerializer
    
    @action(detail=True, methods=['get'])
    @handle_api_exceptions
    def progress(self, request, pk=None):
        course = self.get_object()
        user_id = request.query_params.get('user_id') or request.user.id
        
        if not user_id:
            raise ValidationError(detail='Необходим user_id')
        
        try:
            progress_data = {
                'course_id': course.id,
                'course_name': course.course_name,
                'progress': course.get_completion(user_id),
                'total_points': course.total_points(),
                'rating': course.rating
            }
            
            serializer = CourseProgressSerializer(progress_data)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except Course.DoesNotExist:
            raise CourseNotFoundError()
        except Exception as e:
            raise BusinessLogicError(detail=f'Ошибка при получении прогресса: {str(e)}')

# 7. Курсы-преподаватели
class CourseTeacherViewSet(viewsets.ModelViewSet):
    queryset = CourseTeacher.objects.all()
    serializer_class = CourseTeacherSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage

# 8. Лекции
class LectureViewSet(viewsets.ModelViewSet):
    queryset = Lecture.objects.all()
    serializer_class = LectureSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage

# 9. Практические задания
class PracticalAssignmentViewSet(viewsets.ModelViewSet):
    queryset = PracticalAssignment.objects.all()
    serializer_class = PracticalAssignmentSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage

# 10. Пользователи и их практические работы
class UserPracticalAssignmentViewSet(viewsets.ModelViewSet):
    queryset = UserPracticalAssignment.objects.all()
    serializer_class = UserPracticalAssignmentSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return UserPracticalAssignmentDetailSerializer
        return UserPracticalAssignmentSerializer
    
    @action(detail=True, methods=['post'])
    @handle_api_exceptions
    def submit_files(self, request, pk=None):
        user_assignment = self.get_object()
        serializer = AssignmentSubmissionSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                return Response({
                    'success': True,
                    'message': 'Файлы успешно отправлены'
                })
            except Exception as e:
                raise AssignmentSubmissionError(detail=f'Ошибка при отправке файлов: {str(e)}')
        
        raise ValidationError(detail=serializer.errors)

# 11. Пользователи-курсы
class UserCourseViewSet(viewsets.ModelViewSet):
    queryset = UserCourse.objects.all()
    serializer_class = UserCourseSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage
    
    @handle_api_exceptions
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            try:
                self.perform_create(serializer)
                return Response({
                    'success': True,
                    'message': 'Запись на курс выполнена успешно',
                    'data': serializer.data
                }, status=status.HTTP_201_CREATED)
            except UserCourse.DoesNotExist:
                raise UserNotFoundError()
            except Course.DoesNotExist:
                raise CourseNotFoundError()
            except Exception as e:
                if 'уже записан' in str(e).lower():
                    raise UserAlreadyEnrolledError()
                elif 'мест' in str(e).lower():
                    raise CourseFullError()
                else:
                    raise CourseEnrollmentError(detail=str(e))
        
        raise ValidationError(detail=serializer.errors)

# 12. Обратная связь
class FeedbackViewSet(viewsets.ModelViewSet):
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage

# 13. Отзывы
class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage

# 14. Типы ответов
class AnswerTypeViewSet(viewsets.ModelViewSet):
    queryset = AnswerType.objects.all()
    serializer_class = AnswerTypeSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage

# 15. Тесты
class TestViewSet(viewsets.ModelViewSet):
    queryset = Test.objects.all()
    serializer_class = TestSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage
    
    @action(detail=True, methods=['post'])
    @handle_api_exceptions
    def submit(self, request, pk=None):
        test = self.get_object()
        serializer = TestSubmissionSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                return Response({
                    'success': True,
                    'message': 'Тест успешно отправлен'
                })
            except Exception as e:
                raise BusinessLogicError(detail=f'Ошибка при отправке теста: {str(e)}')
        
        raise ValidationError(detail=serializer.errors)

# 16. Вопросы
class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage

# 17. Варианты ответов
class ChoiceOptionViewSet(viewsets.ModelViewSet):
    queryset = ChoiceOption.objects.all()
    serializer_class = ChoiceOptionSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage

# 18. Пары соответствий
class MatchingPairViewSet(viewsets.ModelViewSet):
    queryset = MatchingPair.objects.all()
    serializer_class = MatchingPairSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage

# 19. Ответы пользователей
class UserAnswerViewSet(viewsets.ModelViewSet):
    queryset = UserAnswer.objects.all()
    serializer_class = UserAnswerSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage

# 20. Выбранные варианты
class UserSelectedChoiceViewSet(viewsets.ModelViewSet):
    queryset = UserSelectedChoice.objects.all()
    serializer_class = UserSelectedChoiceSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage

# 21. Пользовательские сопоставления
class UserMatchingAnswerViewSet(viewsets.ModelViewSet):
    queryset = UserMatchingAnswer.objects.all()
    serializer_class = UserMatchingAnswerSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage

# 22. Результаты тестов
class TestResultViewSet(viewsets.ModelViewSet):
    queryset = TestResult.objects.all()
    serializer_class = TestResultSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage

# 23. Сертификаты
class CertificateViewSet(viewsets.ModelViewSet):
    queryset = Certificate.objects.all()
    serializer_class = CertificateSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage
    
    @handle_api_exceptions
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            try:
                self.perform_create(serializer)
                return Response({
                    'success': True,
                    'message': 'Сертификат успешно создан',
                    'data': serializer.data
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                raise CertificateGenerationError(detail=f'Ошибка генерации сертификата: {str(e)}')
        
        raise ValidationError(detail=serializer.errors)

# 24. Файлы сдачи заданий
class AssignmentSubmissionFileViewSet(viewsets.ModelViewSet):
    queryset = AssignmentSubmissionFile.objects.all()
    serializer_class = AssignmentSubmissionFileSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage

# 25. Коды восстановления пароля
class PasswordResetCodeViewSet(mixins.CreateModelMixin, 
                              mixins.RetrieveModelMixin, 
                              viewsets.GenericViewSet):
    queryset = PasswordResetCode.objects.all()
    serializer_class = PasswordResetCodeSerializer
    permission_classes = []
    pagination_class = PaginationPage
    
    @action(detail=False, methods=['post'])
    @handle_api_exceptions
    def request_reset(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            try:
                return Response({
                    'success': True,
                    'message': 'Код восстановления отправлен'
                })
            except Exception as e:
                raise ServiceUnavailableError(detail='Сервис восстановления временно недоступен')
        
        raise ValidationError(detail=serializer.errors)
    
    @action(detail=False, methods=['post'])
    @handle_api_exceptions
    def confirm_reset(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            try:
                return Response({
                    'success': True,
                    'message': 'Пароль успешно изменен'
                })
            except Exception as e:
                raise BusinessLogicError(detail='Ошибка при сбросе пароля')
        
        raise ValidationError(detail=serializer.errors)


class ViewCoursePracticalAssignmentsViewSet(mixins.ListModelMixin, 
                                           mixins.RetrieveModelMixin, 
                                           viewsets.GenericViewSet):
    queryset = ViewCoursePracticalAssignments.objects.all()
    serializer_class = ViewCoursePracticalAssignmentsSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage

class ViewCourseLecturesViewSet(mixins.ListModelMixin, 
                               mixins.RetrieveModelMixin, 
                               viewsets.GenericViewSet):
    queryset = ViewCourseLectures.objects.all()
    serializer_class = ViewCourseLecturesSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage

class ViewCourseTestsViewSet(mixins.ListModelMixin, 
                            mixins.RetrieveModelMixin, 
                            viewsets.GenericViewSet):
    queryset = ViewCourseTests.objects.all()
    serializer_class = ViewCourseTestsSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage

class ViewAssignmentSubmissionsViewSet(mixins.ListModelMixin, 
                                      mixins.RetrieveModelMixin, 
                                      viewsets.GenericViewSet):
    queryset = ViewAssignmentSubmissions.objects.all()
    serializer_class = ViewAssignmentSubmissionsSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage


class CourseAnalyticsViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage
    
    @handle_api_exceptions
    def list(self, request):
        try:
            courses_data = Course.objects.annotate(
                student_count=Count('usercourse', filter=Q(usercourse__is_active=True)),
                avg_rating=Avg('review__rating')
            ).values('id', 'course_name', 'student_count', 'avg_rating')
            
            return Response({
                'success': True,
                'data': list(courses_data)
            })
        except Exception as e:
            raise BusinessLogicError(detail=f'Ошибка при получении аналитики: {str(e)}')

class UserProgressViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage
    
    @handle_api_exceptions
    def list(self, request):
        user_id = request.query_params.get('user_id')
        if not user_id:
            raise ValidationError(detail='Необходим user_id')
        
        try:
            user_courses = UserCourse.objects.filter(user_id=user_id, is_active=True)
            progress_data = []
            
            for user_course in user_courses:
                progress_data.append({
                    'course_id': user_course.course.id,
                    'course_name': user_course.course.course_name,
                    'progress': user_course.course.get_completion(user_id),
                    'registration_date': user_course.registration_date,
                    'status': user_course.status_course
                })
            
            return Response({
                'success': True,
                'data': progress_data
            })
        except User.DoesNotExist:
            raise UserNotFoundError()
        except Exception as e:
            raise BusinessLogicError(detail=f'Ошибка при получении прогресса: {str(e)}')


class PlatformStatsViewSet(viewsets.ViewSet):
    """
    ViewSet для получения статистики платформы
    """
    permission_classes = [] 
    
    @action(detail=False, methods=['get'])
    @handle_api_exceptions
    def stats(self, request):
        """
        Получение статистики платформы
        """
        try:
            students_count = User.objects.filter(role__role_name='слушатель курсов').count()
            courses_count = Course.objects.filter(is_active=True).count()

            stats = {
                'students': students_count,
                'courses': courses_count,
            }
            
            return Response({
                'success': True,
                'data': stats
            })
        except Exception as e:
            raise BusinessLogicError(detail=f'Ошибка при получении статистики: {str(e)}')
        

class TestExceptionsViewSet(viewsets.ViewSet):
    """
    ViewSet для тестирования кастомных исключений
    """
    permission_classes = []  
    
    @action(detail=False, methods=['get'])
    def test_validation_error(self, request):
        """Тест ошибки валидации"""
        raise ValidationError(detail="Тестовое сообщение валидации")
    
    @action(detail=False, methods=['get'])
    def test_not_found_error(self, request):
        """Тест ошибки 'не найдено'"""
        raise CourseNotFoundError()
    
    @action(detail=False, methods=['get'])
    def test_permission_denied(self, request):
        """Тест ошибки доступа"""
        raise InsufficientPermissionsError()
    
    @action(detail=False, methods=['get'])
    def test_business_logic_error(self, request):
        """Тест ошибки бизнес-логики"""
        raise CourseEnrollmentError(detail="Не удалось записаться на курс")
    
    @action(detail=False, methods=['get'])
    def test_conflict_error(self, request):
        """Тест конфликта"""
        raise UserAlreadyEnrolledError()
    
    @action(detail=False, methods=['get'])
    def test_custom_message(self, request):
        """Тест с кастомным сообщением"""
        message = request.query_params.get('message', 'Кастомное сообщение')
        raise BusinessLogicError(detail=message)
    
    @action(detail=False, methods=['get'])
    def test_unhandled_error(self, request):
        """Тест необработанного исключения"""
        result = 1 / 0
        return Response({'result': result})