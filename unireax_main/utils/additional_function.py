from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import simpleSplit
from django.http import HttpResponse
from django.conf import settings
import os
import json
import random
import string
from django.http import HttpResponse

def register_russian_fonts():
    """Регистрируем шрифты с поддержкой кириллицы"""
    try:
        try:
            pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
            pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
            return 'DejaVuSans', 'DejaVuSans-Bold'
        except:
            try:
                pdfmetrics.registerFont(TTFont('DejaVuSans', 'C:/Windows/Fonts/DejaVuSans.ttf'))
                pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', 'C:/Windows/Fonts/DejaVuSans-Bold.ttf'))
                return 'DejaVuSans', 'DejaVuSans-Bold'
            except:
                try:
                    pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
                    pdfmetrics.registerFont(TTFont('Arial-Bold', 'arialbd.ttf'))
                    return 'Arial', 'Arial-Bold'
                except:
                    return 'Helvetica', 'Helvetica-Bold'
    except Exception as e:
        print(f"Ошибка загрузки шрифтов: {e}")
        return 'Helvetica', 'Helvetica-Bold'

def draw_wrapped_text(p, text, x, y, max_width, font_name, font_size, line_height=14):
    """Рисует текст с переносом строк"""
    p.setFont(font_name, font_size)
    lines = simpleSplit(text, font_name, font_size, max_width)
    
    for line in lines:
        p.drawString(x, y, line)
        y -= line_height
    
    return y

def draw_info_block(p, title, items, x, y, width, font_normal, font_bold):
    """Рисует блок информации с переносами"""
    p.setFillColor(HexColor('#5864F1'))
    p.setFont(font_bold, 16)
    p.drawString(x, y, title)
    y -= 30
    p.setFillColor(HexColor('#f8f9ff'))
    block_height = len(items) * 45  
    for label, value in items:
        value_lines = len(simpleSplit(value, font_normal, 12, width - 150)) if value else 1
        if value_lines > 1:
            block_height += (value_lines - 1) * 15
    
    p.rect(x - 10, y - block_height, width, block_height, fill=1, stroke=0)
    p.setFillColor(HexColor('#333333'))
    current_y = y - 20
    
    for label, value in items:
        p.setFont(font_bold, 12)
        p.drawString(x, current_y, label)
        if value:
            value_lines = simpleSplit(value, font_normal, 12, width - 150)
            p.setFont(font_normal, 12)
            for i, line in enumerate(value_lines):
                p.drawString(x + 150, current_y - (i * 15), line)
            current_y -= max(25, len(value_lines) * 15 + 10)
        else:
            current_y -= 25
    
    return y - block_height - 20

def generate_payment_receipt(payment_data):
    """Генерация красивого чека на русском с переносами строк"""
    
    font_normal, font_bold = register_russian_fonts()
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    primary_color = HexColor('#7B7FD5')
    dark_color = HexColor('#151D49')
    text_color = HexColor('#333333')
    
    p.setFillColor(HexColor('#FFFFFF'))
    p.rect(0, 0, width, height, fill=1, stroke=0)
    
    p.setFillColor(primary_color)
    p.rect(0, height - 120, width, 120, fill=1, stroke=0)
    
    p.setFillColor(HexColor('#FFFFFF'))
    p.setFont(font_bold, 24)
    p.drawString(50, height - 60, "UNIREAX")
    
    p.setFont(font_normal, 14)
    p.drawString(50, height - 85, "Образовательная платформа")
    
    p.setFillColor(dark_color)
    p.setFont(font_bold, 20)
    p.drawCentredString(width/2, height - 150, "ЧЕК ОБ ОПЛАТЕ КУРСА")
    
    y_position = height - 200
    content_width = width - 100  
    
    payment_info = [
        ("Номер платежа:", payment_data['payment_id']),
        ("Дата оплаты:", payment_data['payment_date'].strftime("%d.%m.%Y %H:%M")),
        ("Статус:", "Оплачено"),
    ]
    
    y_position = draw_info_block(p, "Информация о платеже", payment_info, 50, y_position, content_width, font_normal, font_bold)
    
    course_info = [
        ("Название курса:", payment_data['course_name']),
        ("Категория:", payment_data['course_category']),
        ("Тип:", payment_data['course_type']),
        ("Сумма:", f"{payment_data['amount']} ₽"),
    ]
    
    y_position = draw_info_block(p, "Информация о курсе", course_info, 50, y_position, content_width, font_normal, font_bold)
    
    user_info = [
        ("ФИО:", payment_data['user_name']),
        ("Email:", payment_data['user_email']),
    ]
    
    y_position = draw_info_block(p, "Информация о пользователе", user_info, 50, y_position, content_width, font_normal, font_bold)
    
    y_position -= 20
    p.setFillColor(primary_color)
    p.setFont(font_bold, 18)
    p.drawString(50, y_position, "Итоговая сумма:")
    p.setFillColor(dark_color)
    p.setFont(font_bold, 22)
    p.drawString(220, y_position, f"{payment_data['amount']} ₽")
    
    p.setFillColor(HexColor("#585757"))
    p.setFont(font_normal, 10)
    p.drawCentredString(width/2, 40, f"Чек №{payment_data['payment_id']}")
    p.drawCentredString(width/2, 25, "Документ сгенерирован автоматически")
    p.drawCentredString(width/2, 10, "и не требует дополнительной подписи")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return buffer

def download_receipt_response(payment_data):
    """Создает HTTP response с PDF чеком"""
    try:
        pdf_buffer = generate_payment_receipt(payment_data)
        
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        filename = f"чек_оплаты_{payment_data['payment_id']}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        print(f"Ошибка генерации PDF: {e}")
        
        try:
            return generate_simple_receipt(payment_data)
        except:
            return HttpResponse(
                "Ошибка генерации чека. Обратитесь в поддержку.",
                content_type='text/plain; charset=utf-8'
            )

def generate_simple_receipt(payment_data):
    """Простая версия без сложного форматирования"""
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    
    pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))
    
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    p.setFont('HeiseiMin-W3', 16)
    p.drawString(50, height - 100, "UNIREAX - Чек об оплате")
    
    y = height - 140
    p.setFont('HeiseiMin-W3', 10)
    
    def add_text(text, max_chars=80):
        nonlocal y
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            if len(' '.join(current_line + [word])) <= max_chars:
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        for line in lines:
            p.drawString(50, y, line)
            y -= 15
        y -= 5
    
    add_text(f"Номер платежа: {payment_data['payment_id']}")
    add_text(f"Дата: {payment_data['payment_date'].strftime('%d.%m.%Y %H:%M')}")
    add_text("Статус: Оплачено")
    y -= 10
    
    add_text(f"Курс: {payment_data['course_name']}")
    add_text(f"Категория: {payment_data['course_category']}")
    add_text(f"Тип: {payment_data['course_type']}")
    add_text(f"Сумма: {payment_data['amount']} ₽")
    y -= 10
    
    add_text(f"Слушатель: {payment_data['user_name']}")
    add_text(f"Email: {payment_data['user_email']}")
    
    y = 40
    p.setFont('HeiseiMin-W3', 9)
    p.drawString(50, y, f"Чек №{payment_data['payment_id']}")
    p.drawString(50, y - 15, "Документ сгенерирован автоматически")
    p.drawString(50, y - 30, "и не требует дополнительной подписи")
    
    p.showPage()
    p.save()
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    filename = f"чек_оплаты_{payment_data['payment_id']}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


from django.conf import settings
import json

def get_favorite_courses(request):
    """Получить список избранных курсов из куки"""
    favorites_cookie = request.COOKIES.get(settings.FAVORITES_COOKIE_NAME, '[]')
    try:
        return json.loads(favorites_cookie)
    except json.JSONDecodeError:
        return []

def add_to_favorites(request, course_id):
    """Добавить курс в избранное"""
    favorites = get_favorite_courses(request)
    if course_id not in favorites:
        favorites.append(course_id)
    
    response = HttpResponse()
    response.set_cookie(
        settings.FAVORITES_COOKIE_NAME,
        json.dumps(favorites),
        max_age=settings.FAVORITES_COOKIE_AGE,
        httponly=True
    )
    return response

def remove_from_favorites(request, course_id):
    """Удалить курс из избранного"""
    favorites = get_favorite_courses(request)
    if course_id in favorites:
        favorites.remove(course_id)
    
    response = HttpResponse()
    response.set_cookie(
        settings.FAVORITES_COOKIE_NAME,
        json.dumps(favorites),
        max_age=settings.FAVORITES_COOKIE_AGE,
        httponly=True
    )
    return response


from django.db import connection

def calculate_course_progress(user, course):
    """Расчет прогресса курса с использованием существующей функции БД"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT calculate_course_completion(%s, %s)", [user.id, course.id])
            result = cursor.fetchone()
            return float(result[0]) if result and result[0] is not None else 0.0
    except Exception as e:
        print(f"Error calculating course progress: {e}")
        return 0.0

def generate_password(length=12):
    """Генерация случайного пароля"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

def generate_username(email):
    """Генерация username на основе email"""
    return email.split('@')[0]