# -*- coding: utf-8 -*-
# flake8: noqa
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mdn', '0007_expand_status_choices'),
    ]

    operations = [
        migrations.AlterField(
            model_name='featurepage',
            name='modified',
            field=models.DateTimeField(help_text='Last modification time', auto_now=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='pagemeta',
            name='crawled',
            field=models.DateTimeField(help_text='Time when the content was retrieved', auto_now=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='translatedcontent',
            name='crawled',
            field=models.DateTimeField(help_text='Time when the content was retrieved', auto_now=True),
            preserve_default=True,
        ),
    ]
