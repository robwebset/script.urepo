# -*- coding: utf-8 -*-
import sys
import traceback
import xbmc
import xbmcgui
import xbmcaddon
import xbmcvfs

if sys.version_info >= (2, 7):
    import json
else:
    import simplejson as json

# Import the common settings
from resources.lib.settings import log
from resources.lib.settings import Settings
from resources.lib.settings import os_path_split
from resources.lib.settings import os_path_join

ADDON = xbmcaddon.Addon(id='script.urepo')


# Class to handle the creation of dummy addons
class AddonTemplate():
    def __init__(self):
        # Record where the root of all the addons should be
        self.addonRoot = xbmc.translatePath('special://masterprofile').decode("utf-8")
        # This will have got the user data, now get the parent directory of that
        self.addonRoot = os_path_join(os_path_split(self.addonRoot)[0], "addons")
        # Make sure the directory ends in a slash
        self.addonRoot = os_path_join(self.addonRoot, "")
        self.addonTemplate = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<addon id="%s" name="%s" version="0.0.1" provider-name="robwebset">
    <requires>
        <import addon="xbmc.python" version="2.14.0"/>
    </requires>
    <extension point="xbmc.python.script" library="default.py"/>
    <extension point="xbmc.addon.metadata">
        <summary lang="en"></summary>
        <language></language>
        <platform>all</platform>
    </extension>
</addon>
'''

    # Create a dummy entry on disk for a given addon
    def createTemplateAddon(self, addonId, addonName):
        log("AddonTemplate: Creating template for id=%s, name=%s" % (addonId, addonName))

        # Create the correct directory in the addons section on disk
        if not xbmcvfs.exists(self.addonRoot):
            log("AddonTemplate: Addons directory does not exist: %s" % self.addonRoot)
            return

        # Check if the addon directory already exists
        addonDir = os_path_join(self.addonRoot, addonId)
        addonDir = os_path_join(addonDir, "")
        if xbmcvfs.exists(addonDir):
            log("AddonTemplate: Addon directory already exists: %s" % addonDir)
            return

        # Create the addon directory
        if not xbmcvfs.mkdir(addonDir):
            log("AddonTemplate: Failed to create addon directory %s" % addonDir)

        # Create the addon.xml file contents
        addonXml = self.addonTemplate % (addonId, addonName)
        addonXmlLocation = os_path_join(addonDir, "addon.xml")

        # Create the addon.xml file on disk
        try:
            f = xbmcvfs.File(addonXmlLocation, 'w')
            f.write(addonXml)
            f.close()
        except:
            log("AddonTemplate: Failed to create addon.xml file %s (error = %s)" % (addonXmlLocation, traceback.format_exc()))


##################################
# Main of URepo Script
##################################
if __name__ == '__main__':
    log("URepo Script Starting %s" % ADDON.getAddonInfo('version'))

    kodiVersion = Settings.getKodiVersion()

    addonsToInstall = []

    # Make sure the username to link to the URepo repository is set
    username = Settings.getUsername()

    if username in [None, ""]:
        # Show a dialog detailing that the username is not set
        xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001), ADDON.getLocalizedString(32005))
    else:
        # TODO: Make a call to the URepo repository to get the list of addons
        # selected for this user
        urepoAddons = []
        urepoAddons.append('screensaver.random')

        requiredAddons = []

        if len(urepoAddons) > 0:
            existingAddons = []

            # Make the call to find out all the addons that are currently installed
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.GetAddons", "params": { "properties": ["enabled"] }, "id": 1}')
            json_response = json.loads(json_query)

            if ("result" in json_response) and ('addons' in json_response['result']):
                # Check each of the screensavers that are installed on the system
                for addonItem in json_response['result']['addons']:
                    addonId = addonItem['addonid']

                    # Now we are left with only the addon screensavers
                    log("URepo: Detected Installed Addon: %s" % addonId)
                    existingAddons.append(addonId)

            # Remove any addon that is already installed
            for urepoAddon in urepoAddons:
                if urepoAddon in existingAddons:
                    log("URepo: Skipping %s as already installed" % urepoAddon)
                else:
                    requiredAddons.append(urepoAddon)

        if len(requiredAddons) > 0:
            selected = []
            # Display a list of addons that will be installed
            # From Kodi v17 onwards there is an option to pre-select the items in the list
            if kodiVersion > 16:
                # Get the indexes to preselect
                preselectIdxs = []
                for i in range(0, len(requiredAddons)):
                    preselectIdxs.append(i)
                selected = xbmcgui.Dialog().multiselect(ADDON.getLocalizedString(32006), requiredAddons, preselect=preselectIdxs)
            else:
                selected = xbmcgui.Dialog().multiselect(ADDON.getLocalizedString(32006), requiredAddons)

            if (selected in [None, ""]) or (len(selected) < 1):
                log("URepo: Install operation cancelled, no addons to install")
            else:
                # Put together the list of addons to install
                for i in selected:
                    addonsToInstall.append(requiredAddons[i])

    # Perform the install for the required addons
    if len(addonsToInstall) > 0:
        # Now create a template for each addon
        addonTemplate = AddonTemplate()
        for addon in addonsToInstall:
            addonTemplate.createTemplateAddon(addon, addon + " Name")
        del addonTemplate

        # The following call will read in the template addons that were created
        # into the Kodi installation, however they will be marked as disabled
        xbmc.executebuiltin("UpdateLocalAddons", True)

        # Make a call for each addon to enable it as it will have been added as disabled originally
        for addonId in addonsToInstall:
            log("URepo: Enabling addon %s" % addonId)
            xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.SetAddonEnabled", "params": { "addonid": "%s", "enabled": "toggle" }, "id": 1}' % addonId)

        # Now force a refresh of all of the addons so that we get the templates that
        # were created replaced with the real addons
        xbmc.executebuiltin("UpdateAddonRepos", True)

        xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001), ADDON.getLocalizedString(32007))
    log("URepo Script Finished")