from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import *
from django.utils.translation import gettext_lazy as _
from datetime import date



class ClassForm(forms.ModelForm):
    class Meta:
        model = Class
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'custom-input'})
        }
        labels = {
            'name': 'Class Name'
        }

class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'class_id']
        widgets = {
            'class_id': forms.Select(choices=[(cls.id, cls.name) for cls in Class.objects.all()])
        }

class StudentForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'custom-input'}),
        required=True
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'custom-input'}),
        required=True
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'custom-input'}),
        required=True
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'custom-input'}),
        required=True
    )
    subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.all().select_related('class_id'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'custom-checkbox'}),
        required=True
    )
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords don't match")
        
        try:
            validate_password(password)
        except ValidationError as e:
            self.add_error('password', e)
            
        # Check if username already exists
        username = cleaned_data.get('username')
        if CustomUser.objects.filter(username=username).exists():
            raise ValidationError({'username': 'Username already exists'})
            
        # Check if email already exists
        email = cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError({'email': 'Email already exists'})
            
        return cleaned_data


class InstructorForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'custom-input'}),
        required=True
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'custom-input'}),
        required=True
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'custom-input'}),
        required=True
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'custom-input'}),
        required=True
    )
    specialization = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'custom-input'}),
        required=False
    )
    subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.all().select_related('class_id'),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'custom-checkbox'}),
        required=True
    )
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords don't match")
        
        try:
            validate_password(password)
        except ValidationError as e:
            self.add_error('password', e)
            
        # Check if username already exists
        username = cleaned_data.get('username')
        if CustomUser.objects.filter(username=username).exists():
            raise ValidationError({'username': 'Username already exists'})
            
        # Check if email already exists
        email = cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError({'email': 'Email already exists'})
            
        return cleaned_data

class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ['title', 'class_id', 'subject', 'exam_date', 'total_marks', 'passing_marks']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'custom-input'}),
            'class_id': forms.Select(attrs={'class': 'custom-select', 'id': 'id_class'}),
            'subject': forms.Select(attrs={'class': 'custom-select'}),
            'exam_date': forms.DateInput(attrs={'class': 'custom-input', 'type': 'date'}),
            'total_marks': forms.NumberInput(attrs={'class': 'custom-input', 'min': '1'}),
            'passing_marks': forms.NumberInput(attrs={'class': 'custom-input', 'min': '1'}),
        }
        labels = {
            'title': _('Exam Title'),
            'class_id': _('Class'),
            'subject': _('Subject'),
            'exam_date': _('Exam Date'),
            'total_marks': _('Total Marks'),
            'passing_marks': _('Passing Marks'),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initially, set subject queryset to empty
        self.fields['subject'].queryset = Subject.objects.none()
        
        # If class_id is provided, filter subjects by that class
        if 'class_id' in self.data:
            try:
                class_id = int(self.data.get('class_id'))
                self.fields['subject'].queryset = Subject.objects.filter(class_id=class_id)
            except (ValueError, TypeError):
                pass
        # If instance is provided (for editing), set subject queryset based on instance's class
        elif self.instance.pk:
            self.fields['subject'].queryset = Subject.objects.filter(class_id=self.instance.class_id)
    
    def clean(self):
        cleaned_data = super().clean()
        total_marks = cleaned_data.get('total_marks')
        passing_marks = cleaned_data.get('passing_marks')
        
        if total_marks and passing_marks and passing_marks > total_marks:
            raise forms.ValidationError(_('Passing marks cannot be greater than total marks.'))
        
        return cleaned_data
    


class NotificationForm(forms.ModelForm):
    create_for = forms.ChoiceField(choices=Notification.CREATE_FOR_CHOICES, required=True)
    class_id = forms.ModelChoiceField(queryset=Class.objects.all(), required=False, label='Class', empty_label="All", widget=forms.CheckboxSelectMultiple)
    students = forms.ModelMultipleChoiceField(queryset=Student.objects.none(), required=False, widget=forms.CheckboxSelectMultiple)
    instructors = forms.ModelMultipleChoiceField(queryset=Instructor.objects.none(), required=False, widget=forms.CheckboxSelectMultiple)

    image = forms.ImageField(required=False)

    class Meta:
        model = Notification
        fields = ['create_for', 'title', 'description', 'class_id', 'students', 'instructors', 'image']

    def __init__(self, *args, **kwargs):
        super(NotificationForm, self).__init__(*args, **kwargs)
        self.fields['class_id'].queryset = Class.objects.all()
        self.fields['students'].queryset = Student.objects.none()
        self.fields['instructors'].queryset = Instructor.objects.none()

        if 'create_for' in self.data:
            create_for = self.data.get('create_for')
            if create_for == Notification.STUDENT:
                if 'class_id' in self.data:
                    try:
                        class_id = int(self.data.get('class_id'))
                        if class_id:
                            self.fields['students'].queryset = Student.objects.filter(class_id=class_id)
                        else:
                            self.fields['students'].queryset = Student.objects.all()
                    except (ValueError, TypeError):
                        pass  # invalid input from the client; ignore and fallback to empty queryset
            elif create_for == Notification.INSTRUCTOR:
                if 'class_id' in self.data:
                    try:
                        class_id = int(self.data.get('class_id'))
                        if class_id:
                            self.fields['instructors'].queryset = Instructor.objects.filter(classes__id=class_id)
                        else:
                            self.fields['instructors'].queryset = Instructor.objects.all()
                    except (ValueError, TypeError):
                        pass  # invalid input from the client; ignore and fallback to empty queryset
        elif self.instance.pk:
            if self.instance.create_for == Notification.STUDENT:
                self.fields['students'].queryset = self.instance.students.all()
            elif self.instance.create_for == Notification.INSTRUCTOR:
                self.fields['instructors'].queryset = self.instance.instructors.all()

class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ['exam', 'title', 'total_questions']
        widgets = {
            'exam': forms.Select(attrs={'class': 'custom-select'}),
            'title': forms.TextInput(attrs={'class': 'custom-input'}),
            'total_questions': forms.NumberInput(attrs={'class': 'custom-input', 'min': '1'}),
        }
        labels = {
            'exam': _('Select Exam'),
            'title': _('Quiz Title'),
            'total_questions': _('Number of Questions'),
        }

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['question_text', 'option1', 'option2', 'option3', 'option4', 'correct_answer']
        widgets = {
            'question_text': forms.Textarea(attrs={'class': 'custom-input', 'rows': 3}),
            'option1': forms.TextInput(attrs={'class': 'custom-input'}),
            'option2': forms.TextInput(attrs={'class': 'custom-input'}),
            'option3': forms.TextInput(attrs={'class': 'custom-input'}),
            'option4': forms.TextInput(attrs={'class': 'custom-input'}),
            'correct_answer': forms.Select(attrs={'class': 'custom-select'}),
        }
        labels = {
            'question_text': _('Question'),
            'option1': _('Option 1'),
            'option2': _('Option 2'),
            'option3': _('Option 3'),
            'option4': _('Option 4'),
            'correct_answer': _('Correct Answer'),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set choices for correct_answer field based on options
        self.fields['correct_answer'].widget.choices = [
            ('option1', 'Option 1'),
            ('option2', 'Option 2'),
            ('option3', 'Option 3'),
            ('option4', 'Option 4'),
        ]


class StudentModelForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'custom-input'}),
        required=True
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'custom-input'}),
        required=True
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'custom-input'}),
        required=True
    )
    
    class Meta:
        model = Student
        fields = ['classes', 'subjects']
        widgets = {
            'classes': forms.SelectMultiple(attrs={'class': 'custom-select'}),
            'subjects': forms.SelectMultiple(attrs={'class': 'custom-select'})
        }
        labels = {
            'classes': 'Classes',
            'subjects': 'Subjects'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Pre-populate user fields if editing an existing student
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
    
    def save(self, commit=True):
        student = super().save(commit=False)
        
        # Update the related user fields
        if student.pk:  # Only if the student already exists
            user = student.user
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.email = self.cleaned_data['email']
            user.save()
        
        if commit:
            student.save()
            self.save_m2m()
        
        return student

class InstructorModelForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'custom-input'}),
        required=True
    )
    last_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'custom-input'}),
        required=True
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'custom-input'}),
        required=True
    )
    
    class Meta:
        model = Instructor
        fields = ['specialization', 'classes', 'subjects']
        widgets = {
            'specialization': forms.TextInput(attrs={'class': 'custom-input'}),
            'classes': forms.SelectMultiple(attrs={'class': 'custom-select'}),
            'subjects': forms.SelectMultiple(attrs={'class': 'custom-select'})
        }
        labels = {
            'specialization': 'Specialization',
            'classes': 'Classes',
            'subjects': 'Subjects'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Pre-populate user fields if editing an existing instructor
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
    
    def save(self, commit=True):
        instructor = super().save(commit=False)
        
        # Update the related user fields
        if instructor.pk:  # Only if the instructor already exists
            user = instructor.user
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.email = self.cleaned_data['email']
            user.save()
        
        if commit:
            instructor.save()
            self.save_m2m()
        
        return instructor

# class UpdateStudentForm(forms.ModelForm):
#     class Meta:
#         model = Student
#         fields = ['email', 'class_id']
#         widgets = {
#             'class_id': forms.Select(),
#         }


class TimetableForm(forms.ModelForm):
    class Meta:
        model = Timetable
        fields = ['class_id', 'subject', 'day_of_week', 'start_time', 'end_time']
        widgets = {
            'class_id': forms.Select(attrs={'class': 'custom-select'}),
            'subject': forms.Select(attrs={'class': 'custom-select'}),
            'day_of_week': forms.Select(attrs={'class': 'custom-select'}),
            'start_time': forms.TimeInput(attrs={'class': 'custom-input', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'custom-input', 'type': 'time'}),
        }

class DailyOverrideForm(forms.ModelForm):
    class Meta:
        model = DailyOverride
        fields = ['class_id', 'subject', 'date', 'start_time', 'end_time']
        widgets = {
            'class_id': forms.Select(attrs={'class': 'custom-select'}),
            'subject': forms.Select(attrs={'class': 'custom-select'}),
            'date': forms.DateInput(attrs={'class': 'custom-input', 'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'class': 'custom-input', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'custom-input', 'type': 'time'}),
        }