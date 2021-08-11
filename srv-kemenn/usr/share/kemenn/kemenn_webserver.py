#! /usr/bin/env python3
#coding: utf-8

from config_manager import *
from flask import Flask, render_template, request, redirect, abort, url_for

app = Flask(__name__)

password = ""
global connected
connected = False
global config
client_config = {
    "alert_msg" : None,         #str
    "confirm_msg" : None,       #str
    "error_msg" : None,         #str
    "general_group" : None,     #str : userid1,userid2
    "other_groups" : None,      #dict : {groupname : userid3,userid4, groupname2 : str}
    "default_location" : None,  #str
    "unknow_location" : None,   #str
    "other_locations" : None,   #dict : {macaddr : location_name, macaddr2 : str}
    "contacts" : None}          #dict : {userid : Firstname,Lastname, userid2 : str}


                                                            ###########################
                                                            ### CONFIGURATION TOOLS ###
                                                            ###########################
def refresh_client_config() :
    """ Met à jour le dictionnaire de la configuration
    cliente."""
    global client_config
    #message configuration
    client_config["alert_msg"] = getmessage('alert')
    client_config["confirm_msg"] = getmessage('confirm')
    client_config["error_msg"] = getmessage('error')
    #sort group
    groups = getgroups()
    client_config["general_group"] = ",".join(groups["general"])
    del groups["general"]
    client_config["other_groups"] = groups
    for k in client_config["other_groups"] :
        client_config["other_groups"][k] = ",".join(client_config["other_groups"][k])
    #sort location
    locations = getconfloc()
    client_config["default_location"] = locations["default"]
    client_config["unknow_location"] = locations["unknow"]
    del locations["default"], locations["unknow"]
    client_config["other_locations"] = locations
    #contatcs configuration
    client_config["contacts"] = getcontacts()
    for k in client_config["contacts"] :
        client_config["contacts"][k] = ",".join(client_config["contacts"][k])


                                                            #######################
                                                            ### CONNECTION PAGE ###
                                                            #######################
@app.route('/')
def login(text="") :
    """ Page qui demande le mot de passe de connection"""
    return render_template('login.html', additional_message=text)
@app.route('/logout', methods=['POST'])
def logout() :
    """Page qui déconnecte l'utilisateur """
    global connected
    if not connected :
        return redirect(url_for('login'))
    connected = False
    return login(text="Vous êtes déconnecté.")
@app.route('/authentication', methods=['POST'])
def authentication() :
    """ Page qui autorise l'accès à la configuration, seulement si le mot de
    passe est bon et que personne n'est déjà connecté """
    global connected
    if validpassword(request.form['password']) and not connected :
        connected = True
        return redirect(url_for('configuration'))
    else :
        return login(text="Mauvais mot de passe.")


                                                          ############################
                                                          ### CLIENT CONFIGURATION ###
                                                          ############################    
@app.route('/configuration', methods=['GET', 'POST'])
def configuration() :
    """ Page qui fait la liste de la configuration """
    if not connected :
        return login(text="Veuillez d'abord vous connecter")
    refresh_client_config()
    global client_config
    return render_template('configuration.html',
        alert_message=client_config["alert_msg"],
        confirm_message=client_config["confirm_msg"],
        error_message=client_config["error_msg"],
        general_users=client_config["general_group"],
        groups=client_config["other_groups"],
        contacts=client_config["contacts"],
        default_location=client_config["default_location"],
        unknow_location=client_config["unknow_location"],
        locations=client_config["other_locations"],)
@app.route('/appli_config', methods=['POST', 'GET'])
def appli_config() :
    """ Applique la configuration au fichier clt_config.ini"""
    global client_config
    #Config messages
    setmessages("alert", request.form['alert_msg'])
    setmessages("confirm", request.form['confirm_msg'])
    setmessages("error", request.form['error_msg'])
    #Config contact
    for contact in client_config['contacts'].keys() :
        new_contact_name = request.form["{}_id".format(contact)]
        new_contact_info = request.form["{}_names".format(contact)]
        if new_contact_name == "" : rmuser(contact)
        else :
            if new_contact_name != contact : rmuser(contact)
            adduser(new_contact_name, new_contact_info)
    if request.form['new_contact'] != "" :
        adduser(request.form['new_contact'],
                request.form['new_name'])
    #Config groups
    setgroup("general", request.form['general_usr'])
    for group in client_config["other_groups"].keys() :
        new_group_name = request.form["{}_groupname".format(group)]
        new_group_users = request.form["{}_usersvalue".format(group)]
        if new_group_name == "" : rmgroup(group)
        else :
            if new_group_name != group : rmgroup(group)
            setgroup(new_group_name, new_group_users)
    if request.form['new_group'] != "" :
        setgroup(request.form['new_group'], request.form['new_users'])
    #Config locations
    addmacaddr("default", request.form['default_location'])
    addmacaddr("unknow", request.form['unknow_location'])
    for macaddr in client_config["other_locations"].keys() :
        new_mac_addr = request.form["{}_mac".format(macaddr)]
        new_mac_loca = request.form["{}_location".format(macaddr)]
        if new_mac_addr == "" : rmmac(macaddr)
        else :
            if new_mac_addr != macaddr : rmmac(macaddr)
            addmacaddr(new_mac_addr, new_mac_loca)
    if request.form['new_macaddr'] != "" :
        addmacaddr(request.form['new_macaddr'],
                   request.form['new_location'])

    return redirect(url_for('configuration'))


                                                          ###########################
                                                          ### ADMIN CONFIGURATION ###
                                                          ###########################
@app.route('/configuration_admin', methods=['GET', 'POST'])
def configuration_admin() :
    """ Page qui fait la liste de la configuration """
    if not connected :
        return login(text="Veuillez d'abord vous connecter")
    else :
        ldap_conf = getldapconfig()
        rds_conf = getrdsconfig()
        return render_template('configuration_admin.html',
            ldap_address=ldap_conf[0],
            ldap_username=ldap_conf[1],
            ldap_password=ldap_conf[2],
            ldap_base=ldap_conf[3],
            list_rds=",".join(rds_conf[0]),
            rds_username=rds_conf[1],
            rds_password=rds_conf[2])

@app.route('/appli_admin_config', methods=['GET', 'POST'])
def appli_admin_config() :
    """ Applique la nouvelle configuration administrateur"""
    if request.form['new_password'] != "" :
        setpassword(request.form['new_password'])
    setldapconfig(
        request.form['new_ldap_address'],
        request.form['new_ldap_username'],
        request.form['new_ldap_password'],
        request.form['new_ldap_base'])
    setrdsconfig(
        request.form['new_list_rds'].replace(" ", "").split(","),
        request.form['new_rds_username'],
        request.form['new_rds_password'])
    return redirect(url_for('configuration_admin'))

if __name__ == "__main__" :
    app.run()
