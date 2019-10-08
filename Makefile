# Add ISO code for any locales you want to support here (space separated)
LOCALES = fr
# Name of the plugin, for the ZIP file
PLUGINNAME = LayerBoard

help:
	$(MAKE) -C qgis_plugin_tools help

docker_test:
	$(MAKE) -C qgis_plugin_tools docker_test PLUGINNAME=$(PLUGINNAME)

i18n_%:
	$(MAKE) -C qgis_plugin_tools i18n_$* LOCALES=$(LOCALES)

deploy_%:
	$(MAKE) -C qgis_plugin_tools deploy_$* PLUGINNAME=$(PLUGINNAME)