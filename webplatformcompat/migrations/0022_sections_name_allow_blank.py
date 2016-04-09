# -*- coding: utf-8 -*-
#flake8: noqa
from __future__ import unicode_literals

from django.db import migrations, models
import webplatformcompat.validators
import webplatformcompat.fields


class Migration(migrations.Migration):

    dependencies = [
        ('webplatformcompat', '0021_drop_feature_section_m2m'),
    ]

    operations = [
        migrations.AlterField(
            model_name='section',
            name='name',
            field=webplatformcompat.fields
            .TranslatedField(help_text='Name of section, without section number'
                             , validators=[webplatformcompat.validators
                                           .LanguageDictValidator(False)],
                             blank=True),
        ),
    ]

