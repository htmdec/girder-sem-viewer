import { parse, View as VegaView } from 'vega';
import { compile } from 'vega-lite';

const $ = girder.$;
const _ = girder._;
const { restRequest } = girder.rest;
const View = girder.views.View;
const { AccessType } = girder.constants;

import VegaWidgetTemplate from '../templates/vegaWidget.pug';
import '../stylesheets/vegaWidget.styl';

var VegaWidget = View.extend({
    initialize: function (settings) {
        this.item = settings.item;
        this.accessLevel = settings.accessLevel;
        this.item.on('change', function () {
            this.render();
        }, this);
        this.render();
    },

    render: function () {
        var meta = this.item.get('meta');

        if (this.accessLevel >= AccessType.READ && meta && meta.vega) {
            $(VegaWidgetTemplate()).insertBefore('#g-app-body-container .g-item-metadata');
            restRequest({
                url: `item/${this.item.id}/download`
            })
                .done(_.bind(function (data) {
                    const vegaSpec = JSON.parse(meta.vega);
                    // Check for two extra keys: 'vega:separator' and 'vega:skipRows'
                    // to determine how to parse the data, pop them out of the
                    // meta object so they don't interfere with the Vega spec
                    const skipRows = parseInt(meta['vega:skipRows'] || '1', 10);
                    const separator = meta['vega:separator'] || ',';
                    const parsedData = data.split('\n').slice(skipRows).map(row => {
                      const [x, y] = row.split(separator);
                      return {x: parseFloat(x), y: parseFloat(y)};
                    });

                    const spec = {...vegaSpec, data: {values: parsedData}};
                    let runtime = parse(compile(spec).spec);
                    let view = new VegaView(runtime)
                        .initialize($('.g-item-vega-vis')[0])
                        .renderer('svg');
                    view.run();
                }, this));
        } else {
            $('.g-item-vega')
                .remove();
        }

        return this;
    }
});

export default VegaWidget;
