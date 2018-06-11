// ==UserScript==
// @name        Better labels.
// @include     /^https://github\.com/.+/.+/issues/[0-9]+$/
// @require     http://code.jquery.com/jquery-latest.js
// @grant       GM_xmlhttpRequest
// ==/UserScript==

const ElementFactory = {
    blackOrWhite: (hex) => {
        var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        var red = parseInt(result[1], 16);
        var green = parseInt(result[2], 16);
        var blue = parseInt(result[3], 16);

        if ((red*0.299 + green*0.587 + blue*0.114) > 186) {
            return '#000000';
        }
        else {
            return '#ffffff';
        }
    },

    sidebar: (issue) => {
        var sidebarHTML = '<div class="discussion-sidebar-item">' +
            '<button type="button" id="bl-button" class="discussion-sidebar-heading discussion-sidebar-toggle ' +
            'js-menu-target" data-hotkey="b">' +
            '<svg class="octicon octicon-gear" viewBox="0 0 14 16" version="1.1" width="14" height="16" aria-hidden="true"><path fill-rule="evenodd" d="M14 8.77v-1.6l-1.94-.64-.45-1.09.88-1.84-1.13-1.13-1.81.91-1.09-.45-.69-1.92h-1.6l-.63 1.94-1.11.45-1.84-.88-1.13 1.13.91 1.81-.45 1.09L0 7.23v1.59l1.94.64.45 1.09-.88 1.84 1.13 1.13 1.81-.91 1.09.45.69 1.92h1.59l.63-1.94 1.11-.45 1.84.88 1.13-1.13-.92-1.81.47-1.09L14 8.75v.02zM7 11c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3z"></path></svg>' +
            'Better Labels' +
            '</button>' +
            '<div id="bl-selector" class="select-menu label-select-menu"> ' +
            '<div class="select-menu-modal-holder" > ' +
            '<div class="select-menu-modal">' +
            '<div class="select-menu-header">' +
            '<div class="select-menu-title">' +
            'Apply better labels to this issue' +
            '</div>' +
            '</div>' +

            '<div class="select-menu-filters">' +
            '<div class="select-menu-text-filter">' +
            '<input type="text" id="label-filter-field" class="form-control js-label-filter-field js-filterable-field js-navigation-enable" placeholder="Filter or create labels" autocomplete="off">' +
            '</div>' +
            '</div>' +

            '<div class="select-menu-list" id="bl-labels">' +
            '</div>' +
            '</div>' +
            '</div>' +
            '</div>' +
            '<div id="bl-issue-labels" class="labels css-truncate"></div>' +
            '</div>';

        var sidebar = jQuery(sidebarHTML);
        var selector = sidebar.find('#bl-selector');
        var button = sidebar.find('#bl-button');
        button.click(function() {
            if (selector.hasClass('active')) {
                selector.removeClass('active');
            }
            else {
                LabelsAPI.getLabelsForIssue(issue)
                    .then((labels) => {
                    var label_ids = labels.map((label) => { return label.id; });
                    selector.find('.select-menu-item').each((_, selectorLabel) => {
                        if (label_ids.indexOf(selectorLabel.id) > -1) {
                            jQuery(selectorLabel).addClass('selected');
                        }
                        else {
                            jQuery(selectorLabel).removeClass('selected');
                        }
                    });
                    selector.addClass('active');
                });
            }
        });

        return sidebar;
    },

    selectorLabel: (label) => {
        var bgcolor = label.fields.color || 'lightgray';
        var fgcolor = label.fields.fgcolor || ElementFactory.blackOrWhite(bgcolor);
        var name = label.fields.displayName || label.name;
        var description = label.fields.description || '';
        var selectorLabel = jQuery('<div class="select-menu-item" id="' + label.id + '">' +
                                   '<div class="select-menu-item-text">' +
                                   '<svg class="octicon octicon-check select-menu-item-icon" viewBox="0 0 12 16" version="1.1" width="12" height="16" aria-hidden="true"><path fill-rule="evenodd" d="M12 5l-8 8-4-4 1.5-1.5L4 10l6.5-6.5L12 5z"></path></svg>' +
                                   '<div class="float-left color mr-2" style="margin-top: 2px; background-color: ' + bgcolor + '"></div>' +
                                   '<div>' +
                                   '<span class="name">' + name + '</span>' +
                                   '<div class="description d-block text-gray css-truncate-target m-0">' + description + '</div>' +
                                   '</div>' +
                                   '</div>' +
                                   '</div>');
        return selectorLabel;
    },

    issueLabel: (label) => {
        var bgcolor = label.fields.color || 'lightgray';
        var fgcolor = label.fields.fgcolor || ElementFactory.blackOrWhite(bgcolor);
        var name = label.fields.displayName || label.name;
        var description = label.fields.description || name;
        var category = label.fields.category ? ('<span style="font-weight: 100; font-variant: small-caps;">' + label.fields.category + ': ' + '</span>') : '';
        var issueLabel= jQuery('#bl-issue-labels').append('<a title="' + description + '" class="sidebar-labels-style box-shadow-none width-full d-block ' +
                                                          'IssueLabel v-align-text-top" style="background-color: ' + bgcolor + '; ' +
                                                          'color: ' + fgcolor + '; margin-top: 3px;">' + category + name + '</a>');
        return issueLabel;
    }
};

const LabelsAPI = {

    compareLabels: (labelA, labelB) => {
        var categoriesOrder = [
            'impact',
            'category',
            'bug_type',
            'bug_cause',
            'functional_area',
            'info',
            'epic'
            ];
        if (categoriesOrder.indexOf(labelA.fields.category) < categoriesOrder.indexOf(labelB.fields.category)) return -1;
        if (categoriesOrder.indexOf(labelA.fields.category) > categoriesOrder.indexOf(labelB.fields.category)) return 1;
        if(labelA.name < labelB.name) return -1;
        if(labelA.name > labelB.name) return 1;
        return 0;
    },

    getLabels: () => {
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: 'GET',
                url: 'https://3iplbb6gp0.execute-api.us-east-1.amazonaws.com/dev/labels',
                onload: function(response) {
                    var labels = JSON.parse(response.responseText);
                    labels.sort(LabelsAPI.compareLabels);
                    resolve(labels);
                },
                onerror: function() {
                    reject();
                }
            });
        });
    },

    getLabelsForIssue: (issue) => {
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: 'GET',
                url: 'https://3iplbb6gp0.execute-api.us-east-1.amazonaws.com/dev/' + issue + '/labels',
                onload: function(response) {
                    var labels = JSON.parse(response.responseText).labels;
                    labels.sort(LabelsAPI.compareLabels);
                    resolve(labels);
                },
                onerror: function() {
                    reject();
                }
            });
        });
    },

    addLabelToIssue: (issue, label) => {
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: 'POST',
                headers: {"Content-Type": "application/json"},
                url: 'https://3iplbb6gp0.execute-api.us-east-1.amazonaws.com/dev/' + window.location.pathname + '/labels',
                data: JSON.stringify([label.id]),
                onload: (response) => {
                    resolve(response);
                },
                onerror: () => {
                    reject();
                }
            });
        });
    },

    removeLabelFromIssue: (issue, label) => {
        return new Promise((resolve, reject) => {
            GM_xmlhttpRequest({
                method: 'DELETE',
                headers: {"Content-Type": "application/json"},
                url: 'https://3iplbb6gp0.execute-api.us-east-1.amazonaws.com/dev/' + window.location.pathname + '/labels/' + label.id,
                data: JSON.stringify([label.id]),
                onload: (response) => {
                    resolve(response);
                },
                onerror: () => {
                    reject();
                }
            });
        });
    }

};


(function() {
    'use strict';

    jQuery(document).ready(function() {

        var issue = window.location.pathname;

        var sidebar = ElementFactory.sidebar(issue);
        jQuery('#partial-discussion-sidebar').prepend(sidebar);
        LabelsAPI.getLabels().then((labels) => {
            labels.forEach(function(label) {
                var selectorLabel = ElementFactory.selectorLabel(label);
                sidebar.find('#bl-labels').append(selectorLabel);
                selectorLabel.click(function() {
                    if (jQuery(selectorLabel).hasClass('selected')) {
                        LabelsAPI.removeLabelFromIssue(issue, label)
                       .then((success) => {
                            jQuery(selectorLabel).removeClass('selected');
                        });
                    }
                    else {
                        LabelsAPI.addLabelToIssue(issue, label)
                        .then((success) => {
                            jQuery(selectorLabel).addClass('selected');
                        });
                    }
                });
            });
        });

        LabelsAPI.getLabelsForIssue(window.location.pathname)
            .then((labels) => {
                labels.forEach(function(label) {
                    sidebar.find('#bl-issue-labels').append(ElementFactory.issueLabel(label));
                });
        });
    });
})();
