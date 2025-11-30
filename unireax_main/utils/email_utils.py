from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

def send_account_approved_email(user, admin_comment=None):
    """Функция для отправки письма на почту о подтверждении аккаунта"""
    subject = 'Ваш аккаунт подтвержден'
    
    context = {
        'user_obj': user, 
        'admin_comment': admin_comment,
        'site_url': settings.SITE_URL,
    }
    
    html_message = render_to_string('emails/account_approved.html', context)
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Ошибка отправки email: {e}")
        return False

def send_account_rejected_email(user, admin_comment=None):
    """Функция отправки письма об отказе в аккаунте"""
    subject = 'Регистрация не подтверждена'
    
    context = {
        'user_obj': user, 
        'admin_comment': admin_comment,
        'site_url': settings.SITE_URL,
    }
    
    html_message = render_to_string('emails/account_rejected.html', context)
    plain_message = strip_tags(html_message)
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Ошибка отправки email: {e}")
        return False