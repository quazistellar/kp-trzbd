# import threading
# from django.apps import AppConfig
# from django.core.management import call_command
# from django.db.utils import OperationalError, ProgrammingError

# def run_initial_setup():
#     """функция, которая запускает первоначальную настройку приложения в фоновом режиме"""
#     try:
#         from unireax_main.models import User
#         if User.objects.count() == 0:
#             print("🔄 Автоматическая настройка: создание суперпользователя...")
#             call_command('initial_setup')
#     except (OperationalError, ProgrammingError):
#         print("⏳ База данных не готова, пропускаем автоматическую настройку")
#     except Exception as e:
#         print(f"⚠️ Ошибка автоматической настройки: {e}")

# class UnireaxMainConfig(AppConfig):
#     default_auto_field = 'django.db.models.BigAutoField'
#     name = 'unireax_main'
#     verbose_name = 'Таблицы автоматизированной системы управления образовательными процессами UNIREAX'

#     def ready(self):
#         """запускается при готовности приложения"""
#         import unireax_main.utils.logging_handler
        
#         thread = threading.Thread(target=run_initial_setup)
#         thread.daemon = True
#         thread.start()



import threading
from django.apps import AppConfig
from django.core.management import call_command
from django.db.utils import OperationalError, ProgrammingError

def run_initial_setup():
    """функция, которая запускает первоначальную настройку приложения в фоновом режиме"""
    try:
        from unireax_main.models import User
        if User.objects.count() == 0:
            print("🔄 Автоматическая настройка: создание суперпользователя...")
            call_command('initial_setup')
    except (OperationalError, ProgrammingError):
        print("⏳ База данных не готова, пропускаем автоматическую настройку")
    except Exception as e:
        print(f"⚠️ Ошибка автоматической настройки: {e}")

def start_influxdb_metrics():
    """Запуск автоматической отправки метрик в InfluxDB"""
    try:
        from unireax_main.influxdb import auto_sender
        auto_sender.start_auto_send(interval=60)  
        print("Автоматическая отправка метрик в InfluxDB запущена")
    except Exception as e:
        print(f"⚠️ Ошибка запуска отправки метрик: {e}")

class UnireaxMainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'unireax_main'
    verbose_name = 'Таблицы автоматизированной системы управления образовательными процессами UNIREAX'

    def ready(self):
        """запускается при готовности приложения"""
        import unireax_main.utils.logging_handler
        
        thread_setup = threading.Thread(target=run_initial_setup)
        thread_setup.daemon = True
        thread_setup.start()

        thread_metrics = threading.Thread(target=start_influxdb_metrics)
        thread_metrics.daemon = True
        thread_metrics.start()