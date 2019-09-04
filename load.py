#
# KodeBlox Copyright 2019 Sayak Mukhopadhyay
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http: //www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from os.path import dirname, join
from sys import platform
import sys
import time
import ctypes
import Tkinter as tk
import myNotebook as nb
from config import config

CLIENT_ID = '386149818227097610'

VERSION = '1.1.0'

#
# From discrod-rpc.h
#
discord_rpc_lib = 'discord-rpc.dll'
if platform == 'darwin':
    discord_rpc_lib = 'libdiscord-rpc.dylib'
elif platform == 'linux' or platform == 'linux2':
    discord_rpc_lib = 'libdiscord-rpc.so'
discord_rpc = ctypes.cdll.LoadLibrary(join(dirname(__file__), discord_rpc_lib))


class DiscordRichPresence(ctypes.Structure):
    _fields_ = [
        ('state', ctypes.c_char_p),		# max 128 bytes
        ('details', ctypes.c_char_p),		# max 128 bytes
        ('startTimestamp', ctypes.c_int64),
        ('endTimestamp', ctypes.c_int64),
        ('largeImageKey', ctypes.c_char_p),  # max 32 bytes
        ('largeImageText', ctypes.c_char_p),  # max 128 bytes
        ('smallImageKey', ctypes.c_char_p),  # max 32 bytes
        ('smallImageText', ctypes.c_char_p),  # max 128 bytes
        ('partyId', ctypes.c_char_p),		# max 128 bytes
        ('partySize', ctypes.c_int),
        ('partyMax', ctypes.c_int),
        ('matchSecret', ctypes.c_char_p),  # max 128 bytes
        ('joinSecret', ctypes.c_char_p),  # max 128 bytes
        ('spectateSecret', ctypes.c_char_p),  # max 128 bytes
        ('instance', ctypes.c_int8)
    ]


class DiscordJoinRequest(ctypes.Structure):
    _fields_ = [
        ('userId', ctypes.c_char_p),
        ('username', ctypes.c_char_p),
        ('avatar', ctypes.c_char_p)
    ]


ReadyProc = ctypes.CFUNCTYPE(None)
DisconnectedProc = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p)  # errorCode, message
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
Discord_Initialize.argtypes = [ctypes.c_char_p, ctypes.POINTER(DiscordEventHandlers), ctypes.c_int, ctypes.c_char_p]  # applicationId, handlers, autoRegister, optionalSteamId
Discord_Shutdown = discord_rpc.Discord_Shutdown
Discord_Shutdown.argtypes = None
Discord_UpdatePresence = discord_rpc.Discord_UpdatePresence
Discord_UpdatePresence.argtypes = [ctypes.POINTER(DiscordRichPresence)]
Discord_Respond = discord_rpc.Discord_Respond
Discord_Respond.argtypes = [ctypes.c_char_p, ctypes.c_int]  # userid, reply

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


event_handlers = DiscordEventHandlers(ReadyProc(ready),
                                      DisconnectedProc(disconnected),
                                      ErroredProc(errored),
                                      JoinGameProc(joinGame),
                                      SpectateGameProc(spectateGame),
                                      JoinRequestProc(joinRequest))

Discord_Initialize(CLIENT_ID, event_handlers, True, None)

this = sys.modules[__name__]	# For holding module globals

this.game_mode = None
this.in_wing = False
this.in_crew = False
this.crew_captain = None

this.presence_details = 'Connecting CMDR Interface'
this.presence_party_size = -1
this.presence_party_max = -1
# TODO: read time from entry['timestamp']
# TODO: figure out a better place to set time_start
this.time_start = time.time()
this.presence_time_end = None

def update_presence():
    presence = DiscordRichPresence()
    if config.getint("disable_presence") == 0:
        presence.details = this.presence_details
        if this.in_wing:
            presence.state = 'In wing in %s' % this.game_mode
            this.presence_party_max = 4
        elif this.in_crew:
            if this.crew_captain is True:
                presence.state = 'Commanding crew in %s' % this.game_mode
            elif this.crew_captain is None:
                presence.state = 'In crew in %s' % this.game_mode
            else:
                presence.state = 'In %s crew in %s' % (posessivify(this.crew_captain), this.game_mode)
        elif this.game_mode is not None:
            presence.state = 'Playing in %s' % this.game_mode
        if this.presence_party_size > 0:
            presence.partySize = this.presence_party_size
            if this.presence_party_max > 0:
                presence.partyMax = this.presence_party_max
    presence.startTimestamp = int(this.time_start)
    if this.presence_time_end:
        presence.endTimestamp = this.presence_time_end
    Discord_UpdatePresence(presence)

this.disablePresence = None


def plugin_prefs(parent, cmdr, is_beta):
    """
    Return a TK Frame for adding to the EDMC settings dialog.
    """
    this.disablePresence = tk.IntVar(value=config.getint("disable_presence"))
    frame = nb.Frame(parent)
    nb.Checkbutton(frame, text="Disable Presence", variable=this.disablePresence).grid()
    nb.Label(frame, text='Version %s' % VERSION).grid(padx=10, pady=10, sticky=tk.W)

    return frame

def prefs_changed(cmdr, is_beta):
    """
    Save settings.
    """
    config.set('disable_presence', this.disablePresence.get())
    update_presence()

def plugin_start():
    update_presence()
    return 'DiscordPresence'


def plugin_stop():
    Discord_Shutdown()


def journal_entry(cmdr, is_beta, system, station, entry, state):
    # GAME EVENTS
    # TODO: is StartUp even a real event?
    if entry['event'] == 'StartUp':
        if station is None:
            this.presence_details = 'Flying in %s' % system
        else:
            this.presence_details = 'Docked at %s in %s' % (entry['StationName'], system)
    elif entry['event'] == 'LoadGame':
        this.game_mode = entry['GameMode']
    elif entry['event'] == 'ShutDown':
        # TODO: read time from entry['timestamp']
        this.presence_time_end = time.time()
        this.presence_details = 'Shutdown'
    elif entry['event'] == 'Music':
        if entry['MusicTrack'] == 'MainMenu':
            # TODO: read time from entry['timestamp']
            this.presence_time_end = time.time()
            this.presence_details = 'In main menu'
    elif entry['event'] == 'Location' and station is None:
        this.presence_details = 'Flying in %s' % system
    # SUPERCRUISE EVENTS
    elif entry['event'] == 'StartJump':
        if entry['JumpType'] == 'Hyperspace':
            this.presence_details = 'Jumping to %s' % entry['StarSystem']
        elif entry['JumpType'] == 'Supercruise':
            this.presence_details = 'Supercruising around %s' % system
    elif entry['event'] == 'SupercruiseEntry' or entry['event'] == 'FSDJump':
        this.presence_details = 'Supercruising around %s' % system
    elif entry['event'] == 'SupercruiseExit':
        nearest_body = station or entry['Body']
        this.presence_details = 'Flying around %s in %s' % (nearest_body, system)
    # STATION EVENTS
    elif entry['event'] == 'Location' and station is not None:
        this.presence_details = 'Docked at %s in %s' % (station, system)
    elif entry['event'] == 'DockingGranted':
        this.presence_details = 'Docking at %s in %s' % (entry['StationName'], system)
    elif entry['event'] == 'ApproachSettlement':
        this.presence_details = 'Approaching settlement on %s in %s' % (entry['BodyName'], system)
    elif entry['event'] == 'Docked':
        this.presence_details = 'Docked at %s in %s' % (entry['StationName'], system)
    elif entry['event'] == 'Undocked' or entry['event'] == 'DockingCancelled' or entry['event'] == 'DockingTimeout':
        this.presence_details = 'Flying at %s in %s' % (entry['StationName'], system)
    # Planetary events
    elif entry['event'] == 'ApproachBody':
        this.presence_details = 'Approaching %s in %s' % (entry['Body'], system)
    elif entry['event'] == 'Touchdown' and entry['PlayerControlled']:
        # TODO: get planet's name
        this.presence_details = 'Landed on planet in %s' % system
    elif entry['event'] == 'Liftoff' and entry['PlayerControlled']:
        # TODO: get planet's name
        this.presence_details = 'Flying around %s' % system
    elif entry['event'] == 'LeaveBody':
        this.presence_details = 'Supercruising around %s' % system
    # EXTERNAL VEHICLE EVENTS
    elif entry['event'] == 'LaunchFighter' and entry['PlayerControlled']:
        this.presence_details = 'Flying fighter in %s' % system
    elif entry['event'] == 'DockFighter':
        this.presence_details = 'Flying in %s' % system
    elif entry['event'] == 'DockSRV':
        # TODO: figure out how to get planet's name
        this.presence_details = 'Landed on planet in %s' % system
    # WING EVENTS
    elif entry['event'] == 'WingJoin':
        this.in_wing = True
        this.presence_party_size = len(entry['Others']) + 1
    elif entry['event'] == 'WingAdd':
        this.in_wing = True
        if this.presence_party_size <= 0:
            this.presence_party_size = 1
        this.presence_party_size += 1
    elif entry['event'] == 'WingLeave':
        this.in_wing = False
        this.presence_party_size = -1
    # CREW EVENTS
    elif entry['event'] == 'JoinACrew':
        this.in_crew = True
        this.presence_party_size = 2
        this.crew_captain = entry['Captain']
    elif entry['event'] == 'CrewMemberJoins':
        this.in_crew = True
        this.presence_party_size += 1
        # TODO: does this event only fire when you're captain?
        this.crew_captain = True
    elif entry['event'] == 'ChangeCrewRole':
        this.in_crew = True
    elif entry['event'] == 'CrewMemberQuits' or entry['event'] == 'KickCrewMember':
        this.in_crew = True
        this.presence_party_size -= 1
    elif entry['event'] == 'QuitACrew' or entry['event'] == 'EndCrewSession':
        this.in_crew = False
        this.presence_party_size = -1
        this.crew_captain = None

    update_presence()
            
def posessivify(str):
    return str.last == 's' if "%s'" % str else "%s's" % str
