# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('webplatformcompat', '0014_disallow_blank_versions'),
    ]

    operations = [
        migrations.AlterField(
            model_name='changeset',
            name='created',
            field=models.DateTimeField(auto_now_add=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='changeset',
            name='modified',
            field=models.DateTimeField(auto_now=True),
            preserve_default=True,
        ),
    ]
