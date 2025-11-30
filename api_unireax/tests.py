from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from unireax_main.models import Course, CourseCategory, CourseType, Role

User = get_user_model()

class APIAccessTests(TestCase):
    """Тесты доступа к API с выводом подробных результатов"""
    def setUp(self):
        self.client = APIClient()
        self.superuser = User.objects.create_superuser(

            username='superuser',
            email='super@test.com',
            password='superpass123'
        )
        
        self.role = Role.objects.create(role_name='слушатель')
        self.user = User.objects.create_user(
            username='student',
            password='student123',
            email='student@test.com',
            role=self.role
        )
        
        self.category = CourseCategory.objects.create(course_category_name='Программирование')
        self.course_type = CourseType.objects.create(course_type_name='Онлайн')
        
        self.course = Course.objects.create(
            course_name='Тестовый курс API',
            course_category=self.category,
            course_type=self.course_type,
            course_hours=40,
            created_by=self.superuser,
            is_active=True
        )
    
    def test_api_access_with_superuser(self):
        """Тест доступа к API с суперпользователем"""
        print("\nТестируем доступ с суперпользователем...")
        
        self.client.force_authenticate(user=self.superuser)
        
        response = self.client.get('/api/courses/')
        print(f"   GET /api/courses/ - статус: {response.status_code}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response = self.client.get(f'/api/courses/{self.course.id}/')
        print(f"   GET /api/courses/{self.course.id}/ - статус: {response.status_code}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        new_course_data = {
            'course_name': 'Новый курс через API',
            'course_description': 'Описание нового курса',
            'course_category': self.category.id,
            'course_type': self.course_type.id,
            'course_hours': 36,
            'is_active': True
        }
        response = self.client.post('/api/courses/', data=new_course_data, format='json')
        print(f"   POST /api/courses/ - статус: {response.status_code}")
        
        if response.status_code == status.HTTP_201_CREATED:
            print("   ✅ Курс успешно создан через API!")
            self.assertEqual(Course.objects.count(), 2)
        else:
            print(f"   ❌ Не удалось создать курс: {response.data}")
        
        print("✅ Тесты с суперпользователем завершены")
    
    def test_api_access_with_regular_user(self):
        """Тест доступа к API с обычным пользователем"""
        print("\nТестируем доступ с обычным пользователем...")
        
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get('/api/courses/')
        print(f"   GET /api/courses/ - статус: {response.status_code}")
        
        new_course_data = {
            'course_name': 'Курс от студента',
            'course_category': self.category.id,
            'course_type': self.course_type.id,
            'course_hours': 20
        }
        response = self.client.post('/api/courses/', data=new_course_data, format='json')
        print(f"   POST /api/courses/ - статус: {response.status_code}")
        
        if response.status_code == status.HTTP_403_FORBIDDEN:
            print("   ✅ Правильно: обычный пользователь не может создавать курсы")
        elif response.status_code == status.HTTP_201_CREATED:
            print("   ⚠️  Неожиданно: обычный пользователь смог создать курс")
        else:
            print(f"   ℹ️  Статус: {response.status_code}")
        
        print("✅ Тесты с обычным пользователем завершены")
    
    def test_course_categories_api(self):
        """Тест API категорий курсов"""
        print("\nТестируем API категорий курсов...")
        
        self.client.force_authenticate(user=self.superuser)
        
        response = self.client.get('/api/course-categories/')
        print(f"   GET /api/course-categories/ - статус: {response.status_code}")
        
        if response.status_code == status.HTTP_200_OK:
            categories_count = len(response.data)
            print(f"   ✅ Найдено категорий: {categories_count}")
        else:
            print(f"   ❌ Не удалось получить категории: {response.status_code}")
        
        new_category_data = {
            'course_category_name': 'Новая категория'
        }
        response = self.client.post('/api/course-categories/', data=new_category_data, format='json')
        print(f"   POST /api/course-categories/ - статус: {response.status_code}")
        
        if response.status_code == status.HTTP_201_CREATED:
            print("   ✅ Новая категория создана!")
        else:
            print(f"   ❌ Не удалось создать категорию: {response.data}")
        
        print("✅ Тесты категорий завершены")

class CourseCreationTest(TestCase):
    """Тест на создание курса"""
    
    def test_create_course_success(self):
        """Тест: cоздание нового курса"""
        
        role = Role.objects.create(role_name='методист')
        category = CourseCategory.objects.create(course_category_name='Разработка')
        course_type = CourseType.objects.create(course_type_name='Интенсив')
        
        user = User.objects.create_user(
            username='creator',
            password='testpass',
            email='creator@test.com',
            role=role
        )
        
        course = Course.objects.create(
            course_name='Новый курс Django',
            course_description='Изучение Django framework',
            course_category=category,
            course_type=course_type,
            course_hours=48,
            course_price='12000.00',
            has_certificate=True,
            course_max_places=25,
            created_by=user,
            is_active=True
        )
        
        self.assertEqual(course.course_name, 'Новый курс Django')
        self.assertEqual(course.course_hours, 48)
        self.assertEqual(str(course.course_price), '12000.00')
        self.assertTrue(course.has_certificate)
        self.assertTrue(course.is_active)
        self.assertEqual(course.created_by, user)
        
        print("✅  Курс успешно создан!")
        print(f"   Название: {course.course_name}")
        print(f"   Часы: {course.course_hours}")
        print(f"   Цена: {course.course_price}")
        print(f"   Сертификат: {'Да' if course.has_certificate else 'Нет'}")
        print(f"   Создатель: {course.created_by}")


class QuickTests(TestCase):
    """Быстрые тесты для проверки работы"""
    
    def test_quick_model_creation(self):
        """Тест создания моделей"""
        
        role = Role.objects.create(role_name='администратор')
        print("✅ Роль создана")
        
        category = CourseCategory.objects.create(course_category_name='Тестовая категория')
        print("✅ Категория создана")
        
        course_type = CourseType.objects.create(course_type_name='Тестовый тип')
        print("✅ Тип курса создан")
        
        user = User.objects.create_user(username='quick', password='test')
        print("✅ Пользователь создан")
        
        course = Course.objects.create(
            course_name='Быстрый курс',
            course_category=category,
            course_type=course_type,
            course_hours=10,
            created_by=user
        )
        print("✅ Курс создан")
        
        self.assertEqual(course.course_name, 'Быстрый курс')
        self.assertEqual(Course.objects.count(), 1)
        print("✅ Все проверки пройдены!")


class ShowRealCoursesAPITest(TestCase):
    """Тест для показа курсов через API с авторизацией пользователя-администратора"""
    
    def test_show_real_courses_via_api(self):
        """Функция для создания двух курсов и показа их через API с авторизацией суперпользователя"""
        client = APIClient()
        
        print("\n" + "="*50)
        print("СОЗДАНИЕ И ВЫВОД КУРСОВ ЧЕРЕЗ API")
        print("="*50)
        
        try:
            superuser = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='User123456!'
            )
            print("✅ Создан суперпользователь для теста!")
            client.force_authenticate(user=superuser)
            
        except Exception as e:
            print(f"[X] Ошибка создания суперпользователя: {e}")
            return
        
        try:
            category = CourseCategory.objects.create(course_category_name="Программирование")
            course_type = CourseType.objects.create(course_type_name="Онлайн-курс")
            print("✅ Созданы категория и тип курса")
        except Exception as e:
            print(f"[X] Ошибка создания категории/типа: {e}")
            return
        
        course1_data = {
            'course_name': 'Python для начинающих',
            'course_description': 'Изучение Python с нуля',
            'course_category': category.id,
            'course_type': course_type.id,
            'course_hours': 72,
            'course_price': '15000.00',
            'has_certificate': True,
            'course_max_places': 25,
            'is_active': True
        }
        
        response1 = client.post('/api/courses/', data=course1_data, format='json')
        if response1.status_code == status.HTTP_201_CREATED:
            print("✅ Создан курс: Python для начинающих")
        else:
            print(f"[X] Ошибка создания первого курса: {response1.status_code}")
            print(f"Детали: {response1.data}")
        
        course2_data = {
            'course_name': 'Django Web Development',
            'course_description': 'Создание веб-приложений на Django',
            'course_category': category.id,
            'course_type': course_type.id,
            'course_hours': 48,
            'course_price': '20000.00',
            'has_certificate': True,
            'course_max_places': 20,
            'is_active': True
        }
        
        response2 = client.post('/api/courses/', data=course2_data, format='json')
        if response2.status_code == status.HTTP_201_CREATED:
            print("✅ Создан курс: Django Web Development")
        else:
            print(f"[X] Ошибка создания второго курса: {response2.status_code}")
            print(f"Детали: {response2.data}")
        
        print("\n" + "="*50)
        print("ВЫВОД СОЗДАННЫХ КУРСОВ ЧЕРЕЗ API")
        print("="*50)
        
        response = client.get('/api/courses/')
        
        if response.status_code != status.HTTP_200_OK:
            print(f"[X] Ошибка получения курсов: {response.status_code}")
            if hasattr(response, 'data'):
                print(f"Детали: {response.data}")
            return
        
        if 'results' in response.data:
            courses = response.data['results']
        else:
            courses = response.data
        
        total_courses = len(courses)
        
        print(f"Всего курсов: {total_courses}")
        print("-" * 50)
        
        if total_courses == 0:
            print("[X] Не получено ни одного курса")
            return
        
        for i, course in enumerate(courses, 1):
            print(f"{i}. {course.get('course_name', 'Нет названия')}")
            print(f"   ID: {course.get('id', 'Нет ID')}")
            print(f"   Описание: {course.get('course_description', 'Нет описания')}")
            print(f"   Цена: {course.get('course_price', 'Бесплатно')}")
            print(f"   Часы: {course.get('course_hours', 'Не указано')}")
            print(f"   Категория ID: {course.get('course_category', 'Не указана')}")
            print(f"   Тип ID: {course.get('course_type', 'Не указан')}")
            print(f"   Сертификат: {'Да' if course.get('has_certificate', False) else 'Нет'}")
            print(f"   Мест: {course.get('course_max_places', 'Не указано')}")
            print(f"   Активен: {'Да' if course.get('is_active', False) else 'Нет'}")
            if 'rating' in course:
                print(f"   Рейтинг: {course.get('rating', 0)}")
            print("   " + "-" * 40)
        
        print(f"✅ Получено {total_courses} курсов через API")
        
        print("\n" + "="*50)
        print("Проверка через тестовую БД!")
        print("="*50)
        
        db_courses = Course.objects.all()
        print(f"Курсов в тестовой БД: {db_courses.count()}")
        for course in db_courses:
            print(f" - {course.course_name} (ID: {course.id})")