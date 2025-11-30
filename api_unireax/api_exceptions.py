from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException
from rest_framework import status
from django.http import JsonResponse
import logging
import functools

logger = logging.getLogger(__name__)

class CustomAPIException(APIException):
    """Базовое кастомное исключение для API"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Произошла ошибка'
    default_code = 'error'
    
    def __init__(self, detail=None, code=None, status_code=None):
        if detail is not None:
            if isinstance(detail, dict):
                self.detail = detail
            else:
                self.detail = str(detail)
        else:
            self.detail = self.default_detail
            
        if code is not None:
            self.code = code
        else:
            self.code = self.default_code
            
        if status_code is not None:
            self.status_code = status_code

class ValidationError(CustomAPIException):
    """Ошибка валидации данных"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Ошибка валидации данных'
    default_code = 'validation_error'

class NotFoundError(CustomAPIException):
    """Объект не найден"""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'Запрашиваемый объект не найден'
    default_code = 'not_found'

class PermissionDeniedError(CustomAPIException):
    """Доступ запрещен"""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'Доступ запрещен'
    default_code = 'permission_denied'

class AuthenticationError(CustomAPIException):
    """Ошибка аутентификации"""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Требуется аутентификация'
    default_code = 'authentication_error'

class BusinessLogicError(CustomAPIException):
    """Ошибка бизнес-логики"""
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = 'Ошибка бизнес-логики'
    default_code = 'business_logic_error'

class ConflictError(CustomAPIException):
    """Конфликт данных (например, дублирование)"""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Конфликт данных'
    default_code = 'conflict_error'

class ServiceUnavailableError(CustomAPIException):
    """Сервис временно недоступен"""
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Сервис временно недоступен'
    default_code = 'service_unavailable'

class CourseNotFoundError(NotFoundError):
    """Курс не найден"""
    default_detail = 'Курс не найден'
    default_code = 'course_not_found'

class UserNotFoundError(NotFoundError):
    """Пользователь не найден"""
    default_detail = 'Пользователь не найден'
    default_code = 'user_not_found'

class InsufficientPermissionsError(PermissionDeniedError):
    """Недостаточно прав"""
    default_detail = 'Недостаточно прав для выполнения операции'
    default_code = 'insufficient_permissions'

class CourseEnrollmentError(BusinessLogicError):
    """Ошибка записи на курс"""
    default_detail = 'Невозможно записаться на курс'
    default_code = 'course_enrollment_error'

class CourseCompletionError(BusinessLogicError):
    """Ошибка завершения курса"""
    default_detail = 'Невозможно завершить курс'
    default_code = 'course_completion_error'

class AssignmentSubmissionError(BusinessLogicError):
    """Ошибка сдачи задания"""
    default_detail = 'Ошибка при сдаче задания'
    default_code = 'assignment_submission_error'

class CertificateGenerationError(BusinessLogicError):
    """Ошибка генерации сертификата"""
    default_detail = 'Ошибка при генерации сертификата'
    default_code = 'certificate_generation_error'

class UserAlreadyEnrolledError(ConflictError):
    """Пользователь уже записан на курс"""
    default_detail = 'Пользователь уже записан на этот курс'
    default_code = 'user_already_enrolled'

class CourseFullError(BusinessLogicError):
    """Курс заполнен"""
    default_detail = 'На курсе нет свободных мест'
    default_code = 'course_full'

class InvalidFileError(ValidationError):
    """Невалидный файл"""
    default_detail = 'Недопустимый формат или размер файла'
    default_code = 'invalid_file'

class PaymentRequiredError(CustomAPIException):
    """Требуется оплата"""
    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = 'Требуется оплата для доступа к курсу'
    default_code = 'payment_required'

from django.http import Http404
def custom_exception_handler(exc, context):
    """
    Кастомный обработчик исключений для DRF
    """
    logger.error(f"API Exception: {exc}", exc_info=True)
    
    if isinstance(exc, Http404):
        exc = NotFoundError("Запрашиваемый ресурс не найден")
    
    response = exception_handler(exc, context)
    
    if response is not None:
        if isinstance(response.data, dict):
            error_code = getattr(exc, 'code', 
                               getattr(exc, 'default_code', 'unknown_error'))
            
            if hasattr(exc, 'detail'):
                if isinstance(exc.detail, (list, dict)):
                    error_message = str(exc.detail)
                else:
                    error_message = exc.detail
            else:
                error_message = str(exc)
            
            error_data = {
                'success': False,
                'error': {
                    'code': error_code,
                    'message': error_message,
                    'type': exc.__class__.__name__
                }
            }
            
            if hasattr(exc, 'get_full_details'):
                try:
                    error_data['error']['details'] = exc.get_full_details()
                except:
                    pass
            elif hasattr(exc, 'detail') and isinstance(exc.detail, dict):
                error_data['error']['details'] = exc.detail
            
            response.data = error_data
    
    return response

class ErrorResponse:
    """Утилитарный класс для создания стандартизированных ошибок"""
    
    @staticmethod
    def create_error_response(code, message, details=None, status_code=status.HTTP_400_BAD_REQUEST):
        """Создает стандартизированный ответ с ошибкой"""
        error_data = {
            'success': False,
            'error': {
                'code': code,
                'message': message,
                'type': 'CustomError'
            }
        }
        
        if details is not None:
            error_data['error']['details'] = details
        
        return JsonResponse(error_data, status=status_code)
    
    @staticmethod
    def validation_error(message, details=None):
        return ErrorResponse.create_error_response(
            'validation_error', 
            message, 
            details, 
            status.HTTP_400_BAD_REQUEST
        )
    
    @staticmethod
    def not_found(message, details=None):
        return ErrorResponse.create_error_response(
            'not_found', 
            message, 
            details, 
            status.HTTP_404_NOT_FOUND
        )
    
    @staticmethod
    def permission_denied(message, details=None):
        return ErrorResponse.create_error_response(
            'permission_denied', 
            message, 
            details, 
            status.HTTP_403_FORBIDDEN
        )

def handle_api_exceptions(func):
    """
    Декоратор для автоматической обработки исключений в API функциях
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except CustomAPIException as e:
            logger.warning(f"Custom API Exception in {func.__name__}: {e}")
            return ErrorResponse.create_error_response(
                getattr(e, 'default_code', 'custom_error'),
                str(e.detail) if hasattr(e, 'detail') else str(e),
                status_code=getattr(e, 'status_code', status.HTTP_400_BAD_REQUEST)
            )
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            return ErrorResponse.create_error_response(
                'internal_server_error',
                'Внутренняя ошибка сервера',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    return wrapper