# -*- coding: utf-8 -*-
# flake8: noqa

from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mdn', '0003_add_issues_table'),
    ]

    operations = [
        migrations.AddField(
            model_name='translatedcontent',
            name='title',
            field=models.TextField(help_text='Page title in locale', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='featurepage',
            name='status',
            field=models.IntegerField(default=0, help_text='Status of MDN Parsing process', choices=[(0, 'Starting Import'), (1, 'Fetching Metadata'), (2, 'Fetching MDN pages'), (3, 'Parsing MDN pages'), (4, 'Parsing Complete'), (5, 'Scraping Failed'), (6, 'No Compat Data')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='issue',
            name='slug',
            field=models.SlugField(help_text='Human-friendly slug for issue.', choices=[('false_start', 'false_start'), ('bad_json', 'bad_json'), ('feature_header', 'feature_header'), ('section_missed', 'section_missed'), ('halt_import', 'halt_import'), ('failed_download', 'failed_download'), ('unexpected_attribute', 'unexpected_attribute'), ('unknown_spec', 'unknown_spec'), ('spec_h2_id', 'spec_h2_id'), ('spec2_arg_count', 'spec2_arg_count'), ('spec_h2_name', 'spec_h2_name'), ('inline_text', 'inline_text'), ('footnote_multiple', 'footnote_multiple'), ('footnote_missing', 'footnote_missing'), ('footnote_feature', 'footnote_feature'), ('unknown_browser', 'unknown_browser'), ('doc_parse_error', 'doc_parse_error'), ('extra_cell', 'extra_cell'), ('unknown_version', 'unknown_version'), ('spec2_wrong_kumascript', 'spec2_wrong_kumascript'), ('spec_mismatch', 'spec_mismatch'), ('footnote_unused', 'footnote_unused'), ('specname_blank_key', 'specname_blank_key'), ('exception', 'exception'), ('section_skipped', 'section_skipped'), ('compatgeckodesktop_unknown', 'compatgeckodesktop_unknown'), ('compatgeckofxos_unknown', 'compatgeckofxos_unknown'), ('footnote_no_id', 'footnote_no_id'), ('nested_p', 'nested_p'), ('unknown_kumascript', 'unknown_kumascript'), ('compatgeckofxos_override', 'compatgeckofxos_override')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='pagemeta',
            name='path',
            field=models.CharField(help_text='Path of MDN page', max_length=1024),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='translatedcontent',
            name='path',
            field=models.CharField(help_text='Path of MDN page', max_length=1024),
            preserve_default=True,
        ),
    ]
