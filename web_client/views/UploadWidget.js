// Description: UploadWidget.js

import $ from 'jquery';
import _ from 'underscore';

import FileModel from 'girder/models/FileModel';
import FolderModel from 'girder/models/FolderModel';
import HierarchyWidget from 'girder/views/widgets/HierarchyWidget';
import UploadWidget from 'girder/views/widgets/UploadWidget';
import { getCurrentUser } from 'girder/auth';
import { AccessType } from 'girder/constants';
import { formatSize } from 'girder/misc';
import { wrap } from 'girder/utilities/PluginUtils';
import { restRequest } from 'girder/rest';

import '../stylesheets/uploadWidget.styl';

function getSubdirectoryPrefix(file) {
    const parts = file.webkitRelativePath.split('/');
    return parts.length > 1 ? parts.slice(0, -1).join('/') + '/' : '';
}

function groupFilesBySubdirectory(fileList) {
    // Convert FileList to array
    const files = Array.from(fileList);

    // Create a map to store grouped files
    const groupedFiles = new Map();

    // Sort files based on their subdirectory prefix
    files.sort((file1, file2) => {
        const prefix1 = getSubdirectoryPrefix(file1);
        const prefix2 = getSubdirectoryPrefix(file2);
        return prefix1.localeCompare(prefix2);
    });

    // Group files by common subdirectory prefix
    files.forEach((file) => {
        const subdirectoryPrefix = getSubdirectoryPrefix(file);
        if (!groupedFiles.has(subdirectoryPrefix)) {
            groupedFiles.set(subdirectoryPrefix, []);
        }
        groupedFiles.get(subdirectoryPrefix).push(file);
    });

    // Convert map values to an array of arrays (groups)
    return Array.from(groupedFiles.values());
}

wrap(UploadWidget, 'render', function (render) {
    this.parentType = this.parent.attributes._modelType;
    render.call(this);
    if (this.parentType !== 'item') {
        var uploadFolder = '<div class="g-upload-folder"><i class="icon-folder-open"></i>Select a folder to upload</div>';
        uploadFolder += '<div class="form-group hide"><input type="file" id="folderInput" webkitdirectory multiple></div>';
        this.$('.g-drop-zone').after(uploadFolder);
    }
    if (this.parentType === 'user' || this.parentType === 'collection') {
        this.$('.g-drop-zone').addClass('hide');
    }
    return this;
});

wrap(UploadWidget, 'events', function (events) {
    this.events['submit #g-upload-form'] = function (e) {
        e.preventDefault();
        this.$('.g-upload-folder').addClass('hide');
        this.startUpload();
    };

    this.events['click .g-resume-upload'] = function () {
        this.$('.g-upload-error-message').html('');
        this.currentFile.resumeUpload();
    };
    this.events['click .g-restart-upload'] = function () {
        this.$('.g-upload-error-message').html('');
        this.uploadNextFile();
    };
    this.events['change #g-files'] = function () {
        var files = this.$('#g-files')[0].files;

        if (files.length) {
            this.files = files;
            this.filesChanged();
        }
    };
    this.events['click .g-drop-zone'] = function () {
        this.$('#g-files').click();
    };
    this.events['dragenter .g-drop-zone'] = function (e) {
        e.stopPropagation();
        e.preventDefault();
        e.originalEvent.dataTransfer.dropEffect = 'copy';
        this.$('.g-drop-zone')
            .addClass('g-dropzone-show')
            .html('<i class="icon-bullseye"/> Drop files here');
    };
    this.events['dragleave .g-drop-zone'] = function (e) {
        e.stopPropagation();
        e.preventDefault();
        this.$('.g-drop-zone')
            .removeClass('g-dropzone-show')
            .html('<i class="icon-docs"/> Browse or drop files');
    };
    this.events['dragover .g-drop-zone'] = function (e) {
        var dataTransfer = e.originalEvent.dataTransfer;
        if (!dataTransfer) {
            return;
        }
        // The following two lines enable drag and drop from the chrome download bar
        var allowed = dataTransfer.effectAllowed;
        dataTransfer.dropEffect = (allowed === 'move' || allowed === 'linkMove') ? 'move' : 'copy';

        e.preventDefault();
    };
    this.events['drop .g-drop-zone'] = 'filesDropped';
    this.events['click .g-upload-folder'] = function () {
        this.$('#folderInput').click();
    };
    this.events['change #folderInput'] = function () {
        var files = this.$('#folderInput')[0].files;
        if (files.length > 0) {
            this.files = files;
            this.filesChanged();
        }
    };
    return this.events;
});

wrap(UploadWidget, 'uploadNextFile', function (uploadNextFile) {
    const groupedFiles = groupFilesBySubdirectory(this.files);
    if (groupedFiles.length === 1) {
        uploadNextFile.call(this);
    } else {
        this.totalFiles = this.files.length;
        this.groupedFiles = groupedFiles;
        this.currentDirIndex = 0;
        this.uploadNextFileRecursive();
    }
});

wrap(UploadWidget, 'uploadNextFileRecursive', function (uploadNextFileRecursive) {
    this.files = this.groupedFiles[this.currentDirIndex];
    this._currentDirFileIndex = 0;
    this._currentDirTotalFiles = this.files.length;
    const folder = getSubdirectoryPrefix(this.files[0]).slice(0, -1);

    if (this.currentDirIndex >= this.groupedFiles.length) {
        if (this.modal) {
            this.$el.modal('hide');
        }
        this.trigger('g:uploadFinished', {
            files: [].concat(...this.groupedFiles),
            totalFiles: this.totalFiles
        });
        return;
    }

    var widget = this;

    restRequest({
        url: 'folder/recursive',
        method: 'POST',
        data: {
            parentId: this.parent.id,
            parentType: this.parentType,
            path: folder
        }
    }).done(function (result) {
        var currentFolder = new FolderModel();
        currentFolder.set(result);
        widget._uploadNext(currentFolder);
    });
});

wrap(UploadWidget, '_uploadNext', function (_uploadNext, currentFolder) {
    if (this._currentDirFileIndex >= this._currentDirTotalFiles) {
        return;
    }
    this.currentFile = new FileModel();
    this.currentFile.on('g:upload.complete', function () {
        this.files[this._currentDirFileIndex].id = this.currentFile.id;
        this._currentDirFileIndex += 1;
        if (this._currentDirFileIndex < this._currentDirTotalFiles) {
            this._uploadNext(currentFolder);
        } else {
            this.currentDirIndex += 1;
            if (this.currentDirIndex < this.groupedFiles.length) {
                this.uploadNextFileRecursive();
            } else {
                if (this.modal) {
                    this.$el.modal('hide');
                }
                this.trigger('g:uploadFinished', {
                    files: [].concat(...this.groupedFiles),
                    totalFiles: this.totalFiles
                });
            }
        }
    }, this).on('g:upload.chunkSent', function (info) {
        this.overallProgress += info.bytes;
    }, this).on('g:upload.progress', function (info) {
        var currentProgress = info.startByte + info.loaded;
        this.$('.g-progress-current>.progress-bar').css('width',
            Math.ceil(100 * currentProgress / info.total) + '%');
        this.$('.g-progress-overall>.progress-bar').css('width',
            Math.ceil(100 * (this.overallProgress + info.loaded) / this.totalSize) + '%');
        this.$('.g-current-progress-message').html(
            '<i class="icon-doc-text"/>' + (this.currentIndex + 1) + ' of ' +
            this.files.length + ' - <b>' + info.file.name + '</b>: ' +
            formatSize(currentProgress) + ' / ' +
            formatSize(info.total)
        );
        this.$('.g-overall-progress-message').html('Overall progress: ' +
            formatSize(this.overallProgress + info.loaded) + ' / ' +
            formatSize(this.totalSize));
    }, this).on('g:upload.error', function (info) {
        var html = info.message + ' <a class="g-resume-upload">' +
            'Click here to resume the upload</a>';
        $('.g-upload-error-message').html(html);
    }, this).on('g:upload.errorStarting', function (info) {
        var html = info.message + ' <a class="g-restart-upload">' +
            'Click here to restart the upload</a>';
        $('.g-upload-error-message').html(html);
    }, this);

    var otherParams = this.otherParams;
    if (_.isFunction(this.otherParams)) {
        otherParams = this.otherParams(this);
    }
    this.currentFile.upload(currentFolder, this.files[this._currentDirFileIndex], null, otherParams);
});

wrap(HierarchyWidget, 'render', function (render) {
    const accessLevel = this.parentModel.getAccessLevel();
    const user = getCurrentUser();
    const resourceType = this.parentModel.resourceName;

    const button = `<button
                      class="g-upload-here-button btn btn-sm btn-success"
                      title="Upload here">
                      <i class="icon-upload"></i>
                    </button>`;

    render.call(this);
    const folderHeader = this.$('.g-folder-header-buttons');
    if (user && resourceType === 'collection' && accessLevel >= AccessType.WRITE && folderHeader.length > 0) {
        this.$('.g-collection-info-button').after(button);
    }
    if (user && resourceType === 'user' && accessLevel >= AccessType.WRITE) {
        folderHeader.prepend(button);
    }
});
