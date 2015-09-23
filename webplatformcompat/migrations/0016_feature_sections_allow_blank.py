# -*- coding: utf-8 -*-
# flake8: noqa
from __future__ import unicode_literals

from django.db import models, migrations
import sortedm2m.fields


class Migration(migrations.Migration):

    dependencies = [
        ('webplatformcompat', '0015_switch_created_modified_to_datetimefield'),
    ]

    operations = [
        migrations.AlterField(
            model_name='feature',
            name='sections',
            field=sortedm2m.fields.SortedManyToManyField(help_text=None, related_name='features', to='webplatformcompat.Section', blank=True),
            preserve_default=True,
        ),
    ]
