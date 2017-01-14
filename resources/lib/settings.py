# -*- coding: utf-8 -*-
import os
import xbmc
import xbmcaddon

ADDON = xbmcaddon.Addon(id='script.urepo')
ADDON_ID = ADDON.getAddonInfo('id')


# Common logging module
def log(txt, loglevel=xbmc.LOGDEBUG):
    if (ADDON.getSetting("logEnabled") == "true") or (loglevel != xbmc.LOGDEBUG):
        if isinstance(txt, str):
            txt = txt.decode("utf-8")
        message = u'%s: %s' % (ADDON_ID, txt)
        xbmc.log(msg=message.encode("utf-8"), level=loglevel)


# Splits a path the same way as os.path.split but supports paths of a different
# OS than that being run on
def os_path_split(fullpath):
    # Check if it ends in a slash
    if fullpath.endswith("/") or fullpath.endswith("\\"):
        # Remove the slash character
        fullpath = fullpath[:-1]

    try:
        slash1 = fullpath.rindex("/")
    except:
        slash1 = -1

    try:
        slash2 = fullpath.rindex("\\")
    except:
        slash2 = -1

    # Parse based on the last type of slash in the string
    if slash1 > slash2:
        return fullpath.rsplit("/", 1)

    return fullpath.rsplit("\\", 1)


# There has been problems with calling join with non ascii characters,
# so we have this method to try and do the conversion for us
def os_path_join(dir, file):
    # Check if it ends in a slash
    if dir.endswith("/") or dir.endswith("\\"):
        # Remove the slash character
        dir = dir[:-1]

    # Convert each argument - if an error, then it will use the default value
    # that was passed in
    try:
        dir = dir.decode("utf-8")
    except:
        pass
    try:
        file = file.decode("utf-8")
    except:
        pass
    return os.path.join(dir, file)


##############################
# Stores Various Settings
##############################
class Settings():
    @staticmethod
    def getUsername():
        return ADDON.getSetting("username")

    @staticmethod
    def getKodiVersion():
        kodiVer = xbmc.getInfoLabel('system.buildversion')
        # Default the version to 16 as that has hell features
        majorVersion = 16
        try:
            majorVersion = int(kodiVer.split(".", 1)[0])
            log("Settings: Major version is %d" % majorVersion)
        except:
            log("Settings: Failed to get major version, using %d" % majorVersion)

        return majorVersion
