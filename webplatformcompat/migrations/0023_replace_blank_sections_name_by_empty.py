# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def blank_to_empty(apps, schema_editor):
    Section = apps.get_model('webplatformcompat', 'section')
    for section in Section.objects.filter(name__regex='^\s*$'):
        section.name = None
        section.save()


class Migration(migrations.Migration):

    dependencies = [
        ('webplatformcompat', '0022_sections_name_allow_blank'),
    ]

    operations = [
        migrations.RunPython(blank_to_empty),
    ]
