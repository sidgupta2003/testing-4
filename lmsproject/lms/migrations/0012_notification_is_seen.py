# Generated by Django 5.1.7 on 2025-03-11 12:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lms', '0011_quizattempt_questionattempt'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='is_seen',
            field=models.BooleanField(default=False),
        ),
    ]
