
from typing import Dict, List
from direct.directnotify.DirectNotifyGlobal import directNotify
from direct.distributed.DistributedObjectAI import DistributedObjectAI
from direct.showbase.PythonUtil import Functor

from game.cars.dungeon.DistributedDungeonAI import DistributedDungeonAI
from game.cars.carplayer.DistributedCarPlayerAI import DistributedCarPlayerAI
from .Track import Track
from .TrackSegment import TrackSegment
from .RaceGlobals import getRewardsForTrack
from direct.task.Task import Task

class DistributedRaceAI(DistributedDungeonAI):
    notify = directNotify.newCategory("DistributedRaceAI")
    COUNTDOWN_TIME = 4

    def __init__(self, air, track):
        DistributedDungeonAI.__init__(self, air)
        self.track: Track = track
        self.countDown: int = self.COUNTDOWN_TIME

        self.playerIdToLap: Dict[int, int] = {}
        self.playerIdToReady: Dict[int, bool] = {}
        self.playerIdToSegment: Dict[int, TrackSegment] = {}
        self.finishedPlayerIds: List[int] = []

        self.places: List[int] = [0, 0, 0, 0]

    def announceGenerate(self):
        for player in self.playerIds:
            self.playerIdToLap[player] = 1
            self.playerIdToReady[player] = False
            self.playerIdToSegment[player] = self.track.segmentById[self.track.startingTrackSegment]

            self.accept(self.staticGetZoneChangeEvent(player), Functor(self._playerChangedZone, player))
            self.acceptOnce(self.air.getDeleteDoIdEvent(player), self._playerDeleted, extraArgs=[player])

    def _playerChangedZone(self, playerId, newZoneId, oldZoneId):
        self.notify.debug(f"_playerChangedZone: {playerId} - {newZoneId} - {oldZoneId}")
        # FIXME: Client seems to set their player's zone to the quiet zone
        # for single player races, how would this work for multiplayer races?
        if playerId in self.playerIds and oldZoneId == 1:
            self._playerDeleted(playerId)

    def _playerDeleted(self, playerId):
        self.notify.debug(f"Player {playerId} have left the race!")
        self.playerIds.remove(playerId)
        self.ignore(self.staticGetZoneChangeEvent(playerId))
        self.ignore(self.air.getDeleteDoIdEvent(playerId))

        if not self.getActualPlayers():
            self.notify.debug("Everybody has left, shutting down...")
            self.requestDelete()

    def delete(self):
        # Delete the lobby context if it still exists.
        context: DistributedObjectAI = self.air.getDo(self.contextDoId)
        if context:
            context.requestDelete()
        DistributedDungeonAI.delete(self)

    def getActualPlayers(self):
        return list(filter(lambda playerId: not self.isNPC(playerId), self.playerIds))

    def isNPC(self, playerId):
        # SPRaceAI overrides this.
        return False

    def sendPlaces(self):
        playerLapsAndSegmentsIds: Dict[int, tuple] = {}
        firstPlaceIndexToDetermine = 0

        for player in self.playerIds:
            if player in self.finishedPlayerIds:
                finishedPlaceIndex = self.finishedPlayerIds.index(player)
                self.places[3 - finishedPlaceIndex] = player
                firstPlaceIndexToDetermine += 1
                continue

            playerLap = self.playerIdToLap.get(player)
            playerSegment = self.playerIdToSegment.get(player)
            playerLapsAndSegmentsIds[player] = (playerLap, playerSegment.id)

        playersOnFurthestLap: List[int] = []
        playersInFurthestSegment: List[int] = []

        for placeIndex in range(firstPlaceIndexToDetermine, 4):
            # If we still have players to churn through on the furthest lap, we don't need to iterate again.
            if len(playersOnFurthestLap) == 0:
                furthestLap = 1
                for player in playerLapsAndSegmentsIds:
                    playerLap, playerSegmentId = playerLapsAndSegmentsIds.get(player)
                    if playerLap > furthestLap:
                        furthestLap = playerLap
                        playersOnFurthestLap = [player]
                    elif playerLap == furthestLap:
                        playersOnFurthestLap.append(player)

            # Same as above, but for segment:
            if len(playersInFurthestSegment) == 0:
                furthestSegmentId = -1
                for player in playersOnFurthestLap:
                    playerLap, playerSegmentId = playerLapsAndSegmentsIds.get(player)
                    if playerSegmentId > furthestSegmentId:
                        furthestSegmentId = playerSegmentId
                        playersInFurthestSegment = [player]
                    elif playerSegmentId == furthestSegmentId:
                        playersInFurthestSegment.append(player)

            # TODO: Determine what happens if there's a segment tie. Right now, lowest avId gets the lower place.
            playerForThisPlace = playersInFurthestSegment[0]
            self.places[3 - placeIndex] = playerForThisPlace

            # Cleanup for further iterations.
            del playerLapsAndSegmentsIds[playerForThisPlace]
            playersOnFurthestLap.remove(playerForThisPlace)
            playersInFurthestSegment.remove(playerForThisPlace)

        self.sendUpdate('setPlaces', [self.places])

    def raceStarted(self) -> bool:
        return self.countDown == 0

    def isEverybodyReady(self) -> bool:
        if len(self.playerIds) == 4 and all(self.playerIdToReady.values()):
            return True
        return False

    def syncReady(self):
        playerId = self.air.getAvatarIdFromSender()
        if playerId not in self.playerIds:
            self.notify.warning(f"Player {playerId} is not on the race!")
            return
        self.playerIdToReady[playerId] = True

        self.shouldStartRace()

    def shouldStartRace(self):
        if self.raceStarted() or taskMgr.hasTaskNamed(self.taskName("countDown")):
            return

        if self.isEverybodyReady():
            self.notify.debug("Everybody ready, starting countdown.")
            # 0 so the countdown can start next frame
            self.doMethodLater(0, self.__doCountDown, self.taskName("countDown"))

    def onSegmentEnter(self, segment, fromSegment, forward):
        playerId = self.air.getAvatarIdFromSender()
        if playerId not in self.playerIds:
            self.notify.warning(f"Player {playerId} is not on the race!")
            return
        self.handleSegmentEnter(playerId, segment, fromSegment, forward)

    def handleSegmentEnter(self, playerId, segment, fromSegment, forward):
        if not self.raceStarted():
            # The client send those messages early to set things up, ignore.
            self.notify.debug(f"Early handleSegmentEnter called for player {playerId}")
            return

        if playerId in self.finishedPlayerIds:
            return

        currentSegment = self.playerIdToSegment.get(playerId)
        if not currentSegment:
            self.notify.warning(f"Missing current segment for player {playerId}!")
            return

        self.notify.debug(f"handleSegmentEnter: {playerId} - {segment} - {currentSegment.id} - {forward}")

        if segment in currentSegment.childrenIds:
            childSegment = currentSegment.childrenById.get(segment)
            if not childSegment:
                self.notify.warning(f"Child segment {segment} does not exist from segment {currentSegment.id}")
                return
            self.playerIdToSegment[playerId] = childSegment
            if childSegment.id == self.track.startingTrackSegment:
                # It has reached a lap!
                self.playerIdToLap[playerId] += 1
                self.notify.debug(f"{playerId} has reached lap {self.playerIdToLap[playerId]}!")
        elif segment in currentSegment.parentIds:
            parentSegment = currentSegment.parentById.get(segment)
            if not parentSegment:
                self.notify.warning(f"Parent segment {segment} does not exist from segment {currentSegment.id}")
                return
            self.playerIdToSegment[playerId] = parentSegment
            if parentSegment.id == self.track.startingTrackSegment:
                # They have reached back a lap!
                self.playerIdToLap[playerId] -= 1
                self.notify.debug(f"{playerId} went back to lap {self.playerIdToLap[playerId]}!")

        self.sendPlaces()
        if self.playerIdToLap[playerId] > self.track.totalLaps:
            self.playerFinishedRace(playerId)

    def playerFinishedRace(self, playerId):
        if playerId in self.finishedPlayerIds:
            return

        self.notify.debug(f"{playerId} has finished the race!")
        self.finishedPlayerIds.append(playerId)

        place = self.finishedPlayerIds.index(playerId) + 1

        # TODO: Times and photo finish?
        self.sendUpdate('setRacerResult', (playerId, place, 0, 0, 0, 0))

        if self.isNPC(playerId):
            # We don't give out rewards to NPCs.
            return

        player: DistributedCarPlayerAI = self.air.getDo(playerId)
        if not player:
            self.notify.warning(f"No player for playerid: {playerId}")
            return

        coins, racingPoints = getRewardsForTrack(self.track.name, place)
        player.addCoins(coins)
        player.racecar.addRacingPoints(racingPoints)

        # See com.disney.cars.states.isoworld.ISOInstance
        player.d_invokeRuleResponse(0, [1, place, racingPoints, coins], -self.dungeonItemId)

    def __doCountDown(self, task: Task):
        self.countDown -= 1
        self.sendUpdate('setCountDown', (self.countDown,))
        if self.countDown == 0:
            return task.done

        task.delayTime = 1
        return task.again
