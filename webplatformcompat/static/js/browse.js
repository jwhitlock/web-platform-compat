"use strict";
/*global Browse: false, DS: false, Ember: false, window: false */
window.Browse = Ember.Application.create({
    // Debugging flags
    LOG_TRANSITIONS: false,
    LOG_TRANSITIONS_INTERNAL: false,
    LOG_ACTIVE_GENERATION: false,
    LOG_RESOLVER: false,
});

Browse.Utils = {
    htmlEntities: function (str) {
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    },
};

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
    this.resource('sections');
    this.resource('section', {path: '/sections/:section_id'});
    this.resource('maturities');
    this.resource('maturity', {path: '/maturities/:maturity_id'});
    this.resource('users');
    this.resource('user', {path: '/users/:user_id'});
    this.resource('changesets');
    this.resource('changeset', {path: '/changesets/:changeset_id'});
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

Browse.UsersRoute = Ember.Route.extend(Browse.PaginatedRouteMixin, {
    model: function () {
        return this.store.find('user');
    }
});

Browse.ChangesetsRoute = Ember.Route.extend(Browse.PaginatedRouteMixin, {
    model: function () {
        return this.store.find('changeset');
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
    mdn_uri: attr(),
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

Browse.User = DS.Model.extend({
    username: attr('string'),
    created: attr('date'),
    agreement: attr(),
    permissions: attr(),
    changesets: DS.hasMany('changeset', {async: true}),
});

Browse.Changeset = DS.Model.extend({
    created: attr('date'),
    modified: attr('date'),
    closed: attr('boolean'),
    target_resource_type: attr(),
    target_resource_id: attr(),
    user: DS.belongsTo('user', {async: true}),
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
    OptionalDateHTML: function (propertyName) {
        return Ember.computed(propertyName, function () {
            var date = this.get(propertyName), year, month, day;
            if (date) {
                year = date.getFullYear();
                month = (date.getMonth() + 1).toString();
                day = date.getDate().toString();
                return year + '-' +
                    (month.length < 2 ? '0' : '') + month + '-' +
                    (day.length < 2 ? '0' : '') + day;
            }
            return '<em>none</em>';
        });
    },
    TranslationDefaultHTML: function (propertyName) {
        /* Turn a translation object into default HTML */
        return Ember.computed(propertyName, function () {
            var property = this.get(propertyName), en;
            if (!property) { return '<em>none</em>'; }
            if (typeof property === 'string') {
                return '<code>' + property + '</code>';
            }
            en = property.en;
            if (en.indexOf('https://') === 0 || en.indexOf('http://') === 0) {
                return '<a href="' + en + '">' + en + '</a>';
            }
            return en;
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
            if (typeof property === 'string') {
                outArray.push({
                    'lang': 'canonical',
                    'value': '<code>' + property + '</code>'
                });
                return outArray;
            }
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
                i,
                val;
            if (arrayLen === 0) { return '<em>none</em>'; }
            if (arrayLen === 1 && array[0].lang === 'canonical') {
                ul = array[0].value;
                return ul;
            }
            for (i = 0; i < arrayLen; i += 1) {
                item = array[i];
                val = item.value;
                ul += '<li>' + item.lang + ': ';
                if (val.indexOf('https://') === 0 || val.indexOf('http://') === 0) {
                    ul += '<a href="' + val + '">' + val + '</a>';
                } else {
                    ul += val;
                }
                ul += '</li>';
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
Browse.SectionsController = Ember.ArrayController.extend(Browse.LoadMoreMixin);
Browse.MaturitiesController = Ember.ArrayController.extend(Browse.LoadMoreMixin);
Browse.UsersController = Ember.ArrayController.extend(Browse.LoadMoreMixin);
Browse.ChangesetsController = Ember.ArrayController.extend(Browse.LoadMoreMixin);

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
    releaseDayHTML: Browse.Properties.OptionalDateHTML('release_day'),
    retirementDayHTML: Browse.Properties.OptionalDateHTML('retirement_day'),
    supportCount: Browse.Properties.IdCounter('supports'),
    supportCountText: Browse.Properties.IdCounterText('supportCount', 'Feature'),
    releaseNoteUriArray: Browse.Properties.TranslationArray('release_notes_uri'),
    releaseNoteUriDefaultHTML: Browse.Properties.TranslationDefaultHTML('release_notes_uri'),
    releaseNoteUriListHTML: Browse.Properties.TranslationListHTML('releaseNoteUriArray'),
    noteArray: Browse.Properties.TranslationArray('note'),
    noteDefaultHTML: Browse.Properties.TranslationDefaultHTML('note'),
    noteListHTML: Browse.Properties.TranslationListHTML('noteArray'),
});


Browse.FeatureController = Ember.ObjectController.extend(Browse.LoadMoreMixin, {
    mdnDefaultHTML: Ember.computed('mdn_uri', function () {
        var mdn_uri = this.get('mdn_uri'), path;
        if (!mdn_uri) { return '<em>no link</em>'; }
        path = mdn_uri.en.replace("https://developer.mozilla.org", "");
        return (
            '<a href="' +
            Browse.Utils.htmlEntities(mdn_uri.en) +
            '#Browser_compatibility">' + path + '</a>'
        );
    }),
    mdnArray: Browse.Properties.TranslationArray('mdn_uri'),
    mdnListHTML: Ember.computed('mdnArray', function () {
        var mdnArray = this.get('mdnArray'),
            arrayLen = mdnArray.length,
            ul = "<ul>",
            uri,
            i;
        if (arrayLen === 0) {
            return "<em>none</em>";
        }
        for (i = 0; i < arrayLen; i += 1) {
            uri = mdnArray[i];
            ul += (
                '<li>' + uri.lang + ': ' +
                '<a href="' +  uri.value + '#Browser_compatibility">' +
                uri.value.replace("https://developer.mozilla.org", "") +
                '</a></li>'
            );
        }
        ul += '</ul>';
        return ul;
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
    supportCount: Browse.Properties.IdCounter('supports'),
    supportCountText: Browse.Properties.IdCounterText('supportCount', 'Version'),
    childCount: Browse.Properties.IdCounter('children'),
    childCountText: Browse.Properties.IdCounterText('childCount', 'Child', 'Children'),
    viewUrl: Ember.computed('id', function () {
        var id = this.get('id');
        return "/view_feature/" + id;
    }),
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
});

Browse.SpecificationController = Ember.ObjectController.extend(Browse.LoadMoreMixin, {
    nameDefaultHTML: Browse.Properties.TranslationDefaultHTML('name'),
    nameArray: Browse.Properties.TranslationArray('name'),
    nameListHTML: Browse.Properties.TranslationListHTML('nameArray'),
    uriArray: Browse.Properties.TranslationArray('uri'),
    uriDefaultHTML: Ember.computed('uri', function () {
        var uri = this.get('uri');
        return '<a href="' + uri.en + '">' + uri.en + '</a>';
    }),
    uriListHTML: Ember.computed('uriArray', function () {
        var uriArray = this.get('uriArray'),
            arrayLen = uriArray.length,
            ul = "<ul>",
            uri,
            i;
        for (i = 0; i < arrayLen; i += 1) {
            uri = uriArray[i];
            ul += '<li>' + uri.lang + ': <a href="' + uri.value + '">' +
                  uri.value + '</a></li>';
        }
        ul += '</ul>';
        return ul;
    }),
    sectionCount: Browse.Properties.IdCounter('sections'),
    sectionCountText: Browse.Properties.IdCounterText('sectionCount', 'Section'),
});

Browse.SectionController = Ember.ObjectController.extend(Browse.LoadMoreMixin, {
    nameDefaultHTML: Browse.Properties.TranslationDefaultHTML('name'),
    nameArray: Browse.Properties.TranslationArray('name'),
    nameListHTML: Browse.Properties.TranslationListHTML('nameArray'),
    noteDefaultHTML: Browse.Properties.TranslationDefaultHTML('note'),
    noteArray: Browse.Properties.TranslationArray('note'),
    noteListHTML: Browse.Properties.TranslationListHTML('noteArray'),
    subpathDefaultHTML: Ember.computed('subpath', 'specification.uri', function () {
        var subpath = this.get('subpath'),
            specUri = this.get('specification.uri'),
            subpathDefault;
        if (!subpath) {
            subpathDefault = "<em>no path</em>";
        } else {
            subpathDefault = subpath.en;
        }
        if (specUri) {
            return '<a href="' + specUri.en + subpathDefault + '">' + subpathDefault + '</a>';
        }
        return subpathDefault;
    }),
    subpathArray: Browse.Properties.TranslationArray('subpath'),
    subpathListHTML: Ember.computed('subpathArray', 'specification.uri', function () {
        var subpathArray = this.get('subpathArray'),
            specUri = this.get('specification.uri'),
            arrayLen = subpathArray.length,
            subpath,
            ul = "<ul>",
            uri,
            i;
        for (i = 0; i < arrayLen; i += 1) {
            subpath = subpathArray[i];
            if (!specUri) {
                uri = subpath.value;
            } else if (specUri.hasOwnProperty(subpath.lang)) {
                uri = specUri[subpath.lang] + subpath.value;
            } else {
                uri = specUri.en + subpath.value;
            }
            ul += '<li>' + subpath.lang + ': <a href="' + uri + '">' +
                  subpath.value + '</a></li>';
        }
        ul += '</ul>';
        return ul;
    }),
    featureCount: Browse.Properties.IdCounter('features'),
    featureCountText: Browse.Properties.IdCounterText('featureCount', 'Feature'),
});

Browse.MaturityController = Ember.ObjectController.extend(Browse.LoadMoreMixin, {
    specCount: Browse.Properties.IdCounter('specifications'),
    specCountText: Browse.Properties.IdCounterText('specCount', 'Specification'),
    nameDefaultHTML: Browse.Properties.TranslationDefaultHTML('name'),
    nameArray: Browse.Properties.TranslationArray('name'),
    nameListHTML: Browse.Properties.TranslationListHTML('nameArray'),
    specificationCount: Browse.Properties.IdCounter('specifications'),
    specificationCountText: Browse.Properties.IdCounterText('specificationCount', 'Specification'),
});

Browse.UserController = Ember.ObjectController.extend(Browse.LoadMoreMixin, {
    changesetCount: Browse.Properties.IdCounter('changesets'),
    changesetCountText: Browse.Properties.IdCounterText('changesetCount', 'Changeset'),
    createdHTML: Browse.Properties.OptionalDateHTML('created'),
    permissionsText: Ember.computed('permissions', function () {
        var permissions = this.get('permissions'),
            arrayLen = permissions.length,
            out,
            i;
        for (i = 0; i < arrayLen; i += 1) {
            out = permissions[i];
            if (i < (arrayLen - 1)) {
                out += ', ';
            }
        }
        return out;
    }),
    permissionsListHTML: Ember.computed('permissions', function () {
        var permissions = this.get('permissions'),
            arrayLen = permissions.length,
            ul = "<ul>",
            i;
        for (i = 0; i < arrayLen; i += 1) {
            ul += '<li>' + permissions[i] + '</li>';
        }
        ul += '</ul>';
        return ul;
    }),
});

Browse.ChangesetController = Ember.ObjectController.extend(Browse.LoadMoreMixin, {
    changeCount: Ember.computed(function () {
        return "to do";
    }),
    closedText: Ember.computed('closed', function () {
        var closed = this.get('closed');
        if (closed) {
            return 'closed';
        }
        return 'open';
    }),
    createdHTML: Browse.Properties.OptionalDateHTML('created'),
    modifiedHTML: Browse.Properties.OptionalDateHTML('modified'),
    targetHTML: Ember.computed('target_resource_type', 'target_resource_id', function () {
        var target_resource_type = this.get('target_resource_type'),
            target_resource_id = this.get('target_resource_id'),
            link;
        if (target_resource_type && target_resource_id) {
            link = "<a href=\"/browse/" + target_resource_type + "/" +
                   target_resource_id + "\">" + target_resource_type + " " +
                   target_resource_id + "</a>";
            return link;
        }
        return "<em>Not set</em>";
    }),
});
