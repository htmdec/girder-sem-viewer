### SEM Data Viewer

A girder plugins that enable TIFF and metadata preview for SEM data represented as a single Item.

![Example SEM Data Viewer](sem_viewer.png)

### How to test?

1. Install plugin (see Note below if you're using WholeTale dev deployment)
1. Log in to Girder
1. Navigate to your personal folders (`login` > "My folders" in navbar)
1. Create a Folder "test" (user icon + caret down on top right, select "Create folder here")
1. Click on "test" folder
1. From folder actions menu (folder icon + caret down on top right) select "Create item here".
1. Create item "test.tiff"
1. Click on "test.tiff"
1. Click on green upload button. In the "Upload files" modal click on "Browse or drop files here" button.
1. In the "Open Files" modal, select SEM tiff and correspoding header using mouse and holding CTRL button. Click "Open"
1. Back in the "Upload files" modal confirm "Selected 2 files" message is present. Click "Start Upload" button.
1. After files are uploaded successfully, click on "+" button in the "Metadata" panel. Select "Simple"
1. In the Key field type `sem`, and in the Value field type `true`. Click on a blue button with a white checkmark.
1. Refresh the page.

### Note

Following changes to `whole-tale/deploy-dev` are currently required:

```diff
--- a/Makefile
+++ b/Makefile
@@ -1,6 +1,7 @@
 .PHONY: clean dirs dev images gwvolman_src wholetale_src dms_src home_src sources \
        rebuild_dashboard watch_dashboard \
-       restart_worker restart_girder globus_handler_src status update_src
+       restart_worker restart_girder globus_handler_src status update_src \
+       sem_viewer_src

 SUBDIRS = src volumes/ps volumes/workspaces volumes/homes volumes/base volumes/versions volumes/runs volumes/licenses volumes/mountpoints
 TAG = latest
@@ -47,7 +48,10 @@ src/globus_handler:
 src/ngx-dashboard:
        git clone https://github.com/whole-tale/ngx-dashboard src/ngx-dashboard

-sources: src src/gwvolman src/wholetale src/wt_data_manager src/wt_home_dir src/globus_handler src/girderfs src/ngx-dashboard src/virtual_resources src/wt_versioning
+src/sem_viewer:
+       git clone https://github.com/htmdec/sem_viewer src/sem_viewer
+
+sources: src src/gwvolman src/wholetale src/wt_data_manager src/wt_home_dir src/globus_handler src/girderfs src/ngx-dashboard src/virtual_resources src/wt_versioning src/sem_viewer

 dirs: $(SUBDIRS)

@@ -67,7 +71,7 @@ dev: services
        done; \
        true
        docker exec -ti $$(docker ps --filter=name=wt_girder -q) girder-install plugin plugins/wt_data_manager plugins/wholetale plugins/wt_home_dir plugins/globus_handler plugins/virtual_resources plugins/wt_versioning
-       docker exec -ti $$(docker ps --filter=name=wt_girder -q) girder-install web --dev --plugins=oauth,gravatar,jobs,worker,wt_data_manager,wholetale,wt_home_dir,globus_handler
+       docker exec -ti $$(docker ps --filter=name=wt_girder -q) girder-install web --dev --plugins=oauth,gravatar,jobs,worker,wt_data_manager,wholetale,wt_home_dir,globus_handler,sem_viewer
        docker exec --user=root -ti $$(docker ps --filter=name=wt_girder -q) pip install -r /gwvolman/requirements.txt -e /gwvolman
        docker exec --user=root -ti $$(docker ps --filter=name=wt_girder -q) pip install -e /girderfs
        ./setup_girder.py
--- a/setup_girder.py
+++ b/setup_girder.py
@@ -67,6 +67,7 @@ plugins = [
     "wholetale",
     "wt_home_dir",
     "wt_versioning",
+    "sem_viewer",
 ]
 r = requests.put(
     api_url + "/system/plugins",
```
