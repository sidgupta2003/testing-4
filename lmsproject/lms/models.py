from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _




class Role(models.Model):
    role_name = models.CharField(max_length=50)

    def __str__(self):
        return self.role_name

    class Meta:
        db_table = 'lms_role'
        verbose_name = _('role')
        verbose_name_plural = _('roles')



class CustomUser(AbstractUser):
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('role'),
        related_name='users'
    )

    def __str__(self):
        return self.username

    class Meta:
        db_table = 'lms_customuser'
        verbose_name = _('user')
        verbose_name_plural = _('users')
        swappable = 'AUTH_USER_MODEL'



class Class(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name
# Create your models here.

class Subject(models.Model):
    name = models.CharField(max_length=255)
    class_id = models.ForeignKey(Class, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Student(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    classes = models.ManyToManyField(Class, related_name='students')
    subjects = models.ManyToManyField(Subject, related_name='students')
    
    def __str__(self):
        return self.user.username


class Instructor(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    classes = models.ManyToManyField(Class, related_name='instructors')
    subjects = models.ManyToManyField(Subject, related_name='instructors')
    specialization = models.CharField(max_length=255, blank=True, null=True)
    
    def __str__(self):
        return self.user.username

class Exam(models.Model):
    title = models.CharField(max_length=255)
    class_id = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='exams')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='exams')
    exam_date = models.DateField()
    total_marks = models.PositiveIntegerField()
    passing_marks = models.PositiveIntegerField()
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_exams')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.subject.name} ({self.class_id.name})"
    
    class Meta:
        ordering = ['-exam_date']
        verbose_name = _('exam')
        verbose_name_plural = _('exams')


class Notification(models.Model):
    ALL = 'all'
    INSTRUCTOR = 'instructor'
    STUDENT = 'student'
    CREATE_FOR_CHOICES = [
        (ALL, 'All'),
        (INSTRUCTOR, 'Instructor'),
        (STUDENT, 'Student'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    create_for = models.CharField(max_length=20, choices=CREATE_FOR_CHOICES)
    students = models.ManyToManyField('Student', blank=True)
    instructors = models.ManyToManyField('Instructor', blank=True)
    image = models.ImageField(upload_to='notifications/images/', blank=True, null=True)
    is_seen = models.BooleanField(default=False)

    def __str__(self):
        return self.title

class Quiz(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='quizzes')
    title = models.CharField(max_length=255)
    total_questions = models.PositiveIntegerField()
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.exam.title}"

    class Meta:
        verbose_name = _('quiz')
        verbose_name_plural = _('quizzes')

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    option1 = models.CharField(max_length=255)
    option2 = models.CharField(max_length=255)
    option3 = models.CharField(max_length=255)
    option4 = models.CharField(max_length=255)
    correct_answer = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Question {self.id} - {self.quiz.title}"

class QuizAttempt(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.student.user.username} - {self.quiz.title}"

class QuestionAttempt(models.Model):
    quiz_attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='question_attempts')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.CharField(max_length=1)  # A, B, C, or D
    is_correct = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.quiz_attempt.student.user.username} - {self.question.text[:30]}"



class Timetable(models.Model):
    class_id = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='timetables')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    day_of_week = models.IntegerField(choices=[
        (1, 'Monday'),
        (2, 'Tuesday'),
        (3, 'Wednesday'),
        (4, 'Thursday'),
        (5, 'Friday'),
        (6, 'Saturday'),
        (7, 'Sunday'),
    ])
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        day_names = {1: 'Monday', 2: 'Tuesday', 3: 'Wednesday', 4: 'Thursday', 5: 'Friday', 6: 'Saturday', 7: 'Sunday'}
        return f"{self.class_id.name} - {self.subject.name} ({day_names[self.day_of_week]})"
    


class DailyOverride(models.Model):
    class_id = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='daily_overrides')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    def __str__(self):
        return f"{self.class_id.name} - {self.subject.name} ({self.date})"