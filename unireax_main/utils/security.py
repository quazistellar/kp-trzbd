from django.shortcuts import render
from django.http import HttpResponse
from django.views import View
import os
import subprocess
from django.conf import settings
from datetime import datetime
import logging
import tempfile
import glob
import psycopg2

logger = logging.getLogger(__name__)

class BackupDatabaseView(View):
    def get(self, request):
        """функция для получения списка существующих бэкапов"""
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        backups = []
        if os.path.exists(backup_dir):
            backup_files = glob.glob(os.path.join(backup_dir, "*.sql"))
            for file_path in backup_files:
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                backups.append({
                    'name': file_name,
                    'path': file_path,
                    'size': file_size,
                    'time': file_time,
                    'formatted_size': self.format_size(file_size),
                    'formatted_time': file_time.strftime("%d.%m.%Y %H:%M:%S")
                })

        backups.sort(key=lambda x: x['time'], reverse=True)        
        return render(request, 'admin/backup.html', {'backups': backups})

    def post(self, request):
        """ функция, которая вызывается в момент создания резервной копии или её восстановления,
        определяя, какое именно действие произошло и что нужно выполнить
        """
        action = request.POST.get('action')
        
        if action == 'backup':
            return self.create_backup(request)
        elif action == 'restore':
            backup_file = request.POST.get('backup_file')
            return self.restore_backup(request, backup_file)
        else:
            return HttpResponse("Неизвестное действие", status=400)

    def format_size(self, size_bytes):
        """Функция, форматирующая размер файла в читаемый вид"""
        for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} ТБ"

    def create_backup(self, request):
        """Функция создания бэкапа с помощью pg_dump"""
        try:
            db_config = settings.DATABASES['default']
            db_name = db_config['NAME']
            db_user = db_config['USER']
            db_password = db_config['PASSWORD']
            db_host = db_config['HOST']
            db_port = db_config['PORT']

            backup_dir = os.path.join(settings.BASE_DIR, 'backups')
            os.makedirs(backup_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{db_name}_backup_{timestamp}.sql"
            backup_path = os.path.join(backup_dir, backup_file)

            os.environ['PGPASSWORD'] = db_password

            possible_paths = [
                r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe",
                r"C:\Program Files\PostgreSQL\15\bin\pg_dump.exe",
                r"C:\Program Files\PostgreSQL\14\bin\pg_dump.exe",
                r"C:\Program Files\PostgreSQL\13\bin\pg_dump.exe",
                r"C:\Program Files\PostgreSQL\12\bin\pg_dump.exe",
                "pg_dump.exe",
                "pg_dump"
            ]

            pg_dump_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    pg_dump_path = path
                    break
                try:
                    subprocess.run([path, "--version"], capture_output=True, check=True)
                    pg_dump_path = path
                    break
                except:
                    continue

            if not pg_dump_path:
                return HttpResponse(
                    "❌ Ошибка: pg_dump не найден. Убедитесь, что PostgreSQL установлен и добавлен в PATH.",
                    status=500
                )

            command = [
                pg_dump_path,
                '-U', db_user,
                '-h', db_host,
                '-p', str(db_port),
                '-d', db_name,
                '-f', backup_path,
                '-v'
            ]

            logger.info(f"Starting backup: {' '.join(command)}")
            result = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            if os.path.exists(backup_path) and os.path.getsize(backup_path) > 0:
                file_size = os.path.getsize(backup_path)
                logger.info(f"Backup successful: {backup_path}")
                return HttpResponse(
                    f"✅ Бэкап базы данных успешно создан!<br>"
                    f"📁 Файл: <strong>{backup_file}</strong><br>"
                    f"📊 Размер: <strong>{self.format_size(file_size)}</strong><br>"
                    f"📂 Путь: <code>{backup_path}</code><br>"
                    f"🕒 Создан: <strong>{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</strong>"
                )
            else:
                logger.error(f"Backup file is empty: {backup_path}")
                return HttpResponse(
                    f"❌ Ошибка: файл бэкапа пуст<br>"
                    f"STDOUT: {result.stdout}<br>"
                    f"STDERR: {result.stderr}",
                    status=500
                )
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Backup failed: {e}")
            return HttpResponse(
                f"❌ Ошибка при создании бэкапа:<br>"
                f"STDOUT: {e.stdout}<br>"
                f"STDERR: {e.stderr}",
                status=500
            )
        except Exception as e:
            logger.error(f"Unexpected error during backup: {e}")
            return HttpResponse(f"❌ Неожиданная ошибка: {e}", status=500)

    def restore_backup(self, request, backup_file):
        """Восстановление базы данных из бэкапа"""
        try:
            db_config = settings.DATABASES['default']
            db_name = db_config['NAME']
            db_user = db_config['USER']
            db_password = db_config['PASSWORD']
            db_host = db_config['HOST']
            db_port = db_config['PORT']

            backup_dir = os.path.join(settings.BASE_DIR, 'backups')
            backup_path = os.path.join(backup_dir, backup_file)

            if not os.path.exists(backup_path):
                return HttpResponse(f"❌ Файл бэкапа не найден: {backup_path}", status=404)

            os.environ['PGPASSWORD'] = db_password

            possible_paths = [
                r"C:\Program Files\PostgreSQL\16\bin\psql.exe",
                r"C:\Program Files\PostgreSQL\15\bin\psql.exe",
                r"C:\Program Files\PostgreSQL\14\bin\psql.exe",
                r"C:\Program Files\PostgreSQL\13\bin\psql.exe",
                r"C:\Program Files\PostgreSQL\12\bin\psql.exe",
                "psql.exe",
                "psql"
            ]

            psql_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    psql_path = path
                    break
                try:
                    subprocess.run([path, "--version"], capture_output=True, check=True)
                    psql_path = path
                    break
                except:
                    continue

            if not psql_path:
                return HttpResponse(
                    "❌ Ошибка: psql не найден. Убедитесь, что PostgreSQL установлен и добавлен в PATH.",
                    status=500
                )

            temp_restore_file = backup_path + ".temp_restore.sql"
            
            try:
                with open(backup_path, 'r', encoding='utf-8') as f:
                    backup_content = f.read()

                modified_content = self.prepare_backup_for_restore(backup_content)

                with open(temp_restore_file, 'w', encoding='utf-8') as f:
                    f.write(modified_content)

                command = [
                    psql_path,
                    '-U', db_user,
                    '-h', db_host,
                    '-p', str(db_port),
                    '-d', db_name,
                    '-f', temp_restore_file,
                    '-v',
                    '-v', 'ON_ERROR_STOP=1'  
                ]

                logger.info(f"Starting restore: {' '.join(command)}")
                result = subprocess.run(
                    command, 
                    capture_output=True, 
                    text=True, 
                    check=True,
                    timeout=300  
                )

                if result.returncode == 0:
                    logger.info(f"Restore successful from: {backup_path}")
                    return HttpResponse(
                        f"✅ База данных успешно восстановлена из бэкапа!<br>"
                        f"📁 Файл: <strong>{backup_file}</strong><br>"
                        f"🕒 Восстановлено: <strong>{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</strong><br>"
                        f"<div class='warning-box' style='margin-top: 15px;'>"
                        f"<strong>⚠️ ВАЖНО</strong><br>"
                        f"Рекомендуется перезагрузить приложение для применения всех изменений."
                        f"</div>"
                    )
                else:
                    logger.error(f"Restore failed: {result.stderr}")
                    return HttpResponse(
                        f"❌ Ошибка при восстановлении бэкапа:<br>"
                        f"Код возврата: {result.returncode}<br>"
                        f"STDOUT: {result.stdout}<br>"
                        f"STDERR: {result.stderr}",
                        status=500
                    )

            finally:
                if os.path.exists(temp_restore_file):
                    os.remove(temp_restore_file)
                    
        except subprocess.CalledProcessError as e:
            logger.error(f"Restore failed: {e}")
            return HttpResponse(
                f"❌ Ошибка при восстановлении бэкапа:<br>"
                f"Код возврата: {e.returncode}<br>"
                f"STDOUT: {e.stdout}<br>"
                f"STDERR: {e.stderr}",
                status=500
            )
        except subprocess.TimeoutExpired:
            logger.error("Restore timeout")
            return HttpResponse(
                f"❌ Восстановление заняло слишком много времени (таймаут 5 минут).<br>"
                f"Попробуйте восстановить базу данных вручную через pgAdmin или командную строку.",
                status=500
            )
        except Exception as e:
            logger.error(f"Unexpected error during restore: {e}")
            return HttpResponse(f"❌ Неожиданная ошибка: {e}", status=500)

    def prepare_backup_for_restore(self, backup_content):
        """Подготавливает бэкап для безопасного восстановления"""
        lines = backup_content.split('\n')
        modified_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            if line.strip().startswith('SET ') and any(param in line for param in [
                'statement_timeout', 'lock_timeout', 'idle_in_transaction_session_timeout'
            ]):
                i += 1
                continue
                
            if line.strip().startswith('CREATE TABLE'):
                table_name = self.extract_table_name(line)
                if table_name:
                    modified_lines.append(f'DROP TABLE IF EXISTS {table_name} CASCADE;')
            
            elif line.strip().startswith('CREATE FUNCTION'):
                func_name = self.extract_function_name(line)
                if func_name:
                    modified_lines.append(f'DROP FUNCTION IF EXISTS {func_name} CASCADE;')
            
            elif line.strip().startswith('CREATE PROCEDURE'):
                proc_name = self.extract_procedure_name(line)
                if proc_name:
                    modified_lines.append(f'DROP PROCEDURE IF EXISTS {proc_name} CASCADE;')
            
            elif line.strip().startswith('CREATE VIEW'):
                view_name = self.extract_view_name(line)
                if view_name:
                    modified_lines.append(f'DROP VIEW IF EXISTS {view_name} CASCADE;')
            
            elif line.strip().startswith('CREATE TRIGGER'):
                trigger_info = self.extract_trigger_info(line, lines[i:min(i+10, len(lines))])
                if trigger_info:
                    modified_lines.append(f'DROP TRIGGER IF EXISTS {trigger_info} CASCADE;')
            
            modified_lines.append(line)
            i += 1
        
        return '\n'.join(modified_lines)

    def extract_table_name(self, create_table_line):
        """Извлекает имя таблицы из строки CREATE TABLE"""
        try:
            parts = create_table_line.split()
            if len(parts) >= 3:
                table_name = parts[2].strip()
                if '(' in table_name:
                    table_name = table_name.split('(')[0]
                return table_name
        except:
            pass
        return None

    def extract_function_name(self, create_function_line):
        """Извлекает имя функции из строки CREATE FUNCTION"""
        try:
            parts = create_function_line.split()
            if len(parts) >= 3:
                func_name = parts[2].strip()
                if '(' in func_name:
                    func_name = func_name.split('(')[0]
                return func_name
        except:
            pass
        return None

    def extract_procedure_name(self, create_procedure_line):
        """Извлекает имя процедуры из строки CREATE PROCEDURE"""
        try:
            parts = create_procedure_line.split()
            if len(parts) >= 3:
                proc_name = parts[2].strip()
                if '(' in proc_name:
                    proc_name = proc_name.split('(')[0]
                return proc_name
        except:
            pass
        return None

    def extract_view_name(self, create_view_line):
        """Извлекает имя представления из строки CREATE VIEW"""
        try:
            parts = create_view_line.split()
            if len(parts) >= 3:
                view_name = parts[2].strip()
                return view_name
        except:
            pass
        return None

    def extract_trigger_info(self, create_trigger_line, next_lines):
        """Извлекает информацию о триггере"""
        try:
            parts = create_trigger_line.split()
            if len(parts) >= 4:
                trigger_name = parts[2].strip()
                full_text = ' '.join([create_trigger_line] + next_lines[:5])
                if 'ON' in full_text:
                    on_index = full_text.index('ON')
                    table_part = full_text[on_index:].split()[1]
                    table_name = table_part.strip()
                    if '.' in table_name:
                        return f'{trigger_name} ON {table_name}'
                    else:
                        return f'{trigger_name} ON public.{table_name}'
        except:
            pass
        return None