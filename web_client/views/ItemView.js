import { restRequest } from 'girder/rest';
import ItemView from 'girder/views/body/ItemView';
import { wrap } from 'girder/utilities/PluginUtils';

import RelatedDataWidgetTemplate from '../templates/relatedDataWidget.pug';
import '../stylesheets/relatedDataWidget.styl';

wrap(ItemView, 'initialize', function (initialize, ...args) {
    initialize.apply(this, args);
    const tag = this.model.attributes.name.match(/\d{8}--\d{5}/gm) || [''];
    const q = `"${tag[0]}"`;
    if (q !== '') {
        this._dataRequest = restRequest({
            url: 'resource/search',
            data: {
                q: `"${tag[0]}"`,
                mode: 'text',
                types: JSON.stringify(['item', 'folder']),
                limit: 10
            }
        });
    }
});

wrap(ItemView, 'render', function (render) {
    this.once('g:rendered', function () {
        if (this._dataRequest !== null) {
            this._dataRequest
                .done((results) => {
                    $('.g-item-info').append(RelatedDataWidgetTemplate({
                        items: results.item,
                        folders: results.folder,
                        parentView: this
                    }));
                });
        }
    }, this);

    render.call(this);
    return this;
});
