import VegaWidget from './VegaWidget';
import RelatedDataWidgetTemplate from '../templates/relatedDataWidget.pug';
import '../stylesheets/relatedDataWidget.styl';

const { restRequest } = girder.rest;
const ItemView = girder.views.body.ItemView;
const { wrap } = girder.utilities.PluginUtils;

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
                    girder.$('.g-item-info').append(RelatedDataWidgetTemplate({
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

    this.model.getAccessLevel((accessLevel) => {
        // Because the passthrough call to render() also does an async call to
        // getAccessLevel(), wait until this one completes before invoking that
        // one.
        //
        // Furthermore, we need to call this *first*, because of how the Vega
        // view inserts itself into the app-body-container, which doesn't seem
        // to exist until the passthrough call is made.
        render.call(this);

        this.vegaWidget = new VegaWidget({
            item: this.model,
            accessLevel: accessLevel,
            parentView: this
        });
    });

    return this;
});
