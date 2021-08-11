#! /usr/bin/env python3
#coding: utf-8

""" Module chargé de lire ou écrire la configuration dans les fichiers de
configurations srv_config.ini et clt_config.ini."""

import os
import sys
import hashlib
import ldap_client
import configparser
from time import sleep
from random import randint, sample

srv_path = "/etc/kemenn/srv_config.ini"
clt_path = "/etc/kemenn/clt_config.ini"
USE_LDAP = True


def adduser(userid, infos) :
    """ Ajoute un utilisateur dans le fichier de configuration. Prend un
    string qui doit comprendre au minimum "firstname, lastname". Les
    caractères de séparation sont : ", " """
    cfg = configparser.ConfigParser()
    cfg.read(clt_path)
    if len(infos.split(",")) < 2 :
        sys.stderr.write(
        "Argument {} is to short. Required a minimum of 2 informations : firstname, lastname".format(
        infos))
        sys.stderr.flush()
    elif len(infos.split(",")) > 3 :
        sys.stderr.write(
        "Argument {} is to big. Required a maximum of 3 informations : firstname, lastname, phone number".format(
        infos))
        sys.stderr.flush()
    if contactexist(userid) : rmuser(userid)
    cfg.set('Contacts', userid.lower(), infos.replace(" ", "").replace(",", ", "))
    cfg.write(open(clt_path, 'w'))
def addgroup(group) :
    """ Créer un nouveau groupe dans la configuration"""
    cfg = configparser.ConfigParser()
    cfg.read(clt_path)
    cfg.set('Groups', group.lower(), 'None')
    cfg.write(open(clt_path, 'w'))
def addusergroup(userid, group, user_infos="") :
    """ Ajoute un utilisateur dans un groupe. Si
    l'utilisateur n'existe pas il tente de le créer."""
    if not uservalid(userid) and user_infos != "" :
        adduser(userid, user_infos)
    cfg = configparser.ConfigParser()
    cfg.read(clt_path)
    users = cfg.get('Groups', group.lower())
    if users == 'None' : users = userid
    elif not userid in users : users = "{},{}".format(users, userid.lower())
    cfg.set('Groups', group.lower(), users)
    cfg.write(open(clt_path, 'w'))
def setgroup(group_name, users) :
    """ Configure un groupe. S'il existe, met à jour les utilisateurs.
    S'il n'existe pas, créer le groupe et ajoute les utilisateurs."""
    if not groupexist(group_name) :
        addgroup(group_name)
    users = users.replace(" ,", ",").replace(", ", ",").replace(" ", ",")
    cfg = configparser.ConfigParser()
    cfg.read(clt_path)
    cfg.set('Groups', group_name.lower(), users.lower())
    cfg.write(open(clt_path, 'w'))
def addmacaddr(macaddr, location) :
    """ Ajoute une adresse mac et la localisation qui lui est associé"""
    if macexist(macaddr) :
        rmmac(macaddr)
    cfg = configparser.ConfigParser()
    cfg.read(clt_path)
    cfg.set('Locations', macaddr.replace(":", "").lower(), location)
    cfg.write(open(clt_path, 'w'))
def setmessages(msg_type, message) :
    """ Configure les messages """
    cfg = configparser.ConfigParser()
    cfg.read(clt_path)
    if not msg_type in cfg.options('Messages') :
        sys.stderr.write("{} is not a valide type message : {}".format(msg_type, cfg.options('Messages')))
        sys.stderr.flush()
    cfg.set('Messages', msg_type, message)
    cfg.write(open(clt_path, 'w'))
def setpassword(chaine) :
    """Chiffre et enregistre le mot de passe"""
    cfg = configparser.ConfigParser()
    cfg.read(srv_path)
    from string import printable
    random_sel = "".join(sample(printable[:-6].replace("$%",""), randint(40,70)))
    hashed_password = hashlib.sha256((random_sel+chaine).encode('utf-8')).hexdigest()
    cfg.set('General', 'admin', "{}${}".format(hashed_password, random_sel))
    cfg.write(open(srv_path, 'w'))
def setldapconfig(addr, username, password, base) :
    """ Configure les paramètres LDAP """
    cfg = configparser.ConfigParser()
    cfg.read(srv_path)
    cfg.set('Ldap', 'ldap_address', addr)
    cfg.set('Ldap', 'ldap_username', username)
    cfg.set('Ldap', 'ldap_password', password.replace("%", "$percent"))
    cfg.set('Ldap', 'ldap_base', base)
    cfg.write(open(srv_path, 'w'))
def setrdsconfig(servers, username, password) :
    """ Configure les paramètres d'accessibilité Rds """
    if type(servers) != list :
        sys.stderr.write("Error, the servers ip should be a list type : {}.".format(type(servers)))
        sys.stderr.flush()
    cfg = configparser.ConfigParser()
    cfg.read(srv_path)
    cfg.set('Rds', 'list_rds', ",".join(servers))
    cfg.set('Rds', 'username', username)
    cfg.set('Rds', 'password', password.replace("%", "$percent"))
    cfg.write(open(srv_path, 'w'))

def getcontacts() :
    """ Renvoie la configuration des contacts"""
    cfg = configparser.ConfigParser()
    cfg.read(clt_path)
    contacts = {}
    for userid in cfg.options("Contacts") :
        contacts[userid] = getuserinfos(userid, ldap=False)
    return contacts
def getuserinfos(userid, ldap=True) :
    """ Renvoie le tuple des infos sur le contact"""
    if ldap and USE_LDAP :
        try :
            info = ldap_client.search_user(userid, *getldapconfig())
            if not "The user does not exists" in info :
                return info
            else :
                return getuserinfos(userid, ldap=False)
        except : return getuserinfos(userid, ldap=False)
    cfg = configparser.ConfigParser()
    cfg.read(clt_path)
    if contactexist(userid) :
        return (cfg.get('Contacts', userid).split(', '))
    sys.stderr.write("Error, the {} user's does not exists\n".format(userid))
    sys.stderr.flush()
    return ("inconnue", "inconnue")
def getgrouplist() :
    """ Renvoie la liste des groupes"""
    cfg = configparser.ConfigParser()
    cfg.read(clt_path)
    return cfg.options('Groups')
def getusergroups(userid) :
    """ Renvoie la liste des groupes auquel appartient l'utilisateur"""
    if not userexist(userid) :
        sys.stderr.write("Error, the {} user does not exists\n".format(userid))
        sys.stderr.flush()
    cfg = configparser.ConfigParser()
    cfg.read(clt_path)
    groups = cfg.options('Groups')
    usergroups = []
    for group in groups :
        if userid.lower() in cfg.get('Groups', group) :
            usergroups.append(group)
    return usergroups
def getgroupusers(group) :
    """ Renvoie la liste des utilisateurs d'un groupe spécifié """
    if not groupexist(group) :
        sys.stderr.write("Error, the group {} does not exists\n".format(group))
        sys.stderr.flush()
    cfg = configparser.ConfigParser()
    cfg.read(clt_path)
    return cfg.get('Groups', group.lower()).split(",")
def getgroups() :
    """ Renvoie la configuration des groupes"""
    cfg = configparser.ConfigParser()
    cfg.read(clt_path)
    groups = {}
    for i in cfg.options('Groups') :
        groups[i] = getgroupusers(i)
    return groups
def getreceivers(userid, add_global_group=True) :
    """ Revoie la liste des utilisateurs appartenant à ses groupes"""
    cfg = configparser.ConfigParser()
    cfg.read(clt_path)
    groups = getusergroups(userid)
    receivers = []
    for g in groups :
        users = getgroupusers(g)
        for u in users :
            if u != userid.lower() and not u in receivers :
                receivers.append(u)
    if not 'general' in groups and add_global_group :
        users = getgroupusers('general')
        for u in users :
            if u != userid.lower() and not u in receivers :
                receivers.append(u)
    return receivers
def getmessage(msg_type) :
    """ Renvoie le message qui doit être affiché """
    cfg = configparser.ConfigParser()
    cfg.read(clt_path)
    if not msg_type in cfg.options('Messages') :
        sys.stderr.write("{} is not a valide type message : {}".format(msg_type, cfg.options('Messages')))
        sys.stderr.flush()
    return cfg.get('Messages', msg_type)
def getmaclist() :
    """ Renvoie la liste des adresses mac enregistrées"""
    cfg = configparser.ConfigParser()
    cfg.read(clt_path)
    return cfg.options('Locations')
def getlocation(macaddr) :
    """ Renvoie la localisation lié à une adresse mac"""
    cfg = configparser.ConfigParser()
    cfg.read(clt_path)
    if macaddr is None :
        return cfg.get('Locations', 'default')
    elif not macexist(macaddr) :
        sys.stderr.write("Error, the mac address {} does not exists\n".format(macaddr))
        sys.stderr.flush()
        return cfg.get('Locations', 'unknow')
    return cfg.get('Locations', macaddr)
def getconfloc() :
    """ Renvoie la configuration total des localisations"""
    cfg = configparser.ConfigParser()
    cfg.read(clt_path)
    location = {}
    for i in cfg.options('Locations') :
        location[i] = getlocation(i)
    return location
def getwebpassword() :
    """ Renvoie le mot de passe et son sel pour accèder
    à l'interface de configuration"""
    cfg = configparser.ConfigParser()
    cfg.read(srv_path)
    if not "$" in cfg.get('General', 'admin') :
        return "", ""
    return cfg.get('General', 'admin').split("$")
def getldapconfig() :
    """ Renvoie la configuration ldap actuelle"""
    cfg = configparser.ConfigParser()
    cfg.read(srv_path)
    try :
        return (cfg.get('Ldap', 'ldap_address'),
            cfg.get('Ldap', 'ldap_username'),
            cfg.get('Ldap', 'ldap_password').replace("$percent", "%"),
            cfg.get('Ldap', 'ldap_base'))
    except :
        sleep(0.4)
        return getldapconfig()
def getrdsconfig() :
    """ Renvoie la configuration nécessaire pour
    accèder aux rds"""
    cfg = configparser.ConfigParser()
    cfg.read(srv_path)
    try :
        return (cfg.get('Rds', 'list_rds').split(","),
            cfg.get('Rds', 'username'),
            cfg.get('Rds', 'password').replace("$percent", "%"))
    except :
        sleep(0.4)
        return getrdsconfig()
def contactexist(userid) :
    """ Vérifie l'existance du contact """
    cfg = configparser.ConfigParser()
    cfg.read(clt_path)
    if userid in cfg.options('Contacts') :
        return True
    return False
def uservalid(userid) :
    """ Vérifie que le nom d'utilisateur est valide."""
    if ldap_client.userexists(userid, *getldapconfig()) :
        return True
    elif contactexist(userid) :
        return True
    return False
def userexist(userid) :
    """ Vérifie l'existence de l'utilisateur dans les groupes"""
    cfg = configparser.ConfigParser()
    cfg.read(clt_path)
    groups = getgrouplist()
    for group in groups :
        if userid.lower() in getgroupusers(group) :
            return True
    return False
def groupexist(group) :
    """ Vérifie l'existence d'un groupe"""
    cfg = configparser.ConfigParser()
    cfg.read(clt_path)
    if not group.lower() in cfg.options('Groups') :
        return False
    return True
def macexist(macaddr) :
    """ Vérifie l'existence d'une adresse mac """
    cfg = configparser.ConfigParser()
    cfg.read(clt_path)
    if not macaddr.replace(":", "").lower() in cfg.options('Locations') :
        return False
    return True
def validpassword(chaine) :
    """ Vérifie si la chaine est bien le mot de passe"""
    saved_pass, saved_sel = getwebpassword()
    if saved_pass == "" and saved_sel == "" :
        return True
    hashed_password = hashlib.sha256((saved_sel+chaine).encode('utf-8')).hexdigest()
    if hashed_password == saved_pass :
        return True
    return False
def rmgroup(group) :
    """ Supprime un groupe """
    cfg = configparser.ConfigParser()
    cfg.read(clt_path)
    cfg.remove_option('Groups', group.lower())
    cfg.write(open(clt_path, 'w'))
def rmuser(userid) :
    """ Supprime un contact """
    cfg = configparser.ConfigParser()
    cfg.read(clt_path)
    cfg.remove_option('Contacts', userid.lower())
    cfg.write(open(clt_path, 'w'))
def rmmac(macaddr) :
    """ Supprime une LOCATION """
    cfg = configparser.ConfigParser()
    cfg.read(clt_path)
    cfg.remove_option('Locations', macaddr.replace(":", "").lower())
    cfg.write(open(clt_path, 'w'))

def create_configuration_if_not_exists() :
    """Si les fichiers de configuration n'existe pas, création de ceux-ci"""
    if not os.path.exists(srv_path) :
        sys.stdout.write("Create file configuration for kemenn server in /etc/kemenn\n")
        sys.stdout.flush()
        cfg = configparser.ConfigParser()
        #General configuration
        cfg.add_section('General')
        cfg.set('General', 'admin', "password")
        #Conf to get information on LDAP server
        cfg.add_section('Ldap')
        cfg.set('Ldap', 'ldap_address', "ldap://ip_address-or-hostname")
        cfg.set('Ldap', 'ldap_username', "username")
        cfg.set('Ldap', 'ldap_password', "password")
        cfg.set('Ldap', 'ldap_base', "dc=domain,dc=local")
        #Conf to get sessions informations on RDS servers
        cfg.add_section('Rds')
        cfg.set('Rds', 'list_rds', "192.168.1.2,192.168.1.3")
        cfg.set('Rds', 'username', "username")
        cfg.set('Rds', 'password', "password")
        #Conf to send SMS notification
#        cfg.add_section('SMS')
#        cfg.set('SMS', 'phone_number', "None")
#        cfg.set('SMS', 'url_sender', "None")
        if not os.path.exists(os.path.dirname(srv_path)) :
            os.makedirs(os.path.dirname(srv_path))
        cfg.write(open(srv_path, 'w'))

    if not os.path.exists(clt_path) :
        sys.stdout.write("Create file configuration for kemenn clients in /etc/kemenn\n")
        sys.stdout.flush()
        cfg = configparser.ConfigParser()
        # Configuration of displayed message
        cfg.add_section('Messages')
        cfg.set('Messages', 'alert',
            "Alerte, $FIRSTNAME $LASTNAME est en danger à $LOCATION !")
        cfg.set('Messages', 'confirm',
            "L'alerte a bien été envoyée. Elle a été lue par $PERSONNES'")
        cfg.set('Messages', 'error',
            "Erreur, veuillez ignorer le message d'alerte de $FIRSTNAME $LASTNAME.'")
        # Configuration of groups
        cfg.add_section('Groups')
        cfg.set('Groups', 'general', "firstuserid,seconduserid")
        # Configuration des localisations
        cfg.add_section('Locations')
        cfg.set('Locations', 'default', "un endroit")
        cfg.set('Locations', 'unknow', "un endroit inconnu")
        cfg.set('Locations', '000000000000', "un bureau")
        # Configuration des noms prénoms (si pas dans l'ad)
        cfg.add_section('Contacts')
        cfg.set('Contacts', 'userid', "Personne, Inconnue")
        if not os.path.exists(os.path.dirname(clt_path)) :
            os.makedirs(os.path.dirname(clt_path))
        cfg.write(open(clt_path, 'w'))

def test_clt_conf() :
    user_id = "userid_test"
    username = "Firstname, Lastname"
    group_test = "GroupTest"
    mac_addr = "85:79:90:5C:98:18"
    location_test = "Un endroit de test"
    msg_type = "alert" #alert/confirm/error
    message_alerte = "Ceci est une alerte du logiciel : $FIRSTNAME $LASTNAME $LOCATION"

    adduser(user_id, username)
    addgroup(group_test)
    addusergroup(user_id, group_test) #user_infos=username : to create user if not exists
    addmacaddr(mac_addr, location_test)
    setmessages(msg_type, message_alerte)

    print("1 -", getuserinfos(user_id))
    print("2 -", getgrouplist())
    print("3 -", getusergroups(user_id))
    print("4 -", getgroupusers(group_test))
    print("5 -", getgroups())
    print("6 -", getreceivers(user_id, add_global_group=False))
    print("7 -", getmessage(msg_type))
    print("8 -", getlocation(mac_addr))
    print("9 -", getconfloc())

    rmgroup(group_test)
    rmuser(user_id)
    rmmac(mac_addr)

def test_srv_conf() :
    web_interface_pass = "interface_password"
    ldap_addr = "192.168.1.2"
    ldap_user = "administrateur"
    ldap_password = "un_password"
    ldap_base = "dc=mydomain,dc=local"
    rds_server_list = ["192.168.1.3", "192.168.1.4"]
    rds_user = "one_user" #required full access of powershell
    rds_pswd = "one_pass"

    setpassword(web_interface_pass)
    setldapconfig(ldap_addr, ldap_user, ldap_password, ldap_base)
    setrdsconfig(rds_server_list, rds_user, rds_pswd)

    print("1 -", getwebpassword())
    print("2 -", getldapconfig())
    print("3 -", getrdsconfig())
    print("4 -", validpaddword(web_interface_pass), "/", validpaddword("wrong_pass"))

if __name__ == "__main__" :
    create_configuration_if_not_exists()
