import Tiff from 'tiff.js';
// import { ConfigIniParser } from "config-ini-parser";
import { restRequest } from 'girder/rest';
import View from 'girder/views/View';
import FileCollection from 'girder/collections/FileCollection';

import SemItemTemplate from '../templates/semItem.pug';
import '../stylesheets/semItem.styl';
import SemMetadataTemplate from '../templates/semMetadata.pug';
import '../stylesheets/semMetadata.styl';

const ConfigIniParser = require('config-ini-parser').ConfigIniParser;

const SemItemView = View.extend({
    className: 'g-sem-view',

    initialize: function (settings) {
        this._semImageView = null;
        this._semMetadataView = null;

        this.collection = new FileCollection();
        this.collection.altUrl = 'item/' +
            (settings.itemId || settings.item.get('_id')) + '/files';
        this.collection.append = true;

        var view = this;

        this.collection.on('g:changed', function () {
            const files = this.toArray();
            restRequest({
                url: `file/${files[0].id}/download`,
                xhrFields: {
                    responseType: 'arraybuffer'
                }
            }).done((resp) => {
                Tiff.initialize({
                    TOTAL_MEMORY: 100000000
                });
                const dataView = new Tiff({buffer: resp});
                const canvas = dataView.toCanvas();
                view.image = canvas.toDataURL('image/jpeg', 0.8);
                view.trigger('g:tiffLoaded');
            });
            restRequest({
                url: `item/${settings.item.id}/tiff_metadata`,
            }).done((resp) => {
                const parser = new ConfigIniParser('\r\n');
                parser.parse(resp);
                view.config = parser;
                view.trigger('g:configLoaded');
            });
        }).fetch({ itemId: settings.item.id });
        this.listenTo(this, 'g:tiffLoaded', this.render);
    },

    render: function () {
        this.$el.html(SemItemTemplate({}));
        this._semImageView = new SemImageWidget({
            el: this.$('.g-sem-image'),
            parentView: this
        });
        this._semMetadataView = new SemMetadataWidget({
            el: this.$('.g-sem-tags'),
            parentView: this
        });

        this._semImageView.render();
        this._semMetadataView.render();

        return this;
    }
});

const SemImageWidget = View.extend({
    className: 'g-sem-image',

    initialize: function (settings) {
        this.listenTo(this.parentView, 'g:tiffLoaded', this.render);
    },

    render: function () {
        var $image = this.$('div > img');
        if (this.parentView.image) {
            $image[0].src = this.parentView.image;
            $image[0].width = 768;
        }
        return this;
    }

});

const SemMetadataWidget = View.extend({
    className: 'g-sem-tags',

    initialize: function (settings) {
        this.listenTo(this.parentView, 'g:configLoaded', this.render);
    },

    render: function () {
        const config = [];
        if (this.parentView.config) {
            this.parentView.config.sections().forEach((section) => {
                var sec = {'name': section, 'data': {}};
                this.parentView.config.items(section).forEach((obj) => {
                    sec.data[obj[0]] = obj[1];
                });
                config.push(sec);
            });

            this.$el.html(SemMetadataTemplate({
                config: config
            }));
        }
        return this;
    }

});

export default SemItemView;
