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
                    const parsedData = data.split('\n').slice(1).map(row => {
                      const [x, y] = row.split(',');
                      return {x: parseFloat(x), y: parseFloat(y)};
                    });
                    const vegaSpec = JSON.parse(meta.vega);
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
