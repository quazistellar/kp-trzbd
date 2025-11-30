from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import connection
from django.db.models import Avg, Func, DecimalField
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from datetime import timedelta
import random
import string

# 1. роли пользователей
class Role(models.Model):
    role_name = models.CharField(max_length=255, unique=True, verbose_name='Название роли')

    def __str__(self):
        return self.role_name
    
    def get_previous_name(self):
        return self._state.db

    class Meta:
        db_table = 'role'
        verbose_name = 'Роль'
        verbose_name_plural = 'Роли'

# 2. пользователи
class User(AbstractUser): 
    patronymic = models.CharField(max_length=35, blank=True, verbose_name='Отчество', null=True)
    is_verified = models.BooleanField(default=False, verbose_name='Подтверждён')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, verbose_name='Роль', null=True)
    profile_theme = models.CharField(max_length=30, null=True, blank=True, verbose_name='Цветовая тема приложения пользователя')
    position = models.CharField(max_length=100, null=True, blank=True, verbose_name='Полное название должности по месту работы')
    educational_institution = models.CharField(max_length=100, null=True, blank=True, verbose_name='Учебное заведение')
    certificat_from_the_place_of_work_path = models.FileField(
        max_length=255, 
        null=True, 
        blank=True, 
        verbose_name='Справка с места работы/документ об образовании',
        upload_to='certificates/',
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'pdf'])
        ],
        help_text='Форматы: JPG, PNG, PDF. Максимальный размер: 10 МБ'
    )
    
    def clean(self):
        super().clean()
        if self.certificat_from_the_place_of_work_path:
            if self.certificat_from_the_place_of_work_path.size > 10 * 1024 * 1024: 
                raise ValidationError({
                    'certificat_from_the_place_of_work_path': 'Файл слишком большой. Максимальный размер: 10 МБ'
                })
            
    def __str__(self):
        return f'{self.last_name} {self.first_name}'
    
    @property
    def is_admin(self):
        return self.role and self.role.role_name == "администратор"

    class Meta:
        db_table = 'user'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

# 3. категории курсов
class CourseCategory(models.Model):
    course_category_name = models.CharField(max_length=255, verbose_name='Название категории курса', unique=True)

    def __str__(self):
        return self.course_category_name

    class Meta:
        db_table = 'course_category'
        verbose_name = 'Категория курса'
        verbose_name_plural = 'Категории курсов'

# 4. типы курсов
class CourseType(models.Model):
    course_type_name = models.CharField(max_length=255, verbose_name='Название типа курса', unique=True)
    course_type_description = models.TextField(null=True, blank=True, verbose_name='Описание типа курса')

    def __str__(self):
        return self.course_type_name

    class Meta:
        db_table = 'course_type'
        verbose_name = 'Тип курса'
        verbose_name_plural = 'Типы курсов'

# 5. статусы заданий
class AssignmentStatus(models.Model):
    assignment_status_name = models.CharField(max_length=255, unique=True, verbose_name='Название статуса задания')

    def __str__(self):
        return self.assignment_status_name

    class Meta:
        db_table = 'assignment_status'
        verbose_name = 'Статус задания'
        verbose_name_plural = 'Статусы заданий'

# 6. курсы
class Course(models.Model):
    course_name = models.CharField(max_length=255, verbose_name='Название курса')
    course_description = models.TextField(null=True, blank=True, verbose_name='Описание курса')
    course_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Цена курса')
    course_category = models.ForeignKey(CourseCategory, on_delete=models.CASCADE, verbose_name='Категория курса')
    course_photo_path = models.ImageField(upload_to='photos/', null=True, blank=True, verbose_name='Фото курса', validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])])
    has_certificate = models.BooleanField(default=False, verbose_name='Есть сертификат')
    course_max_places = models.IntegerField(null=True, blank=True, verbose_name='Максимум мест')
    course_hours = models.IntegerField(verbose_name='Количество часов')
    is_completed = models.BooleanField(default=False, verbose_name='Завершён')
    code_room = models.CharField(max_length=255, null=True, blank=True, verbose_name='Код комнаты')
    course_type = models.ForeignKey(CourseType, on_delete=models.CASCADE, verbose_name='Тип курса')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Создан пользователем', null=True, blank=True)
    is_active = models.BooleanField(default=True, verbose_name='Активность курса')

    def clean(self):
        if self.created_by is not None:
            if not hasattr(self.created_by, 'role') or self.created_by.role.role_name != 'методист':
                raise ValidationError('Поле created_by должно ссылаться на пользователя с ролью методист')

    def __str__(self):
        return self.course_name

    @property
    def rating(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT calculate_course_rating(%s)", [self.id])
            return cursor.fetchone()[0] or 0

    def get_completion(self, user_id):
        with connection.cursor() as cursor:
            cursor.execute("SELECT calculate_course_completion(%s, %s)", [user_id, self.id])
            return cursor.fetchone()[0] or 0

    def total_points(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT calculate_total_course_points(%s)", [self.id])
            return cursor.fetchone()[0] or 0

    class Meta:
        db_table = 'course'
        verbose_name = 'Курс'
        verbose_name_plural = 'Курсы'

# 7. курсы_преподаватели
class CourseTeacher(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name='Курс')
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Преподаватель')
    start_date = models.DateField(default=timezone.now, 
                                  null=True,  
                                  blank=True,
                                  verbose_name='Дата начала курса')
    is_active = models.BooleanField(default=True, verbose_name='Активность преподавателя на курсе')

    def clean(self):
        if not self.teacher.role.role_name == 'преподаватель':
            raise ValidationError('Поле teacher_id должно ссылаться на пользователя с ролью преподавателя')

    def __str__(self):
        return f'{self.teacher} - {self.course}'

    class Meta:
        db_table = 'course_teacher'
        verbose_name = 'Преподаватель курса'
        verbose_name_plural = 'Преподаватели курсов'
        unique_together = ('course', 'teacher')

# 8. лекции
class Lecture(models.Model):
    lecture_name = models.CharField(max_length=255, verbose_name='Название лекции')
    lecture_content = models.TextField(verbose_name='Содержание лекции')
    lecture_document_path = models.FileField(upload_to='lectures/', null=True, blank=True, verbose_name='Документ лекции', validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx'])])
    lecture_order = models.IntegerField(verbose_name='Порядок лекции')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name='Курс')
    is_active = models.BooleanField(default=True, verbose_name='Активность лекции')

    def __str__(self):
        return self.lecture_name

    class Meta:
        db_table = 'lecture'
        verbose_name = 'Лекция'
        verbose_name_plural = 'Лекции'

# 9. практические задания
class PracticalAssignment(models.Model):
    GRADING_TYPE_CHOICES = [
        ('points', 'По баллам'),
        ('pass_fail', 'Зачёт/незачёт'),
    ]
    practical_assignment_name = models.CharField(max_length=255, verbose_name='Название задания')
    practical_assignment_description = models.TextField(verbose_name='Описание задания')
    assignment_document_path = models.FileField(upload_to='assignments/', null=True, blank=True, verbose_name='Документ задания', validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx'])])
    assignment_criteria = models.TextField(null=True, blank=True, verbose_name='Критерии задания')
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, verbose_name='Лекция')
    assignment_deadline = models.DateTimeField(verbose_name='Срок сдачи', null=True, blank=True)
    grading_type = models.CharField(max_length=20, choices=GRADING_TYPE_CHOICES, verbose_name='Тип оценки')
    max_score = models.IntegerField(null=True, blank=True, verbose_name='Максимальный балл')
    is_active = models.BooleanField(default=True, verbose_name='Активность практического задания')

    def clean(self):
        if self.grading_type == 'points' and (self.max_score is None or self.max_score <= 0):
            raise ValidationError('Для grading_type "points" max_score должен быть больше 0')
        if self.grading_type == 'pass_fail' and self.max_score is not None:
            raise ValidationError('Для grading_type "pass_fail" max_score должен быть NULL')

    def __str__(self):
        return self.practical_assignment_name

    class Meta:
        db_table = 'practical_assignment'
        verbose_name = 'Практическое задание'
        verbose_name_plural = 'Практические задания'

# 10. пользователи и их практические работы
class UserPracticalAssignment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    practical_assignment = models.ForeignKey(PracticalAssignment, on_delete=models.CASCADE, verbose_name='Практическое задание')
    submission_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата сдачи')
    submission_status = models.ForeignKey(AssignmentStatus, on_delete=models.CASCADE, verbose_name='Статус сдачи')
    attempt_number = models.IntegerField(default=1, verbose_name='Номер попытки')
    comment = models.TextField(null=True, blank=True, verbose_name='Комментарий к сдаче')  # Новое поле для комментария

    def clean(self):
        if self.attempt_number <= 0:
            raise ValidationError('Номер попытки должен быть больше 0')

    def __str__(self):
        return f'{self.user} - {self.practical_assignment}'

    @property
    def files(self):
        return self.assignmentsubmissionfile_set.all()

    class Meta:
        db_table = 'user_practical_assignment'
        verbose_name = 'Сдача практического задания'
        verbose_name_plural = 'Сдачи практических заданий'

# 11. пользователи_курсы
class UserCourse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name='Курс')
    registration_date = models.DateField(default=timezone.now, verbose_name='Дата регистрации')
    status_course = models.BooleanField(default=False, verbose_name='Статус курса')
    payment_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата оплаты')
    completion_date = models.DateField(null=True, blank=True, verbose_name='Дата завершения')
    course_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Цена курса')
    is_active = models.BooleanField(default=True, verbose_name='Активность слушателя на курсе')

    def __str__(self):
        return f'{self.user} - {self.course}'

    class Meta:
        db_table = 'user_course'
        verbose_name = 'Пользователь на курсе'
        verbose_name_plural = 'Пользователи на курсах'
        unique_together = ('user', 'course')

# 12. обратная связь
class Feedback(models.Model):
    user_practical_assignment = models.OneToOneField(UserPracticalAssignment, on_delete=models.CASCADE, verbose_name='Сдача задания')
    score = models.IntegerField(null=True, blank=True, verbose_name='Балл')
    is_passed = models.BooleanField(null=True, blank=True, verbose_name='Зачтено')
    comment_feedback = models.TextField(null=True, blank=True, verbose_name='Комментарий')

    def clean(self):
        grading_type = self.user_practical_assignment.practical_assignment.grading_type
        if grading_type == 'points' and (self.score is None or self.is_passed is not None):
            raise ValidationError('Для grading_type "points" score должен быть заполнен, а is_passed должен быть NULL')
        if grading_type == 'pass_fail' and (self.is_passed is None or self.score is not None):
            raise ValidationError('Для grading_type "pass_fail" is_passed должен быть заполнен, а score должен быть NULL')

    def __str__(self):
        return f'Обратная связь для {self.user_practical_assignment}'

    class Meta:
        db_table = 'feedback'
        verbose_name = 'Обратная связь'
        verbose_name_plural = 'Обратные связи'

# 13. отзывы
class Review(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name='Курс')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    review_text = models.TextField(verbose_name='Текст отзывы')
    rating = models.IntegerField(verbose_name='Рейтинг', choices=[(i, i) for i in range(1, 6)])
    publish_date = models.DateTimeField(default=timezone.now, verbose_name='Дата публикации')
    comment_review = models.TextField(null=True, blank=True, verbose_name='Комментарий к отзыву')

    def __str__(self):
        return f'Отзыв от {self.user} на {self.course}'

    class Meta:
        db_table = 'review'
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        unique_together = ('course', 'user')

# 14. типы ответов
class AnswerType(models.Model):
    answer_type_name = models.CharField(max_length=50, unique=True, verbose_name='Название типа ответа')
    answer_type_description = models.TextField(null=True, blank=True, verbose_name='Описание типа ответа')

    def __str__(self):
        return self.answer_type_name

    class Meta:
        db_table = 'answer_type'
        verbose_name = 'Тип ответа'
        verbose_name_plural = 'Типы ответов'

# 15. тесты
class Test(models.Model):
    GRADING_FORM_CHOICES = [
        ('points', 'По баллам'),
        ('pass_fail', 'Зачёт/незачёт'),
    ]
    test_name = models.CharField(max_length=255, verbose_name='Название теста')
    test_description = models.TextField(null=True, blank=True, verbose_name='Описание теста')
    is_final = models.BooleanField(default=False, verbose_name='Финальный тест')
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE, verbose_name='Лекция')
    max_attempts = models.IntegerField(null=True, blank=True, verbose_name='Максимум попыток')
    grading_form = models.CharField(max_length=20, choices=GRADING_FORM_CHOICES, verbose_name='Форма оценки')
    passing_score = models.IntegerField(null=True, blank=True, verbose_name='Проходной балл')
    is_active = models.BooleanField(default=True, verbose_name='Активность теста')

    def clean(self):
        if self.grading_form == 'points' and (self.passing_score is None or self.passing_score < 0):
            raise ValidationError('Для grading_form "points" passing_score должен быть >= 0')
        if self.grading_form == 'pass_fail' and self.passing_score is not None:
            raise ValidationError('Для grading_form "pass_fail" passing_score должен быть NULL')
        if self.max_attempts is not None and self.max_attempts <= 0:
            raise ValidationError('Максимум попыток должен быть больше 0')

    def __str__(self):
        return self.test_name

    class Meta:
        db_table = 'test'
        verbose_name = 'Тест'
        verbose_name_plural = 'Тесты'

# 16. вопросы
class Question(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, verbose_name='Тест')
    question_text = models.TextField(verbose_name='Текст вопроса')
    answer_type = models.ForeignKey(AnswerType, on_delete=models.CASCADE, verbose_name='Тип ответа')
    question_score = models.IntegerField(default=1, verbose_name='Балл за вопрос')
    correct_text = models.TextField(null=True, blank=True, verbose_name='Правильный ответ')
    question_order = models.IntegerField(verbose_name='Порядок вопроса')

    def clean(self):
        if self.question_score < 0:
            raise ValidationError('Балл за вопрос должен быть >= 0')

    def __str__(self):
        return self.question_text[:50]

    class Meta:
        db_table = 'question'
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'

# 17. варианты ответов
class ChoiceOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name='Вопрос')
    option_text = models.TextField(verbose_name='Текст варианта')
    is_correct = models.BooleanField(verbose_name='Правильный')

    def __str__(self):
        return self.option_text[:50]

    class Meta:
        db_table = 'choice_option'
        verbose_name = 'Вариант ответа'
        verbose_name_plural = 'Варианты ответов'

# 18. пары соответствий
class MatchingPair(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name='Вопрос')
    left_text = models.TextField(verbose_name='Левый текст')
    right_text = models.TextField(verbose_name='Правый текст')

    def __str__(self):
        return f'{self.left_text} -> {self.right_text}'

    class Meta:
        db_table = 'matching_pair'
        verbose_name = 'Пара соответствия'
        verbose_name_plural = 'Пары соответствия'

# 19. ответы пользователей
class UserAnswer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name='Вопрос')
    answer_text = models.TextField(null=True, blank=True, verbose_name='Текст ответа')
    answer_date = models.DateTimeField(default=timezone.now, verbose_name='Дата ответа')
    attempt_number = models.IntegerField(default=1, verbose_name='Номер попытки')
    score = models.IntegerField(null=True, blank=True, verbose_name='Балл')

    def clean(self):
        if self.attempt_number <= 0:
            raise ValidationError('Номер попытки должен быть больше 0')

    def __str__(self):
        return f'{self.user} - {self.question}'

    class Meta:
        db_table = 'user_answer'
        verbose_name = 'Ответ пользователя'
        verbose_name_plural = 'Ответы пользователей'
        unique_together = ('user', 'question', 'attempt_number')

# 20. выбранные варианты для single_choice и multiple_choice
class UserSelectedChoice(models.Model):
    user_answer = models.ForeignKey(UserAnswer, on_delete=models.CASCADE, verbose_name='Ответ пользователя')
    choice_option = models.ForeignKey(ChoiceOption, on_delete=models.CASCADE, verbose_name='Выбранный вариант')

    def __str__(self):
        return f'{self.user_answer} - {self.choice_option}'

    class Meta:
        db_table = 'user_selected_choice'
        verbose_name = 'Выбранный вариант'
        verbose_name_plural = 'Выбранные варианты'
        unique_together = ('user_answer', 'choice_option')

# 21. пользовательские сопоставления для matching
class UserMatchingAnswer(models.Model):
    user_answer = models.ForeignKey(UserAnswer, on_delete=models.CASCADE, verbose_name='Ответ пользователя')
    matching_pair = models.ForeignKey(MatchingPair, on_delete=models.CASCADE, verbose_name='Пара соответствия')
    user_selected_right_text = models.TextField(verbose_name='Выбранный правый текст')

    def __str__(self):
        return f'{self.user_answer} - {self.matching_pair}'

    class Meta:
        db_table = 'user_matching_answer'
        verbose_name = 'Ответ на сопоставление'
        verbose_name_plural = 'Ответы на сопоставления'
        unique_together = ('user_answer', 'matching_pair')

# 22. результаты тестов
class TestResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    test = models.ForeignKey(Test, on_delete=models.CASCADE, verbose_name='Тест')
    completion_date = models.DateTimeField(default=timezone.now, verbose_name='Дата завершения')
    final_score = models.IntegerField(null=True, blank=True, verbose_name='Итоговый балл')
    is_passed = models.BooleanField(null=True, blank=True, verbose_name='Зачтено')
    attempt_number = models.IntegerField(default=1, verbose_name='Номер попытки')

    def clean(self):
        if self.test.grading_form == 'points' and (self.final_score is None or self.is_passed is not None):
            raise ValidationError('Для grading_form "points" final_score должен быть заполнен, а is_passed должен быть NULL')
        if self.test.grading_form == 'pass_fail' and (self.is_passed is None or self.final_score is not None):
            raise ValidationError('Для grading_form "pass_fail" is_passed должен быть заполнен, а final_score должен быть NULL')
        if self.attempt_number <= 0:
            raise ValidationError('Номер попытки должен быть больше 0')

    def __str__(self):
        return f'{self.user} - {self.test}'

    class Meta:
        db_table = 'test_result'
        verbose_name = 'Результат теста'
        verbose_name_plural = 'Результаты тестов'
        unique_together = ('user', 'test', 'attempt_number')


from .utils.additional_function import calculate_course_progress
# 23. сертификаты
class Certificate(models.Model):
    user_course = models.OneToOneField(UserCourse, on_delete=models.CASCADE, verbose_name='Пользователь на курсе')
    certificate_number = models.CharField(max_length=255, unique=True, verbose_name='Номер сертификата')
    issue_date = models.DateField(verbose_name='Дата выдачи')
    certificate_file_path = models.CharField(max_length=255, null=True, blank=True, verbose_name='Путь к файлу сертификата')

    def clean(self):
        if not self.user_course.status_course:
            raise ValidationError('Сертификат не может быть выдан: курс не завершён')
        
        if not self.user_course.course.is_completed:
            raise ValidationError('Сертификат не может быть выдан: курс ещё пополняется материалами')
        
        # Используем функцию БД для проверки прогресса
        progress = calculate_course_progress(self.user_course.user, self.user_course.course)
        if progress < 100:
            raise ValidationError(f'Сертификат не может быть выдан: прогресс курса {progress}% (требуется 100%)')

    def save(self, *args, **kwargs):
        if not self.certificate_number:
            self.certificate_number = self.generate_certificate_number()
        super().save(*args, **kwargs)

    def generate_certificate_number(self):
        """Генерация уникального номера сертификата"""
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"CERT-{timestamp}-{random_str}"

    def __str__(self):
        return f'Сертификат {self.certificate_number} - {self.user_course.user}'

    class Meta:
        db_table = 'certificate'
        verbose_name = 'Сертификат'
        verbose_name_plural = 'Сертификаты'


#  таблица для поддержки нескольких файлов
class AssignmentSubmissionFile(models.Model):
    user_assignment = models.ForeignKey('UserPracticalAssignment', on_delete=models.CASCADE, verbose_name='Сдача задания')
    file = models.FileField(
        upload_to='assignment_submissions/',
        verbose_name='Файл сдачи',
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'zip'])
        ]
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата загрузки')
    file_name = models.CharField(max_length=255, verbose_name='Имя файла')
    file_size = models.BigIntegerField(verbose_name='Размер файла')

    def clean(self):
        if self.file and self.file.size > 50 * 1024 * 1024:  # 50 МБ
            raise ValidationError('Файл слишком большой. Максимальный размер: 50 МБ')

    def __str__(self):
        return self.file_name

    class Meta:
        db_table = 'assignment_submission_file'
        verbose_name = 'Файл сдачи задания'
        verbose_name_plural = 'Файлы сдачи заданий'


# представления
class ViewCoursePracticalAssignments(models.Model):
    course_id = models.BigIntegerField() 
    course_name = models.CharField(max_length=255)
    lecture_id = models.BigIntegerField()  
    lecture_name = models.CharField(max_length=255)
    lecture_order = models.IntegerField()
    practical_assignment_id = models.BigIntegerField(primary_key=True)  
    practical_assignment_name = models.CharField(max_length=255)
    practical_assignment_description = models.TextField()
    assignment_document_path = models.CharField(max_length=255, null=True, blank=True)
    assignment_criteria = models.TextField(null=True, blank=True)
    assignment_deadline = models.DateTimeField()
    grading_type = models.CharField(max_length=20)
    max_score = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'view_course_practical_assignments'
        verbose_name = 'Представление: практическая работа'
        verbose_name_plural = 'Представление: практические работы'


class ViewCourseLectures(models.Model):
    course_id = models.BigIntegerField() 
    course_name = models.CharField(max_length=255)
    lecture_id = models.BigIntegerField(primary_key=True) 
    lecture_name = models.CharField(max_length=255)
    lecture_content = models.TextField()
    lecture_document_path = models.CharField(max_length=255, null=True, blank=True)
    lecture_order = models.IntegerField()
    is_active = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'view_course_lectures'
        verbose_name = 'Представление: лекция'
        verbose_name_plural = 'Представление: лекции'


class ViewCourseTests(models.Model):
    course_id = models.BigIntegerField()  
    course_name = models.CharField(max_length=255)
    lecture_id = models.BigIntegerField() 
    lecture_name = models.CharField(max_length=255)
    lecture_order = models.IntegerField()
    test_id = models.BigIntegerField(primary_key=True)  
    test_name = models.CharField(max_length=255)
    test_description = models.TextField(null=True, blank=True)
    is_final = models.BooleanField()
    max_attempts = models.IntegerField(null=True, blank=True)
    grading_form = models.CharField(max_length=20)
    passing_score = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'view_course_tests'
        verbose_name = 'Представление: тест'
        verbose_name_plural = 'Представление: тесты'


class ViewAssignmentSubmissions(models.Model):
    submission_id = models.BigIntegerField(primary_key=True)
    user_id = models.BigIntegerField()
    user_name = models.CharField(max_length=255)
    practical_assignment_id = models.BigIntegerField()
    practical_assignment_name = models.CharField(max_length=255)
    lecture_name = models.CharField(max_length=255)
    course_name = models.CharField(max_length=255)
    submission_date = models.DateTimeField(null=True, blank=True)
    attempt_number = models.IntegerField()
    status = models.CharField(max_length=255)
    comment = models.TextField(null=True, blank=True)
    file_count = models.IntegerField()
    total_size = models.BigIntegerField()

    class Meta:
        managed = False
        db_table = 'view_assignment_submissions'
        verbose_name = 'Представление: сданная практическая работа'
        verbose_name_plural = 'Представление: сданные практические работы'

# 25. коды восстановления
class PasswordResetCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    code = models.CharField(max_length=6, verbose_name='Код подтверждения')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Время создания')
    is_used = models.BooleanField(default=False, verbose_name='Использован')
    
    def is_valid(self):
        """функция проверяет, действителен ли код (15 минут)"""
        return not self.is_used and (timezone.now() - self.created_at) < timedelta(minutes=15)
    
    def mark_as_used(self):
        """Помечает код как использованный"""
        self.is_used = True
        self.save()
    
    @classmethod
    def generate_code(cls):
        """генерирует 6-значный цифровой код"""
        return ''.join(random.choices(string.digits, k=6))
    
    def __str__(self):
        return f"{self.user.email} - {self.code}"
    
    class Meta:
        db_table = 'password_reset_code'
        verbose_name = 'Код восстановления пароля'
        verbose_name_plural = 'Коды восстановления пароля'