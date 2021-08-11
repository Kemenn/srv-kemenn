#! /usr/bin/env python3
#coding: utf-8

import re
import sys
import threading
import config_manager

from time import time, sleep
from pypsrp.client import Client
from getmac import get_mac_address
from datetime import datetime, timedelta

#Source : https://xkln.net/blog/how-to-obtain-ip-addresses-of-remote-desktop-clients-with-powershell/
SCRIPT = """$CurrentUsers = quser
$CurrentUsers = $CurrentUsers[1..$CurrentUsers.Length] | % {$_.trim().Split(" ")[0].Replace(">", "")}

$Events = Get-WinEvent -FilterHashtable @{
    Logname   = 'Microsoft-Windows-TerminalServices-RemoteConnectionManager/Operational'
    ID        = 1149
    StartTime = (Get-Date).AddDays(-31)    
}
$EventObjects = @()
$Events | % {
    $EventXML = [xml]$_.ToXml()
    $obj = New-Object -TypeName PSObject -Property @{
        Username  = $EventXML.Event.UserData.EventXML.Param1
        IP        = $EventXML.Event.UserData.EventXML.Param3
        Timestamp = [datetime]$EventXML.Event.System.TimeCreated.SystemTime
    }
    $EventObjects += $obj
}

$CurrentSessions = $CurrentUsers | ForEach-Object {
    $EventObjects | Sort-Object -Property Timestamp -Descending | Where-Object Username -eq $_ | Select-Object -First 1
}

$CurrentSessions | Select-Object Username, IP, Timestamp
echo $CurrentSessions
"""
RE_SPLIT_LINE = re.compile(r"(?P<username>^[a-zA-Z0-9]+)( +)(?P<ipaddress>[0-9\.]+)( +)(?P<timestamp>[0-9\/ :]+[A|P]M)")
INTERFACE='enp0s3'

def date_to_unix_time(date) :
    """ Convert the timestamps of powershell in
    unix timestamp"""
    if date[-2:] == "PM" :
        split_date = date.split(" ")[:-1]
        split_hour = split_date[1].split(":")
        if split_hour[0] != "12" : split_hour[0] = str(int(split_hour[0])+12)
        date = "{} {}".format(split_date[0], ":".join(split_hour))
    else :
        date = " ".join(date.split(" ")[:-1])
    return datetime.strptime(date, "%m/%d/%Y %H:%M:%S").timestamp()
def matching_line(line) :
    """ Test if the line respect this type :
    username       01/01/2000 01:01:01 PM  192.168.01.01
    There is no verification of valid ip adress, date or
    username... is just for example ;)"""
    if re.match(
        r"(^[a-zA-Z0-9]+)( +)([0-9\.]+)( +)([0-9\/ :]+[A|P]M)", line) :
        return True
    return False
def split_line(line) :
    """ Get a line matched with regex in matching_line
    function, and extract the username, the date and
    the ip address in dictionnary"""
    match = RE_SPLIT_LINE.match(line)
    return match.groupdict()
def dictionnaryze_sheet(sheet) :
    """ Return a dict from the sheet output of
    powershell command line."""
    dicted_sheet = []
    for i in sheet :
        dicted_line = split_line(i)
        dicted_line['timestamp'] = date_to_unix_time(dicted_line['timestamp'])
        dicted_line['username'] = dicted_line['username'].lower()
        dicted_line['time_session'] = str(timedelta(
            seconds=int(time())-int(dicted_line['timestamp'])))
        dicted_sheet.append(dicted_line)
    return dicted_sheet
def just_last_sessions(list_sessions) :
    """ Return the same list of session but without the
    complete list, just the last sessions for all user"""
    cleaned_sessions = []
    for i, j in enumerate(list_sessions) :
        if not j['username'] in [i['username'] for i in list_sessions][i+1:] :
            cleaned_sessions.append(j)
    return cleaned_sessions
def add_mac(sessions) :
    """ Add mac address in dictionnary"""
    for session in sessions :
        session['mac_addr'] = get_mac(sessions, session['username'])
    return sessions

def get_output_ps(server, username, password, all_std=False) :
    """ The function execute the PowerShell script pass
    in argument with the identifiant for authentication
    on remote windows computer"""
    with Client(server, username=username, password=password, ssl=False) as client:
        stdout, stderr, rc = client.execute_ps(SCRIPT)
    if all_std : return stdout, stderr, rc
    return stdout
def get_mac(sessions, username) :
    """ Return the mac address of an ip address
    with arping command"""
    for session in sessions :
        if session['username'] == username.lower() :
            i = 0
            mac_addr = get_mac_address(interface=INTERFACE, ip=session['ipaddress'])
            for i in range(7) :
                if mac_addr != "00:00:00:00:00:00" :
                    return mac_addr
                sleep(0.4)
                mac_addr = get_mac_address(interface=INTERFACE, ip=session['ipaddress'])
    return None

def main(servers, username, password, user="all", all_info=False) :
    """ The main function
    if parameter user = all, return informations of all sessions"""
    output_ps = ""
    for server in servers :
        try :
            output_ps += get_output_ps(server, username, password)
        except :
            sys.stderr.write("Error : an error is occured for server {}\n".format(server))
            sys.stdout.flush()
    remote_sessions_output = [i for i in output_ps.split("\n") if matching_line(i)]
    #remote_sessions is list of session with unix time in list of dict, sorted by time
    remote_sessions = sorted(
        dictionnaryze_sheet(remote_sessions_output),
        key=lambda colonnes: colonnes['timestamp'])
    remote_sessions = just_last_sessions(remote_sessions)

    if user != "all" :
        if all_info :
            mac_user = get_mac(remote_sessions, user)
            for i in remote_sessions :
                if i['username'] == user.lower() :
                    i['mac_addr'] = mac_user
                    return i
        else :
            return get_mac(remote_sessions, user)
    else :
        add_mac(remote_sessions)
        return remote_sessions



class GetMacService(threading.Thread) :
    """ Service to check every number of second the
    new client mac in RDS server """
    def __init__(self, *args, **kwargs) :
        #Internal functionment of class
        threading.Thread.__init__(self)
        self.sniff_mac = kwargs['SEARCH_MAC_RDP_CLIENTS'] #lock to search or stop module
        self.timer_event = threading.Event()
        self.sleep_time = kwargs['MAC_SERVICE_TIME']
        #Informations to access of rds servers (get in config file)
        self.servers = ""
        self.username = ""
        self.password = ""
        #calculare informations
        self.servers_mac_addr = [0,0,0] #list of mac addr of servers from self.servers
        self.remote_session = []
        self.direct_session = [] # {userid, mac address},
        self.ask_for_all_client = False
        self.asklocation = []    #list of {mac address, userid(, location)},
        self.asked_location = [] #to must be request location
    def run(self) :
        if self.sniff_mac :
            sys.stdout.write("[started] Mac sniffer service !\n")
            sys.stdout.flush()
        while self.sniff_mac :
            try : self.update_server_infos()
            except :
                self.writeerr("[{DATE}] In getting server informations.")
            try :
                self.remote_session = main(
                    self.servers, self.username, self.password)
                self.verify_existing_remote_mac()
            except :
                self.writeerr("[{DATE}] In getting remote session.")
            print(self.remote_session)
            self.timer_event.wait(self.sleep_time)
        self.sniff_mac = "stopped"
    def stop(self) :
        sys.stdout.write("[stopping] Mac sniffer service...\n")
        sys.stdout.flush()
        self.sniff_mac = False
        self.timer_event.set()
        if not self.is_alive() : self.sniff_mac = "stopped"
        while self.sniff_mac != "stopped" : sleep(4)
        sys.stdout.write("[stopped] Mac sniffer service !\n")
        sys.stdout.flush()

    ### INIT ###
    def init_client(self, macaddr, username) :
        """ Manages the arrival of a new customer:
         - indexing according to type (thin/heavy client)
         - checking its mac address in the configuration"""
        mac = self.normalizemac(macaddr)
        user = username.lower()
        if mac in self.servers_mac_addr : return None
        self.check_config(mac, user)
        self.direct_session.append({'macaddr' : mac, 'username' : user})
    def verify_existing_remote_mac(self) :
        """ Verify if mac is in the configuration. If not
        exists, add mac address in unknow_mac."""
        for session in self.remote_session :
            if session['mac_addr'] is not None :
                mac = self.normalizemac(session['mac_addr'])
                user = session['username'].lower()
                self.check_config(mac, user)
    def switch_config_all_mac(self, status=None) :
        #the remote sessions are appends later by thread
        self.asked_location = self.direct_session
        if status is not None :
            self.ask_for_all_client = status
        elif self.ask_for_all_client :
            self.ask_for_all_client = False
        else :
            self.ask_for_all_client = True

    ### LOCATION TOOLS ###
    def check_config(self, mac, username) :
        """Check if is necessary to ask location"""
        if config_manager.macexist(mac) and not self.ask_for_all_client :
            return None
        if self.key_in_listdict(self.asklocation, 'macaddr', mac) :
            return None
        if self.key_in_listdict(self.asked_location, 'macaddr', mac) :
            return None
        infos = {'macaddr' : mac, 'username' : username}
        self.asklocation.append(infos)
    def mark_sended_request(self, infos) :
        """ Move mac info from asklocation to asked_location"""
        self.asklocation.remove(infos)
        self.asked_location.append(infos)

    ### SERVICE ###
    def get_mac_from_user(self, username, mac) :
        """ Return the mac address of one user"""
        mac = self.normalizemac(mac)
        user = username.lower()
        if mac in self.servers_mac_addr :
            for session in self.remote_session :
                if session['username'] == user :
                    return self.normalizemac(session['mac_addr'])
        else :
            for i in self.direct_session :
                if i['username'] == user :
                    return self.normalizemac(i['macaddr'])
        return None
    def config_mac(self, username, location, mac) :
        """ Configure the location of mac"""
        real_mac = self.get_mac_from_user(username, mac)
        if real_mac is not None :
            config_manager.addmacaddr(real_mac, location)
        #Remove infos from list if it must do automaticaly
        if not self.ask_for_all_client :
            for i, j in enumerate(self.asked_location) :
                if j['username'] == username :
                    del self.asked_location[i]
    def remove_client(self, username) :
        user = username.lower()
        for i, j in enumerate(self.direct_session) :
            if j['username'] == user :
                self.remove_ask_mac(self.asklocation, self.normalizemac(j['macaddr']))
                self.remove_ask_mac(self.asked_location, self.normalizemac(j['macaddr']))
                del self.direct_session[i]
        for i, j in enumerate(self.remote_session) :
            if j['username'] == user :
                self.remove_ask_mac(self.asklocation, self.normalizemac(j['mac_addr']))
                self.remove_ask_mac(self.asked_location, self.normalizemac(j['mac_addr']))
        sys.stdout.write("[mac_srvc] cleaned infos for user {} from list request location\n".format(user))
        sys.stdout.flush()

    ### BACKEND TOOLS ###
    def update_server_infos(self) :
        """Get and save the mac address of rds servers"""
        infos = config_manager.getrdsconfig()
        self.servers, self.username, self.password = infos
        for i in range(len(self.servers)) :
            mac = get_mac_address(interface=INTERFACE, ip=self.servers[i])
            self.servers_mac_addr[i] = mac.replace(":", "").lower()
    def key_in_listdict(self, lst, key, val) :
        """Verify if value is a value of a key of a dictionnary"""
        for i in lst :
            if i[key] == val : return True
        return False
    def normalizemac(self, mac) :
        if mac is None : return None
        return mac.replace(':','').lower()
    def remove_ask_mac(self, lst, mac) :
        """ Remove infos from list with the mac"""
        mac = self.normalizemac(mac)
        for i, j in enumerate(lst) :
            if j['macaddr'] == mac :
                del lst[i]
    def writeerr(self, text) :
        text = text.replace('{DATE}', str(datetime.now()))
        sys.stderr.write(text)
        sys.stderr.flush()


if __name__ == "__main__" :
    service_mac = GetMacService()
    service_mac.start()
    for i in range(4) :
        sleep(10)
        for info in service_mac.actual_remote_session :
            print(info)
    service_mac.stop()
    service_mac.join()
