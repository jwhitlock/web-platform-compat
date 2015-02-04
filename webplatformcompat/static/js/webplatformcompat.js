"use strict";
/*global window: false, document: false */

window.WPC = {
    parse_resources: function (obj) {
        /* Parse resources from a JSON API response */
        var key, value, rType, rItem, rArray, rIdx, rCnt, resources = {};

        for (key in obj) {
            if (obj.hasOwnProperty(key)) {
                value = obj[key];
                if (key === 'linked') {
                    /* linked is a dictionary of resource type strings
                     * ("browsers", "versions", etc.) to an array of
                     * resource representations.  Turn this into a
                     * dictionary of IDs to representations
                     */
                    for (rType in value) {
                        if (value.hasOwnProperty(rType)) {
                            resources[rType] = {};
                            rArray = value[rType];
                            rCnt = rArray.length;
                            for (rIdx = 0; rIdx < rCnt; rIdx += 1) {
                                rItem = rArray[rIdx];
                                resources[rType][rItem.id] = rItem;
                            }
                        }
                    }
                } else if (key === 'meta' || key === 'links') {
                    /* "meta" is meta data for the request, such as pagination
                     * "links" contains link patterns for related objects
                     * Copy to the resources
                     */
                    resources[key] = obj[key];
                } else {
                    /* Key is a resource type string ("browsers", etc.)
                     * and value is the main item.  Copy to the special
                     * "data" key, as well as the resource by type by ID lookup
                     */
                    value = obj[key];
                    if (!resources.hasOwnProperty(key)) {
                        resources[key] = {};
                    }
                    resources[key][value.id] = value;
                    resources.data = value;
                }
            }
        }
        return resources;
    },
    trans_span: function (trans, lang) {
        var span = document.createElement('span');
        span.innerHTML = this.trans_str(trans, lang);
        return span;
    },
    trans_str: function (trans, lang) {
        if (trans === null || trans === undefined) {
            return null;
        }
        if (typeof trans === 'string') {
            return "<code>" + trans + "</code>";
        }
        if (trans.hasOwnProperty(lang)) {
            return trans[lang];
        }
        if (trans.hasOwnProperty('en')) {
            return trans.en;
        }
        return '';
    },
    generate_specification_table: function (resources, lang) {
        var table, thead, tbody, tr, th, td, a, sCnt, sIdx, sectionId,
            section, spec, maturity, matClass, small, span;
        if (resources.data.links.sections) {
            // Create the table
            table = document.createElement('table');
            table.setAttribute('class', 'wpc-specifications-table table');

            // Create the table header
            thead = document.createElement('thead');
            tr = document.createElement('tr');
            th = document.createElement('th');
            th.innerHTML = "Specification";
            tr.appendChild(th);
            th = document.createElement('th');
            th.innerHTML = "Status";
            tr.appendChild(th);
            th = document.createElement('th');
            th.innerHTML = "Comment";
            tr.appendChild(th);
            thead.appendChild(tr);
            table.appendChild(thead);

            // Create the table body
            tbody = document.createElement('tbody');
            sCnt = resources.data.links.sections.length;
            for (sIdx = 0; sIdx < sCnt; sIdx += 1) {
                sectionId = resources.data.links.sections[sIdx];
                section = resources.sections[sectionId];
                spec = resources.specifications[section.links.specification];
                maturity = resources.maturities[spec.links.maturity];
                matClass = "maturity-" + maturity.slug;
                tr = document.createElement('tr');

                td = document.createElement('td');
                a = document.createElement('a');
                a.setAttribute('href', this.trans_str(spec.uri, lang) + this.trans_str(section.subpath, lang));
                a.appendChild(this.trans_span(spec.name, lang));
                a.appendChild(document.createElement('br'));
                small = document.createElement('small');
                small.appendChild(this.trans_span(section.number, lang));
                small.appendChild(document.createTextNode(' '));
                small.appendChild(this.trans_span(section.name, lang));
                a.appendChild(small);
                td.appendChild(a);
                tr.appendChild(td);

                td = document.createElement('td');
                span = this.trans_span(maturity.name, lang);
                span.setAttribute('class', matClass);
                td.appendChild(span);
                tr.appendChild(td);

                td = document.createElement('td');
                if (section.note) {
                    td.appendChild(this.trans_span(section.note, lang));
                }
                tr.appendChild(td);

                tbody.appendChild(tr);
            }
            table.appendChild(tbody);

            return table;
        }
        return null;
    },
    generate_browser_tables: function (resources, lang) {
        var a, backlink, browser, browserCnt, browserId, browserIdx,
            browserMap, feature, featureId, footnote, footnoteArray,
            footnoteCnt, footnoteDiv, footnoteId, footnoteIdx, footnoteNum,
            footnoteSup, idPrefix, nosupport, note, noteTxt, panel, prefix,
            releaseUri, span1, span2, support, supportCnt, supportId,
            supportIdx, supportMap, supports, tab, tabCnt, tabContent,
            tabContentItem, tabId, tabIdx, tabList, tabListItem, table, tabs,
            tbody, td, th, thead, tr, unknown, version, versionId, versionLink;
        if (resources.meta.compat_table.tabs) {
            idPrefix = 'wpc-compat-' + resources.data.id;
            tabs = resources.meta.compat_table.tabs;
            tabCnt = tabs.length;

            // Add bootstrap tab control for browser types (Desktop, etc.)
            panel = document.createElement('div');
            panel.setAttribute('role', 'tabpanel');
            tabList = document.createElement('ul');
            tabList.setAttribute('class', 'nav nav-tabs');
            tabList.setAttribute('role', 'tablist');
            tabContent = document.createElement('div');
            tabContent.setAttribute('class', 'tab-content');
            for (tabIdx = 0; tabIdx < tabCnt; tabIdx += 1) {
                tab = tabs[tabIdx];
                tabId = idPrefix + '_' + tabIdx;

                tabListItem = document.createElement('li');
                tabListItem.setAttribute('role', 'presentation');
                if (tabIdx === 0) {
                    tabListItem.setAttribute('class', 'active');
                }
                a = document.createElement('a');
                a.setAttribute('href', "#" + tabId);
                a.setAttribute('aria-controls', tabId);
                a.setAttribute('role', 'tab');
                a.setAttribute('data-toggle', 'tab');
                a.appendChild(this.trans_span(tab.name, lang));
                tabListItem.appendChild(a);
                tabList.appendChild(tabListItem);

                tabContentItem = document.createElement('div');
                tabContentItem.setAttribute('role', 'tabpanel');
                tabContentItem.setAttribute('id', tabId);
                if (tabIdx === 0) {
                    tabContentItem.setAttribute('class', 'tab-pane active');
                } else {
                    tabContentItem.setAttribute('class', 'tab-pane');
                }

                // Add the compat table for browser type
                table = document.createElement('table');
                table.setAttribute('class', 'table table-striped compat-table');

                thead = document.createElement('thead');

                tr = document.createElement('tr');
                th = document.createElement('th');
                th.appendChild(document.createTextNode('Feature'));
                tr.appendChild(th);

                browserCnt = tab.browsers.length;
                for (browserIdx = 0; browserIdx < browserCnt; browserIdx += 1) {
                    browserId = tab.browsers[browserIdx];
                    browser = resources.browsers[browserId];
                    th = document.createElement('th');
                    th.appendChild(this.trans_span(browser.name, lang));
                    tr.appendChild(th);
                }
                thead.appendChild(tr);

                // Add the compat table body (rows of sub-features)
                tbody = document.createElement('tbody');
                supportMap = resources.meta.compat_table.supports;
                for (featureId in supportMap) {
                    if (supportMap.hasOwnProperty(featureId) &&
                            featureId !== resources.data.id) {
                        browserMap = supportMap[featureId];
                        feature = resources.features[featureId];
                        tr = document.createElement('tr');
                        td = document.createElement('td');
                        td.appendChild(this.trans_span(feature.name, lang));
                        if (feature.experimental) {
                            span1 = document.createElement('span');
                            span1.setAttribute('class', 'glyphicon glyphicon-fire');
                            span1.setAttribute('style', 'color: #09d;');
                            span1.setAttribute('aria-hidden', 'true');
                            span1.setAttribute('data-toggle', 'tooltip');
                            span1.setAttribute('data-placement', 'top');
                            span1.setAttribute('title', 'This is an experimental API that should not be used in production code.');
                            span2 = document.createElement('span');
                            span2.setAttribute('class', 'sr-only');
                            span2.appendChild(document.createTextNode('This is an experimental API that should not be used in production code.'));
                            td.appendChild(span1);
                            td.appendChild(span2);
                        }
                        tr.appendChild(td);

                        for (browserIdx = 0; browserIdx < browserCnt; browserIdx += 1) {
                            browserId = tab.browsers[browserIdx];
                            browser = resources.browsers[browserId];

                            // Add each version / support for sub-feature / browser
                            td = document.createElement('td');
                            supports = browserMap[browserId];
                            if (supports) {
                                supportCnt = supports.length;
                                for (supportIdx = 0; supportIdx < supportCnt; supportIdx += 1) {
                                    supportId = supports[supportIdx];
                                    support = resources.supports[supportId];
                                    versionId = support.links.version;
                                    version = resources.versions[versionId];

                                    // Version with support text
                                    if (supportIdx !== 0) {
                                        td.appendChild(document.createElement('br'));
                                    }
                                    if (version.version) {
                                        releaseUri = this.trans_str(version.release_notes_uri, lang);
                                        if (releaseUri) {
                                            versionLink = document.createElement('a');
                                            versionLink.setAttribute('href', releaseUri);
                                            versionLink.setAttribute('title', 'Release Notes');
                                            versionLink.appendChild(document.createTextNode(version.version));
                                            td.appendChild(versionLink);
                                        } else {
                                            td.appendChild(document.createTextNode(version.version));
                                        }
                                    }
                                    if (support.support === 'no') {
                                        nosupport = document.createElement('span');
                                        nosupport.setAttribute('style', 'color: #f00;');
                                        nosupport.appendChild(document.createTextNode('Not supported'));
                                        td.appendChild(nosupport);
                                    } else if (support.support !== 'yes' || (!version.version)) {
                                        td.appendChild(document.createTextNode(' (' + support.support + ')'));
                                    }

                                    // Prefix
                                    if (support.prefix && support.prefix_mandatory) {
                                        td.appendChild(document.createTextNode(' '));
                                        prefix = document.createElement('code');
                                        prefix.setAttribute('style', 'white-space: nowrap;');
                                        prefix.appendChild(document.createTextNode(support.prefix));
                                        td.appendChild(prefix);
                                    } else {
                                        prefix = null;
                                    }

                                    // Note
                                    if (support.note) {
                                        td.appendChild(document.createTextNode(' '));
                                        noteTxt = "(" + this.trans_str(support.note) + ")";
                                        note = document.createElement("span");
                                        note.appendChild(document.createTextNode(noteTxt));
                                        td.appendChild(note);
                                    } else {
                                        note = null;
                                    }

                                    // Footnote
                                    if (support.footnote) {
                                        td.appendChild(document.createTextNode(' '));
                                        footnoteNum = resources.meta.compat_table.footnotes[supportId];
                                        footnoteId = 'wpc-compat-' + resources.data.id + '-footnote-' + footnoteNum;
                                        footnoteSup = document.createElement('sup');
                                        footnote = document.createElement('a');
                                        footnote.setAttribute('id', footnoteId + '-back');
                                        footnote.setAttribute('href', '#' + footnoteId);
                                        footnote.appendChild(document.createTextNode("[" + footnoteNum + "]"));
                                        footnoteSup.appendChild(footnote);
                                        td.appendChild(footnoteSup);
                                    } else {
                                        footnote = null;
                                    }
                                }
                            } else {
                                unknown = document.createElement('span');
                                unknown.setAttribute('style', 'color: rgb(255, 153, 0);');
                                unknown.setAttribute('title', "Compatibility unknown; please update this.");
                                unknown.appendChild(document.createTextNode('?'));
                                td.appendChild(unknown);
                            }
                            tr.appendChild(td);
                        }

                        tbody.appendChild(tr);
                    }
                }

                table.appendChild(thead);
                table.appendChild(tbody);
                tabContentItem.appendChild(table);
                tabContent.appendChild(tabContentItem);
            }

            // Add footnotes
            if (resources.meta.compat_table.footnotes) {
                supportMap = resources.meta.compat_table.footnotes;
                footnoteArray = [];
                for (supportId in supportMap) {
                    if (supportMap.hasOwnProperty(supportId)) {
                        support = resources.supports[supportId];
                        footnoteNum = supportMap[supportId];
                        footnote = document.createElement('p');
                        footnoteId = 'wpc-compat-' + resources.data.id + '-footnote-' + footnoteNum;
                        footnote.setAttribute('id', footnoteId);
                        backlink = document.createElement('a');
                        backlink.setAttribute('href', '#' + footnoteId + '-back');
                        backlink.appendChild(document.createTextNode('[' + footnoteNum + ']'));
                        footnote.appendChild(backlink);
                        footnote.appendChild(document.createTextNode(' '));
                        footnote.appendChild(this.trans_span(support.footnote, lang));
                        footnoteArray[footnoteNum] = footnote;
                    }
                }
                footnoteDiv = document.createElement('div');
                footnoteDiv.setAttribute('id', 'wpc-compat-' + resources.data.id + '-footnotes');
                footnoteCnt = footnoteArray.length;
                for (footnoteIdx = 1; footnoteIdx < footnoteCnt; footnoteIdx += 1) {
                    footnoteDiv.appendChild(footnoteArray[footnoteIdx]);
                }
            } else {
                footnoteDiv = null;
            }

            panel.appendChild(tabList);
            panel.appendChild(tabContent);
            if (footnoteDiv) {
                panel.appendChild(footnoteDiv);
            }
            return panel;
        }
        return null;
    },
};
