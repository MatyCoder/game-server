from ai.DistributedSmoothNodeAI import DistributedSmoothNodeAI
from direct.directnotify.DirectNotifyGlobal import directNotify

from ai.house.DistributedHouseItemAI import DistributedHouseItemAI
from ai.house import HouseGlobals
from ai.catalog import CatalogItem

class DistributedFurnitureItemAI(DistributedHouseItemAI, DistributedSmoothNodeAI):
    notify = directNotify.newCategory('DistributedFurnitureItemAI')

    def __init__(self, air, furnitureMgr, item):
        DistributedHouseItemAI.__init__(self, air)
        DistributedSmoothNodeAI.__init__(self, air)

        self.furnitureMgr = furnitureMgr
        self.item = item
        self.posHpr = item.posHpr
        self.mode = HouseGlobals.FURNITURE_MODE_OFF
        self.directorAvId = 0

    def delete(self):
        del self.furnitureMgr
        del self.item

        DistributedSmoothNodeAI.delete(self)
        DistributedHouseItemAI.delete(self)

    def getItem(self):
        return (self.furnitureMgr.do_id, self.item.getBlob(store = CatalogItem.Customization))

    def d_setSmPosHpr(self, x, y, z, h, p, r, t):
        self.sendUpdate('setSmPosHpr', [x, y, z, h, p, r, t])

    def b_setMode(self, mode, directorAvId):
        self.setMode(mode, directorAvId)
        self.d_setMode(mode, directorAvId)

    def d_setMode(self, mode, directorAvId):
        self.sendUpdate('setMode', (mode, directorAvId))

    def setMode(self, mode, directorAvId):
        self.mode = mode
        self.directorAvId = directorAvId

    def getMode(self):
        return (self.mode, self.directorAvId)

    def requestPosHpr(self, final, x, y, z, h, p, r, timestamp):
        directorAvId = self.air.currentAvatarSender

        # check to see if this avId has permission to change this furniture
        if self.furnitureMgr.requestControl(self, directorAvId):
            if not self.directorAvId:
                self.b_setMode(HouseGlobals.FURNITURE_MODE_START, directorAvId)
            self.posHpr = (x,y,z,h,p,r)
            # TODO: should we trust the av timestamp, or generate our own?
            # Broadcast down the new poshpr
            self.d_setSmPosHpr(x,y,z,h,p,r,timestamp)
            if final:
                # Write these properties to the database.
                self.__savePosition()
                # Stop this piece
                self.b_setMode(HouseGlobals.FURNITURE_MODE_STOP, directorAvId)
                # And turn it off too, clearing the director
                self.b_setMode(HouseGlobals.FURNITURE_MODE_OFF, 0)
        else:
            self.air.writeServerEvent('suspicious', directorAvId, 'DistributedFurnitureItem no permission to move')
            self.notify.warning('setPosHpr: avId: %s tried to move item: %s without permission' %
                                (directorAvId, self.item))

    def removeDirector(self):
        # Forcibly removes the current director.  This is called from
        # DistributedFurnitureManagerAI.  The item is left where it
        # is.
        if self.directorAvId != 0:
            oldDirector = self.directorAvId
            self.__savePosition()
            self.b_setMode(HouseGlobals.FURNITURE_MODE_STOP, oldDirector)
            self.b_setMode(HouseGlobals.FURNITURE_MODE_OFF, 0)

    def __savePosition(self):
        self.furnitureMgr.saveItemPosition(self)