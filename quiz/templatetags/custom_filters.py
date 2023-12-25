import random

from django import template
from django.db.models import QuerySet

from quiz.models import Option

register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def shuffle_options(queryset: QuerySet[Option]) -> QuerySet[Option]:
    return queryset.order_by("option_order")

