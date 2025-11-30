from django.core.exceptions import ValidationError
import re

class UppercaseValidator:
    def validate(self, password, user=None):
        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                "Пароль должен содержать хотя бы одну заглавную букву.",
                code='no_uppercase',
            )

    def get_help_text(self):
        return "Ваш пароль должен содержать хотя бы одну заглавную букву."

class SpecialCharacterValidator:
    def validate(self, password, user=None):
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError(
                "Пароль должен содержать хотя бы один специальный символ.",
                code='no_special_character',
            )

    def get_help_text(self):
        return "Ваш пароль должен содержать хотя бы один специальный символ."

class RussianMinimumLengthValidator:
    def __init__(self, min_length=8):
        self.min_length = min_length

    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                "Пароль слишком короткий. Он должен содержать как минимум %(min_length)d символов.",
                code='password_too_short',
                params={'min_length': self.min_length},
            )

    def get_help_text(self):
        return "Пароль должен содержать как минимум %(min_length)d символов." % {'min_length': self.min_length}

class RussianCommonPasswordValidator:
    def validate(self, password, user=None):
        common_passwords = [
            'password', '12345678', '123456789', 'qwerty', 'admin', 
            'password123', '1234567890', 'abc123', '111111', '123123'
        ]
        if password.lower() in common_passwords:
            raise ValidationError(
                "Этот пароль слишком распространён.",
                code='password_too_common',
            )

    def get_help_text(self):
        return "Ваш пароль не должен быть распространённым."

class RussianNumericPasswordValidator:
    def validate(self, password, user=None):
        if password.isdigit():
            raise ValidationError(
                "Пароль не может состоять только из цифр.",
                code='password_entirely_numeric',
            )

    def get_help_text(self):
        return "Пароль не может состоять только из цифр."

class RussianUserAttributeSimilarityValidator:
    def validate(self, password, user=None):
        if not user:
            return
            
        attribute_words = []
        for attribute_name in ['username', 'first_name', 'last_name', 'email']:
            attribute = getattr(user, attribute_name, None)
            if attribute and len(attribute) > 2:
                attribute_words.append(attribute.lower())
                
        for word in attribute_words:
            if word in password.lower():
                raise ValidationError(
                    "Пароль слишком похож на ваши личные данные.",
                    code='password_too_similar',
                )

    def get_help_text(self):
        return "Пароль не должен быть похож на ваши личные данные."