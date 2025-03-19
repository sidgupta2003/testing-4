from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.utils import timezone
from .models import *
from .forms import *
import csv
from django.http import HttpResponse, JsonResponse
from datetime import date, datetime, timedelta
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q
from django.urls import reverse
import json
from django import template
import openai
from django.conf import settings
# from transformers import pipeline
import requests
import google.generativeai as genai

# from django.core.exceptions import PageNotAnInteger, EmptyPage

register = template.Library()

def is_admin(user):
    return user.role and user.role.role_name.lower() == 'admin'

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        role_id = request.POST.get('role')
        
        user = authenticate(username=username, password=password)
        
        if user is not None:
            # Check if the user has the selected role
            if user.role and str(user.role.id) == role_id:
                login(request, user)

                # Get the latest notifications for this user
                newest_notifications = []
                
                if user.role.role_name.lower() == 'student':
                    try:
                        student = Student.objects.get(user=user)
                        # Get student-specific and general notifications
                        newest_notifications = Notification.objects.filter(
                            Q(create_for='all') | 
                            Q(create_for='student', students=student),
                            is_seen=False
                        ).distinct().order_by('-created_at')[:5]
                    except Student.DoesNotExist:
                        messages.error(request, 'Student profile not found.')
                    
                elif user.role.role_name.lower() == 'instructor':
                    try:
                        instructor = Instructor.objects.get(user=user)
                        # Get instructor-specific and general notifications
                        newest_notifications = Notification.objects.filter(
                            Q(create_for='all') | 
                            Q(create_for='instructor', instructors=instructor),
                            is_seen=False
                        ).distinct().order_by('-created_at')[:5]
                    except Instructor.DoesNotExist:
                        messages.error(request, 'Instructor profile not found.')
                else:
                    # For admin, show all notifications
                    newest_notifications = Notification.objects.filter(
                        is_seen=False
                    ).distinct().order_by('-created_at')[:5]

                # Store notifications in session
                if newest_notifications:
                    request.session['new_notifications'] = [{
                        'id': notification.id,
                        'title': notification.title,
                        'description': notification.description,
                        'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'image': notification.image.url if notification.image else None
                    } for notification in newest_notifications]
                    # Save the session explicitly
                    request.session.modified = True
                    print(f"Added {len(newest_notifications)} notifications to session") # Debug print
                
                # Redirect based on role
                if user.role.role_name.lower() == 'admin':
                    return redirect('admin_dashboard')
                elif user.role.role_name.lower() == 'instructor':
                    return redirect('instructor_dashboard')
                elif user.role.role_name.lower() == 'student':
                    return redirect('student_dashboard')
            else:
                messages.error(request, 'Invalid role selected for this user.')
        else:
            messages.error(request, 'Invalid username or password.')
    
    roles = Role.objects.all()
    return render(request, 'lms/login.html', {'roles': roles})

@login_required
def admin_dashboard(request):
    if not request.user.role or request.user.role.role_name.lower() != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')
    
    # Get counts for dashboard statistics
    total_users = CustomUser.objects.count()
    total_students = Student.objects.count()
    total_instructors = Instructor.objects.count()
    total_classes = Class.objects.count()
    total_subjects = Subject.objects.count()
    total_exams = Exam.objects.count()
    
    # Get today's date
    today = date.today()
    
    # Get upcoming exams (exams with future dates)
    upcoming_exams = Exam.objects.filter(exam_date__gte=today).order_by('exam_date')[:5]
    
    # Get recent activities (latest 5 exams created)
    recent_exams = Exam.objects.order_by('-created_at')[:5]
    
    context = {
        'total_users': total_users,
        'total_students': total_students,
        'total_instructors': total_instructors,
        'total_classes': total_classes,
        'total_subjects': total_subjects,
        'total_exams': total_exams,
        'upcoming_exams': upcoming_exams,
        'recent_exams': recent_exams,
        'today': today,
    }
    
    return render(request, 'lms/admin/dashboard.html', context)

@login_required
def student_dashboard(request):
    if not request.user.role or request.user.role.role_name.lower() != 'student':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')
    
    try:
        student = Student.objects.get(user=request.user)
        
        # Get student's classes and subjects
        classes = student.classes.all()
        subjects = student.subjects.all()
        
        # Get notifications for the student - using distinct() to avoid duplicates
        student_notifications = Notification.objects.filter(
            Q(students=student) | Q(create_for='all'),
            is_seen=False
        ).distinct().order_by('-created_at')
        
        # Store new notifications in session - ensure each notification appears only once
        if student_notifications.exists():
            # Use a dictionary to ensure uniqueness by notification ID
            notification_dict = {}
            for notification in student_notifications[:5]:
                notification_dict[notification.id] = {
                    'id': notification.id,
                    'title': notification.title,
                    'description': notification.description,
                    'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M:%S')
                }
            
            # Convert dictionary values to list for session storage
            request.session['new_notifications'] = list(notification_dict.values())
            request.session.modified = True
        
        # Get quizzes for the student's classes and subjects
        student_quizzes = Quiz.objects.filter(
            exam__class_id__in=classes,
            exam__subject__in=subjects
        ).order_by('-created_at')
        
        # Get attempted quizzes
        attempted_quizzes = QuizAttempt.objects.filter(student=student).order_by('-completed_at')
        attempted_quiz_ids = set(attempted_quizzes.values_list('quiz_id', flat=True))
        
        # Filter out attempted quizzes from available quizzes
        available_quizzes = student_quizzes.exclude(id__in=attempted_quiz_ids)
        
        # Get total counts
        total_subjects = subjects.count()
        total_classes = classes.count()
        total_available_quizzes = available_quizzes.count()
        total_attempted_quizzes = attempted_quizzes.count()
        
        # Limit the querysets after evaluation
        student_notifications = list(student_notifications[:5])
        available_quizzes = list(available_quizzes[:5])
        attempted_quizzes = list(attempted_quizzes[:5])
        
        context = {
            'student': student,
            'notifications': student_notifications,
            'available_quizzes': available_quizzes,
            'attempted_quizzes': attempted_quizzes,
            'classes': classes,
            'subjects': subjects,
            'total_subjects': total_subjects,
            'total_classes': total_classes,
            'total_available_quizzes': total_available_quizzes,
            'total_attempted_quizzes': total_attempted_quizzes,
        }
        return render(request, 'lms/student/dashboard.html', context)
    except Student.DoesNotExist:
        messages.error(request, 'Student profile not found.')
        return redirect('login')

@login_required
def instructor_dashboard(request):
    if not request.user.role or request.user.role.role_name.lower() != 'instructor':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')
    
    try:
        instructor = Instructor.objects.get(user=request.user)
        
        # Get instructor's classes and subjects
        classes = instructor.classes.all()
        subjects = instructor.subjects.all()
        
        # Get students in instructor's classes
        students = Student.objects.filter(classes__in=classes).distinct()
        
        # Get quizzes for instructor's classes and subjects
        quizzes = Quiz.objects.filter(
            exam__class_id__in=classes,
            exam__subject__in=subjects
        ).order_by('-created_at')
        
        # Get quiz attempts by students
        quiz_attempts = QuizAttempt.objects.filter(
            quiz__in=quizzes
        ).select_related('student', 'quiz').order_by('-completed_at')
        
        # Get notifications for the instructor
        instructor_notifications = Notification.objects.filter(instructors=instructor).order_by('-created_at')
        all_notifications = Notification.objects.filter(create_for='all').order_by('-created_at')
        
        # Get total counts
        total_students = students.count()
        total_classes = classes.count()
        total_subjects = subjects.count()
        total_quizzes = quizzes.count()
        total_attempts = quiz_attempts.count()
        
        # Limit the querysets for display
        recent_students = list(students[:5])
        recent_quiz_attempts = list(quiz_attempts[:5])
        instructor_notifications = list(instructor_notifications[:5])
        all_notifications = list(all_notifications[:5])
        
        context = {
            'instructor': instructor,
            'classes': classes,
            'subjects': subjects,
            'recent_students': recent_students,
            'recent_quiz_attempts': recent_quiz_attempts,
            'notifications': instructor_notifications,
            'all_notifications': all_notifications,
            'total_students': total_students,
            'total_classes': total_classes,
            'total_subjects': total_subjects,
            'total_quizzes': total_quizzes,
            'total_attempts': total_attempts,
        }
        return render(request, 'lms/instructor/dashboard.html', context)
    except Instructor.DoesNotExist:
        messages.error(request, 'Instructor profile not found.')
        return redirect('login')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def create_class(request):
    if request.method == 'POST':
        form = ClassForm(request.POST)
        if form.is_valid():
            new_class = form.save()
            messages.success(request, f'Class "{new_class.name}" has been created successfully.')
            return redirect('view_classes')
    else:
        form = ClassForm()
    return render(request, 'lms/create/create_class.html', {'form': form})

@login_required
def delete_class(request, class_id):
    class_to_delete = get_object_or_404(Class, id=class_id)
    class_name = class_to_delete.name  # Store the name before deletion
    class_to_delete.delete()
    messages.success(request, f'Class "{class_name}" has been deleted successfully.')
    return redirect('view_classes')

@login_required
def update_class(request, class_id):
    class_instance = get_object_or_404(Class, id=class_id)
    return render(request, 'lms/edit/edit_class.html', {'class_instance' : class_instance})



@login_required
def create_subject(request):
    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Subject created successfully.')
            return redirect('view_subjects')
    else:
        form = SubjectForm()
    
    classes = Class.objects.all()
    return render(request, 'lms/create/create_subject.html', {'form': form, 'classes': classes})

@login_required
def delete_subject(request, subject_id):
    subject_to_delete = get_object_or_404(Subject, id=subject_id)
    subject_name = subject_to_delete.name  # Store the name before deletion
    subject_to_delete.delete()
    messages.success(request, f'Subject "{subject_name}" has been deleted successfully.')
    return redirect('view_subjects')

@login_required
def update_subject(request, subject_id):
    subject_instance = get_object_or_404(Subject, id=subject_id)
    if request.method == 'POST' :
        form = SubjectForm(request.Post, instance=subject_instance)
        if form.is_valid():
            form.save()
            messages.success(request, 'Subject updated successfully')
            return redirect('view_subjects')
    else:
        form = SubjectForm(instance=subject_instance)
    return render(request, 'lms/edit/edit_subject.html', {'form' : form, 'subject_instance': subject_instance})



@login_required
def view_classes(request):
    classes = Class.objects.all()
    return render(request, 'lms/view/view_classes.html', {'classes': classes})

@login_required
def view_subjects(request):
    subjects_list = Subject.objects.all()
    paginator = Paginator(subjects_list, 10)  # Show 10 subjects per page

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'lms/view/view_subjects.html', {'page_obj': page_obj, 'subjects': subjects_list})

@login_required
def create_student(request):
    if not request.user.role or request.user.role.role_name.lower() != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')
        
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            # Get the student role
            student_role = Role.objects.get(role_name='student')
            
            # Create the user
            user = CustomUser.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password']
            )
            user.role = student_role
            user.save()
            
            # Create the student
            student = Student.objects.create(user=user)
            
            # Get selected subjects and their classes
            selected_subjects = form.cleaned_data['subjects']
            classes = set(subject.class_id for subject in selected_subjects)
            
            # Add classes and subjects
            student.classes.set(classes)
            student.subjects.set(selected_subjects)
            
            messages.success(request, 'Student created successfully.')
            return redirect('view_students')
    else:
        form = StudentForm()
    
    # Group subjects by class
    subjects_by_class = {}
    for subject in Subject.objects.all().select_related('class_id'):
        class_name = subject.class_id.name
        if class_name not in subjects_by_class:
            subjects_by_class[class_name] = []
        subjects_by_class[class_name].append(subject)
    
    return render(request, 'lms/create/create_student.html', {
        'form': form,
        'subjects_by_class': subjects_by_class
    })

@login_required
def view_students(request):
    if not request.user.role or request.user.role.role_name.lower() != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')
        
    students_list = Student.objects.all()
    paginator = Paginator(students_list, 10)  # Show 10 students per page

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'lms/view/view_students.html', {'page_obj': page_obj, 'students': students_list})

@login_required
def update_student(request, student_id):
    if not request.user.role or request.user.role.role_name.lower() != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')
    
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            # Update user information
            student.user.username = form.cleaned_data['username']
            student.user.email = form.cleaned_data['email']
            if form.cleaned_data['password']:  # Only update password if provided
                student.user.set_password(form.cleaned_data['password'])
            student.user.save()
            
            # Update student's classes and subjects
            student.classes.set(form.cleaned_data['classes'])
            student.subjects.set(form.cleaned_data['subjects'])
            student.save()
            
            messages.success(request, 'Student updated successfully.')
            return redirect('view_students')
    else:
        initial_data = {
            'username': student.user.username,
            'email': student.user.email,
            'classes': student.classes.all(),
            'subjects': student.subjects.all(),
        }
        form = StudentForm(initial=initial_data)
    
    return render(request, 'lms/edit/edit_student.html', {
        'form': form,
        'student': student
    })

@login_required
def delete_student(request, student_id):
    student_to_delete = get_object_or_404(Student, id=student_id)
    student_to_delete.delete()
    messages.success(request, 'Student deleted successfully.')
    return redirect('view_students')


@login_required
def create_instructor(request):
    if not request.user.role or request.user.role.role_name.lower() != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')
        
    if request.method == 'POST':
        form = InstructorForm(request.POST)
        if form.is_valid():
            # Get the instructor role
            instructor_role = Role.objects.get(role_name='instructor')
            
            # Create the user
            user = CustomUser.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password']
            )
            user.role = instructor_role
            user.save()
            
            # Create the instructor
            instructor = Instructor.objects.create(
                user=user,
                specialization=form.cleaned_data['specialization']
            )
            
            # Get selected subjects and their classes
            selected_subjects = form.cleaned_data['subjects']
            classes = set(subject.class_id for subject in selected_subjects)
            
            # Add classes and subjects
            instructor.classes.set(classes)
            instructor.subjects.set(selected_subjects)
            
            messages.success(request, 'Instructor created successfully.')
            return redirect('view_instructors')
    else:
        form = InstructorForm()
    
    # Group subjects by class
    subjects_by_class = {}
    for subject in Subject.objects.all().select_related('class_id'):
        class_name = subject.class_id.name
        if class_name not in subjects_by_class:
            subjects_by_class[class_name] = []
        subjects_by_class[class_name].append(subject)
    
    return render(request, 'lms/create/create_instructor.html', {
        'form': form,
        'subjects_by_class': subjects_by_class
    })

@login_required
def view_instructors(request):
    if not request.user.role or request.user.role.role_name.lower() != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')
        
    instructors_list = Instructor.objects.all()
    paginator = Paginator(instructors_list, 10)  # Show 10 instructors per page

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'lms/view/view_instructors.html', {'page_obj': page_obj, 'instructors': instructors_list})

@login_required
def update_instructor(request, instructor_id):
    if not request.user.role or request.user.role.role_name.lower() != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')
    
    instructor = get_object_or_404(Instructor, id=instructor_id)
    if request.method == 'POST':
        form = InstructorForm(request.POST, instance=instructor)
        if form.is_valid():
            # Update user information
            instructor.user.username = form.cleaned_data['username']
            instructor.user.email = form.cleaned_data['email']
            if form.cleaned_data['password']:  # Only update password if provided
                instructor.user.set_password(form.cleaned_data['password'])
            instructor.user.save()
            
            # Update instructor's specialization, classes and subjects
            instructor.specialization = form.cleaned_data['specialization']
            instructor.classes.set(form.cleaned_data['classes'])
            instructor.subjects.set(form.cleaned_data['subjects'])
            instructor.save()
            
            messages.success(request, 'Instructor updated successfully.')
            return redirect('view_instructors')
    else:
        initial_data = {
            'username': instructor.user.username,
            'email': instructor.user.email,
            'specialization': instructor.specialization,
            'classes': instructor.classes.all(),
            'subjects': instructor.subjects.all(),
        }
        form = InstructorForm(initial=initial_data)
    
    return render(request, 'lms/edit/edit_instructor.html', {
        'form': form,
        'instructor': instructor
    })

@login_required
def delete_instructor(request, instructor_id):
    instructor_to_delete = get_object_or_404(Instructor, id=student_id)
    instructor_to_delete.delete()
    messages.success(request, 'instructor deleted successfully.')
    return redirect('view_instructors')

@login_required
def import_students(request):
    if request.user.role.role_name.lower() != 'admin':
        return redirect('login')
    
    if request.method == 'POST':
        if 'csv_file' in request.FILES:
            csv_file = request.FILES['csv_file']
            
            # Check if it's a CSV file
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Please upload a CSV file.')
                return render(request, 'lms/admin/import_students.html')
            
            # Process the CSV file
            try:
                # Decode the file
                file_data = csv_file.read().decode('utf-8')
                lines = file_data.split('\n')
                
                # Skip the header row
                header = lines[0].strip().split(',')
                required_fields = ['username', 'email', 'password']
                
                # Check if required fields are in the header
                for field in required_fields:
                    if field not in header:
                        messages.error(request, f'CSV file is missing required field: {field}')
                        return render(request, 'lms/admin/import_students.html')
                
                # Get indices for each field
                username_idx = header.index('username')
                email_idx = header.index('email')
                password_idx = header.index('password')
                
                # Optional fields
                classes_idx = header.index('classes') if 'classes' in header else None
                subjects_idx = header.index('subjects') if 'subjects' in header else None
                
                # Process each row
                success_count = 0
                error_count = 0
                
                for i in range(1, len(lines)):
                    if not lines[i].strip():
                        continue
                    
                    row = lines[i].strip().split(',')
                    
                    # Skip rows that don't have enough fields
                    if len(row) < len(required_fields):
                        error_count += 1
                        continue
                    
                    username = row[username_idx].strip()
                    email = row[email_idx].strip()
                    password = row[password_idx].strip()
                    
                    # Check if user already exists
                    if CustomUser.objects.filter(username=username).exists():
                        error_count += 1
                        continue
                    
                    if CustomUser.objects.filter(email=email).exists():
                        error_count += 1
                        continue
                    
                    # Get student role
                    student_role = Role.objects.get(role_name='student')
                    
                    # Create user
                    user = CustomUser.objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                        role=student_role
                    )
                    
                    # Create student
                    student = Student.objects.create(user=user)
                    
                    # Add classes if provided
                    if classes_idx is not None and len(row) > classes_idx:
                        class_ids = row[classes_idx].strip().split(';')
                        for class_id in class_ids:
                            if class_id.strip():
                                try:
                                    class_obj = Class.objects.get(id=int(class_id.strip()))
                                    student.classes.add(class_obj)
                                except (Class.DoesNotExist, ValueError):
                                    pass
                    
                    # Add subjects if provided
                    if subjects_idx is not None and len(row) > subjects_idx:
                        subject_ids = row[subjects_idx].strip().split(';')
                        for subject_id in subject_ids:
                            if subject_id.strip():
                                try:
                                    subject_obj = Subject.objects.get(id=int(subject_id.strip()))
                                    student.subjects.add(subject_obj)
                                except (Subject.DoesNotExist, ValueError):
                                    pass
                    
                    success_count += 1
                
                if success_count > 0:
                    messages.success(request, f'Successfully imported {success_count} students.')
                
                if error_count > 0:
                    messages.warning(request, f'Failed to import {error_count} students due to errors.')
                
                return redirect('view_students')
                
            except Exception as e:
                messages.error(request, f'Error processing CSV file: {str(e)}')
        else:
            messages.error(request, 'Please select a CSV file to upload.')
    
    return render(request, 'lms/admin/import_students.html')

@login_required
def export_students(request):
    if request.user.role.role_name.lower() != 'admin':
        return redirect('login')
    
    classes = Class.objects.all()
    
    if request.method == 'POST':
        class_id = request.POST.get('class_id')
        
        if not class_id:
            messages.error(request, 'Please select a class.')
            return render(request, 'lms/admin/export_students.html', {'classes': classes})
        
        try:
            class_obj = Class.objects.get(id=class_id)
            students = Student.objects.filter(classes=class_obj)
            
            if not students:
                messages.warning(request, f'No students found in class {class_obj.name}.')
                return render(request, 'lms/admin/export_students.html', {'classes': classes})
            
            # Create CSV response
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="students_{class_obj.name}.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['username', 'email', 'classes', 'subjects'])
            
            for student in students:
                # Get classes as comma-separated string
                classes_str = ';'.join([str(c.id) for c in student.classes.all()])
                
                # Get subjects as comma-separated string
                subjects_str = ';'.join([str(s.id) for s in student.subjects.all()])
                
                writer.writerow([
                    student.user.username,
                    student.user.email,
                    classes_str,
                    subjects_str
                ])
            
            return response
            
        except Class.DoesNotExist:
            messages.error(request, 'Selected class does not exist.')
        except Exception as e:
            messages.error(request, f'Error exporting students: {str(e)}')
    
    return render(request, 'lms/admin/export_students.html', {'classes': classes})

@login_required
def import_instructors(request):
    if request.user.role.role_name.lower() != 'admin':
        return redirect('login')
    
    if request.method == 'POST':
        if 'csv_file' in request.FILES:
            csv_file = request.FILES['csv_file']
            
            # Check if it's a CSV file
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Please upload a CSV file.')
                return render(request, 'lms/admin/import_instructors.html')
            
            # Process the CSV file
            try:
                # Decode the file
                file_data = csv_file.read().decode('utf-8')
                lines = file_data.split('\n')
                
                # Skip the header row
                header = lines[0].strip().split(',')
                required_fields = ['username', 'email', 'password']
                
                # Check if required fields are in the header
                for field in required_fields:
                    if field not in header:
                        messages.error(request, f'CSV file is missing required field: {field}')
                        return render(request, 'lms/admin/import_instructors.html')
                
                # Get indices for each field
                username_idx = header.index('username')
                email_idx = header.index('email')
                password_idx = header.index('password')
                
                # Optional fields
                specialization_idx = header.index('specialization') if 'specialization' in header else None
                classes_idx = header.index('classes') if 'classes' in header else None
                subjects_idx = header.index('subjects') if 'subjects' in header else None
                
                # Process each row
                success_count = 0
                error_count = 0
                
                for i in range(1, len(lines)):
                    if not lines[i].strip():
                        continue
                    
                    row = lines[i].strip().split(',')
                    
                    # Skip rows that don't have enough fields
                    if len(row) < len(required_fields):
                        error_count += 1
                        continue
                    
                    username = row[username_idx].strip()
                    email = row[email_idx].strip()
                    password = row[password_idx].strip()
                    
                    # Check if user already exists
                    if CustomUser.objects.filter(username=username).exists():
                        error_count += 1
                        continue
                    
                    if CustomUser.objects.filter(email=email).exists():
                        error_count += 1
                        continue
                    
                    # Get instructor role
                    instructor_role = Role.objects.get(role_name='instructor')
                    
                    # Create user
                    user = CustomUser.objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                        role=instructor_role
                    )
                    
                    # Create instructor
                    specialization = None
                    if specialization_idx is not None and len(row) > specialization_idx:
                        specialization = row[specialization_idx].strip()
                    
                    instructor = Instructor.objects.create(
                        user=user,
                        specialization=specialization
                    )
                    
                    # Add classes if provided
                    if classes_idx is not None and len(row) > classes_idx:
                        class_ids = row[classes_idx].strip().split(';')
                        for class_id in class_ids:
                            if class_id.strip():
                                try:
                                    class_obj = Class.objects.get(id=int(class_id.strip()))
                                    instructor.classes.add(class_obj)
                                except (Class.DoesNotExist, ValueError):
                                    pass
                    
                    # Add subjects if provided
                    if subjects_idx is not None and len(row) > subjects_idx:
                        subject_ids = row[subjects_idx].strip().split(';')
                        for subject_id in subject_ids:
                            if subject_id.strip():
                                try:
                                    subject_obj = Subject.objects.get(id=int(subject_id.strip()))
                                    instructor.subjects.add(subject_obj)
                                except (Subject.DoesNotExist, ValueError):
                                    pass
                    
                    success_count += 1
                
                if success_count > 0:
                    messages.success(request, f'Successfully imported {success_count} instructors.')
                
                if error_count > 0:
                    messages.warning(request, f'Failed to import {error_count} instructors due to errors.')
                
                return redirect('view_instructors')
                
            except Exception as e:
                messages.error(request, f'Error processing CSV file: {str(e)}')
        else:
            messages.error(request, 'Please select a CSV file to upload.')
    
    return render(request, 'lms/admin/import_instructors.html')

@login_required
def export_instructors(request):
    if request.user.role.role_name.lower() != 'admin':
        return redirect('login')
    
    classes = Class.objects.all()
    
    if request.method == 'POST':
        class_id = request.POST.get('class_id')
        
        if not class_id:
            messages.error(request, 'Please select a class.')
            return render(request, 'lms/admin/export_instructors.html', {'classes': classes})
        
        try:
            class_obj = Class.objects.get(id=class_id)
            instructors = Instructor.objects.filter(classes=class_obj)
            
            if not instructors:
                messages.warning(request, f'No instructors found in class {class_obj.name}.')
                return render(request, 'lms/admin/export_instructors.html', {'classes': classes})
            
            # Create CSV response
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="instructors_{class_obj.name}.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['username', 'email', 'specialization', 'classes', 'subjects'])
            
            for instructor in instructors:
                # Get classes as comma-separated string
                classes_str = ';'.join([str(c.id) for c in instructor.classes.all()])
                
                # Get subjects as comma-separated string
                subjects_str = ';'.join([str(s.id) for s in instructor.subjects.all()])
                
                writer.writerow([
                    instructor.user.username,
                    instructor.user.email,
                    instructor.specialization or '',
                    classes_str,
                    subjects_str
                ])
            
            return response
            
        except Class.DoesNotExist:
            messages.error(request, 'Selected class does not exist.')
        except Exception as e:
            messages.error(request, f'Error exporting instructors: {str(e)}')
    
    return render(request, 'lms/admin/export_instructors.html', {'classes': classes})

@login_required
def create_exam(request):
    if request.user.role.role_name.lower() != 'admin':
        return redirect('login')
    
    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.created_by = request.user
            exam.save()
            messages.success(request, 'Exam created successfully.')
            return redirect('view_exams')
    else:
        form = ExamForm()
    
    return render(request, 'lms/create/create_exam.html', {'form': form})

@login_required
def view_exams(request):
    if request.user.role.role_name.lower() != 'admin':
        return redirect('login')
    
    exams_list = Exam.objects.all()
    paginator = Paginator(exams_list, 10)  # Show 10 exams per page
    
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'lms/view/view_exams.html', {'page_obj': page_obj, 'exams': exams_list})

@login_required
def get_subjects_by_class(request):
    class_id = request.GET.get('class_id')
    subjects = []
    
    if class_id:
        subjects = list(Subject.objects.filter(class_id=class_id).values('id', 'name'))
    
    return JsonResponse({'subjects': subjects})


@login_required
def create_notification(request):
    if request.method == 'POST':
        create_for = request.POST.get('create_for')
        title = request.POST.get('title')
        description = request.POST.get('description')
        student_ids = request.POST.getlist('students')  # List of student IDs
        instructor_ids = request.POST.getlist('instructors')  # List of instructor IDs
        image = request.FILES.get('image')  # Get the uploaded image file

        # Create a single notification
        notification = Notification.objects.create(
            create_for=create_for,
            title=title,
            description=description
        )

        # Assign recipients based on role
        if create_for == 'student':
            if 'all' in student_ids:
                # Add all students to the notification
                students = Student.objects.all()
                notification.students.add(*students)
                recipient_msg = "all students"
            else:
                # Add selected students to the notification
                students = Student.objects.filter(id__in=student_ids)
                notification.students.add(*students)
                recipient_msg = f"{students.count()} selected students"
        
        elif create_for == 'instructor':
            if 'all' in instructor_ids:
                # Add all instructors to the notification
                instructors = Instructor.objects.all()
                notification.instructors.add(*instructors)
                recipient_msg = "all instructors"
            else:
                # Add selected instructors to the notification
                instructors = Instructor.objects.filter(id__in=instructor_ids)
                notification.instructors.add(*instructors)
                recipient_msg = f"{instructors.count()} selected instructors"

        else:  # If "all" is selected for both students and instructors
            # Add all students and instructors to the notification
            students = Student.objects.all()
            instructors = Instructor.objects.all()
            notification.students.add(*students)
            notification.instructors.add(*instructors)
            recipient_msg = "all users"

        # Handle image upload if provided
        if image:
            notification.image = image
            notification.save()

        messages.success(request, f'Notification "{title}" has been created successfully for {recipient_msg}.')
        return redirect('view_notifications')

    classes = Class.objects.all()
    instructors = Instructor.objects.all()

    context = {
        'classes': classes,
        'instructors': instructors,
        'user_role': 'admin' if request.user.is_superuser else 'instructor'
    }
    return render(request, 'lms/create/create_notification.html', context)



@login_required
def get_students(request, class_id):
    try:
        students = Student.objects.filter(classes__id=class_id).select_related('user')
        student_data = [{
            'id': student.id,
            'username': student.user.username,
            'email': student.user.email
        } for student in students]
        return JsonResponse({'students': student_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)




@login_required
def get_instructors(request, class_id):
    try:
        instructors = Instructor.objects.filter(classes__id=class_id).select_related('user')
        instructor_data = [{
            'id': instructor.id,
            'username': instructor.user.username,
            'email': instructor.user.email,
            'specialization': instructor.specialization
        } for instructor in instructors]
        return JsonResponse({'instructors': instructor_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)




@login_required
def student_notifications(request):
    # student = get_object_or_404(Notification, user=request.user)
    # results = Result.objects.filter(student=student)
    student = get_object_or_404(Student, user=request.user.username)
    notifications = Notification.objects.filter(students=student)
    all_notifications = Notification.objects.filter(create_for='all')

    context = {
        'notifications': notifications,
        'all_notifications': all_notifications,
    }
    return render(request, 'lms/student/dashboard.html', context)
    
    # student=request.user
    
    # notifications = Notification.objects.all()
    # context = {
    #     'notifications': notifications
    # }
    # return render(request, 'dashboard/student_notifications.html', context)



@login_required
def view_notifications(request):
    student_id = request.GET.get('student_id')
    instructor_id = request.GET.get('instructor_id')
    
    notifications = Notification.objects.all()
    
    # if student_id:
    #     notifications = notifications.filter(student_id=student_id)
    # if instructor_id:
    #     notifications = notifications.filter(instructor_id=instructor_id)

    paginator = Paginator(notifications, 20)  # Show 10 instructors per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    students = Student.objects.all()
    instructors = Instructor.objects.all()
    

    
    context = {
        'page_obj': page_obj,
        'notifications': notifications,
        'students': students,
        'instructors': instructors,
        'selected_student_id': student_id,
        'selected_instructor_id': instructor_id,
        'user_role': 'admin' if request.user.is_superuser else 'instructor'
    }
    return render(request, 'lms/view/view_notifications.html', context)

@login_required
@user_passes_test(is_admin)
def create_quiz(request):
    if request.method == 'POST':
        quiz_form = QuizForm(request.POST)
        if quiz_form.is_valid():
            quiz = quiz_form.save(commit=False)
            quiz.created_by = request.user
            quiz.save()
            messages.success(request, 'Quiz details saved. Now add questions.')
            return redirect('create_quiz_questions', quiz_id=quiz.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        quiz_form = QuizForm()
    
    return render(request, 'lms/create/create_quiz.html', {
        'quiz_form': quiz_form,
        'step': 1
    })

@login_required
@user_passes_test(is_admin)
def create_quiz_questions(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    total_questions = Question.objects.filter(quiz=quiz).count()
    remaining_questions = quiz.total_questions - total_questions
    
    if remaining_questions <= 0:
        messages.info(request, 'All questions have been added for this quiz.')
        return redirect('view_quiz', quiz_id=quiz.id)
    
    if request.method == 'POST':
        question_form = QuestionForm(request.POST)
        if question_form.is_valid():
            question = question_form.save(commit=False)
            question.quiz = quiz
            question.save()
            
            # Update remaining questions count
            total_questions = Question.objects.filter(quiz=quiz).count()
            remaining_questions = quiz.total_questions - total_questions
            
            if remaining_questions > 0:
                messages.success(request, f'Question added successfully! {remaining_questions} questions remaining.')
                # Redirect to the same page with a fresh form
                return redirect('create_quiz_questions', quiz_id=quiz.id)
            else:
                messages.success(request, 'All questions have been added successfully!')
                return redirect('view_quiz', quiz_id=quiz.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        question_form = QuestionForm()
    
    return render(request, 'lms/create/create_quiz.html', {
        'question_form': question_form,
        'quiz': quiz,
        'remaining_questions': remaining_questions,
        'step': 2
    })

@login_required
# @user_passes_test(is_admin)
def view_quizzes(request):
    quiz_list = Quiz.objects.all().order_by('-created_at')
    paginator = Paginator(quiz_list, 10)  # Show 10 quizzes per page
    page = request.GET.get('page')
    
    try:
        quizzes = paginator.page(page)
    except PageNotAnInteger:
        quizzes = paginator.page(1)
    except EmptyPage:
        quizzes = paginator.page(paginator.num_pages)
    
    return render(request, 'lms/view/view_quizzes.html', {'quizzes': quizzes})

@login_required
# @user_passes_test(is_admin)
def view_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = Question.objects.filter(quiz=quiz)
    return render(request, 'lms/view/view_quiz.html', {
        'quiz': quiz,
        'questions': questions
    })

@login_required
@user_passes_test(is_admin)
def edit_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    if request.method == 'POST':
        form = QuizForm(request.POST, instance=quiz)
        if form.is_valid():
            form.save()
            messages.success(request, 'Quiz updated successfully!')
            return redirect('view_quizzes')
    else:
        form = QuizForm(instance=quiz)
    return render(request, 'lms/edit/edit_quiz.html', {'form': form, 'quiz': quiz})

@login_required
# @user_passes_test(is_admin)
def delete_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    quiz.delete()
    messages.success(request, 'Quiz deleted successfully!')
    return redirect('view_quizzes')




@login_required
def student_quizzes(request):
    if not request.user.role or request.user.role.role_name.lower() != 'student':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')
    
    try:
        student = Student.objects.get(user=request.user)
        
        # Get student's classes and subjects
        classes = student.classes.all()
        subjects = student.subjects.all()
        
        # Get quizzes for the student's classes and subjects
        student_quizzes = Quiz.objects.filter(
            exam__class_id__in=classes,
            exam__subject__in=subjects
        ).order_by('-created_at')
        
        context = {
            'student': student,
            'student_quizzes': student_quizzes,
        }
        return render(request, 'lms/student/quizzes.html', context)
    except Student.DoesNotExist:
        messages.error(request, 'Student profile not found.')
        return redirect('login')

@login_required
def student_quiz_detail(request, quiz_id):
    if not request.user.role or request.user.role.role_name.lower() != 'student':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')
    
    try:
        student = Student.objects.get(user=request.user)
        quiz = get_object_or_404(Quiz, id=quiz_id)
        
        # Check if student has access to this quiz
        if not (student.classes.filter(id=quiz.exam.class_id.id).exists() and 
                student.subjects.filter(id=quiz.exam.subject.id).exists()):
            messages.error(request, 'You do not have access to this quiz.')
            return redirect('student_dashboard')
        
        questions = Question.objects.filter(quiz=quiz)
        
        context = {
            'student': student,
            'quiz': quiz,
            'questions': questions,
        }
        return render(request, 'lms/student/quiz_detail.html', context)
    except Student.DoesNotExist:
        messages.error(request, 'Student profile not found.')
        return redirect('login')

@login_required
def take_quiz(request, quiz_id):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        # Create a temporary student record for the user if they don't have one
        student = Student.objects.create(user=request.user)
    
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    # Check if quiz has already been attempted
    if QuizAttempt.objects.filter(student=student, quiz=quiz).exists():
        messages.error(request, 'You have already attempted this quiz.')
        return redirect('quiz_result', quiz_id=quiz_id)
    
    if request.method == 'POST':
        # Create quiz attempt
        quiz_attempt = QuizAttempt.objects.create(
            student=student,
            quiz=quiz,
            started_at=request.POST.get('started_at'),
            completed_at=timezone.now()
        )
        
        score = 0
        questions = quiz.questions.all()
        
        # Process each question's answer
        for question in questions:
            selected_option = request.POST.get(f'question_{question.id}')
            is_correct = selected_option == question.correct_answer
            if is_correct:
                score += 1
            
            # Create question attempt
            QuestionAttempt.objects.create(
                quiz_attempt=quiz_attempt,
                question=question,
                selected_option=selected_option,
                is_correct=is_correct
            )
        
        # Update quiz attempt with final score
        quiz_attempt.score = score
        quiz_attempt.save()
        
        messages.success(request, 'Quiz submitted successfully!')
        return redirect('quiz_result', quiz_id=quiz_id)
    
    questions = quiz.questions.all()
    context = {
        'student': student,
        'quiz': quiz,
        'questions': questions,
    }
    return render(request, 'lms/student/take_quiz.html', context)

@login_required
def quiz_result(request, quiz_id):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        # Create a temporary student record for the user if they don't have one
        student = Student.objects.create(user=request.user)
    
    quiz = get_object_or_404(Quiz, id=quiz_id)
    quiz_attempt = get_object_or_404(QuizAttempt, student=student, quiz=quiz)
    
    context = {
        'student': student,
        'quiz_attempt': quiz_attempt,
    }
    return render(request, 'lms/student/quiz_result.html', context)

@login_required
def update_exam(request, exam_id):
    if not request.user.role or request.user.role.role_name.lower() != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')
    
    exam = get_object_or_404(Exam, id=exam_id)
    if request.method == 'POST':
        form = ExamForm(request.POST, instance=exam)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.updated_by = request.user
            exam.save()
            messages.success(request, 'Exam updated successfully.')
            return redirect('view_exams')
    else:
        form = ExamForm(instance=exam)
    
    return render(request, 'lms/edit/edit_exam.html', {
        'form': form,
        'exam': exam
    })

@login_required
def delete_exam(request, exam_id):
    if not request.user.role or request.user.role.role_name.lower() != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')
    
    exam = get_object_or_404(Exam, id=exam_id)
    exam.delete()
    messages.success(request, 'Exam deleted successfully.')
    return redirect('view_exams')

@login_required
def delete_notification(request, notification_id):
    if not request.user.role or request.user.role.role_name.lower() != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')
    
    notification = get_object_or_404(Notification, id=notification_id)
    title = notification.title  # Store the title before deletion
    notification.delete()
    messages.success(request, f'Notification "{title}" has been deleted successfully.')
    return redirect('view_notifications')

@login_required
def update_notification(request, notification_id):
    if not request.user.role or request.user.role.role_name.lower() != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')
    
    notification = get_object_or_404(Notification, id=notification_id)
    
    if request.method == 'POST':
        create_for = request.POST.get('create_for')
        title = request.POST.get('title')
        description = request.POST.get('description')
        student_ids = request.POST.getlist('students')
        instructor_ids = request.POST.getlist('instructors')
        
        # Update basic fields
        notification.create_for = create_for
        notification.title = title
        notification.description = description
        notification.save()
        
        # Update recipients
        notification.students.clear()
        notification.instructors.clear()
        
        if create_for == 'student':
            if 'all' in student_ids:
                notification.students.set(Student.objects.all())
            else:
                notification.students.set(Student.objects.filter(id__in=student_ids))
        elif create_for == 'instructor':
            if 'all' in instructor_ids:
                notification.instructors.set(Instructor.objects.all())
            else:
                notification.instructors.set(Instructor.objects.filter(id__in=instructor_ids))
        else:  # all
            notification.students.set(Student.objects.all())
            notification.instructors.set(Instructor.objects.all())
        
        messages.success(request, f'Notification "{title}" has been updated successfully.')
        return redirect('view_notifications')
    
    context = {
        'notification': notification,
        'students': Student.objects.all(),
        'instructors': Instructor.objects.all(),
    }
    return render(request, 'lms/edit/edit_notification.html', context)

@login_required
def mark_notification_as_seen(request, notification_id):
    try:
        if request.user.role.role_name.lower() == 'student':
            notification = Notification.objects.get(id=notification_id, students__user=request.user)
        elif request.user.role.role_name.lower() == 'instructor':
            notification = Notification.objects.get(id=notification_id, instructors__user=request.user)
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid user role'})
        
        notification.is_seen = True
        notification.save()
        return JsonResponse({'status': 'success'})
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Notification not found'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def mark_notifications_as_seen(request):
    if request.method == 'POST':
        try:
            if request.user.role.role_name.lower() == 'student':
                student = Student.objects.get(user=request.user)
                # Update notifications for this student
                Notification.objects.filter(
                    Q(students=student) | Q(create_for='all')
                ).update(is_seen=True)
                
                # Clear session notifications
                if 'new_notifications' in request.session:
                    del request.session['new_notifications']
                    request.session.modified = True
                
                return JsonResponse({'status': 'success'})
            
            elif request.user.role.role_name.lower() == 'instructor':
                instructor = Instructor.objects.get(user=request.user)
                # Update notifications for this instructor
                Notification.objects.filter(
                    Q(instructors=instructor) | Q(create_for='all')
                ).update(is_seen=True)
                
                # Clear session notifications
                if 'new_notifications' in request.session:
                    del request.session['new_notifications']
                    request.session.modified = True
                
                return JsonResponse({'status': 'success'})
            
            return JsonResponse({'status': 'error', 'message': 'Invalid user role'})
            
        except (Student.DoesNotExist, Instructor.DoesNotExist) as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})




@login_required
def create_timetable(request):
    if request.method == 'POST':
        try:
            class_id = request.POST.get('class_id')
            if not class_id:
                messages.error(request, 'Please select a class.')
                return redirect('create_timetable')

            # Get all subjects for this class
            subjects = Subject.objects.filter(class_id=class_id)
            
            # Get selected days from the form
            selected_days = request.POST.getlist('days[]')
            if not selected_days:
                messages.error(request, 'Please select at least one day.')
                return redirect('create_timetable')
            
            # Day mapping
            day_mapping = {
                '1': 1,  # Monday
                '2': 2,  # Tuesday
                '3': 3,  # Wednesday
                '4': 4,  # Thursday
                '5': 5,  # Friday
                '6': 6,  # Saturday
                '7': 7   # Sunday
            }
            
            # Check existing timetable entries for this class
            existing_entries = Timetable.objects.filter(class_id_id=class_id)
            existing_days = set()
            for entry in existing_entries:
                existing_days.add(entry.day_of_week)
            
            # Create timetable entries only for days that don't exist
            entries_created = 0
            for day in selected_days:
                day_number = day_mapping[day]
                # Skip if day already exists
                if day_number in existing_days:
                    continue
                
                for subject in subjects:
                    start_time = request.POST.get(f'start_time_{subject.id}')
                    end_time = request.POST.get(f'end_time_{subject.id}')
                    
                    if start_time and end_time:  # Only create entry if times are provided
                        Timetable.objects.create(
                            class_id_id=class_id,
                            subject=subject,
                            day_of_week=day_number,
                            start_time=start_time,
                            end_time=end_time
                        )
                        entries_created += 1
            
            if entries_created > 0:
                messages.success(request, f'Successfully created {entries_created} new timetable entries.')
            else:
                messages.info(request, 'No new timetable entries were created. Selected days already exist.')
            return redirect('view_timetables')
            
        except Exception as e:
            messages.error(request, f'Error creating timetable entries: {str(e)}')
            return redirect('create_timetable')
    
    form = TimetableForm()
    return render(request, 'lms/create/create_timetable.html', {'form': form})

@login_required
def create_daily_override(request):
    if not request.user.role or request.user.role.role_name.lower() != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')
        
    if request.method == 'POST':
        try:
            class_id = request.POST.get('class_id')
            override_date = request.POST.get('override_date')
            subjects_data = request.POST.getlist('subjects[]')

            if not class_id or not override_date or not subjects_data:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Missing required fields'
                })

            # Create daily overrides for each subject
            for subject_data in subjects_data:
                subject_info = json.loads(subject_data)
                DailyOverride.objects.create(
                    class_id_id=class_id,
                    subject_id=subject_info['subject_id'],
                    override_date=override_date,
                    start_time=subject_info['start_time'],
                    end_time=subject_info['end_time']
                )

            return JsonResponse({
                'status': 'success',
                'message': 'Daily overrides created successfully',
                'redirect_url': reverse('view_daily_overrides')
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    classes = Class.objects.all()
    return render(request, 'lms/create/create_daily_override.html', {'classes': classes})



@login_required
def view_timetables(request):
    classes = Class.objects.all()
    return render(request, 'lms/view/view_timetables.html', {'classes': classes})

@login_required
def get_timetable_data(request):
    class_id = request.GET.get('class_id')
    query = Timetable.objects.all()
    
    if class_id:
        query = query.filter(class_id_id=class_id)
    
    timetables = query.select_related('subject', 'class_id').order_by('day_of_week', 'start_time')
    
    # Day mapping for display
    day_mapping = {
        1: 'Monday',
        2: 'Tuesday',
        3: 'Wednesday',
        4: 'Thursday',
        5: 'Friday',
        6: 'Saturday',
        7: 'Sunday'
    }
    
    timetable_data = [{
        'id': entry.id,
        'day_of_week': entry.day_of_week,  # Keep numeric value for sorting
        'day_name': day_mapping[entry.day_of_week],  # Add day name for display
        'subject_name': entry.subject.name,
        'subject_id': entry.subject.id,
        'start_time': entry.start_time.strftime('%H:%M:%S'),
        'end_time': entry.end_time.strftime('%H:%M:%S'),
        'class_name': entry.class_id.name
    } for entry in timetables]
    
    return JsonResponse({'timetables': timetable_data})

@login_required
def view_daily_overrides(request):
    daily_overrides = DailyOverride.objects.all()
    return render(request, 'lms/view/view_daily_overrides.html', {'daily_overrides': daily_overrides})

@login_required
def update_timetable(request, id):
    if not request.user.role or request.user.role.role_name.lower() != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')

    timetable = get_object_or_404(Timetable, id=id)
    
    if request.method == 'POST':
        try:
            start_time = request.POST.get('start_time')
            end_time = request.POST.get('end_time')
            
            if start_time and end_time:
                timetable.start_time = start_time
                timetable.end_time = end_time
                timetable.save()
                messages.success(request, 'Timetable updated successfully.')
                return redirect('view_timetables')
            else:
                messages.error(request, 'Please provide both start and end times.')
        except Exception as e:
            messages.error(request, f'Error updating timetable: {str(e)}')
    
    context = {
        'timetable': timetable,
        'class': timetable.class_id,
        'subject': timetable.subject,
    }
    return render(request, 'lms/update/update_timetable.html', context)

@login_required
def delete_timetable(request, id):
    if not request.user.role or request.user.role.role_name.lower() != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')

    timetable = get_object_or_404(Timetable, id=id)
    try:
        timetable.delete()
        messages.success(request, 'Timetable entry deleted successfully.')
    except Exception as e:
        messages.error(request, f'Error deleting timetable entry: {str(e)}')
    
    return redirect('view_timetables')

@login_required
def update_daily_override(request, id):
    if not request.user.role or request.user.role.role_name.lower() != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')

    daily_override = get_object_or_404(DailyOverride, id=id)
    
    if request.method == 'POST':
        try:
            date = request.POST.get('date')
            start_time = request.POST.get('start_time')
            end_time = request.POST.get('end_time')
            
            if date and start_time and end_time:
                daily_override.date = date
                daily_override.start_time = start_time
                daily_override.end_time = end_time
                daily_override.save()
                messages.success(request, 'Daily override updated successfully.')
                return redirect('view_daily_overrides')
            else:
                messages.error(request, 'Please provide all required fields.')
        except Exception as e:
            messages.error(request, f'Error updating daily override: {str(e)}')
    
    context = {
        'daily_override': daily_override,
        'class': daily_override.class_id,
        'subject': daily_override.subject,
    }
    return render(request, 'lms/update/update_daily_override.html', context)

@login_required
def delete_daily_override(request, id):
    if not request.user.role or request.user.role.role_name.lower() != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')

    daily_override = get_object_or_404(DailyOverride, id=id)
    try:
        daily_override.delete()
        messages.success(request, 'Daily override deleted successfully.')
    except Exception as e:
        messages.error(request, f'Error deleting daily override: {str(e)}')
    
    return redirect('view_daily_overrides')

@login_required
def get_subjects_for_timetable(request):
    class_id = request.GET.get('class_id')
    if not class_id:
        return JsonResponse({'error': 'Class ID is required'}, status=400)
    
    try:
        subjects = Subject.objects.filter(class_id=class_id).values('id', 'name')
        return JsonResponse({'subjects': list(subjects)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    


@login_required
def student_timetable(request):
    student = Student.objects.get(user=request.user)
    class_id = student.classes.first().id  

    # Get current month's date range
    today = datetime.today()
    start_of_month = today.replace(day=1)
    end_of_month = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    # Get all dates in the current month
    date_list = [start_of_month + timedelta(days=i) for i in range((end_of_month - start_of_month).days + 1)]

    # Get timetables and daily overrides
    timetables = Timetable.objects.filter(class_id=class_id).select_related('subject')
    daily_overrides = DailyOverride.objects.filter(
        class_id=class_id, 
        date__range=[start_of_month, end_of_month]
    ).select_related('subject')

    # Organize timetables by day
    timetable_by_day = {}
    for timetable in timetables:
        day = int(timetable.day_of_week)
        if day not in timetable_by_day:
            timetable_by_day[day] = []
        timetable_by_day[day].append({
            'subject': {
                'name': timetable.subject.name,
                'id': timetable.subject.id
            },
            'start_time': timetable.start_time.strftime('%H:%M:%S'),
            'end_time': timetable.end_time.strftime('%H:%M:%S')
        })

    # Organize daily overrides by date - now handling multiple subjects per date
    daily_override_by_date = {}
    for override in daily_overrides:
        date_str = override.date.strftime('%Y-%m-%d')
        if date_str not in daily_override_by_date:
            daily_override_by_date[date_str] = []
        daily_override_by_date[date_str].append({
            'subject': {
                'name': override.subject.name,
                'id': override.subject.id
            },
            'start_time': override.start_time.strftime('%H:%M:%S'),
            'end_time': override.end_time.strftime('%H:%M:%S')
        })

    context = {
        'timetable_by_day': timetable_by_day,
        'daily_override_by_date': daily_override_by_date,
        'date_list': date_list,
        'today': today,
    }
    return render(request, 'lms/student/student_timetable.html', context)




@register.filter
def date_range(start_date, end_date):
    delta = end_date - start_date
    return [start_date + timedelta(days=i) for i in range(delta.days + 1)]

@login_required
def create_single_timetable(request):
    if not request.user.role or request.user.role.role_name.lower() != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('login')

    class_id = request.GET.get('class_id')
    day = request.GET.get('day')
    
    # Get all classes for the form
    classes = Class.objects.all()
    
    # Map day number to name
    day_names = {
        '1': 'Monday',
        '2': 'Tuesday',
        '3': 'Wednesday',
        '4': 'Thursday',
        '5': 'Friday',
        '6': 'Saturday',
        '7': 'Sunday'
    }
    day_name = day_names.get(str(day), '')
    
    try:
        class_obj = None
        subjects = []
        
        if class_id and class_id != 'undefined':
            class_obj = Class.objects.get(id=class_id)
            subjects = Subject.objects.filter(class_id=class_id)
            
            if not subjects.exists():
                messages.warning(request, 'No subjects found for this class. Please add subjects first.')
                return redirect('view_timetables')

        if request.method == 'POST':
            selected_class_id = request.POST.get('class_id')
            subject_id = request.POST.get('subject')
            start_time = request.POST.get('start_time')
            end_time = request.POST.get('end_time')

            if selected_class_id and subject_id and start_time and end_time:
                # Check if entry already exists
                existing_entry = Timetable.objects.filter(
                    class_id_id=selected_class_id,
                    subject_id=subject_id,
                    day_of_week=day
                ).exists()

                if existing_entry:
                    messages.error(request, 'A timetable entry already exists for this subject on this day.')
                else:
                    Timetable.objects.create(
                        class_id_id=selected_class_id,
                        subject_id=subject_id,
                        day_of_week=day,
                        start_time=start_time,
                        end_time=end_time
                    )
                    messages.success(request, 'Timetable entry created successfully.')
                    return redirect('view_timetables')
            else:
                messages.error(request, 'Please fill in all required fields.')

        context = {
            'classes': classes,
            'class_id': class_id if class_id and class_id != 'undefined' else None,
            'class_name': class_obj.name if class_obj else None,
            'day': day,
            'day_name': day_name,
            'subjects': subjects,
        }
        return render(request, 'lms/create/create_single_timetable.html', context)

    except Class.DoesNotExist:
        messages.error(request, 'Class not found.')
        return redirect('view_timetables')
    except Exception as e:
        messages.error(request, f'Error creating timetable entry: {str(e)}')
        return redirect('view_timetables')
    

def gemini_chat_view(request):
    return render(request, "lms/chat/gemini_chat.html")

def gemini_ai_chat(request):
    try:
        # Get user input from the request
        user_input = request.GET.get("query", "")
        
        if not user_input.strip():
            return JsonResponse({
                "error": "Please enter a message"
            }, status=400)

        # Configure the Gemini API
        genai.configure(api_key=settings.GEMINI_API_KEY)
        
        try:
            # Create a Gemini model instance
            model = genai.GenerativeModel('gemini-pro')
            
            # Generate response
            response = model.generate_content(user_input)
            
            # Check if response was blocked
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                return JsonResponse({
                    "error": "Response was blocked due to safety concerns"
                }, status=400)
            
            # Return the response
            return JsonResponse({
                "response": response.text if hasattr(response, 'text') else str(response)
            })
            
        except Exception as api_error:
            # Log the specific API error
            print(f"Gemini API Error Details: {str(api_error)}")
            if settings.DEBUG:
                return JsonResponse({
                    "error": f"API Error: {str(api_error)}"
                }, status=500)
            else:
                return JsonResponse({
                    "error": "Sorry, I encountered an error while processing your request. Please try again."
                }, status=500)
            
    except Exception as e:
        import traceback
        print(f"General Error: {str(e)}")
        print(traceback.format_exc())
        if settings.DEBUG:
            return JsonResponse({
                "error": f"Error: {str(e)}"
            }, status=500)
        else:
            return JsonResponse({
                "error": "Sorry, I encountered an error while processing your request. Please try again."
            }, status=500)
