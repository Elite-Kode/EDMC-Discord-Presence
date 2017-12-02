from os.path import dirname, join
from sys import platform
import time
import ctypes

CLIENT_ID = '386149818227097610'

#
# From discrod-rpc.h
#
discord_rpc = ctypes.cdll.LoadLibrary(join(dirname(__file__), platform == 'darwin' and 'libdiscord-rpc.dylib' or 'discord-rpc.dll'))

class DiscordRichPresence(ctypes.Structure):
    _fields_ = [
        ('state', ctypes.c_char_p),		# max 128 bytes
        ('details', ctypes.c_char_p),		# max 128 bytes
        ('startTimestamp', ctypes.c_int64),
        ('endTimestamp', ctypes.c_int64),
        ('largeImageKey', ctypes.c_char_p),	# max 32 bytes
        ('largeImageText', ctypes.c_char_p),	# max 128 bytes
        ('smallImageKey', ctypes.c_char_p),	# max 32 bytes
        ('smallImageText', ctypes.c_char_p),	# max 128 bytes
        ('partyId', ctypes.c_char_p),		# max 128 bytes
        ('partySize', ctypes.c_int),
        ('partyMax', ctypes.c_int),
        ('matchSecret', ctypes.c_char_p),	# max 128 bytes
        ('joinSecret', ctypes.c_char_p),	# max 128 bytes
        ('spectateSecret', ctypes.c_char_p),	# max 128 bytes
        ('instance', ctypes.c_int8)
    ]

class DiscordJoinRequest(ctypes.Structure):
    _fields_ = [
        ('userId', ctypes.c_char_p),
        ('username', ctypes.c_char_p),
        ('avatar', ctypes.c_char_p)
    ]

ReadyProc = ctypes.CFUNCTYPE(None)
DisconnectedProc = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p)	# errorCode, message
ErroredProc = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p)		# errorCode, message
JoinGameProc = ctypes.CFUNCTYPE(None, ctypes.c_char_p)				# joinSecret
SpectateGameProc = ctypes.CFUNCTYPE(None, ctypes.c_char_p)			# spectateSecret
JoinRequestProc = ctypes.CFUNCTYPE(None, ctypes.POINTER(DiscordJoinRequest))

class DiscordEventHandlers(ctypes.Structure):
    _fields_ = [
        ('ready', ReadyProc),
        ('disconnected', DisconnectedProc),
        ('errored', ErroredProc),
        ('joinGame', JoinGameProc),
        ('spectateGame', SpectateGameProc),
        ('joinRequest', JoinRequestProc)
    ]

DISCORD_REPLY_NO, DISCORD_REPLY_YES, DISCORD_REPLY_IGNORE = range(3)

Discord_Initialize = discord_rpc.Discord_Initialize
Discord_Initialize.argtypes = [ctypes.c_char_p, ctypes.POINTER(DiscordEventHandlers), ctypes.c_int, ctypes.c_char_p]	# applicationId, handlers, autoRegister, optionalSteamId
Discord_Shutdown = discord_rpc.Discord_Shutdown
Discord_Shutdown.argtypes = None
Discord_UpdatePresence = discord_rpc.Discord_UpdatePresence
Discord_UpdatePresence.argtypes = [ctypes.POINTER(DiscordRichPresence)];
Discord_Respond = discord_rpc.Discord_Respond
Discord_Respond.argtypes = [ctypes.c_char_p, ctypes.c_int]	# userid, reply

#
# Callback handlers
#

def ready():
    print 'ready'

def disconnected(errorCode, message):
    print 'disconnected', errorCode, message

def errored(errorCode, message):
    print 'errored', errorCode, message

def joinGame(joinSecret):
    print 'joinGame', joinSecret

def spectateGame(spectateSecret):
    print 'spectateGame', spectateSecret

def joinRequest(request):
    print 'joinRequest', request.userId, request.username, request.avatar

x = ReadyProc(ready)
y = JoinRequestProc(joinRequest)

event_handlers = DiscordEventHandlers(ReadyProc(ready),
                                      DisconnectedProc(disconnected),
                                      ErroredProc(errored),
                                      JoinGameProc(joinGame),
                                      SpectateGameProc(spectateGame),
                                      JoinRequestProc(joinRequest))

Discord_Initialize(CLIENT_ID, event_handlers, True, None)


#
# Update presence
#

presence = DiscordRichPresence('My state',
                               'My details',
                               0,
                               0,
                               'default',
                               "Blade's Edge Arena",
                               'rogue',
                               'Rogue - Level 100',
                               'Dunno',
                               1,
                               3,
                               'secret1',
                               'secret2',
                               'secret3',
                               0)

def plugin_start():
    presence.startTimestamp = int(time.time())
    Discord_UpdatePresence(presence)
    return 'Discord'

def plugin_stop():
    Discord_Shutdown()

def journal_entry(cmdr, is_beta, system, station, entry, state):
    print entry['event']
