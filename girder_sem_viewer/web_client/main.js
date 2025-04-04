// Extends and overrides API

import SemItemView from './views/SemView';
import GraphItemView from './views/GraphView';
import './views/HierarchyWidget';
import './views/FilesystemImportView';
import './views/ItemView';
import './views/UploadWidget';

const { wrap } = girder.utilities.PluginUtils;
const ItemView = girder.views.body.ItemView;
const SearchFieldWidget = girder.views.widgets.SearchFieldWidget;


wrap(ItemView, 'render', function (render) {
    this.once('g:rendered', () => {
        if (this.model.attributes.name.endsWith('.tif') || this.model.attributes.name.endsWith('.tiff')) {
            new SemItemView({
                parentView: this,
                item: this.model
            })
                .render()
                .$el.insertAfter(this.$('.g-item-info'));
        }
        if (this.model.attributes.meta && this.model.attributes.meta.graphml) {
            new GraphItemView({
                parentView: this,
                graphId: this.model.attributes.meta.graphml
            })
                .render()
                .$el.insertAfter(this.$('.g-item-info'));
        }
    });
    return render.call(this);
});

SearchFieldWidget.addMode(
    'jhuId',
    ['item', 'folder'],
    'Search by JHU ID',
    'You are searching for all data collected for a specific JHU ID. (e.g. F138-R2C7)'
);
