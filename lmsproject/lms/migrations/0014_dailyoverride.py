# Generated by Django 5.1.7 on 2025-03-12 03:45

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lms', '0013_timetable'),
    ]

    operations = [
        migrations.CreateModel(
            name='DailyOverride',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('class_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='daily_overrides', to='lms.class')),
                ('subject', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='lms.subject')),
            ],
        ),
    ]
