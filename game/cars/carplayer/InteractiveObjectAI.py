from .DistributedCarAvatarAI import DistributedCarAvatarAI

TYPE_NPC = 0
TYPE_SPAWNED_SPRITE = 1
TYPE_MAP_SPRITE = 2

# Interation types
CMD_TYPE_NEGATIVE = 0
CMD_TYPE_POSITIVE = 1

COMMAND_OFFER_QUERY_INTERACTIONS = 1
COMMAND_OFFER_PLAYER_APPROACH = 54
COMMAND_OFFER_PLAYER_RETREAT = 55
COMMAND_OFFER_PLAYER_CLICK = 57
COMMAND_CLICK = COMMAND_OFFER_PLAYER_CLICK

COMMAND_OFFER_QUEST_ACCEPT = 20
COMMAND_OFFER_QUEST_PASSIVE = 24
COMMAND_OFFER_PLAYER_INTRODUCTION = 30
COMMAND_OFFER_SPEAK = 31
COMMAND_OFFER_SHOP = 32
COMMAND_OFFER_GAME = 33

COMMAND_SET_MAP_EFFECT = 78

COMMAND_SHOW_GPS = 72

class InteractiveObjectAI(DistributedCarAvatarAI):
    def __init__(self, air):
        DistributedCarAvatarAI.__init__(self, air)
        self.name = ''
        self.assetId = 0
        self.objType = TYPE_NPC
        self.globalState = 0
        self.visible = 1

    def announceGenerate(self):
        DistributedCarAvatarAI.announceGenerate(self)

        # Experiments
        self.d_setTelemetry(280, 193, 0, -2511, -2297, -3254, -20104, 600979)

    def getName(self):
        return self.name

    def getAssetId(self):
        return self.assetId

    def getType(self):
        return self.objType

    def getGlobalState(self):
        return self.globalState

    def getVisible(self):
        return self.visible

    def getClientScript(self):
        return 'scripts/interactive/default_npc_no_physics.lua'

    def triggerInteraction(self, eventId: int, args: list):
        avatarId = self.air.getAvatarIdFromSender()
        print(f'triggerInteraction - {eventId} - {args}')

        if eventId == COMMAND_OFFER_QUERY_INTERACTIONS:
            self.d_setInteractiveCommands(avatarId, eventId, [COMMAND_SET_MAP_EFFECT, 102, CMD_TYPE_POSITIVE])

    def d_setInteractiveCommands(self, avatarId: int, eventId: int, args: list):
        self.sendUpdateToAvatarId(avatarId, 'setInteractiveCommands', [eventId, [args]])
