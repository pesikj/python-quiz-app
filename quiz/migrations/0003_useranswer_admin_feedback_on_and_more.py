# Generated by Django 5.0 on 2023-12-25 14:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0002_useranswer_admin_feedback_useranswer_ai_feedback_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='useranswer',
            name='admin_feedback_on',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='useranswer',
            name='ai_feedback_on',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]