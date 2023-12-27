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


@register.filter
def is_image(file_path) -> bool:
    return file_path.lower().endswith(("png", "jpg", "jpeg", "gif"))


@register.filter
def filename(file_path) -> bool:
    return file_path.split("/")[-1]
