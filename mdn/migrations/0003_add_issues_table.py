# -*- coding: utf-8 -*-
# flake8: noqa
from __future__ import unicode_literals

from django.db import models, migrations
import django_extensions.db.fields.json


class Migration(migrations.Migration):

    dependencies = [
        ('mdn', '0002_data_add_group'),
    ]

    operations = [
        migrations.CreateModel(
            name='Issue',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('slug', models.SlugField(help_text='Human-friendly slug for issue.', choices=[('false_start', 'false_start'), ('bad_json', 'bad_json'), ('halt_import', 'halt_import'), ('section_missed', 'section_missed'), ('spec_hERROR_id', 'spec_hERROR_id'), ('failed_download', 'failed_download'), ('unknown_kumascript', 'unknown_kumascript'), ('unknown_spec', 'unknown_spec'), ('spec_hERROR_name', 'spec_hERROR_name'), ('inline_text', 'inline_text'), ('footnote_multiple', 'footnote_multiple'), ('footnote_missing', 'footnote_missing'), ('footnote_feature', 'footnote_feature'), ('unknown_browser', 'unknown_browser'), ('extra_cell', 'extra_cell'), ('unknown_version', 'unknown_version'), ('spec_mismatch', 'spec_mismatch'), ('footnote_unused', 'footnote_unused'), ('exception', 'exception'), ('section_skipped', 'section_skipped'), ('compatgeckodesktop_unknown', 'compatgeckodesktop_unknown'), ('compatgeckofxos_unknown', 'compatgeckofxos_unknown'), ('footnote_no_id', 'footnote_no_id'), ('nested_p', 'nested_p'), ('compatgeckofxos_override', 'compatgeckofxos_override')])),
                ('start', models.IntegerField(help_text='Start position in source text')),
                ('end', models.IntegerField(help_text='End position in source text')),
                ('params', django_extensions.db.fields.json.JSONField(help_text='Parameters for description templates')),
                ('content', models.ForeignKey(blank=True, to='mdn.TranslatedContent', help_text='Content the issue was found on', null=True)),
                ('page', models.ForeignKey(related_name='issues', to='mdn.FeaturePage')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.RemoveField(
            model_name='featurepage',
            name='has_issues',
        ),
    ]
