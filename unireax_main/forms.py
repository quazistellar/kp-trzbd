from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm
from .models import (
    Course, CourseCategory, CourseType, Role, UserCourse, CourseTeacher,
    Lecture, Test, Question, PracticalAssignment, User, AnswerType
)

User = get_user_model()


class UserForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'user-form-input'}),
        required=False,
        min_length=8
    )
    password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={'class': 'user-form-input'}),
        required=False
    )

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'patronymic', 'email', 'username',
            'role', 'position', 'educational_institution', 'profile_theme',
            'is_verified', 'is_active', 'is_staff', 'is_superuser',
            'certificat_from_the_place_of_work_path'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'user-form-input', 'required': True}),
            'last_name': forms.TextInput(attrs={'class': 'user-form-input', 'required': True}),
            'patronymic': forms.TextInput(attrs={'class': 'user-form-input'}),
            'email': forms.EmailInput(attrs={'class': 'user-form-input', 'required': True}),
            'username': forms.TextInput(attrs={'class': 'user-form-input', 'required': True}),
            'role': forms.Select(attrs={'class': 'user-form-select', 'required': True}),
            'position': forms.TextInput(attrs={'class': 'user-form-input'}),
            'educational_institution': forms.TextInput(attrs={'class': 'user-form-input'}),
            'profile_theme': forms.TextInput(attrs={'class': 'user-form-input'}),
            'certificat_from_the_place_of_work_path': forms.ClearableFileInput(attrs={'class': 'user-form-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if not self.instance.pk and (not password1 or not password2):
            raise ValidationError("Пароль обязателен для нового пользователя")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Пароли не совпадают")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get('password1'):
            user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            'course_name', 'course_description', 'course_price', 'course_category',
            'course_type', 'course_hours', 'course_max_places', 'has_certificate',
            'code_room', 'is_active', 'is_completed', 'course_photo_path', 'created_by'
        ]
        widgets = {
            'course_name': forms.TextInput(attrs={'class': 'user-form-input', 'required': True}),
            'course_description': forms.Textarea(attrs={'class': 'user-form-textarea', 'rows': 4}),
            'course_price': forms.NumberInput(attrs={'class': 'user-form-input', 'step': '0.01', 'min': '0'}),
            'course_category': forms.Select(attrs={'class': 'user-form-select', 'required': True}),
            'course_type': forms.Select(attrs={'class': 'user-form-select', 'required': True}),
            'course_hours': forms.NumberInput(attrs={'class': 'user-form-input', 'required': True, 'min': '1'}),
            'course_max_places': forms.NumberInput(attrs={'class': 'user-form-input', 'min': '1'}),
            'code_room': forms.TextInput(attrs={'class': 'user-form-input'}),
            'created_by': forms.Select(attrs={'class': 'user-form-select'}),
            'course_photo_path': forms.ClearableFileInput(attrs={'class': 'user-form-input'}),
            'has_certificate': forms.CheckboxInput(attrs={'class': 'user-form-checkbox'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'user-form-checkbox'}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'user-form-checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['created_by'].queryset = User.objects.filter(role__role_name='методист')
        self.fields['created_by'].required = False
        self.fields['created_by'].empty_label = "Не выбрано"

    def clean_created_by(self):
        created_by = self.cleaned_data.get('created_by')
        if created_by and created_by.role.role_name != 'методист':
            raise ValidationError('Создателем курса может быть только методист')
        return created_by

    def clean_course_photo_path(self):
        photo = self.cleaned_data.get('course_photo_path')
        if photo and photo.size > 5 * 1024 * 1024:
            raise ValidationError("Фото не более 5 МБ")
        return photo


class MethodistCourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            'course_name', 'course_description', 'course_price', 'course_category',
            'course_type', 'course_hours', 'course_max_places', 'has_certificate',
            'code_room', 'is_active', 'is_completed', 'course_photo_path'
        ]
        widgets = {
            'course_name': forms.TextInput(attrs={'class': 'methodist-form-input', 'required': True}),
            'course_description': forms.Textarea(attrs={'class': 'methodist-form-textarea', 'rows': 4}),
            'course_price': forms.NumberInput(attrs={'class': 'methodist-form-input', 'step': '0.01', 'min': '0'}),
            'course_category': forms.Select(attrs={'class': 'methodist-form-select'}),
            'course_type': forms.Select(attrs={'class': 'methodist-form-select'}),
            'course_hours': forms.NumberInput(attrs={'class': 'methodist-form-input', 'min': '1'}),
            'course_max_places': forms.NumberInput(attrs={'class': 'methodist-form-input', 'min': '1'}),
            'code_room': forms.TextInput(attrs={'class': 'methodist-form-input'}),
            'course_photo_path': forms.ClearableFileInput(attrs={'class': 'methodist-form-input'}),
            'has_certificate': forms.CheckboxInput(attrs={'class': 'methodist-form-checkbox'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'methodist-form-checkbox'}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'methodist-form-checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)  # ← методист
        super().__init__(*args, **kwargs)

    def clean_course_photo_path(self):
        photo = self.cleaned_data.get('course_photo_path')
        if photo and photo.size > 5 * 1024 * 1024:
            raise ValidationError("Фото не более 5 МБ")
        return photo

    def save(self, commit=True):
        course = super().save(commit=False)
        if self.user:
            course.created_by = self.user
        if commit:
            course.save()
        return course


# forms.py
from django import forms
from django.core.exceptions import ValidationError
from .models import Course
from django.core.validators import FileExtensionValidator
   



class CourseSettingsForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            'course_hours',
            'course_max_places',
            'course_price',
            'code_room',
            'course_photo_path',
            'has_certificate',
            'is_active',
        ]
        widgets = {
            'course_hours': forms.NumberInput(attrs={
                'class': 'methodist-form-input',
                'min': '1',
                'required': True
            }),
            'course_max_places': forms.NumberInput(attrs={
                'class': 'methodist-form-input',
                'min': '1',
                'placeholder': 'Оставьте пустым для неограниченного'
            }),
            'course_price': forms.NumberInput(attrs={
                'class': 'methodist-form-input',
                'min': '0',
                'step': '0.01',
                'placeholder': '0 — бесплатно'
            }),
            'code_room': forms.TextInput(attrs={
                'class': 'methodist-form-input',
                'placeholder': 'Код для доступа к курсу'
            }),
            'course_photo_path': forms.ClearableFileInput(attrs={
                'class': 'methodist-form-input',
                'accept': 'image/*'
            }),
            'has_certificate': forms.CheckboxInput(attrs={
                'class': 'methodist-form-checkbox'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'methodist-form-checkbox'
            }),
        }
        labels = {
            'course_hours': 'Количество часов',
            'course_max_places': 'Максимум мест',
            'course_price': 'Цена курса (руб)',
            'code_room': 'Код комнаты',
            'course_photo_path': 'Фото курса',
            'has_certificate': 'Выдавать сертификат',
            'is_active': 'Курс активен',
        }

    def clean_course_photo_path(self):
        photo = self.cleaned_data.get('course_photo_path')
        if photo:
            if photo.size > 5 * 1024 * 1024:  
                raise ValidationError("Размер фото не должен превышать 5 МБ.")
            if not photo.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                raise ValidationError("Поддерживаются только изображения: PNG, JPG, GIF, WebP.")
        return photo



class RoleForm(forms.ModelForm):
    class Meta:
        model = Role
        fields = ['role_name']
        widgets = {'role_name': forms.TextInput(attrs={'class': 'user-form-input', 'required': True})}


class UserCourseForm(forms.ModelForm):
    class Meta:
        model = UserCourse
        fields = [
            'user', 'course', 'registration_date', 'status_course',
            'payment_date', 'completion_date', 'course_price', 'is_active'
        ]
        widgets = {
            'user': forms.Select(attrs={'class': 'user-form-select', 'required': True}),
            'course': forms.Select(attrs={'class': 'user-form-select', 'required': True}),
            'registration_date': forms.DateInput(attrs={'class': 'user-form-input', 'type': 'date'}),
            'payment_date': forms.DateInput(attrs={'class': 'user-form-input', 'type': 'date'}),
            'completion_date': forms.DateInput(attrs={'class': 'user-form-input', 'type': 'date'}),
            'course_price': forms.NumberInput(attrs={'class': 'user-form-input', 'step': '0.01', 'min': '0'}),
            'status_course': forms.CheckboxInput(attrs={'class': 'user-form-checkbox'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'user-form-checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = User.objects.filter(role__role_name='слушатель курсов')
        self.fields['course'].queryset = Course.objects.filter(is_active=True)

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        course = cleaned_data.get('course')
        if user and course:
            existing = UserCourse.objects.filter(user=user, course=course)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise ValidationError("Этот пользователь уже записан на данный курс.")
        return cleaned_data


class CourseTeacherForm(forms.ModelForm):
    class Meta:
        model = CourseTeacher
        fields = ['teacher', 'course', 'start_date', 'is_active']
        widgets = {
            'teacher': forms.Select(attrs={'class': 'user-form-select', 'required': True}),
            'course': forms.Select(attrs={'class': 'user-form-select', 'required': True}),
            'start_date': forms.DateInput(attrs={'class': 'user-form-input', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'user-form-checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['teacher'].queryset = User.objects.filter(role__role_name='преподаватель')

    def clean(self):
        cleaned_data = super().clean()
        teacher = cleaned_data.get('teacher')
        course = cleaned_data.get('course')
        if teacher and course:
            existing = CourseTeacher.objects.filter(teacher=teacher, course=course)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise ValidationError("Этот преподаватель уже назначен на данный курс.")
        return cleaned_data


class ListenerRegistrationForm(UserCreationForm):
    username = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=35, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=35, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    patronymic = forms.CharField(max_length=35, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    accept_policies = forms.BooleanField(required=True, error_messages={'required': 'Необходимо согласиться с политиками'})

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'patronymic', 'email', 'password1', 'password2']

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Пользователь с таким именем уже существует')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Пользователь с таким email уже существует')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.patronymic = self.cleaned_data['patronymic']
        listener_role, _ = Role.objects.get_or_create(role_name="слушатель курсов")
        user.role = listener_role
        user.is_verified = True
        if commit:
            user.save()
        return user
    

class TeacherMethodistRegistrationForm(UserCreationForm):
    username = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=35, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=35, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    patronymic = forms.CharField(max_length=35, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    
    role_choice = forms.ChoiceField(
        choices=[
            ('teacher', 'Преподаватель'),
            ('methodist', 'Методист'),
        ],
        required=True,
        widget=forms.RadioSelect(attrs={'class': 'role-radio'}),
        error_messages={'required': 'Пожалуйста, выберите одну из ролей'}
    )
    
    position = forms.CharField(
        max_length=100, 
        required=True, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Должность по месту работы'})
    )
    
    educational_institution = forms.CharField(
        max_length=100, 
        required=True, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Учебное заведение'})
    )
    
    certificat_from_the_place_of_work_path = forms.FileField(
        required=True,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'pdf'])],
        help_text='Форматы: JPG, PNG, PDF. Максимальный размер: 10 МБ'
    )
    
    accept_policies = forms.BooleanField(
        required=True, 
        error_messages={'required': 'Необходимо согласиться с политиками'}
    )

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'patronymic', 'email', 
            'password1', 'password2', 'role_choice', 'position', 
            'educational_institution', 'certificat_from_the_place_of_work_path'
        ]

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Пользователь с таким именем уже существует')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Пользователь с таким email уже существует')
        return email

    def clean_certificat_from_the_place_of_work_path(self):
        file = self.cleaned_data.get('certificat_from_the_place_of_work_path')
        if file:
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('Файл слишком большой. Максимальный размер: 10 МБ')
        return file

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.patronymic = self.cleaned_data['patronymic']
        
        role_choice = self.cleaned_data['role_choice']
        if role_choice == 'teacher':
            teacher_role, _ = Role.objects.get_or_create(role_name="преподаватель")
            user.role = teacher_role
        else:  
            methodist_role, _ = Role.objects.get_or_create(role_name="методист")
            user.role = methodist_role
        
        user.position = self.cleaned_data['position']
        user.educational_institution = self.cleaned_data['educational_institution']
        user.certificat_from_the_place_of_work_path = self.cleaned_data['certificat_from_the_place_of_work_path']
        
        if commit:
            user.save()
        return user


class LectureForm(forms.ModelForm):
    class Meta:
        model = Lecture
        fields = [
            'lecture_name', 'lecture_content', 'lecture_document_path',
            'lecture_order', 'is_active'
        ]
        widgets = {
            'lecture_name': forms.TextInput(attrs={'class': 'methodist-form-input', 'required': True}),
            'lecture_content': forms.Textarea(attrs={'class': 'methodist-form-textarea', 'rows': 6}),
            'lecture_document_path': forms.ClearableFileInput(attrs={'class': 'methodist-form-input'}),
            'lecture_order': forms.NumberInput(attrs={'class': 'methodist-form-input', 'min': 1}),
            'is_active': forms.CheckboxInput(attrs={'class': 'methodist-form-checkbox'}),
        }

    def __init__(self, *args, **kwargs):
        course = kwargs.pop('course', None)
        super().__init__(*args, **kwargs)
        if course:
            self.fields['lecture_order'].initial = Lecture.objects.filter(course=course).count() + 1

    def clean_lecture_document_path(self):
        doc = self.cleaned_data.get('lecture_document_path')
        if doc and doc.size > 10 * 1024 * 1024:
            raise ValidationError("Документ не более 10 МБ")
        return doc


class TestForm(forms.ModelForm):
    lecture = forms.ModelChoiceField(queryset=Lecture.objects.none(), required=True)

    class Meta:
        model = Test
        fields = ['test_name', 'test_description', 'lecture', 'is_final', 'max_attempts', 'grading_form', 'passing_score', 'is_active']
        widgets = {
            'test_description': forms.Textarea(attrs={'rows': 3}),
            'max_attempts': forms.NumberInput(attrs={'min': 1}),
            'passing_score': forms.NumberInput(attrs={'min': 0, 'max': 100}),
            'is_active': forms.CheckboxInput(attrs={'class': 'methodist-form-checkbox'}),
        }

    def __init__(self, *args, course_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if course_id:
            self.fields['lecture'].queryset = Lecture.objects.filter(course_id=course_id).order_by('lecture_order')
        else:
            self.fields['lecture'].queryset = Lecture.objects.none()


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['question_text', 'answer_type', 'question_score', 'correct_text']
        widgets = {
            'question_text': forms.Textarea(attrs={'rows': 3}),
            'answer_type': forms.Select(attrs={'required': True}),
            'question_score': forms.NumberInput(attrs={'min': 0}),
            'correct_text': forms.Textarea(attrs={'rows': 2}),
        }


class PracticalAssignmentForm(forms.ModelForm):
    lecture = forms.ModelChoiceField(queryset=Lecture.objects.none(), required=True)

    class Meta:
        model = PracticalAssignment
        fields = [
            'practical_assignment_name', 'practical_assignment_description',
            'lecture', 'assignment_deadline', 'grading_type', 'max_score',
            'assignment_criteria', 'assignment_document_path', 'is_active'
        ]
        widgets = {
            'practical_assignment_description': forms.Textarea(attrs={'rows': 4}),
            'assignment_criteria': forms.Textarea(attrs={'rows': 3}),
            'assignment_deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}), 
            'max_score': forms.NumberInput(attrs={'min': 1}),
            'assignment_document_path': forms.ClearableFileInput(attrs={'accept': '.pdf,.doc,.docx'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'methodist-form-checkbox'}),
            
        }

    def __init__(self, *args, course_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if course_id:
            self.fields['lecture'].queryset = Lecture.objects.filter(course_id=course_id).order_by('lecture_order')
        else:
            self.fields['lecture'].queryset = Lecture.objects.none()

    def clean_assignment_document_path(self):
        doc = self.cleaned_data.get('assignment_document_path')
        if doc and doc.size > 10 * 1024 * 1024:
            raise ValidationError("Файл не более 10 МБ")
        return doc
    

from django import forms
from django.contrib.auth.forms import SetPasswordForm
from .models import User, PasswordResetCode
import re

class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        label='Email',
        max_length=100,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите ваш email',
            'autocomplete': 'email'
        })
    )

class CodeVerificationForm(forms.Form):
    code = forms.CharField(
        label='Код подтверждения',
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите 6-значный код',
            'autocomplete': 'off'
        })
    )

class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label="Новый пароль",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите новый пароль',
            'autocomplete': 'new-password'
        }),
    )
    new_password2 = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Повторите новый пароль',
            'autocomplete': 'new-password'
        }),
    )
    
    def clean_new_password1(self):
        password1 = self.cleaned_data.get('new_password1')
        if len(password1) < 8:
            raise forms.ValidationError("Пароль должен содержать минимум 8 символов")
        if not re.search(r'[A-Z]', password1):
            raise forms.ValidationError("Пароль должен содержать хотя бы одну заглавную букву")
        if not re.search(r'[a-z]', password1):
            raise forms.ValidationError("Пароль должен содержать хотя бы одну строчную букву")
        if not re.search(r'[0-9]', password1):
            raise forms.ValidationError("Пароль должен содержать хотя бы одну цифру")
        return password1
    



from django import forms
from .models import Course, PracticalAssignment, Test, Question

class CourseSettingsForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['course_hours', 'course_max_places', 'course_price', 'code_room', 
                 'course_photo_path', 'has_certificate', 'is_active']
        widgets = {
            'course_hours': forms.NumberInput(attrs={'class': 'methodist-form-input'}),
            'course_max_places': forms.NumberInput(attrs={'class': 'methodist-form-input'}),
            'course_price': forms.NumberInput(attrs={'class': 'methodist-form-input', 'step': '0.01'}),
            'code_room': forms.TextInput(attrs={'class': 'methodist-form-input'}),
            'course_photo_path': forms.FileInput(attrs={'class': 'methodist-form-input'}),
        }

class PracticalAssignmentForm(forms.ModelForm):
    class Meta:
        model = PracticalAssignment
        fields = ['practical_assignment_name', 'practical_assignment_description', 
                 'assignment_criteria', 'lecture', 'assignment_deadline', 
                 'grading_type', 'max_score', 'assignment_document_path']
        widgets = {
            'practical_assignment_name': forms.TextInput(attrs={'class': 'methodist-form-input'}),
            'practical_assignment_description': forms.Textarea(attrs={'class': 'methodist-form-textarea', 'rows': 5}),
            'assignment_criteria': forms.Textarea(attrs={'class': 'methodist-form-textarea', 'rows': 3}),
            'lecture': forms.Select(attrs={'class': 'methodist-form-select'}),
            'assignment_deadline': forms.DateTimeInput(attrs={'class': 'methodist-form-input', 'type': 'datetime-local'}),
            'grading_type': forms.Select(attrs={'class': 'methodist-form-select'}),
            'max_score': forms.NumberInput(attrs={'class': 'methodist-form-input'}),
            'assignment_document_path': forms.FileInput(attrs={'class': 'methodist-form-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.course_id = kwargs.pop('course_id', None)
        super().__init__(*args, **kwargs)
        if self.course_id:
            self.fields['lecture'].queryset = Lecture.objects.filter(course_id=self.course_id)

class TestForm(forms.ModelForm):
    class Meta:
        model = Test
        fields = ['test_name', 'test_description', 'lecture', 'max_attempts', 
                 'grading_form', 'passing_score', 'is_final']
        widgets = {
            'test_name': forms.TextInput(attrs={'class': 'methodist-form-input'}),
            'test_description': forms.Textarea(attrs={'class': 'methodist-form-textarea', 'rows': 3}),
            'lecture': forms.Select(attrs={'class': 'methodist-form-select'}),
            'max_attempts': forms.NumberInput(attrs={'class': 'methodist-form-input'}),
            'grading_form': forms.Select(attrs={'class': 'methodist-form-select'}),
            'passing_score': forms.NumberInput(attrs={'class': 'methodist-form-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.course_id = kwargs.pop('course_id', None)
        super().__init__(*args, **kwargs)
        if self.course_id:
            self.fields['lecture'].queryset = Lecture.objects.filter(course_id=self.course_id)

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['question_text', 'answer_type', 'question_score', 'correct_text']
        widgets = {
            'question_text': forms.Textarea(attrs={'class': 'methodist-form-textarea', 'rows': 3}),
            'answer_type': forms.Select(attrs={'class': 'methodist-form-select'}),
            'question_score': forms.NumberInput(attrs={'class': 'methodist-form-input'}),
            'correct_text': forms.Textarea(attrs={'class': 'methodist-form-textarea', 'rows': 3}),
        }