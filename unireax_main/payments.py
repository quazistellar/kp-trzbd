import uuid
from django.conf import settings
from django.utils import timezone
from .models import UserCourse

class YookassaPayment:
    """интеграция с Юкассой"""
    
    def __init__(self):
        from yookassa import Configuration
        Configuration.account_id = settings.YOOKASSA_SHOP_ID
        Configuration.secret_key = settings.YOOKASSA_SECRET_KEY
    
    def create_payment(self, course, user, return_url):
        from yookassa import Payment
        
        payment = Payment.create({
            "amount": {
                "value": str(course.course_price),
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": return_url
            },
            "capture": True,
            "description": f"Оплата курса: {course.course_name}",
            "metadata": {
                "course_id": course.id,
                "user_id": user.id,
                "course_name": course.course_name
            }
        }, str(uuid.uuid4()))
        
        return payment
    
    def check_payment_status(self, payment_id):
        from yookassa import Payment
        payment_info = Payment.find_one(payment_id)
        return payment_info.status
    
    def process_successful_payment(self, payment_id):
        from yookassa import Payment
        from .models import Course, User
        
        payment_info = Payment.find_one(payment_id)
        
        if payment_info.status == 'succeeded':
            course_id = payment_info.metadata.get('course_id')
            user_id = payment_info.metadata.get('user_id')
            
            course = Course.objects.get(id=course_id)
            user = User.objects.get(id=user_id)
            
            if not UserCourse.objects.filter(user=user, course=course).exists():
                user_course = UserCourse(
                    user=user,
                    course=course,
                    course_price=course.course_price,
                    payment_date=timezone.now(),
                    status_course=False,
                    is_active=True
                )
                user_course.save()
                return True
        
        return False