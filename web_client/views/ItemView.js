import { restRequest } from 'girder/rest';
import ItemView from 'girder/views/body/ItemView';
import { wrap } from 'girder/utilities/PluginUtils';

import RelatedDataWidgetTemplate from '../templates/relatedDataWidget.pug';
import '../stylesheets/relatedDataWidget.styl';

wrap(ItemView, 'initialize', function (initialize, ...args) {
    initialize.apply(this, args);
    this._dataRequest = null;
    if (this.model.attributes.meta && this.model.attributes.meta['jhu_id']) {
        const tag = this.model.attributes.meta['jhu_id'];
        // Restrict search to items/folders in the same collection
        const filters = {
            baseParentId: this.model.attributes.baseParentId,
            baseParentType: this.model.attributes.baseParentType
        };
        this._dataRequest = restRequest({
            url: 'resource/search',
            data: {
                q: tag,
                mode: 'jhuId',
                types: JSON.stringify(['item', 'folder']),
                filters: JSON.stringify(filters),
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
                    const dsItems = results.item.map((obj) => {
                        return {itemId: obj._id, mountPath: `/${obj.name}`, _modelType: 'item'};
                    });
                    const dsFolders = results.folder.map((obj) => {
                        return {itemId: obj._id, mountPath: `/${obj.name}`, _modelType: 'folder'};
                    });
                    const dataSet = dsItems.concat(dsFolders);
                    const subDomain = window.location.hostname.split('.')[0];
                    // TODO: get from settings
                    const dashboardUrl = window.location.origin.replace(subDomain, 'dashboard') + '/mine';
                    const params = new URLSearchParams();
                    params.set('name', 'My Tale');
                    params.set('asTale', false);
                    params.set('dataSet', JSON.stringify(dataSet));
                    document.querySelector('#ainwt').href = `${dashboardUrl}?${params.toString()}`;
                });
        }
    }, this);

    render.call(this);
    return this;
});
