from django.contrib import admin
from django.urls import path
from . import views
from unireax_main.utils.security import BackupDatabaseView

urlpatterns = [

    path('trigger-500/', views.test_500_error, name='trigger_500'),

    path('', views.main, name='main'),
    path('catalog/', views.catalog, name='catalog'),
    path('search/', views.search_courses, name='search_courses'),
    path('auth/', views.auth_view, name='auth'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),


    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/verify/', views.password_reset_verify, name='password_reset_verify'),
    path('password-reset/confirm/', views.password_reset_confirm, name='password_reset_confirm'),
    path('password-reset/complete/', views.password_reset_complete, name='password_reset_complete'),


    path('register/teacher-methodist/', views.register_teacher_methodist, name='register_teacher_methodist'),
    path('registration-listener/', views.register_listener, name='registration_listener'),
    path('policy/site/', views.site_policy, name='site_policy'),
    path('policy/privacy/', views.privacy_notice, name='privacy_notice'),
    path('policy/cookies/', views.cookies_policy, name='cookies_policy'),
    path('about_us/', views.about_us, name='about_us'),
    path('update-theme/', views.update_theme, name='update_theme'),


    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('admin-logs/', views.logs_page, name='logs_page'),
    path('backup/', BackupDatabaseView.as_view(), name='backup_database'),

    path('course/<int:course_id>/', views.course_enroll_detail, name='course_enroll_detail'),
    path('course/<int:course_id>/enroll/', views.enroll_course, name='enroll_course'),
    path('course/<int:course_id>/review/', views.submit_review, name='submit_review'),
    
    
    # оплата
    path('course/<int:course_id>/payment/', views.create_payment, name='create_payment'),
    path('course/<int:course_id>/payment/success/', views.payment_success, name='payment_success'),
    path('course/<int:course_id>/payment/cancel/', views.payment_cancel, name='payment_cancel'),
    path('yookassa/webhook/', views.yookassa_webhook, name='yookassa_webhook'),
    path('course/<int:course_id>/receipt/<str:payment_id>/', views.download_receipt, name='download_receipt'),

    # пользователи
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.create_update_user, name='create_update_user'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('users/<int:user_id>/edit/', views.create_update_user, name='create_update_user'),
    path('users/<int:user_id>/delete/', views.delete_user, name='delete_user'),

    # курсы
    path('courses/', views.course_list, name='course_list'),
    path('courses/<int:course_id>/', views.course_detail, name='course_detail'),
    path('courses/create/', views.create_update_course, name='create_course'),
    path('courses/<int:course_id>/edit/', views.create_update_course, name='update_course'),
    path('courses/<int:course_id>/delete/', views.delete_course, name='delete_course'),

    # роли
    path('roles/', views.role_list, name='role_list'),
    path('roles/create/', views.create_update_role, name='create_update_role'),
    path('roles/<int:role_id>/', views.role_detail, name='role_detail'),
    path('roles/<int:role_id>/edit/', views.create_update_role, name='create_update_role'),
    path('roles/<int:role_id>/delete/', views.delete_role, name='delete_role'),

    # слушатели
    path('user-courses/', views.user_course_list, name='user_course_list'),
    path('user-courses/create/', views.create_update_user_course, name='create_update_user_course'),
    path('user-courses/<int:user_course_id>/', views.user_course_detail, name='user_course_detail'),
    path('user-courses/<int:user_course_id>/edit/', views.create_update_user_course, name='create_update_user_course'),
    path('user-courses/<int:user_course_id>/delete/', views.delete_user_course, name='delete_user_course'),

    # преподаватели
    path('course-teachers/', views.course_teacher_list, name='course_teacher_list'),
    path('course-teachers/create/', views.create_update_course_teacher, name='create_update_course_teacher'),
    path('course-teachers/<int:course_teacher_id>/', views.course_teacher_detail, name='course_teacher_detail'),
    path('course-teachers/<int:course_teacher_id>/edit/', views.create_update_course_teacher, name='create_update_course_teacher'),
    path('course-teachers/<int:course_teacher_id>/delete/', views.delete_course_teacher, name='delete_course_teacher'),

    # верификация
    path('user-verification/', views.admin_user_verification_list, name='admin_user_verification_list'),
    path('user-verification/<int:user_id>/', views.admin_user_verification_detail, name='admin_user_verification_detail'),

    # методист
    path('methodist/dashboard/', views.methodist_dashboard, name='methodist_dashboard'),
    path('methodist/courses/create/', views.create_course, name='methodist_create_course'),
    path('methodist/courses/<int:course_id>/constructor/', views.course_constructor_main, name='methodist_course_constructor'),
    path('methodist/courses/<int:course_id>/lectures/', views.lecture_management, name='methodist_lecture_management'),
    path('methodist/courses/<int:course_id>/tests/', views.test_constructor, name='methodist_test_constructor'),
    path('methodist/courses/<int:course_id>/tests/create/', views.create_test, name='methodist_create_test'),
    path('methodist/courses/<int:course_id>/tests/<int:test_id>/editor/', views.test_editor, name='methodist_test_editor'),
    path('methodist/courses/<int:course_id>/assignments/', views.practical_assignment_management, name='methodist_assignment_management'),
    path('methodist/courses/<int:course_id>/settings/', views.course_settings, name='methodist_course_settings'),

    # методист вопросы 
    path('methodist/courses/<int:course_id>/tests/<int:test_id>/questions/add/', views.add_question, name='methodist_add_question'),
    path('methodist/courses/<int:course_id>/tests/<int:test_id>/questions/<int:question_id>/delete/', views.delete_question, name='methodist_delete_question'),
    path('methodist/courses/<int:course_id>/tests/<int:test_id>/questions/<int:question_id>/choices/add/', views.add_choice_option, name='methodist_add_choice_option'),
    path('methodist/delete_choice_option/<int:option_id>/', views.delete_choice_option, name='delete_choice_option'),
    path('methodist/courses/<int:course_id>/tests/<int:test_id>/questions/<int:question_id>/matching/add/', views.add_matching_pair, name='add_matching_pair'),
    path('methodist/delete_matching_pair/<int:pair_id>/', views.delete_matching_pair, name='delete_matching_pair'),


    # Статистика для методиста
    path('methodist/statistics/', views.methodist_statistics, name='methodist_statistics'),
    path('methodist/export/csv/<str:export_type>/', views.export_statistics_csv, name='export_statistics_csv'),
    path('methodist/export/pdf/<str:export_type>/', views.export_statistics_pdf, name='export_statistics_pdf'),



    path('course/<int:course_id>/statistics/', views.student_statistics_view, name='student_statistics'),
    path('course/<int:course_id>/graded/', views.graded_assignments_view, name='graded_assignments'),
    path('course/<int:course_id>/all-test-results/', views.all_test_results_view, name='all_test_results'),



    path('course/study/<int:course_id>/', views.course_study_view, name='course_study'),
    path('lecture/<int:lecture_id>/', views.lecture_detail_view, name='lecture_detail'),


    path('test/start/<int:test_id>/', views.test_start_view, name='test_start'),
    path('test/<int:test_id>/submit/', views.test_submit_view, name='test_submit'),
    path('course/<int:course_id>/results/', views.test_results_view, name='test_results'),

    path('practical/submit/<int:assignment_id>/', views.practical_submit_view, name='practical_submit'),

    path('favorites/toggle/<int:course_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('favorites/', views.favorites_page, name='favorites_page'),


    path('certificates/', views.my_certificates, name='my_certificates'),
    path('certificate/<int:certificate_id>/', views.certificate_detail, name='certificate_detail'),
    path('certificate/<int:certificate_id>/download/', views.download_certificate, name='download_certificate'),
    path('course/<int:course_id>/check-certificate/', views.check_certificate_eligibility, name='check_certificate_eligibility'),
    path('course/<int:course_id>/generate-certificate/', views.generate_certificate, name='generate_certificate'),



    # преподавание
    path('course/<int:course_id>/teach/', views.course_teach, name='course_teach'),
    path('submission/<int:submission_id>/grade/', views.grade_assignment, name='grade_assignment'),
    path('course/<int:course_id>/student/<int:student_id>/progress/', views.student_progress, name='student_progress'),

    path('course/create/', views.create_course_teacher, name='create_course'),
    path('course/<int:course_id>/students/', views.course_students_management, name='course_students_management'),
    path('course/<int:course_id>/upload-csv/', views.upload_students_csv, name='upload_students_csv'),
    path('course/<int:course_id>/generate-csv/', views.generate_students_csv, name='generate_students_csv'),
    path('teacher/courses/', views.teacher_courses, name='teacher_courses'),    


    path('course/<int:course_id>/exit/', views.exit_course, name='exit_course'),
    path('course/<int:course_id>/return/', views.return_to_course, name='return_to_course'),
    path('delete-account/', views.delete_account, name='delete_account'),
    
]