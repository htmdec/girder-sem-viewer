// Extends and overrides API
import { wrap } from 'girder/utilities/PluginUtils';

import ItemView from 'girder/views/body/ItemView';

import SemItemView from './views/SemView';
import './views/FilesystemImportView';
import './views/ItemView';

wrap(ItemView, 'render', function (render) {
    this.once('g:rendered', () => {
        if (this.model.has('meta') && Boolean(this.model.attributes.meta.sem)) {
            new SemItemView({
                parentView: this,
                item: this.model
            })
                .render()
                .$el.insertAfter(this.$('.g-item-info'));
        }
    });
    return render.call(this);
});
