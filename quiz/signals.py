import random

from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Option


@receiver(pre_save, sender=Option)
def question_added(sender, instance: Option, **kwargs):
    if not instance.option_order:
        instance.option_order = random.randint(1, 1000)
