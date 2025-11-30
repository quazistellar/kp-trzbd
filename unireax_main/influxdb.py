from django.db.models import Count
from django.conf import settings
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.rest import ApiException
import time
import threading
import logging
from .models import Course, CourseCategory, User, Role

logger = logging.getLogger(__name__)

class InfluxDBAutoSender:
    def __init__(self):
        try:
            self.client = InfluxDBClient(
                url=settings.INFLUXDB_URL,
                token=settings.INFLUXDB_TOKEN,
                org=settings.INFLUXDB_ORG,
                timeout=30_000
            )
            self.client.ready()
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.bucket = settings.INFLUXDB_BUCKET
            self._setup_bucket()
        except Exception as e:
            self.client = None

    def _escape_influx_value(self, value):
        """экранирование значений для InfluxDB"""
        if value is None:
            return "unknown"
        value = str(value)
        value = value.replace(',', '\\,').replace(' ', '\\ ').replace('=', '\\=')
        return value

    def _check_connection(self):
        """тест подключения к InfluxDB"""
        if not self.client:
            return False
        try:
            return self.client.ready()
        except Exception:
            return False

    def send_courses_metrics(self):
        """метрики курсов по категориям"""
        if not self._check_connection():
            return
            
        try:
            counts = Course.objects.values('course_category__course_category_name').annotate(count=Count('id'))
            
            records = []
            for row in counts:
                category_name = row['course_category__course_category_name'] or "Без категории"
                escaped_category = self._escape_influx_value(category_name)
                record = f"courses_by_category,category={escaped_category} count={row['count']}"
                records.append(record)
            if records:
                self.write_api.write(self.bucket, settings.INFLUXDB_ORG, records)
            else:
                logger.info("нет курсов для отправки метрик")
            
        except ApiException as e:
            logger.error("ошибка сбора метрик")
        except Exception as e:
            logger.error('ошибка отправки метрик')

    def send_users_metrics(self):
        """метрики пользователей по ролям"""
        if not self._check_connection():
            return
            
        try:
            records = []
            for role in Role.objects.all():
                count = User.objects.filter(role=role).count()
                escaped_role = self._escape_influx_value(role.role_name)
                record = f"users_by_role,role={escaped_role} count={count}"
                records.append(record)
            null_count = User.objects.filter(role__isnull=True).count()
            if null_count > 0:
                record = f"users_by_role,role=No_Role count={null_count}"
                records.append(record)
            if records:
                self.write_api.write(self.bucket, settings.INFLUXDB_ORG, records)
            else:
                print('нет данных по ролям для отправки')
        except ApiException as e:
            print('ошибка сбора метрик')
            if hasattr(e, 'body'):
                print('ошибка отправки body')
        except Exception as e:
            print('ошибка')

    def send_verification_metrics(self):
        """метрики верификации"""
        if not self._check_connection():
            return
        try:
            pending_count = User.objects.filter(is_verified=False).count()
            verified_count = User.objects.filter(is_verified=True).count()

            records = [
                f"users_verification,status=pending count={pending_count}",
                f"users_verification,status=verified count={verified_count}"
            ]
            
            self.write_api.write(self.bucket, settings.INFLUXDB_ORG, records)
            
        except Exception as e:
            logger.error('ошибка отправки метрик подтвержденных пользователелй')

    def send_all_metrics(self):
        """отправляет все метрики в InfluxDB"""
        try:
            if not self._check_connection():
                logger.error(
                    'нет подключения к influxdb'
                )
                return False
            self.send_courses_metrics()
            self.send_users_metrics()
            self.send_verification_metrics()
            logger.info('все метрики были отправлены успешно')
            return True
        except Exception as e:
            logger.error('ошибка отправки метрик')
            return False
        
    def start_auto_send(self, interval=60):
        """запуск автоматической отправки"""
        def send_loop():
            while True:
                try:
                    self.send_all_metrics()
                except Exception as e:
                    logger.error('ошибка автоматической отправки метрик')
                time.sleep(interval)
        thread = threading.Thread(target=send_loop, daemon=True)
        thread.start()
auto_sender = InfluxDBAutoSender()