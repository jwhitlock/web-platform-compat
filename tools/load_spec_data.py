#!/usr/bin/env python
import re

from common import Tool
from resources import Collection, Maturity, Specification


class LoadSpecData(Tool):
    """Initialize API with specification data from MDN."""
    logger_name = 'tools.load_spec_data'
    parser_options = ['api', 'user', 'password']

    def run(self, *args, **kwargs):
        self.login()
        api_collection = Collection(self.client)
        local_collection = Collection()

        self.logger.info('Reading existing spec data from API')
        api_collection.load_all('maturities')
        api_collection.load_all('specifications')

        self.logger.info('Reading spec data from MDN templates')
        specname = self.specname_template()
        self.parse_specname(specname, api_collection, local_collection)
        spec2 = self.spec2_template()
        self.parse_spec2(spec2, local_collection)

        # Load API sections into local collection
        local_collection.override_ids_to_match(api_collection)
        local_specs = local_collection.get_resources('specifications')
        for local_spec in local_specs:
            api_spec = api_collection.get('specifications', local_spec.id.id)
            if api_spec:
                local_spec.sections = api_spec.sections.ids
        return self.sync_changes(api_collection, local_collection)

    def specname_template(self):
        return self.cached_download(
            'SpecName.txt',
            'https://developer.mozilla.org/en-US/docs/Template:SpecName?raw')

    def spec2_template(self):
        return self.cached_download(
            'Spec2.txt',
            'https://developer.mozilla.org/en-US/docs/Template:Spec2?raw')

    def parse_specname(self, specname, api_collection, local_collection):
        phase = 0
        mdn_key = None
        name = None
        url = None
        slugs = set([
            s.slug for s in api_collection.get_resources('specifications')])
        mdn_key_re = re.compile(r"\s+['\"](.*)['\"]\s*:\s*{")
        name_re = re.compile(r"\s+name\s*:\s*['\"](.*)['\"],?\s*$")
        url_re = re.compile(r"\s+url\s*:\s*['\"](.*)['\"],?\s*$")
        api_specs = api_collection.get_resources_by_data_id('specifications')

        for line in specname.split('\n'):
            if phase == 0:
                # Looking for start of specList
                if line.startswith('var specList = {'):
                    phase = 1
            elif phase == 1:
                # Inside specList
                if line.startswith('}'):
                    phase = 2
                elif mdn_key_re.match(line):
                    assert mdn_key is None
                    mdn_key = mdn_key_re.match(line).group(1).strip()
                elif name_re.match(line):
                    assert name is None
                    name = name_re.match(line).group(1).strip()
                elif url_re.match(line):
                    assert url is None
                    url = url_re.match(line).group(1).strip()
                elif line.startswith('    }'):
                    assert mdn_key is not None
                    assert name is not None
                    assert url is not None
                    if url.startswith('http'):
                        api_spec = api_specs.get(('specifications', mdn_key))
                        if api_spec:
                            slug = api_spec.slug
                        else:
                            slug = self.unique_slugify(mdn_key, slugs)
                        spec = Specification(
                            id="_" + slug, slug=slug, mdn_key=mdn_key,
                            name={u'en': name}, uri={u'en': url}, sections=[])
                        local_collection.add(spec)
                    else:
                        self.logger.warning(
                            'Discarding specification "%s" with url "%s"',
                            mdn_key, url)
                    mdn_key = None
                    name = None
                    url = None
                else:
                    raise Exception('Unparsed line:', line)
            elif phase == 2:
                # Not processing rest of SpecName, including dupe lines
                pass
        assert phase == 2, "SpecName didn't match expected format"

    def parse_spec2(self, spec2, collection):
        phase = 0
        key = None
        name = None
        status_re = re.compile(r"\s+['\"](.*)['\"]\s+: ['\"](.*)['\"],?\s*$")
        mat_re = re.compile(r"\s+['\"](.*)['\"]\s*:\s*mdn\.localString\({\s*$")
        name_re = re.compile(r"\s+['\"](.*)['\"]\s*:\s*['\"](.*)['\"],?\s*$")
        local_specs = collection.get_resources_by_data_id('specifications')

        for line in spec2.split('\n'):
            if phase == 0:
                # Looking for start of status
                if line.startswith('var status = {'):
                    phase = 1
            elif phase == 1:
                # Inside status
                if line.startswith('}'):
                    phase = 2
                elif status_re.match(line):
                    spec_key, maturity_key = status_re.match(line).groups()
                    spec = local_specs.get(('specifications', spec_key))
                    if spec:
                        spec.maturity = maturity_key
                    else:
                        self.logger.warning(
                            'Skipping maturity for unknown spec "%s"',
                            spec_key)
                else:
                    raise Exception('Unparsed line:', line)
            elif phase == 2:
                # Skiping dupe lines, looking for var label
                if line.startswith('var label = {'):
                    phase = 3
            elif phase == 3:
                if line.startswith('}'):
                    phase = 4
                elif mat_re.match(line):
                    assert key is None
                    key = mat_re.match(line).group(1).strip()
                    name = {}
                elif name_re.match(line):
                    assert key is not None
                    assert name is not None
                    lang, trans = name_re.match(line).groups()
                    if lang == 'en-US':
                        lang = 'en'
                    assert lang not in name
                    text = trans.strip().replace('\\\\', '&#92;')
                    text = text.replace('\\', '').replace('&#92;', '\\')
                    name[lang.strip()] = text
                elif line.startswith('  })'):
                    assert key is not None
                    assert name
                    specs = collection.filter('specifications', maturity=key)
                    if specs:
                        maturity = Maturity(id=key, slug=key, name=name)
                        collection.add(maturity)
                    else:
                        self.logger.warning(
                            'Skipping unused maturity "%s"', key)
                    key = None
                    name = None
            elif phase == 4:
                # Not processing rest of file
                pass
        assert phase == 4, "Spec2 didn't match expected format"

        # Remove Specs without maturities
        immature_specs = collection.filter('specifications', maturity=None)
        for spec in immature_specs:
            self.logger.warning(
                'Skipping spec with no maturity "%s"', spec.name['en'])
            collection.remove(spec)


if __name__ == '__main__':
    tool = LoadSpecData()
    tool.init_from_command_line()
    tool.logger.info("Loading data into {tool.api}".format(tool=tool))
    changes = tool.run()
    tool.report_changes(changes)
