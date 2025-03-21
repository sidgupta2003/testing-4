from django.urls import path
from . import views
from .views import *

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('instructor_dashboard/', views.instructor_dashboard, name='instructor_dashboard'),
    path('student_dashboard/', views.student_dashboard, name='student_dashboard'),
    path('create_class/', views.create_class, name='create_class'),
    path('delete_class/<int:class_id>/', views.delete_class, name='delete_class'),
    path('update_class/<int:class_id>/', views.update_class, name='update_class'),
    path('create_subject/', views.create_subject, name='create_subject'),
    path('view_classes/', views.view_classes, name='view_classes'),
    path('view_subjects/', views.view_subjects, name='view_subjects'),
    path('delete_subject/<int:subject_id>/', views.delete_subject, name="delete_subject"),
    path('update_subject/<int:subject_id>/', views.update_subject, name='update_subject'),
    path('create_student/', views.create_student, name='create_student'),
    path('view_students/', views.view_students, name='view_students'),
    path('update_student/<int:student_id>/', views.update_student, name='update_student'),
    path('delete_student/<int:student_id>/', views.delete_student, name='delete_student'),
    path('create_instructor/', views.create_instructor, name='create_instructor'),
    path('view_instructors/', views.view_instructors, name='view_instructors'),
    path('update_instructor/<int:instructor_id>/', views.update_instructor, name='update_instructor'),
    path('delete_instructor/<int:instructor_id>/', views.delete_instructor, name='delete_instructor'),
    path('import_students/', views.import_students, name='import_students'),
    path('export_students/', views.export_students, name='export_students'),
    path('import_instructors/', views.import_instructors, name='import_instructors'),
    path('export_instructors/', views.export_instructors, name='export_instructors'),
    path('create_exam/', views.create_exam, name='create_exam'),
    path('view_exams/', views.view_exams, name='view_exams'),
    path('update_exam/<int:exam_id>/', views.update_exam, name='update_exam'),
    path('delete_exam/<int:exam_id>/', views.delete_exam, name='delete_exam'),
    path('get_subjects_by_class/', views.get_subjects_by_class, name='get_subjects_by_class'),
    path('create_notification/', create_notification, name='create_notification'),
    path('view_notifications/', view_notifications, name='view_notifications'),
    path('notifications/delete/<int:notification_id>/', views.delete_notification, name='delete_notification'),
    path('get_students/<int:class_id>/', get_students, name='get_students'),
    path('get_instructors/<int:class_id>/', get_instructors, name='get_instructors'),
    path('student_notifications/', views.student_notifications, name='student_notifications'),
    path('student_quizzes/', views.student_quizzes, name='student_quizzes'),
    path('student_quiz/<int:quiz_id>/', views.student_quiz_detail, name='student_quiz_detail'),
    path('take_quiz/<int:quiz_id>/', views.take_quiz, name='take_quiz'),
    path('quiz_result/<int:quiz_id>/', views.quiz_result, name='quiz_result'),
    path('update_notification/<int:notification_id>/', views.update_notification, name='update_notification'),
    # path('instructor_notifications/', views.instructor_notifications, name='instructor_notifications'),
    # Quiz Management
    path('quizzes/', views.view_quizzes, name='view_quizzes'),
    path('quizzes/create/', views.create_quiz, name='create_quiz'),
    path('quizzes/create/<int:quiz_id>/questions/', views.create_quiz_questions, name='create_quiz_questions'),
    path('quizzes/<int:quiz_id>/', views.view_quiz, name='view_quiz'),
    path('quizzes/<int:quiz_id>/edit/', views.edit_quiz, name='edit_quiz'),
    path('quizzes/<int:quiz_id>/delete/', views.delete_quiz, name='delete_quiz'),
    path('mark_notification_as_seen/<int:notification_id>/', views.mark_notification_as_seen, name='mark_notification_as_seen'),
    path('mark_notifications_as_seen/', views.mark_notifications_as_seen, name='mark_notifications_as_seen'),
    path('create_timetable/', views.create_timetable, name='create_timetable'),
    path('create_daily_override/', views.create_daily_override, name='create_daily_override'),
    path('view_timetables/', views.view_timetables, name='view_timetables'),
    path('view_daily_overrides/', views.view_daily_overrides, name='view_daily_overrides'),
    path('get_subjects_for_timetable/', views.get_subjects_for_timetable, name='get_subjects_for_timetable'),
    path('get_timetable_data/', views.get_timetable_data, name='get_timetable_data'),
    path('student_timetable/', views.student_timetable, name='student_timetable'),
    path('update_timetable/<int:id>/', views.update_timetable, name='update_timetable'),
    path('delete_timetable/<int:id>/', views.delete_timetable, name='delete_timetable'),
    path('update_daily_override/<int:id>/', views.update_daily_override, name='update_daily_override'),
    path('delete_daily_override/<int:id>/', views.delete_daily_override, name='delete_daily_override'),
    path('create_single_timetable/', views.create_single_timetable, name='create_single_timetable'),
    path('gemini_chat/', views.gemini_chat_view, name='gemini_chat_view'),
    path('gemini_get_response/', views.gemini_ai_chat, name='gemini_ai_chat'),
    # path("chat/", chat_view, name="chat_view"),
    # path("get_response/", ai_chat, name="ai_chat"),
    # path('chat_/', ai_chat_, name='ai_chat_'),
    # path("chats/", chat_with_ai),   # API route
    # path("chatsss", chatbot_page), 
] 