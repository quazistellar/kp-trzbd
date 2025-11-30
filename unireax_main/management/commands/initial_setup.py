import re
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.utils import OperationalError, ProgrammingError
from django.conf import settings
try:
    from unireax_main.models import User
except ImportError:
    from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Данная команда выполняет первоначальную настройку приложения, включая создание суперпользователя если база данных пуста'

    def handle(self, *args, **options):
        """ Функция проверяет количество пользователей в базе данных и,
          если их нет, создает суперпользователя, обрабатывая возможные 
          ошибки подключения к БД """
        self.stdout.write(self.style.HTTP_INFO('Запуск проверки первоначальной настройки...'))

        try:
            user_count = User.objects.count()
            if user_count == 0:
                self.stdout.write(self.style.SUCCESS("База данных пуста. Создаем суперпользователя..."))
                self.create_superuser_if_not_exists()
            else:
                self.stdout.write(self.style.WARNING(f"В базе данных уже есть {user_count} пользователь(ей), создание суперпользователя пропускается.."))

        except (OperationalError, ProgrammingError) as e:
            self.stderr.write(self.style.ERROR(f"Ошибка базы данных: {e}"))
            self.stderr.write(self.style.ERROR("Возможно, миграции не применены. Примените их командой 'python manage.py migrate'!"))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Непредвиденная ошибка: {e}"))

        self.stdout.write(self.style.HTTP_INFO('Проверка первоначальной настройки завершена.'))

    def create_superuser_if_not_exists(self):
        """ Функция, которая создает суперпользователя, если он еще не существует в базе данных """
        username = getattr(settings, 'DJANGO_SUPERUSER_USERNAME', 'admin')
        email = getattr(settings, 'DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
        password = getattr(settings, 'DJANGO_SUPERUSER_PASSWORD', None)

        if not password:
            self.stderr.write(self.style.ERROR("Пароль суперпользователя не установлен!"))
            self.stderr.write(self.style.ERROR("Установите переменную окружения 'DJANGO_SUPERUSER_PASSWORD'"))
            return

        password_error = self.validate_password(password, username)
        if password_error:
            self.stderr.write(self.style.ERROR(f"Ненадежный пароль: {password_error}"))
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f"Суперпользователь '{username}' уже существует."))
        else:
            try:
                User.objects.create_superuser(username, email, password)
                self.stdout.write(self.style.SUCCESS(f"Суперпользователь '{username}' успешно создан."))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Ошибка при создании суперпользователя: {e}"))

    def validate_password(self, password, username):
        """ Функция, которая проверяет надежность 
        пароля и возвращает соответствующее сообщение"""

        min_length = getattr(settings, 'DJANGO_SUPERUSER_MIN_PASSWORD_LENGTH', 8)
        if len(password) < min_length:
            return f"Пароль должен содержать минимум {min_length} символов"

        weak_passwords = getattr(settings, 'DJANGO_SUPERUSER_WEAK_PASSWORDS', ['admin', 'password', '12345678'])
        if password.lower() in weak_passwords:
            return "Пароль слишком простой"

        if password == username:
            return "Пароль не должен совпадать с именем пользователя"

        require_strong = getattr(settings, 'DJANGO_SUPERUSER_REQUIRE_STRONG_PASSWORD', False)
        if require_strong:
            if not re.search(r'[A-Z]', password):
                return "Пароль должен содержать хотя бы одну заглавную букву"
            if not re.search(r'[a-z]', password):
                return "Пароль должен содержать хотя бы одну строчную букву"
            if not re.search(r'\d', password):
                return "Пароль должен содержать хотя бы одну цифру"
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                return "Пароль должен содержать хотя бы один специальный символ"

        return None