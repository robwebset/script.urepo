# -*- coding: utf-8 -*-
import sys
import traceback
import base64
import urllib2
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

ADDON = xbmcaddon.Addon(id='script.urepo.helper')


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
            return False

        # Check if the addon directory already exists
        addonDir = os_path_join(self.addonRoot, addonId)
        addonDir = os_path_join(addonDir, "")
        if xbmcvfs.exists(addonDir):
            log("AddonTemplate: Addon directory already exists: %s" % addonDir)
            return False

        # Create the addon directory
        if not xbmcvfs.mkdir(addonDir):
            log("AddonTemplate: Failed to create addon directory %s" % addonDir)
            return False

        # Create the addon.xml file contents
        addonXml = self.addonTemplate % (addonId, addonName)
        addonXmlLocation = os_path_join(addonDir, "addon.xml")

        # Create the addon.xml file on disk
        try:
            f = xbmcvfs.File(addonXmlLocation, 'wb')
            f.write(str(addonXml))
            f.close()
        except:
            log("AddonTemplate: Failed to create addon.xml file %s (error = %s)" % (addonXmlLocation, traceback.format_exc()))
            return False

        return True


# Class to retrieve data from URepo
class URepo():
    def __init__(self, defaultUsername):
        self.url_prefix = base64.b64decode('aHR0cDovL3d3dy51cmVwby5vcmcvYXBpL3YxL2pzb24vMjU4OS8=')
        self.username = defaultUsername

    def getAddonCollection(self):
        collectionUrl = "%suser.php?user=%s" % (self.url_prefix, self.username)

        collection = []

        # Make the call to theaudiodb.com
        json_details = self._makeCall(collectionUrl)

        if json_details not in [None, ""]:
            json_response = json.loads(json_details)

            # The results of the search come back as an array of entries
            if 'addons' in json_response:
                for addon in json_response['addons']:
                    addonId = addon['idAddonKodi']
                    # Skip the URepo helper addon, we don't want to install ourself
                    if addonId in [None, "", "script.urepo.helper"]:
                        continue
                    log("URepo: Addon collection: %s" % addonId)
                    addonDetails = {'id': addonId, 'name': addon['strAddon']}
                    collection.append(addonDetails)

        return collection

    # Perform the API call
    def _makeCall(self, url):
        log("makeCall: Making query using %s" % url)
        resp_details = None
        try:
            req = urllib2.Request(url)
            req.add_header('Accept', 'application/json')
            req.add_header('User-Agent', 'Kodi Browser')
            response = urllib2.urlopen(req)
            resp_details = response.read()
            try:
                response.close()
                log("makeCall: Request returned %s" % resp_details)
            except:
                pass
        except:
            log("makeCall: Failed to retrieve details from %s: %s" % (url, traceback.format_exc()))

        return resp_details


##################################
# Main of URepo Script
##################################
if __name__ == '__main__':
    log("URepo Script Starting %s" % ADDON.getAddonInfo('version'))

    kodiVersion = Settings.getKodiVersion()

    # Make sure the username to link to the URepo repository is set
    username = Settings.getUsername()

    urepoInstalled = False

    if username in [None, ""]:
        # Show a dialog detailing that the username is not set
        xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001), ADDON.getLocalizedString(32005))
    else:
        # Make sure the URepo repository is installed - otherwise things do not work
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.GetAddonDetails", "params": { "addonid": "repository.urepo", "properties": ["enabled", "broken", "name", "author"]  }, "id": 1}')
        json_response = json.loads(json_query)

        if ("result" in json_response) and ('addon' in json_response['result']):
            addonItem = json_response['result']['addon']
            if (addonItem['enabled'] is True) and (addonItem['broken'] is False) and (addonItem['type'] == 'xbmc.addon.repository') and (addonItem['addonid'] == 'repository.urepo'):
                urepoInstalled = True

        if not urepoInstalled:
            xbmcgui.Dialog().ok(ADDON.getLocalizedString(32001), ADDON.getLocalizedString(32008))

    addonsToInstall = []

    if urepoInstalled:
        try:
            xbmc.executebuiltin("ActivateWindow(busydialog)")

            # Make a call to the URepo repository to get the list of addons
            # selected for this user
            urepo = URepo(username)
            urepoAddons = urepo.getAddonCollection()
            del urepo

            requiredAddons = []

            if len(urepoAddons) > 0:
                existingAddons = []

                # Make the call to find out all the addons that are currently installed
                json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.GetAddons", "params": { "properties": ["enabled"] }, "id": 1}')
                json_response = json.loads(json_query)

                if ("result" in json_response) and ('addons' in json_response['result']):
                    # Check each of the addons that are installed on the system
                    for addonItem in json_response['result']['addons']:
                        addonId = addonItem['addonid']
                        log("URepo: Detected Installed Addon: %s" % addonId)
                        existingAddons.append(addonId)

                # Remove any addon that is already installed
                for urepoAddon in urepoAddons:
                    if urepoAddon['id'] in existingAddons:
                        log("URepo: Skipping %s as already installed" % urepoAddon['id'])
                    else:
                        requiredAddons.append(urepoAddon)
        finally:
            xbmc.executebuiltin("Dialog.Close(busydialog)")

        if len(requiredAddons) > 0:
            selected = []
            # Extract the display name
            displayList = []
            for anAddon in requiredAddons:
                displayList.append(anAddon['name'])

            # Display a list of addons that will be installed
            # From Kodi v17 onwards there is an option to pre-select the items in the list
            if kodiVersion > 16:
                # Get the indexes to preselect
                preselectIdxs = []
                for i in range(0, len(requiredAddons)):
                    preselectIdxs.append(i)
                selected = xbmcgui.Dialog().multiselect(ADDON.getLocalizedString(32006), displayList, preselect=preselectIdxs)
            else:
                selected = xbmcgui.Dialog().multiselect(ADDON.getLocalizedString(32006), displayList)

            if (selected in [None, ""]) or (len(selected) < 1):
                log("URepo: Install operation cancelled, no addons to install")
            else:
                # Put together the list of addons to install
                for i in selected:
                    addonsToInstall.append(requiredAddons[i])

    # Perform the install for the required addons
    if len(addonsToInstall) > 0:
        successCountDisplay = ""
        failedCountDisplay = ""

        # Now create a template for each addon
        addonTemplate = AddonTemplate()
        for addon in addonsToInstall:
            addonTemplate.createTemplateAddon(addon['id'], addon['name'])

        # The following call will read in the template addons that were created
        # into the Kodi installation, however they will be marked as disabled
        xbmc.executebuiltin("UpdateLocalAddons", True)

        xbmc.sleep(1000)

        # Make a call for each addon to enable it as it will have been added as disabled originally
        for addonToInstall in addonsToInstall:
            log("URepo: Enabling addon %s" % addonToInstall['id'])
            xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "Addons.SetAddonEnabled", "params": { "addonid": "%s", "enabled": "toggle" }, "id": 1}' % addonToInstall['id'])

        xbmc.sleep(1000)

        # Now force a refresh of all of the addons so that we get the templates that
        # were created replaced with the real addons
        xbmc.executebuiltin("UpdateAddonRepos", True)

    log("URepo Script Finished")
