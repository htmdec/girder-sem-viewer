import cytoscape from 'cytoscape';

import { restRequest } from 'girder/rest';
import View from 'girder/views/View';

import GraphItemTemplate from '../templates/graphItem.pug';
import '../stylesheets/graphItem.styl';

var cyOptions = {
    node: {
        css: false,
        data: true,
        position: true,
        discludeds: []
    },
    edge: {
        css: false,
        data: true,
        discludeds: []
    },
    layoutBy: 'cose' // string of layout name or layout function
};

cytoscape('core', 'graphml', function (cyGraphML) {
    var cy = this;
    var res;

    var importer = function (cy, $, cyOptions, graphStr) {
        function renderNode($graph, $parent) {
            $graph.children('node').each(function () {
                var $node = $(this);

                var settings = {
                    data: {id: $node.attr('id')},
                    css: {},
                    position: {}
                };

                if ($parent !== null) { settings['data']['parent'] = $parent.attr('id'); }

                $node.children('data').each(function () {
                    var $data = $(this);
                    settings['data'][$data.attr('key')] = $data.text();
                });

                cy.add({
                    group: 'nodes',
                    data: settings.data,
                    css: settings.css,
                    position: settings.position
                });

                $node.children('graph').each(function () {
                    var $graph = $(this);

                    renderNode($graph, $node);
                });
            });
        }

        cy.batch(function () {
            const $xml = $($.parseXML(cyGraphML));
            const $graphs = $xml.find('graph').first();

            $graphs.each(function () {
                var $graph = $(this);

                renderNode($graph, null);

                $graph.find('edge').each(function () {
                    var $edge = $(this);

                    var settings = {
                        data: {id: $edge.attr('id'), source: $edge.attr('source'), target: $edge.attr('target')},
                        css: {},
                        position: {}
                    };

                    $edge.find('data').each(function () {
                        var $data = $(this);
                        settings['data'][$data.attr('key')] = $data.text();
                    });

                    cy.add({
                        group: 'edges',
                        data: settings.data,
                        css: settings.css
                    });
                });
            });
            var layoutOptT = typeof cyOptions.layoutBy;
            if (layoutOptT === 'string') { cy.layout({name: cyOptions.layoutBy}).run(); } else if (layoutOptT === 'function') { cyOptions.layoutBy(); }
        });
    };

    switch (typeof cyGraphML) {
        case 'string': // import
            console.log('Importing GraphML...');
            res = importer(cy, $, cyOptions, cyGraphML);
            break;
        case 'object': // set options
            $.extend(true, cyOptions, cyGraphML);
            res = cy;
            break;
        case 'undefined': // export
            console.log("Exporter doesn't work yet.");
            // res = exporter(cy, $, cyOptions);
            break;
        default:
            console.log('Functionality(argument) of .graphml() is not recognized.');
    }

    return res;
});

const GraphItemView = View.extend({
    className: 'g-graph-view',

    initialize: function (settings) {
        this.graphId = settings.graphId;
        var view = this;
        restRequest({
            url: `file/${settings.graphId}/download`
        }).done((resp) => {
            view.graphFile = resp;
            view.render();
        });
    },

    render: function () {
        this.$el.html(GraphItemTemplate({}));
        if (document.getElementById('cy')) {
            var view = this;
            cytoscape({
                container: document.getElementById('cy'),
                style: [
                    {
                        selector: 'node',
                        style: {
                            'background-color': '#666',
                            'label': 'data(id)'
                        }
                    },
                    {
                        selector: 'edge',
                        style: {
                            'width': 3,
                            'line-color': '#ccc',
                            'target-arrow-color': '#ccc',
                            'target-arrow-shape': 'triangle',
                            'curve-style': 'bezier'
                        }
                    }
                ],
                layout: {
                    name: 'grid',
                    rows: 1
                },
                ready: function () {
                    console.log(view.graphFile);
                    this.graphml({layoutBy: 'cose'});
                    this.graphml(view.graphFile);
                }
            });
        }

        return this;
    }
});

export default GraphItemView;
