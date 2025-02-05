import $ from 'jquery';

import FilesystemImportTemplate from '../templates/filesystemImport.pug';

const router = girder.router;
const FilesystemImportView = girder.views.body.FilesystemImportView;
const { wrap } = girder.utilities.PluginUtils;

FilesystemImportView.prototype.events['submit .g-filesystem-import-form'] = function (e) {
    e.preventDefault();
    var destId = this.$('#g-filesystem-import-dest-id').val().trim().split(/\s/)[0],
        destType = this.$('#g-filesystem-import-dest-type').val(),
        foldersAsItems = this.$('#g-filesystem-import-leaf-items').val();

    this.$('.g-validation-failed-message').empty();

    this.assetstore.off('g:imported').on('g:imported', function () {
        router.navigate(destType + '/' + destId, {trigger: true});
    }, this).on('g:error', function (resp) {
        this.$('.g-validation-failed-message').text(resp.responseJSON.message);
    }, this).import({
        importPath: this.$('#g-filesystem-import-path').val().trim(),
        leafFoldersAsItems: foldersAsItems,
        destinationId: destId,
        destinationType: destType,
        dataType: this.$('#g-htmdec-data').val(),
        progress: true
    });
};

wrap(FilesystemImportView, 'render', function (render) {
    render.call(this);
    $('.g-filesystem-import-form > .form-group').last().after(FilesystemImportTemplate());
    return this;
});
