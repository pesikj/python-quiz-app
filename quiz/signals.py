import random

from django.db.models.signals import pre_save, post_init
from django.dispatch import receiver
from .models import Option, UserAnswer


@receiver(pre_save, sender=Option)
def question_added(sender, instance: Option, **kwargs):
    if not instance.option_order:
        instance.option_order = random.randint(1, 1000)


@receiver(pre_save, sender=UserAnswer)
def set_attempt_number(sender, instance: UserAnswer, **kwargs):
    instance.attempt_number = (UserAnswer.get_attempt_number_for_user_question(instance.user.pk, instance.question.pk)
                               + 1)
