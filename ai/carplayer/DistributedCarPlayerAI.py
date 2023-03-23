from .DistributedCarAvatarAI import DistributedCarAvatarAI

class DistributedCarPlayerAI(DistributedCarAvatarAI):
    def __init__(self, air):
        DistributedCarAvatarAI.__init__(self, air)

    def announceGenerate(self):
        self.sendUpdateToAvatar(self.air.currentAvatarSender, 'setRuleStates', [[[100, 1, 1, 1]]]) # To skip the tutorial, remove me to go to tutorial.
        self.sendUpdateToAvatar(self.air.currentAvatarSender, 'generateComplete', [])

    def sendEventLog(self, event: str, params: list, args: list):
        self.air.writeServerEvent(event, self.doId, f'{params}:{args}')

    def persistRequest(self, context: int):
        self.sendUpdateToAvatar(self.air.currentAvatarSender, 'persistResponse', [context, 1])
