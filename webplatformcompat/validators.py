from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.utils.six import string_types


class LanguageDictValidator(object):
    '''Check for valid language dictionary'''

    def __init__(self, allow_canonical=False):
        self.allow_canonical = allow_canonical

    def __call__(self, value):
        if not isinstance(value, dict):
            raise ValidationError(
                _("Value must be a JSON dictionary of language codes to"
                  " strings."))
        if 'zxx' in value:
            if self.allow_canonical and list(value.keys()) != ['zxx']:
                raise ValidationError(
                    _("Language code 'zxx' not allowed with other values."))
            elif not self.allow_canonical:
                raise ValidationError(_("Language code 'zxx' not allowed"))
        elif 'en' not in value:
            raise ValidationError(_("Missing required language code 'en'."))
        for language_code, text in value.items():
            if not isinstance(text, string_types):
                raise ValidationError(
                    _('For language "%(lang)s, text "%(text)s" is not a'
                      ' string.'),
                    params={'lang': language_code, 'text': text})
