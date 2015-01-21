# -*- coding: utf-8 -*-
# flake8: noqa
from __future__ import unicode_literals

from django.db import models, migrations
import mdn.models
import django.utils.timezone
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('webplatformcompat', '0004_drop_field_feature_mdn_path'),
    ]

    operations = [
        migrations.CreateModel(
            name='FeaturePage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('url', models.URLField(help_text='URL of the English translation of an MDN page', unique=True, db_index=True, validators=[mdn.models.validate_mdn_url])),
                ('status', models.IntegerField(default=0, help_text='Status of MDN Parsing process', choices=[(0, 'Starting Import'), (1, 'Fetching Metadata'), (2, 'Fetching MDN pages'), (3, 'Parsing MDN pages'), (4, 'Parsing Complete'), (5, 'Scraping Failed')])),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(default=django.utils.timezone.now, help_text='Last modification time', db_index=True, editable=False, blank=True)),
                ('raw_data', models.TextField(help_text='JSON-encoded parsed content')),
                ('has_issues', models.BooleanField(default=False, help_text='Issues found when parsing the page')),
                ('feature', models.ForeignKey(to='webplatformcompat.Feature', help_text='Feature in API', unique=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PageMeta',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('path', models.CharField(help_text='Path of MDN page', max_length=255)),
                ('crawled', django_extensions.db.fields.ModificationDateTimeField(default=django.utils.timezone.now, help_text='Time when the content was retrieved', editable=False, blank=True)),
                ('raw', models.TextField(help_text='Raw content of the page')),
                ('status', models.IntegerField(default=0, help_text='Status of MDN fetching process', choices=[(0, 'Starting Fetch'), (1, 'Fetching Page'), (2, 'Fetched Page'), (3, 'Error Fetching Page')])),
                ('page', models.ForeignKey(to='mdn.FeaturePage')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TranslatedContent',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('path', models.CharField(help_text='Path of MDN page', max_length=255)),
                ('crawled', django_extensions.db.fields.ModificationDateTimeField(default=django.utils.timezone.now, help_text='Time when the content was retrieved', editable=False, blank=True)),
                ('raw', models.TextField(help_text='Raw content of the page')),
                ('status', models.IntegerField(default=0, help_text='Status of MDN fetching process', choices=[(0, 'Starting Fetch'), (1, 'Fetching Page'), (2, 'Fetched Page'), (3, 'Error Fetching Page')])),
                ('locale', models.CharField(help_text='Locale for page translation', max_length=5, db_index=True)),
                ('page', models.ForeignKey(to='mdn.FeaturePage')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
    ]
