import ItemPreviewWidget from './ItemPreviewWidget';

const { wrap } = girder.utilities.PluginUtils;
const HierarchyWidget = girder.views.widgets.HierarchyWidget;

wrap(HierarchyWidget, 'render', function (render) {
    render.call(this);
    if (this.parentModel.resourceName === 'folder' && this._showItems) {
        this.itemPreviewView = new ItemPreviewWidget({
            class: 'g-item-previews-container',
            collection: this.itemListView.collection,
            parentView: this
        });
        this.$el.append(this.itemPreviewView.$el);
        this.itemPreviewView.setCollection(this.itemListView.collection);
        this.itemPreviewView.render();
    }

    return this;
});
