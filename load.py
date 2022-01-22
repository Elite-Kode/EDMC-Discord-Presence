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

import functools
import logging
import threading
import tkinter as tk
from os.path import dirname, join

import semantic_version
import sys
import time

import l10n
import myNotebook as nb
from config import config, appname, appversion
from py_discord_sdk import discordsdk as dsdk

plugin_name = "DiscordPresence"

logger = logging.getLogger(f'{appname}.{plugin_name}')

_ = functools.partial(l10n.Translations.translate, context=__file__)

CLIENT_ID = 386149818227097610

VERSION = '3.1.0'

# Add global var for Planet name (landing + around)
planet = '<Hidden>'
landingPad = '2'

this = sys.modules[__name__]  # For holding module globals


def callback(result):
    logger.info(f'Callback: {result}')
    if result == dsdk.Result.ok:
        logger.info("Successfully set the activity!")
    elif result == dsdk.Result.transaction_aborted:
        logger.warning(f'Transaction aborted due to SDK shutting down: {result}')
    else:
        logger.error(f'Error in callback: {result}')
        raise Exception(result)


def update_presence():
    if isinstance(appversion, str):
        core_version = semantic_version.Version(appversion)

    elif callable(appversion):
        core_version = appversion()

    logger.info(f'Core EDMC version: {core_version}')
    if core_version < semantic_version.Version('5.0.0-beta1'):
        logger.info('EDMC core version is before 5.0.0-beta1')
        if config.getint("disable_presence") == 0:
            this.activity.state = this.presence_state
            this.activity.details = this.presence_details
    else:
        logger.info('EDMC core version is at least 5.0.0-beta1')
        if config.get_int("disable_presence") == 0:
            this.activity.state = this.presence_state
            this.activity.details = this.presence_details

    this.activity.timestamps.start = int(this.time_start)
    this.activity_manager.update_activity(this.activity, callback)


def plugin_prefs(parent, cmdr, is_beta):
    """
    Return a TK Frame for adding to the EDMC settings dialog.
    """
    if isinstance(appversion, str):
        core_version = semantic_version.Version(appversion)

    elif callable(appversion):
        core_version = appversion()

    logger.info(f'Core EDMC version: {core_version}')
    if core_version < semantic_version.Version('5.0.0-beta1'):
        logger.info('EDMC core version is before 5.0.0-beta1')
        this.disablePresence = tk.IntVar(value=config.getint("disable_presence"))
    else:
        logger.info('EDMC core version is at least 5.0.0-beta1')
        this.disablePresence = tk.IntVar(value=config.get_int("disable_presence"))

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


def plugin_start3(plugin_dir):
    this.plugin_dir = plugin_dir
    this.discord_thread = threading.Thread(target=check_run, args=(plugin_dir,))
    this.discord_thread.setDaemon(True)
    this.discord_thread.start()
    return 'DiscordPresence'


def plugin_stop():
    this.activity_manager.clear_activity(callback)
    this.call_back_thread = None


def journal_entry(cmdr, is_beta, system, station, entry, state):
    global planet
    global landingPad
    presence_state = this.presence_state
    presence_details = this.presence_details
    if entry['event'] == 'StartUp':
        presence_state = _('In system {system}').format(system=system)
        if station is None:
            presence_details = _('Flying in normal space')
        else:
            presence_details = _('Docked at {station}').format(station=station)
    elif entry['event'] == 'Location':
        presence_state = _('In system {system}').format(system=system)
        if station is None:
            presence_details = _('Flying in normal space')
        else:
            presence_details = _('Docked at {station}').format(station=station)
    elif entry['event'] == 'StartJump':
        presence_state = _('Jumping')
        if entry['JumpType'] == 'Hyperspace':
            presence_details = _('Jumping to system {system}').format(system=entry['StarSystem'])
        elif entry['JumpType'] == 'Supercruise':
            presence_details = _('Preparing for supercruise')
    elif entry['event'] == 'SupercruiseEntry':
        presence_state = _('In system {system}').format(system=system)
        presence_details = _('Supercruising')
    elif entry['event'] == 'SupercruiseExit':
        presence_state = _('In system {system}').format(system=system)
        presence_details = _('Flying in normal space')
    elif entry['event'] == 'FSDJump':
        presence_state = _('In system {system}').format(system=system)
        presence_details = _('Supercruising')
    elif entry['event'] == 'Docked':
        presence_state = _('In system {system}').format(system=system)
        presence_details = _('Docked at {station}').format(station=station)
    elif entry['event'] == 'Undocked':
        presence_state = _('In system {system}').format(system=system)
        presence_details = _('Flying in normal space')
    elif entry['event'] == 'ShutDown':
        presence_state = _('Connecting CMDR Interface')
        presence_details = ''
    elif entry['event'] == 'DockingGranted':
        landingPad = entry['LandingPad']
    elif entry['event'] == 'Music':
        if entry['MusicTrack'] == 'MainMenu':
            presence_state = _('Connecting CMDR Interface')
            presence_details = ''
    # Todo: This elif might not be executed on undocked. Functionality can be improved
    elif entry['event'] == 'Undocked' or entry['event'] == 'DockingCancelled' or entry['event'] == 'DockingTimeout':
        presence_details = _('Flying near {station}').format(station=entry['StationName'])
    # Planetary events
    elif entry['event'] == 'ApproachBody':
        presence_details = _('Approaching {body}').format(body=entry['Body'])
        planet = entry['Body']
    elif entry['event'] == 'Touchdown' and entry['PlayerControlled']:
        presence_details = _('Landed on {body}').format(body=planet)
    elif entry['event'] == 'Liftoff' and entry['PlayerControlled']:
        if entry['PlayerControlled']:
            presence_details = _('Flying around {body}').format(body=planet)
        else:
            presence_details = _('In SRV on {body}, ship in orbit').format(body=planet)
    elif entry['event'] == 'LeaveBody':
        presence_details = _('Supercruising')

    # EXTERNAL VEHICLE EVENTS
    elif entry['event'] == 'LaunchSRV':
        presence_details = _('In SRV on {body}').format(body=planet)
    elif entry['event'] == 'DockSRV':
        presence_details = _('Landed on {body}').format(body=planet)

    if presence_state != this.presence_state or presence_details != this.presence_details:
        this.presence_state = presence_state
        this.presence_details = presence_details
        update_presence()


def check_run(plugin_dir):
    plugin_path = join(dirname(plugin_dir), plugin_name)
    retry = True
    while retry:
        time.sleep(1 / 10)
        try:
            this.app = dsdk.Discord(CLIENT_ID, dsdk.CreateFlags.no_require_discord, plugin_path)
            retry = False
        except Exception:
            pass

    this.activity_manager = this.app.get_activity_manager()
    this.activity = dsdk.Activity()

    this.call_back_thread = threading.Thread(target=run_callbacks)
    this.call_back_thread.setDaemon(True)
    this.call_back_thread.start()
    this.presence_state = _('Connecting CMDR Interface')
    this.presence_details = ''
    this.time_start = time.time()

    this.disablePresence = None

    update_presence()


def journal_entry_cqc(cmdr, is_beta, entry, state):

    maps = {
        'Bleae Aewsy GA-Y d1-14': 'Asteria Point',
        'Eta Cephei': 'Cluster Compound',
        'Theta Ursae Majoris': 'Elevate',
        'Boepp SU-E d12-818': 'Ice Field',
            }  # dict to convert star systems to CQC maps names

    presence_state = this.presence_state
    presence_details = this.presence_details

    if state['Horizons']:
        game_version = 'in Horizons'

    elif state['Odyssey']:
        game_version = 'in Odyssey'

    elif not state['Horizons'] and not state['Odyssey']:
        game_version = 'in Arena standalone'  # or in pre horizons elite but who play it now

    else:
        game_version = ''  # shouldn't happen

    if entry['event'] == ['LoadGame', 'StartUp'] or entry.get('MusicTrack') == 'CQCMenu':
        presence_state = f'Playing CQC {game_version}'
        presence_details = 'In lobby/queue'

    if entry['event'] == 'Music' and entry.get('MusicTrack') == 'MainMenu' or entry['event'].lower() == 'shutdown':
        presence_state = _('Connecting CMDR Interface')
        presence_details = ''

    if entry['event'] == 'Location' and entry.get('StarSystem'):
        presence_details = maps.get(entry['StarSystem'], '')
        presence_state = f'Playing CQC {game_version}'

    if entry['event'] == 'StartUp':
        if entry.get('StarSystem') is None:
            presence_state = _('Connecting CMDR Interface')
            presence_details = ''

        else:
            presence_details = maps.get(entry['StarSystem'], '')
            presence_state = f'Playing CQC {game_version}'

    if presence_state != this.presence_state or presence_details != this.presence_details:
        this.presence_state = presence_state
        this.presence_details = presence_details
        update_presence()


def run_callbacks():
    try:
        while True:
            time.sleep(1 / 10)
            this.app.run_callbacks()
    except Exception:
        check_run(this.plugin_dir)
