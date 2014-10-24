"use strict";
/*global Browse: false, DS: false, Ember: false, window: false */
window.Browse = Ember.Application.create({
    // Debugging flags
    LOG_TRANSITIONS: false,
    LOG_TRANSITIONS_INTERNAL: false,
    LOG_ACTIVE_GENERATION: false,
    LOG_RESOLVER: false,
});

/* Router */
Browse.Router.reopen({
    rootURL: '/browse/',
    location: 'history'
});

Browse.Router.map(function () {
    this.resource('browsers');
    this.resource('browser', {path: '/browsers/:browser_id'});
    this.resource('versions');
    this.resource('version', {path: '/versions/:version_id'});
    this.resource('features');
    this.resource('feature', {path: '/features/:feature_id'});
    this.resource('supports');
    this.resource('support', {path: '/supports/:support_id'});
    this.resource('specifications');
    this.resource('specification', {path: '/specifications/:specification_id'});
    this.resource('maturities');
    this.resource('maturity', {path: '/maturities/:maturity_id'});

});

/* Serializer - JsonApiSerializer with modifictions */
DS.JsonApiNamespacedSerializer = DS.JsonApiSerializer.extend({
    namespace: 'api/v1',
    extractLinks: function (links) {
        // Modifications:
        // Strip the namespace from links as well
        // Camelize linkKeys
        var link, key, value, route, extracted = [], linkEntry, linkKey;

        for (link in links) {
            if (links.hasOwnProperty(link)) {
                key = link.split('.').pop();
                value = links[link];
                if (typeof value === 'string') {
                    route = value;
                } else {
                    key = value.type || key;
                    route = value.href;
                }

                // strip base url
                if (route.substr(0, 4).toLowerCase() === 'http') {
                    route = route.split('//').pop().split('/').slice(1).join('/');
                }

                // strip prefix slash
                if (route.charAt(0) === '/') {
                    route = route.substr(1);
                }

                // strip namespace
                if (route.indexOf(this.namespace) === 0) {
                    route = route.substr(this.namespace.length);
                    if (route.charAt(0) === '/') {
                        route = route.substr(1);
                    }
                }

                linkEntry = { };
                linkKey = Ember.String.singularize(key);
                linkKey = Ember.String.camelize(linkKey);
                linkEntry[linkKey] = route;
                extracted.push(linkEntry);
                /*jslint nomen: true */
                /* DS._routes is convention of DS.JsonApiSerializer */
                DS._routes[linkKey] = route;
                /*jslint nomen: false */
            }
        }

        return extracted;
    },
    extractMeta: function (store, type, payload) {
        if (payload && payload.meta) {
            store.metaForType(type, payload.meta);
            delete payload.meta;
        }
    },
});

/* Adapter - JsonApiAdapter with modifictions */
Browse.ApplicationAdapter = DS.JsonApiAdapter.extend({
    namespace: 'api/v1',
    defaultSerializer: 'DS/jsonApiNamespaced'
});


/* Routes */
Browse.PaginatedRouteMixin = Ember.Mixin.create({
    queryParams: {
        page: {refreshModel: true},
    },
    setupController: function (controller, model) {
        controller.set('model', model);
        controller.updatePagination();
    },
});

Browse.BrowsersRoute = Ember.Route.extend(Browse.PaginatedRouteMixin, {
    model: function () {
        return this.store.find('browser');
    }
});

Browse.VersionsRoute = Ember.Route.extend(Browse.PaginatedRouteMixin, {
    model: function () {
        return this.store.find('version');
    }
});

Browse.FeaturesRoute = Ember.Route.extend(Browse.PaginatedRouteMixin, {
    model: function () {
        return this.store.find('feature');
    }
});

Browse.SupportsRoute = Ember.Route.extend(Browse.PaginatedRouteMixin, {
    model: function () {
        return this.store.find('support');
    }
});

Browse.MaturitiesRoute = Ember.Route.extend(Browse.PaginatedRouteMixin, {
    model: function () {
        return this.store.find('maturity');
    }
});

Browse.SpecificationsRoute = Ember.Route.extend(Browse.PaginatedRouteMixin, {
    model: function () {
        return this.store.find('specification');
    }
});

Browse.SectionsRoute = Ember.Route.extend(Browse.PaginatedRouteMixin, {
    model: function () {
        return this.store.find('section');
    }
});

/* Models */
var attr = DS.attr;

Browse.Browser = DS.Model.extend({
    slug: attr('string'),
    name: attr(),
    note: attr(),
    versions: DS.hasMany('version', {async: true}),
});

Browse.Feature = DS.Model.extend({
    slug: attr('string'),
    mdn_path: attr('string'),
    experimental: attr(),
    standardized: attr(),
    stable: attr(),
    obsolete: attr(),
    name: attr(),
    parent: DS.belongsTo('feature', {inverse: 'children', async: true}),
    children: DS.hasMany('feature', {inverse: 'parent', async: true}),
    supports: DS.hasMany('support', {async: true}),
    sections: DS.hasMany('section', {async: true}),
});

Browse.Version = DS.Model.extend({
    browser: DS.belongsTo('browser'),
    version: attr('string'),
    release_day: attr('date'),
    retirement_day: attr('date'),
    status: attr('string'),
    release_notes_uri: attr(),
    note: attr(),
    order: attr('number'),
    supports: DS.hasMany('support', {async: true}),
});

Browse.Support = DS.Model.extend({
    support: attr('string'),
    prefix: attr('string'),
    prefix_mandatory: attr(),
    alternate_name: attr('string'),
    alternate_mandatory: attr(),
    requires_config: attr('string'),
    default_config: attr('string'),
    protected: attr('boolean'),
    note: attr(),
    footnote: attr(),
    version: DS.belongsTo('version', {async: true}),
    feature: DS.belongsTo('feature', {async: true}),
});

Browse.Maturity = DS.Model.extend({
    slug: attr('string'),
    name: attr(),
    specifications: DS.hasMany('specification', {async: true}),
});

Browse.Specification = DS.Model.extend({
    slug: attr('string'),
    mdn_key: attr('string'),
    name: attr(),
    uri: attr(),
    maturity: DS.belongsTo('maturity', {async: true}),
    sections: DS.hasMany('section', {async: true}),
});

Browse.Section = DS.Model.extend({
    number: attr('string'),
    name: attr(),
    subpath: attr(),
    note: attr(),
    specification: DS.belongsTo('specification', {async: true}),
    features: DS.hasMany('feature', {async: true}),
});

/* Controllers */

/* LoadMoreMixin based on https://github.com/pangratz/dashboard/commit/68d1728 */
Browse.LoadMoreMixin = Ember.Mixin.create(Ember.Evented, {
    loadingMore: false,
    currentPage: 1,
    resetLoadMore: function () {
        this.set('currentPage', 1);
    },
    pagination: null,
    canLoadMore: Ember.computed('pagination', 'model.length', function () {
        var pagination = this.get('pagination');
        return (pagination && pagination.next && pagination.count > this.get("model.length"));
    }),
    updatePagination: function () {
        var store = this.get('store'),
            modelType = this.get('model.type'),
            modelSingular = modelType.typeKey,
            modelPlural = Ember.String.pluralize(modelSingular),
            metadata = store.typeMapFor(modelType).metadata,
            pagination = metadata && metadata.pagination && metadata.pagination[modelPlural];
        this.set("pagination", pagination);
        this.set("loadingMore", false);
    },
    loadMore: function () {
        if (this.get('canLoadMore')) {
            var page = this.incrementProperty('currentPage'),
                self = this,
                modelSingular = this.get('model.type.typeKey'),
                results = this.get('store').findQuery(modelSingular, {page: page});
            this.set("loadingMore", true);
            results.then(function (newRecords) {
                self.updatePagination(newRecords);
            });
            return results;
        }
    },
    actions: {
        loadMore: function () { this.loadMore(); }
    }
});

Browse.Properties = {
    IdCounter: function (relation) {
        /* Count the number of related objects via the private "data" method.
         * The alternative, "models.<relation>.length", will load each
         * related instance from the API before returning a count.  This can
         * make list views slow and makes unneccessary API calls.  The caveat
         * is we're using a private method that may go away in the future.
         * However, Ember devs are opposed to a performant count for this use
         * case: https://github.com/emberjs/data/issues/586
        */
        return Ember.computed('model.data', function () {
            return this.get('model.data.' + relation + '.length');
        });
    },
    IdCounterText: function (countName, singular, plural) {
        /* Return 'X Object(s)' text, via a count property */
        return Ember.computed(countName, function () {
            var count = this.get(countName);
            if (count === 1) {
                return '1 ' + singular;
            }
            return count + ' ' + (plural || singular + 's');
        });
    },
    OptionalHTML: function (propertyName) {
        /* Turn an optional string into HTML */
        return Ember.computed(propertyName, function () {
            var property = this.get(propertyName);
            if (!property) { return '<em>none</em>'; }
            return property;
        });
    },
    TranslationDefaultHTML: function (propertyName) {
        /* Turn a translation object into default HTML */
        return Ember.computed(propertyName, function () {
            var property = this.get(propertyName);
            if (!property) { return '<em>none</em>'; }
            if (typeof property === 'string') {
                return '<code>' + property + '</code>';
            }
            return property.en;
        });
    },
    TranslationArray: function (propertyName) {
        /* Turn a translation object into an array of objects.
         * For example, this translation object:
         * {'en': 'English', 'fr': 'French', 'es': 'Spanish'}
         * becomes:
         * [{'lang': 'en', 'value': 'English'},
         *  {'lang': 'es', 'value': 'Spanish'},
         *  {'lang': 'fr', 'value': 'French'},
         * ]
         * The english translation is the first value, then the remaining are
         * sorted by keys.
         */
        return Ember.computed(propertyName, function () {
            var property = this.get(propertyName),
                keys = [],
                outArray = [],
                key,
                i,
                keyLen;
            if (!property) { return []; }
            for (key in property) {
                if (property.hasOwnProperty(key)) {
                    if (key === 'en') {
                        outArray.push({'lang': key, 'value': property[key]});
                    } else {
                        keys.push(key);
                    }
                }
            }
            keys.sort();
            keyLen = keys.length;
            for (i = 0; i < keyLen; i += 1) {
                key = keys[i];
                outArray.push({'lang': key, 'value': property[key]});
            }
            return outArray;
        });
    },
    TranslationListHTML: function (arrayName) {
        /* Turn a TranslationArray into an unordered list */
        return Ember.computed(arrayName, function () {
            var array = this.get(arrayName),
                arrayLen = array.length,
                ul = "<ul>",
                item,
                i;
            if (arrayLen === 0) { return '<em>none</em>'; }
            for (i = 0; i < arrayLen; i += 1) {
                item = array[i];
                ul += '<li>' + item.lang + ': ' + item.value + '</li>';
            }
            ul += '</ul>';
            return ul;
        });
    },
};

Browse.BrowsersController = Ember.ArrayController.extend(Browse.LoadMoreMixin);
Browse.VersionsController = Ember.ArrayController.extend(Browse.LoadMoreMixin);
Browse.FeaturesController = Ember.ArrayController.extend(Browse.LoadMoreMixin);
Browse.SupportsController = Ember.ArrayController.extend(Browse.LoadMoreMixin);
Browse.SpecificationsController = Ember.ArrayController.extend(Browse.LoadMoreMixin);
Browse.MaturitiesController = Ember.ArrayController.extend(Browse.LoadMoreMixin);

Browse.BrowserController = Ember.ObjectController.extend(Browse.LoadMoreMixin, {
    versionCount: Browse.Properties.IdCounter('versions'),
    versionCountText: Browse.Properties.IdCounterText('versionCount', 'Version'),
    nameArray: Browse.Properties.TranslationArray('name'),
    nameDefaultHTML: Browse.Properties.TranslationDefaultHTML('name'),
    nameListHTML: Browse.Properties.TranslationListHTML('nameArray'),
    noteArray: Browse.Properties.TranslationArray('note'),
    noteDefaultHTML: Browse.Properties.TranslationDefaultHTML('note'),
    noteListHTML: Browse.Properties.TranslationListHTML('noteArray'),
});

Browse.VersionController = Ember.ObjectController.extend(Browse.LoadMoreMixin, {
    versionHTML: Ember.computed('version', function () {
        var version = this.get('version');
        if (version) { return version; }
        return '<em>unspecified</em>';
    }),
    fullVersionHTML: Ember.computed('browser.name.en', 'version', function () {
        var out = this.get('browser.name.en') + ' ',
            version = this.get('version');
        if (!version) {
            out += '(<em>unspecified version</em>)';
        } else {
            out += version;
        }
        return out;
    }),
    releaseDayHTML: Browse.Properties.OptionalHTML('release_day'),
    retirementDayHTML: Browse.Properties.OptionalHTML('retirement_day'),
    featureCount: Browse.Properties.IdCounter('supports'),
    featureCountText: Browse.Properties.IdCounterText('featureCount', 'Feature'),
    releaseNoteUriArray: Browse.Properties.TranslationArray('releaseNoteUri'),
    releaseNoteUriDefaultHTML: Browse.Properties.TranslationDefaultHTML('releaseNoteUri'),
    releaseNoteUriListHTML: Browse.Properties.TranslationListHTML('releaseNoteUriArray'),
    noteArray: Browse.Properties.TranslationArray('note'),
    noteDefaultHTML: Browse.Properties.TranslationDefaultHTML('note'),
    noteListHTML: Browse.Properties.TranslationListHTML('noteArray'),
});


Browse.FeatureController = Ember.ObjectController.extend(Browse.LoadMoreMixin, {
    mdnFullLinkHTML: Ember.computed('mdn_path', function () {
        var mdn_path = this.get('mdn_path');
        if (!mdn_path) { return '<em>no link</em>'; }
        return (
            '<a href="https://developer.mozilla.org/' + mdn_path +
            '#Browser_compatibility">' + mdn_path + '</a>'
        );
    }),
    flagsHTML: Ember.computed('experimental', 'standardized', 'stable', 'obsolete', function () {
        var experimental = this.get('experimental'),
            standardized = this.get('standardized'),
            stable = this.get('stable'),
            obsolete = this.get('obsolete'),
            flags = [];
        if (experimental) { flags.push('experimental'); }
        if (!stable) { flags.push('not stable'); }
        if (!standardized) { flags.push('not standardized'); }
        if (obsolete) { flags.push('obsolete'); }
        if (flags.length === 0) { return '<em>none</em>'; }
        return '<b>' + flags.join('</b><b>') + '</b>';
    }),
    nameDefaultHTML: Browse.Properties.TranslationDefaultHTML('name'),
    nameArray: Browse.Properties.TranslationArray('name'),
    nameListHTML: Browse.Properties.TranslationListHTML('nameArray'),
    versionCount: Browse.Properties.IdCounter('supports'),
    versionCountText: Browse.Properties.IdCounterText('versionCount', 'Version'),
});

Browse.SupportController = Ember.ObjectController.extend(Browse.LoadMoreMixin, {
    prefixHTML: Ember.computed('prefix', 'prefix_mandatory', function () {
        var prefix = this.get('prefix'),
            prefix_mandatory = this.get('prefix_mandatory'),
            out;
        if (!prefix) { return '<em>none</em>'; }
        out = '<code>' + prefix + '</code> (';
        if (prefix_mandatory) {
            out += 'required)';
        } else {
            out += 'mandatory)';
        }
        return out;
    }),
    alternateNameHTML: Ember.computed('alternate_name', 'alternate_name_mandatory', function () {
        var alternate_name = this.get('alternate_name'),
            alternate_name_mandatory = this.get('alternate_name_mandatory'),
            out;
        if (!alternate_name) { return '<em>none</em>'; }
        out = '<code>' + alternate_name + '</code> (';
        if (alternate_name_mandatory) {
            out += 'required)';
        } else {
            out += 'mandatory)';
        }
        return out;
    }),
    requiredConfigHTML: Ember.computed('required_config', 'default_config', function () {
        var required_config = this.get('required_config'),
            default_config = this.get('default_config'),
            out;
        if (!required_config) { return '<em>none</em>'; }
        out = '<code>' + required_config + '</code> (';
        if (default_config === required_config) {
            out += '<em>default config</em>)';
        } else {
            out += 'default is <code>' + default_config + '</code>';
        }
        return out;
    }),
    noteArray: Browse.Properties.TranslationArray('note'),
    noteDefaultHTML: Browse.Properties.TranslationDefaultHTML('note'),
    noteListHTML: Browse.Properties.TranslationListHTML('noteArray'),
    footnoteArray: Browse.Properties.TranslationArray('footnote'),
    footnoteDefaultHTML: Browse.Properties.TranslationDefaultHTML('footnote'),
    footnoteListHTML: Browse.Properties.TranslationListHTML('footnoteArray'),
});

Browse.SpecificationController = Ember.ObjectController.extend(Browse.LoadMoreMixin, {
    namesArray: Browse.Properties.TranslationArray('name'),
    uriArray: Browse.Properties.TranslationArray('uri'),
    uriDefaultHTML: Ember.computed('uri', 'name', function () {
        var uri = this.get('uri'),
            name = this.get('name');
        return '<a href="' + uri.en + '">' + name.en + '</a>';
    }),
    uriListHTML: Ember.computed('uriArray', 'name', function () {
        var uriArray = this.get('uriArray'),
            name = this.get('name'),
            arrayLen = uriArray.length,
            ul = "<ul>",
            uri,
            i;
        for (i = 0; i < arrayLen; i += 1) {
            uri = uriArray[i];
            ul += '<li>' + uri.lang + ': <a href="' +  uri.value + '">';
            if (name.hasOwnProperty(uri.lang)) {
                ul += name[uri.lang];
            } else {
                ul += '(' + name.en + ')';
            }
            ul += '</a></li>';
        }
        ul += '</ul>';
        return ul;
    }),
    sectionCount: Browse.Properties.IdCounter('sections'),
    sectionCountText: Browse.Properties.IdCounterText('sectionCount', 'Section'),
});

Browse.MaturityController = Ember.ObjectController.extend(Browse.LoadMoreMixin, {
    specCount: Browse.Properties.IdCounter('specifications'),
    specCountText: Browse.Properties.IdCounterText('specCount', 'Specification'),
    nameDefaultHTML: Browse.Properties.TranslationDefaultHTML('name'),
    namesArray: Browse.Properties.TranslationArray('name'),
    namesListHTML: Browse.Properties.TranslationListHTML('namesArray'),
});
