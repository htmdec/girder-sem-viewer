// Extends and overrides API
import { wrap } from 'girder/utilities/PluginUtils';

import ItemView from 'girder/views/body/ItemView';
import SearchFieldWidget from 'girder/views/widgets/SearchFieldWidget';

import SemItemView from './views/SemView';
import './views/FilesystemImportView';
import './views/ItemView';

wrap(ItemView, 'render', function (render) {
    this.once('g:rendered', () => {
        if (this.model.attributes.name.endsWith('.tif')) {
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

SearchFieldWidget.addMode(
  "jhuId",
  ["item", "folder"],
  "Search by JHU ID",
  'You are searching for all data collected for a specific JHU ID. (e.g. F138-R2C7)'
);
