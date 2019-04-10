#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import time
import xbmc
import xbmcgui
import xbmcaddon
import subprocess
import json
import urllib2
import socket
import codecs
#import pyxbmct
import pyxbmct.addonwindow as pyxbmct

from datetime import datetime, tzinfo, timedelta
from dateutil import tz
import _strptime

from contextlib import closing


__addon__ = xbmcaddon.Addon()
__setting__ = __addon__.getSetting
__addon_id__ = __addon__.getAddonInfo('id')
__addon_path__ = __addon__.getAddonInfo('path')
__checked_icon__ = os.path.join(__addon_path__, 'checked.png') # Don't decode _path to utf-8!!!
__unchecked_icon__ = os.path.join(__addon_path__, 'unchecked.png') # Don't decode _path to utf-8!!!
__localize__ = __addon__.getLocalizedString


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
        self.set_controls()
        self.listing.addItems(items or [])
        if (self.listing.size() > 0):
            for index in xrange(self.listing.size()):
                if index in self.selected:
                    self.listing.getListItem(index).setIconImage(__checked_icon__)
                    self.listing.getListItem(index).setLabel2("checked")
                else:
                    self.listing.getListItem(index).setIconImage(__unchecked_icon__)
                    self.listing.getListItem(index).setLabel2("unchecked")
        else:
            self.listing.addItems([__localize__(30053)])
        self.place_controls()
        self.connect_controls()
        self.set_navigation()

    def set_controls(self):
        self.listing = pyxbmct.List(_imageWidth=15)
        self.placeControl(self.listing, 0, 0, rowspan=5, columnspan=10)
        self.ok_button = pyxbmct.Button(__localize__(30051))
        self.cancel_button = pyxbmct.Button(__localize__(30052))

    def connect_controls(self):
        self.connect(self.listing, self.check_uncheck)
        self.connect(self.ok_button, self.ok)
        self.connect(self.cancel_button, self.close)
        self.connect(pyxbmct.ACTION_NAV_BACK, self.close)

    def place_controls(self):
        if (self.listing.getListItem(0).getLabel2()):
            self.placeControl(self.ok_button, 5, 3, columnspan=2)
            self.placeControl(self.cancel_button, 5, 5, columnspan=2)
        else:
            self.placeControl(self.cancel_button, 5, 4, columnspan=2)

    def set_navigation(self):
        if (self.listing.getListItem(0).getLabel2()):
            self.listing.controlUp(self.ok_button)
            self.listing.controlDown(self.ok_button)
            self.ok_button.setNavigation(self.listing, self.listing, self.cancel_button, self.cancel_button)
            self.cancel_button.setNavigation(self.listing, self.listing, self.ok_button, self.ok_button)
            self.setFocus(self.listing)
        else:
            self.setFocus(self.cancel_button)

    def check_uncheck(self):
        list_item = self.listing.getSelectedItem()
        if list_item.getLabel2() == "checked":
            list_item.setIconImage(__unchecked_icon__)
            list_item.setLabel2("unchecked")
        else:
            list_item.setIconImage(__checked_icon__)
            list_item.setLabel2("checked")

    def ok(self):
        self.selected = [index for index in xrange(self.listing.size())
                                if self.listing.getListItem(index).getLabel2() == "checked"]
        super(MultiChoiceDialog, self).close()

    def close(self):
        self.selected = None
        super(MultiChoiceDialog, self).close()


def mixed_decoder(unicode_error):

    err_str = unicode_error[1]
    err_len = unicode_error.end - unicode_error.start
    next_position = unicode_error.start + err_len
    replacement = err_str[unicode_error.start:unicode_error.end].decode('cp1252')

    return u'%s' % replacement, next_position

codecs.register_error('mixed', mixed_decoder)


def json_request(method, host, params=None, port=8080, username=None, password=None):

    url    =    'http://{}:{}/jsonrpc'.format(host, port)
    header =    {'Content-Type': 'application/json'}

    jsondata = {
        'jsonrpc': '2.0',
        'method': method,
        'id': method}

    if params:
        jsondata['params'] = params

    if username and password:
        base64str = base64.encodestring('{}:{}'.format(username, password))[:-1]
        header['Authorization'] = 'Basic {}'.format(base64str)

    try:
        request = urllib2.Request(url, json.dumps(jsondata), header)
        with closing(urllib2.urlopen(request, timeout=0.2)) as response:
            data = json.loads(response.read().decode('utf8', 'mixed'))

            if data['id'] == method and data.has_key('result'):
                return data['result']

    except:
        pass

    return False


def find_hosts(port=34890):

    hosts = []

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
                    host['name'] = socket.gethostbyaddr(remote_addr)[0].split('.')[0]
                except:
                    host['name'] = remote_addr
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
        pvrdetails = json_request('PVR.GetChannelDetails', pvrhost, params={'channelid': channelid})
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
        pvrtimers = json_request('PVR.GetTimers', pvrhost, params={'properties': ['title', 'starttime', 'endtime', 'state', 'channelid']})
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

        player = json_request('Player.GetActivePlayers', host['ip'], port=rpcport, username=username, password=password)
        if player and player[0]['type'] in ['audio', 'video']:
            player_id = player[0]['playerid']
            data = json_request('Player.GetItem', host['ip'], params={'properties': ['title', 'file', 'showtitle', 'album', 'artist', 'track'], 'playerid': player_id}, port=rpcport, username=username, password=password)
            if data:
                try:
                    if data['item']['type'] == 'channel':
                        item = '{} (IP: {}): \"{}\" ({}: {})'.format(host['name'], host['ip'], data['item']['title'].encode('utf-8'), ['Radio', 'TV'][player_id], data['item']['label'])
                    elif data['item'].has_key('file') and urllib2.unquote(data['item']['file'].encode('utf-8'))[:6] == 'pvr://':
                        item = '{} (IP: {}): \"{}\" ({})'.format(host['name'], host['ip'], data['item']['title'].encode('utf-8'), __localize__(30054))
                    elif data['item']['type'] == 'song' and data['item'].has_key('artist') and data['item'].has_key('album') and data['item'].has_key('track'):
                        item = '{} (IP: {}): \"{}: {} - {:02d}: {}\" ({})'.format(host['name'], host['ip'], data['item']['artist'][0].encode('utf-8') , data['item']['album'].encode('utf-8'), data['item']['track'], data['item']['label'].encode('utf-8'), data['item']['type'])
                    elif data['item']['type'] == 'musicvideo' and data['item'].has_key('artist'):
                        item = '{} (IP: {}): \"{}: {}\" ({})'.format(host['name'], host['ip'], data['item']['artist'][0].encode('utf-8'), data['item']['label'].encode('utf-8'), data['item']['type'])
                    elif data['item']['type'] == 'episode' and data['item'].has_key('showtitle'):
                        item = '{} (IP: {}): \"{} - {}\" ({})'.format(host['name'], host['ip'], data['item']['showtitle'].encode('utf-8'), data['item']['label'].encode('utf-8'), data['item']['type'])
                    else:
                        item = '{} (IP: {}): \"{}\" ({})'.format(host['name'], host['ip'], data['item']['label'].encode('utf-8'), data['item']['type'])

                except:
                    item = '{} (IP: {}): \"{}\" ({})'.format(host['name'], host['ip'], data['item']['label'].encode('utf-8'), data['item']['type'])

                tdata = json_request('Player.GetProperties', host['ip'], params={'properties': ['time', 'totaltime'], 'playerid': player_id}, port=rpcport, username=username, password=password)
                if tdata:
                    item = '{} @ {:02d}:{:02d}:{:02d} / {:02d}:{:02d}:{:02d}'.format(item, tdata['time']['hours'], tdata['time']['minutes'], tdata['time']['seconds'], \
                                                           tdata['totaltime']['hours'], tdata['totaltime']['minutes'], tdata['totaltime']['seconds'])

                hosts.append(host['ip'])
                rec_channels.append(None)
                items.append(item)

    curr_recs = get_curr_recs('localhost')
    for rec in curr_recs:
        item = '{}: \"{}\" ({})'.format(__localize__(30056), rec['title'].encode('utf-8'), get_channel('localhost', rec['channelid']))
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
                    player = json_request('Player.GetActivePlayers', hosts[index], port=rpcport, username=username, password=password)
                    if player and player[0]['type'] in ['audio', 'video']:
                        player_id = player[0]['playerid']
                        json_request('Player.Stop', hosts[index], params={'playerid': player_id}, port=rpcport, username=username, password=password)
                        json_request('GUI.ShowNotification', hosts[index], params={'title': __addon_id__, 'message': __localize__(30055)}, port=rpcport, username=username, password=password)
                else:
                    json_request('PVR.Record', hosts[index],  params={'channel': rec_channels[index]}, port=rpcport, username=username, password=password)
                    #json_request('GUI.ShowNotification', hosts[index], params={'title': __addon_id__, 'message': __localize__(30057)}, port=rpcport, username=username, password=password)
            except:
                continue

    del dialog
