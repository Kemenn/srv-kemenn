#! /usr/bin/env python3
#coding: utf-8

import ldap

def connect_to_ldap(srv_ad, user_id, user_pwd, base_ad) :
    """ Fonction pour s'authetifier sur le serveur afin
    de faire des requêtes par la suite."""
    session = ldap.initialize(srv_ad)
    session.protocol_version = 3
    session.set_option(ldap.OPT_REFERRALS, 0)
    session.simple_bind_s(user_id+base_ad.replace("dc=", "@").replace(",@", "."), user_pwd)
    return session

def search_user(username, srv_ad, user_id, user_pwd, base_ad) :
    """ Fonction qui fait une recherche dans le serveur ldap
    et retourne le nom et prénom associé au nom d'utilisateur
    passé en paramètre. Retourne un tuple (Prénom, Nom)."""
    session = connect_to_ldap(srv_ad, user_id, user_pwd, base_ad)
    required_term = "(&(objectClass=user)(sAMAccountName={}))".format(username)
    returned_search = session.search_s(base_ad, ldap.SCOPE_SUBTREE, required_term, None)
    info_user = [entry for dn, entry in returned_search if isinstance(entry, dict)]
    if len(info_user) == 0 :
        return "The user does not exists : {}".format(username)
    elif len(info_user) == 1 :
        firstname = info_user[0]['sn'][0].decode()
        lastname = info_user[0]['givenName'][0].decode()
    elif len(info_user) == 2 :
        firstname = info_user[0][1]['sn'][0].decode()
        lastname = info_user[0][1]['givenName'][0].decode()
    return (" ".join([i.capitalize() for i in lastname.split(" ")]),
            " ".join([i.capitalize() for i in firstname.split(" ")]))

def userexists(username, srv_ad, user_id, user_pwd, base_ad) :
    """ Regarde si le serveur LDAP connais les infos sur l'utilisateur"""
    try :
        search_user(username)
        return True
    except :
        return False

if __name__ == "__main__" :
    import sys
    import config_manager
    ldap_addr, ldap_user, ldap_pass, ldap_base = config_manager.getldapconfig()
    #print("try with : {}/{}|{}@{}".format(ldap_addr,ldap_user,ldap_pass,ldap_base))
    searched_username = sys.argv[1]
    username = search_user(searched_username,
        ldap_addr, ldap_user, ldap_pass, ldap_base)
    print(username)
