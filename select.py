#!/usr/bin/python
# -*- coding: utf-8 -*-

######################################
# This addon requires:               #
#                                    #
# pip(3) install python-dateutil     #
# pip(3) install pycryptodomex       #
#                                    #
# sudo apt-get install nettools      #
#                                    #
######################################

import os
import sys
import base64
import time
import xbmc
import xbmcgui
import xbmcaddon
import subprocess
import json
import socket
import codecs
import requests
import pyxbmct.addonwindow as pyxbmct

from datetime import datetime, tzinfo, timedelta
from dateutil import tz
import _strptime

try:
    from urllib.parse import unquote
except ImportError:
    from urllib2 import unquote

if sys.version_info.major < 3:
    INFO = xbmc.LOGNOTICE
else:
    INFO = xbmc.LOGINFO
DEBUG = xbmc.LOGDEBUG

__addon__          = xbmcaddon.Addon()
__setting__        = __addon__.getSetting
__addon_id__       = __addon__.getAddonInfo('id')
__addon_name__     = __addon__.getAddonInfo('name')
__addon_path__     = __addon__.getAddonInfo('path')
__localize__       = __addon__.getLocalizedString

__checked_icon__   = os.path.join(__addon_path__, 'resources', 'media', 'checked.png')
__unchecked_icon__ = os.path.join(__addon_path__, 'resources', 'media', 'unchecked.png')
__list_bg__        = os.path.join(__addon_path__, 'resources', 'media', 'background.png')
__texture_nf__     = os.path.join(__addon_path__, 'resources', 'media', 'texture-nf.png')

# Enable or disable Estuary-based design explicitly
pyxbmct.skin.estuary = True


def convert_date(t_str, t_fmt_in, t_fmt_out):
    ##Legacy check, Python 2.4 does not have strptime attribute, introduced in 2.5
    #if hasattr(datetime, 'strptime'):
    #    strptime = datetime.strptime
    #else:
    #    strptime = lambda date_string, format: datetime(*(time.strptime(date_string, format)[0:6]))

    try:
        t = datetime.strptime(t_str, t_fmt_in)
    except TypeError:
        t = datetime(*(time.strptime(t_str, t_fmt_in)[0:6]))

    return t.strftime(t_fmt_out)


class MultiChoiceDialog(pyxbmct.AddonDialogWindow):
    def __init__(self, title="", items=None, selected=None):
        super(MultiChoiceDialog, self).__init__(title)
        self.setGeometry(1000, 350, 6, 10)

        self.selected = selected or []
        self.items = items or []

        self.set_controls()
        self.place_controls()
        self.connect_controls()

        self.listing.addItems(self.items)
        if (self.listing.size() > 0):
            for index in range(self.listing.size()):
                listitem = self.listing.getListItem(index)
                try:
                    listitem.setIconImage(__checked_icon if index in self.selected else __unchecked_icon__)
                except:
                    listitem.setArt({'icon': __checked_icon__ if index in self.selected else __unchecked_icon__})
                listitem.setProperty('selected', 'true' if index in self.selected else 'false')
        else:
            self.listing.addItems([__localize__(30053)])
            self.listing.getListItem(0).setProperty('selected', '')

        self.set_navigation()

    def set_controls(self):
        self.list_bg = pyxbmct.Image(__list_bg__)
        self.listing = pyxbmct.List(_imageWidth=15, _itemTextYOffset=-1, _alignmentY=pyxbmct.ALIGN_CENTER_Y, _space=3, buttonTexture=__texture_nf__)
        self.ok_button = pyxbmct.Button(__localize__(30051))
        self.cancel_button = pyxbmct.Button(__localize__(30052))

    def place_controls(self):
        self.placeControl(self.list_bg, 0, 0, rowspan=5, columnspan=10)
        self.placeControl(self.listing, 0, 0, rowspan=6, columnspan=10)

        if self.items:
            self.placeControl(self.ok_button, 5, 3, columnspan=2)
            self.placeControl(self.cancel_button, 5, 5, columnspan=2)
        else:
            self.placeControl(self.cancel_button, 5, 4, columnspan=2)

    def connect_controls(self):
        self.connect(self.listing, self.check_uncheck)
        self.connect(self.ok_button, self.ok)
        self.connect(self.cancel_button, self.close)
        self.connect(pyxbmct.ACTION_NAV_BACK, self.close)

    def set_navigation(self):
        if self.items:
            self.listing.controlUp(self.ok_button)
            self.listing.controlDown(self.ok_button)
            self.ok_button.setNavigation(self.listing, self.listing, self.cancel_button, self.cancel_button)
            self.cancel_button.setNavigation(self.listing, self.listing, self.ok_button, self.ok_button)
            self.setFocus(self.listing)
        else:
            self.setFocus(self.cancel_button)

    def check_uncheck(self):
        listitem = self.listing.getSelectedItem()
        listitem.setProperty('selected', 'false' if listitem.getProperty('selected') == 'true' else 'true')
        try:
            listitem.setIconImage(__checked_icon__ if listitem.getProperty('selected') else __unchecked_icon__)
        except:
            listitem.setArt({'icon': __checked_icon__ if listitem.getProperty('selected') == 'true'  else __unchecked_icon__})

    def ok(self):
        self.selected = [index for index in range(self.listing.size())
                                if self.listing.getListItem(index).getProperty('selected') == 'true']
        super(MultiChoiceDialog, self).close()

    def close(self):
        self.selected = []
        super(MultiChoiceDialog, self).close()


def utfy_dict(dic):
    if not sys.version_info.major < 3:
       return dic

    if isinstance(dic,unicode):
        return dic.encode("utf-8")
    elif isinstance(dic,dict):
        for key in dic:
            dic[key] = utfy_dict(dic[key])
        return dic
    elif isinstance(dic,list):
        new_l = []
        for e in dic:
            new_l.append(utfy_dict(e))
        return new_l
    else:
        return dic


#def mixed_decoder(error: UnicodeError) -> (str, int):
#     bs: bytes = error.object[error.start: error.end]
#     return bs.decode("cp1252"), error.start + 1

def mixed_decoder(unicode_error):
    err_str = unicode_error[1]
    err_len = unicode_error.end - unicode_error.start
    next_position = unicode_error.start + err_len
    replacement = err_str[unicode_error.start:unicode_error.end].decode('cp1252')

    if sys.version_info.major < 3:
        return u'%s' % replacement, next_position
    else:
        return '%s' % replacement, next_position

codecs.register_error('mixed', mixed_decoder)


def jsonrpc_request(method, host='localhost', params=None, port=8080, username=None, password=None):
    url     =    'http://{}:{}/jsonrpc'.format(host, port)
    headers =    {'Content-Type': 'application/json'}

    xbmc.log(msg='[{}] Initializing RPC request to host {} with method \'{}\'.'.format(__addon_id__, host, method), level=DEBUG)

    jsondata = {
        'jsonrpc': '2.0',
        'method': method,
        'id': method}

    if params:
        jsondata['params'] = params

    if username and password:
        auth_str = '{}:{}'.format(username, password)
        try:
            base64str = base64.encodestring(auth_str)[:-1]
        except:
            base64str = base64.b64encode(auth_str.encode()).decode()
        headers['Authorization'] = 'Basic {}'.format(base64str)

    try:
        if host in ['localhost', '127.0.0.1']:
            response = xbmc.executeJSONRPC(json.dumps(jsondata))
            if sys.version_info.major < 3:
                data = json.loads(response.decode('utf-8', 'mixed'))
            else:
                data = json.loads(response)
        else:
            response = requests.post(url, data=json.dumps(jsondata), headers=headers)
            if not response.ok:
                xbmc.log(msg='[{}] RPC request to host {} failed with status \'{}\'.'.format(__addon_id__, host, response.status_code), level=INFO)
                return None

            if sys.version_info.major < 3:
                data = json.loads(response.content.decode('utf-8', 'mixed'))
            else:
                data = json.loads(response.text)

        if data['id'] == method and 'result' in data:
            xbmc.log(msg='[{}] RPC request to host {} returns data \'{}\'.'.format(__addon_id__, host, data['result']), level=DEBUG)
            return utfy_dict(data['result'])

    except Exception as e:
        xbmc.log(msg='[{}] RPC request to host {} failed with error \'{}\'.'.format(__addon_id__, host, str(e)), level=INFO)
        pass

    return None


def find_hosts(port=34890):

    hosts = []

    ip_list   = [ __setting__('client{:d}_ip'.format(i + 1)) for i in range(4) ]
    name_list = [ __setting__('client{:d}_name'.format(i + 1)) for i in range(4) ]

    if __setting__('pvrclients').lower() == 'true':
        my_env = os.environ.copy()
        my_env['LC_ALL'] = 'en_EN'
        netstat = subprocess.check_output(['netstat', '-tn'], universal_newlines=True, env=my_env)

        for line in netstat.split('\n')[2:]:
            items = line.split()
            if len(items) < 6 or (items[5] != 'ESTABLISHED'):
                continue

            local_addr, local_port = items[3].rsplit(':', 1)
            remote_addr, remote_port = items[4].rsplit(':', 1)

            if local_addr:
                local_addr  = local_addr.strip('[]')
            if remote_addr:
                remote_addr = remote_addr.strip('[]')
            local_port  = int(local_port)

            if remote_addr and local_port == port:
                host = {'ip': remote_addr}
                try:
                    index = ip_list.index(host['ip'])
                    host['name'] = name_list[index]
                except:
                    try:
                        host['name'] = socket.gethostbyaddr(remote_addr)[0].split('.')[0]
                    except:
                        host['name'] = remote_addr
                if not any(h['ip'] == remote_addr for h in hosts):
                    hosts.append(host)
    else:
        for i in range(4):
            host = {'ip': __setting__('client{:d}_ip'.format(i + 1))}
            if host['ip']:
                host['name'] = __setting__('client{:d}_name'.format(i + 1))
                hosts.append(host)

    return hosts


def utc_to_local(t_str, t_fmt):
    tz_utc = tz.tzutc()
    tz_local = tz.tzlocal()

    try:
        t = datetime.strptime(t_str, t_fmt)
    except TypeError:
        t = datetime(*(time.strptime(t_str, t_fmt)[0:6]))

    t = t.replace(tzinfo=tz_utc)
    t = t.astimezone(tz_local)

    return t.strftime(t_fmt)


def get_channel(pvrhost, channelid):
    channel = ''

    try:
        pvrdetails = jsonrpc_request('PVR.GetChannelDetails', host=pvrhost, params={'channelid': channelid})
        if pvrdetails and pvrdetails['channeldetails']['channelid'] == channelid:
            channel = pvrdetails['channeldetails']['label']
    except:
        pass

    return channel


def get_curr_recs(pvrhost):
    curr_recs = []
    time_fmt = '%Y-%m-%d %H:%M:%S'

    now = int(time.mktime(time.localtime()))

    try:
        pvrtimers = jsonrpc_request('PVR.GetTimers', host=pvrhost, params={'properties': ['title', 'starttime', 'endtime', 'state', 'channelid']})
        if pvrtimers:
            for timer in pvrtimers['timers']:
                if timer['state'] == 'recording':
                    timer_start = int(time.mktime(time.strptime(utc_to_local(timer['starttime'], time_fmt), time_fmt)))
                    timer_end = int(time.mktime(time.strptime(utc_to_local(timer['endtime'], time_fmt), time_fmt)))

                    pos = now - timer_start
                    p = {'hours': int(pos/3600), 'minutes':int(int(pos/60)%60), 'seconds':int(pos%60)}

                    length = timer_end - timer_start
                    l = {'hours': int(length/3600), 'minutes':int(int(length/60)%60), 'seconds':int(length%60)}

                    r = {'title':timer['title'], 'channelid':timer['channelid'], 'time':p, 'totaltime':l}
                    curr_recs.append(r)

    except KeyError:
        pass

    return curr_recs


if __name__ == '__main__':

    items = []
    hosts = []
    rec_channels = []

    username = __setting__('username')
    password = __setting__('password')
    rpcport = int(__setting__('rpcport'))
    pvrport = int(__setting__('pvrport'))

    for host in find_hosts(port=pvrport):

        try:
            player = jsonrpc_request('Player.GetActivePlayers', host=host['ip'], port=rpcport, username=username, password=password)
        except Exception as e:
            # show error msg, it seeme this remote host does not allow rpc control via http
            xbmc.log(msg='[{}] RPC control for host {} failed with error \'{}\'.'.format(__addon_id__, host['ip'], str(e)), level=INFO)
            continue

        if player and player[0]['type'] in ['audio', 'video']:
            player_id = player[0]['playerid']
            data = jsonrpc_request('Player.GetItem', host=host['ip'], params={'properties': ['title', 'file', 'showtitle', 'album', 'artist', 'track'], 'playerid': player_id}, port=rpcport, username=username, password=password)
            if data:
                try:
                    if data['item']['type'] == 'channel':
                        item = '{} (IP: {}): \"{}\" ({}: {})'.format(host['name'], host['ip'], data['item']['title'], ['Radio', 'TV'][player_id], data['item']['label'])
                    elif 'file' in data['item'] and unquote(data['item']['file'])[:6] == 'pvr://':
                        item = '{} (IP: {}): \"{}\" ({})'.format(host['name'], host['ip'], data['item']['title'], __localize__(30054))
                    elif data['item']['type'] == 'song' and 'artist' in data['item'] and 'album' in data['item'] and 'track' in data['item']:
                        item = '{} (IP: {}): \"{}: {} - {:02d}: {}\" ({})'.format(host['name'], host['ip'], data['item']['artist'][0], data['item']['album'], data['item']['track'], data['item']['label'], data['item']['type'])
                    elif data['item']['type'] == 'musicvideo' and 'artist' in data['item']:
                        item = '{} (IP: {}): \"{}: {}\" ({})'.format(host['name'], host['ip'], data['item']['artist'][0], data['item']['label'], data['item']['type'])
                    elif data['item']['type'] == 'episode' and 'showtitle' in data['item']:
                        item = '{} (IP: {}): \"{} - {}\" ({})'.format(host['name'], host['ip'], data['item']['showtitle'], data['item']['label'], data['item']['type'])
                    else:
                        item = '{} (IP: {}): \"{}\" ({})'.format(host['name'], host['ip'], data['item']['label'], data['item']['type'])

                except:
                    item = '{} (IP: {}): \"{}\" ({})'.format(host['name'], host['ip'], data['item']['label'], data['item']['type'])

                tdata = jsonrpc_request('Player.GetProperties', host=host['ip'], params={'properties': ['time', 'totaltime'], 'playerid': player_id}, port=rpcport, username=username, password=password)
                if tdata:
                    item = '{} @ {:02d}:{:02d}:{:02d} / {:02d}:{:02d}:{:02d}'.format(item, tdata['time']['hours'], tdata['time']['minutes'], tdata['time']['seconds'], \
                                                           tdata['totaltime']['hours'], tdata['totaltime']['minutes'], tdata['totaltime']['seconds'])

                hosts.append(host['ip'])
                rec_channels.append(None)
                items.append(item)

    curr_recs = get_curr_recs('localhost')
    for rec in curr_recs:
        item = '{}: \"{}\" ({})'.format(__localize__(30056), rec['title'], get_channel('localhost', rec['channelid']))
        item = '{} @ {:02d}:{:02d}:{:02d} / {:02d}:{:02d}:{:02d}'.format(item, rec['time']['hours'], rec['time']['minutes'], rec['time']['seconds'], \
                                                       rec['totaltime']['hours'], rec['totaltime']['minutes'], rec['totaltime']['seconds'])
        hosts.append('localhost')
        rec_channels.append(rec['channelid'])
        items.append(item)

    dialog = MultiChoiceDialog(__localize__(30050), items)
    dialog.doModal()

    if dialog.selected is not None:
        for index in dialog.selected:
            try:
                if rec_channels[index] is None:
                    player = jsonrpc_request('Player.GetActivePlayers', host=hosts[index], port=rpcport, username=username, password=password)
                    if player and player[0]['type'] in ['audio', 'video']:
                        player_id = player[0]['playerid']
                        jsonrpc_request('Player.Stop', host=hosts[index], params={'playerid': player_id}, port=rpcport, username=username, password=password)
                        jsonrpc_request('GUI.ShowNotification', host=hosts[index], params={'title': __addon_id__, 'message': __localize__(30055)}, port=rpcport, username=username, password=password)
                else:
                    jsonrpc_request('PVR.Record', host=hosts[index],  params={'channel': rec_channels[index]}, port=rpcport, username=username, password=password)
                    #jsonrpc_request('GUI.ShowNotification', host=hosts[index], params={'title': __addon_id__, 'message': __localize__(30057)}, port=rpcport, username=username, password=password)
            except:
                continue

    del dialog
