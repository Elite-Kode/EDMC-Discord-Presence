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

this.presence_state = 'Connecting CMDR Interface'
this.presence_details = ''
# TODO: read time from event['timestamp']
# TODO: figure out a better place to set time_start
this.time_start = time.time()
this.presence_time_end = None

def update_presence():
    presence = DiscordRichPresence()
    if config.getint("disable_presence")==0:
        presence.state = this.presence_state
        presence.details = this.presence_details
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
    # TODO: is StartUp even a real event?
    if entry['event'] == 'StartUp':
        if station is None:
            this.presence_details = f'Flying in {system}'
        else:
            this.presence_details = f'Docked at {event["StationName"]} in {system}'
    elif entry['event'] == 'Location':
        if station is None:
            this.presence_details = f'Flying in {system}'
        else:
            this.presence_details = f'Docked at {event["StationName"]} in {system}'
    elif entry['event'] == 'StartJump':
        if entry['JumpType'] == 'Hyperspace':
            this.presence_details = f'Jumping to {entry['StarSystem']}'
        elif entry['JumpType'] == 'Supercruise':
            this.presence_details = f'Supercruising around {system}'
    elif entry['event'] == 'SupercruiseEntry' or entry['event'] == 'FSDJump':
        this.presence_details = f'Supercruising around {system}'
    elif entry['event'] == 'SupercruiseExit':
        nearest_body = station or event['Body']
        this.presence_details = f'Flying around {nearest_body} in {system}'
    elif entry['event'] == 'Docked':
        this.presence_details = f'Docked at {event["StationName"]} in {system}'
    elif entry['event'] == 'Undocked':
        this.presence_details = f'Flying at {event["StationName"]} in {system}'
    elif entry['event'] == 'ShutDown':
        # TODO: read time from event['timestamp']
        this.presence_time_end = time.time()
        this.presence_details = 'Shutdown'
    elif entry['event'] == 'Music':
        if entry['MusicTrack'] == 'MainMenu':
            # TODO: read time from event['timestamp']
            this.presence_time_end = time.time()
            this.presence_details = 'In main menu'
    update_presence()
            
