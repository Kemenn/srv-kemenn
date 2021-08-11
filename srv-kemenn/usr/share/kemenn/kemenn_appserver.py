#! /usr/bin/env python3
#coding: utf-8

import os
import sys
import socket
import select
import threading
import config_manager
import get_remote_mac
from time import sleep
from ast import literal_eval
from datetime import datetime

DEEP_CONFIG = "/etc/kemenn/kemenn"

class KemennServer(threading.Thread) :
    """ Il s'agit de l'objet principale qui gère la connexion des clients et l'envoie
    des messages entre les clients."""

    def __init__(self, *args, **kwargs) :
        threading.Thread.__init__(self)
        sys.stdout.write("[init] kemenn server...\n")
        sys.stdout.flush()
        self.live_server = True
        self.host = kwargs['HOST']
        self.port = kwargs['PORT']
        self.main_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.main_connection.bind((self.host, self.port))
        self.main_connection.listen(5)
        self.mac_service = get_remote_mac.GetMacService(*args, **kwargs)
        self.mac_service.start()
        config_manager.USE_LDAP = kwargs['USE_LDAP_SERVICE']
        self.client_waiting_accept = list()
        self.connected_client = dict() #{userid : socket}
        self.message_send_dict = dict()
        sys.stdout.write("Kemenn-server is running on {}:{}\n".format(self.host, self.port))
        sys.stdout.flush()

    def run(self) :
        """ Fonction qui lance le serveur principal et écoute l'arrivé des clients, des
        messages, etc...
        - Look if there is newest client and append it in client_waiting_accept list
        because if the client username is not concerned by the alert software, is
        connection is closed.
        - Look in the connected_client and client_waiting_accept if there is a message.
        if is the case, call the response_processing function. This function return a
        response message for the client or False.
        Look if spvs should be sent a message. For this, the mail reader write a file in
        ~/.cache/alerte/spvs
        - Look if the self.message_send_dict dictionnary is not empty, and create in this
        case a loop to send the message of all users who have need"""
        #sleep(74)
        sys.stdout.write("[started] kemenn server !\n")
        sys.stdout.flush()
        while self.live_server :
            #Looking if there is newest clients : append in self.client_waiting_accept list.
            asked_connections, wlist, xlist = select.select(
                [self.main_connection], [], [], 0.05)
            for connection in asked_connections :
                client_connection, infos_connection = connection.accept()
                self.client_waiting_accept.append(client_connection)

            #Looking if client have send message to server
            read_client = []
            if len(self.connected_client.values()) > 0 :
                read_client, wlist, xlist = select.select(
                    self.connected_client.values(), [], [], 0.05)
            if len(self.client_waiting_accept) > 0 :
                waiting_client = []
                waiting_client, wlist, xlist = select.select(
                    self.client_waiting_accept, [], [], 0.05)
                read_client += waiting_client
                del waiting_client
            for client in read_client :
                try : msg = literal_eval(self.code(client.recv(1024)))
                except SyntaxError : msg = {'type' : ""}
                except ConnectionResetError : msg = {'type' : ""}
                except OSError as e:
                    sys.stderr.write("[ERROR] {}".format(e))
                    sys.stderr.flush()
                    msg = {'type' : ""}
                sys.stdout.write("[{}]r {}\n".format(str(datetime.now()), msg))
                sys.stdout.flush()
                self.response_processing(client, msg)

            #Looking if server must send message for clients
            if len(self.message_send_dict) > 0 :
                client_message_deleted = []
                for client in self.message_send_dict.keys() :
                    message = self.message_send_dict[client]
                    client.send(self.code(message))
                    sys.stdout.write("[{}]s sending message \"{}\"\n".format(
                        str(datetime.now()), message))
                    sys.stdout.flush()
                    client_message_deleted.append(client)
                for client in client_message_deleted :
                    del self.message_send_dict[client]
                del client_message_deleted

            #Verifying if there is address mac no configured
            for infos in self.mac_service.asklocation :
                if infos['username'] in self.connected_client.keys() :
                    message = {'type' : "getlocation"}
                    message['sender'] = infos['username']
                    if 'location' in infos :
                        message['location'] = infos['location']
                    self.response_processing(
                        self.connected_client[infos['username']],
                        message)
                    self.mac_service.mark_sended_request(infos)

            threading.Event().wait(0.47)

        self.live_server = "stopped"


    def response_processing(self, client, msg) :
        """ Fonction qui lit le message du client et complète le dictionnaire
        self.message_send_dict avec la connexion du destinataire pour clé et le message
        pour la valeur. Il peut aussi agir sur la liste des clients pour les supprimers
        des connections courantes ou ajouter de nouvelles connexion. Les messages sont
        tous construit de la même manière : type_infos, avec les différentes
        informations séparées par des ";".
        - alert : une alerte vient d'être envoyé d'un client.
        - asklife : demande du client pour savoir s'il reste en vie car appartenant aux
        utilisateurs d'alerte.
        - spvs : une alerte du serveur de supervision doit être afficher pour les
        informaticiens.
        - alert_read : confirmation de lecture."""
        if msg['type'] == "alert" :
            sys.stdout.write("[{}]m alert from {}\n".format(msg['type'], msg['sender']))
            sys.stdout.flush()
            firstname, lastname = config_manager.getuserinfos(msg['sender'])[:2]
            real_mac = self.mac_service.get_mac_from_user(msg['sender'], msg['macaddr'])
            location = config_manager.getlocation(real_mac)
            response = {'type' : "alert",
                        'sender' : msg['sender'],
                        'message' : config_manager.getmessage('alert')}
            response['message'] = response['message'].replace("$FIRSTNAME", firstname
                                                    ).replace("$LASTNAME", lastname
                                                    ).replace("$LOCATION", location)
            receivers = config_manager.getreceivers(msg['sender'])
            self.append_message_send(response, receivers)
            self.append_message_send({'type' : "alert_sending",
                                      'message' : config_manager.getmessage('confirm').replace("$PERSONNES", " : personne")},
                                     [msg['sender']])

        elif msg['type'] == "alert_error" :
            firstname, lastname = config_manager.getuserinfos(msg['sender'])[:2]
            response = {'type' : 'alert_error',
                        'message' : config_manager.getmessage('error')}
            response['message'] = response['message'].replace("$FIRSTNAME", firstname
                                                    ).replace("$LASTNAME", lastname)
            receivers = config_manager.getreceivers(msg['sender'])
            self.append_message_send(response, receivers)

        elif msg['type'] == "asklife" :
            self.mac_service.init_client(msg['macaddr'], msg['sender'])
            if not config_manager.userexist(msg['sender']) :
                self.stop_client(client, msg['sender'])
            else :
                response = {'type' : "command",
                            'cmd' : "accepted"}
                self.connected_client[msg['sender']] = client
                self.message_send_dict[client] = response
            self.client_waiting_accept.remove(client)

        elif msg['type'] == "alert_read" :
            firstname, lastname = config_manager.getuserinfos(msg['sender'])[:2]
            response = {'type' : "alert_read",
                        'reader' : "{} {}".format(firstname, lastname)}
            self.append_message_send(response, [msg['receiver']])

        elif msg['type'] == "getlocation" :
            firstname, lastname = config_manager.getuserinfos(msg['sender'])[:2]
            response = {'type':"asklocation"}
            response['message'] = config_manager.getmessage('alert')
            response['message'] = response['message'].replace("$FIRSTNAME", firstname
                                                    ).replace("$LASTNAME", lastname
                                                    ).replace("$LOCATION", "[votre localisation]")
            if 'location' in msg : response['location'] = msg['location']
            self.append_message_send(response, [msg['sender']])

        elif msg['type'] == "config_location" :
            self.mac_service.config_mac(msg['sender'], msg['location'], msg['macaddr'])

        elif msg['type'] == "" :
            userid = self.get_userid_from_client(client)
            self.mac_service.remove_client(userid)
            sys.stdout.write("[{}]m client {} is disconnected\n".format(str(datetime.now()), userid))
            sys.stdout.flush()
            if len(userid) == 2 :
                self.client_waiting_accept.remove(client)
            elif userid is not None :
                del self.connected_client[userid]

        else :
            sys.stderr.write("[{}] not valide message from {} :\n{}".format(
                str(datetime.now()), client, msg))
            sys.stdout.flush()


    def append_message_send(self, message, receivers) :
        """ Prend un message et une liste de destinataires et ajoute
        au dictionnaire d'envoie chaque connexion utilisateur connecté
        et le message associé."""
        if type(receivers) != list :
            raise TypeError(
                "Error : append_message_send required a list of receivers. {} is {}".format(
                receivers, type(receivers)))
        for userid in receivers :
            if userid in self.connected_client.keys() :
                client = self.connected_client[userid]
                self.message_send_dict[client] = message

    def stop(self, action="shutdown") :
        """ Fonction qui stop toutes les connections avec tous les clients
        et qui stop le thread du server"""
        sys.stdout.write("[stopping] kemenn server...\n")
        sys.stdout.flush()
        #Fait le tour des clients pour leurs dire de s'arrêter/redémarrer...
        Client_disconnected = []
        for userid in self.connected_client.keys() :
            self.stop_client(self.connected_client[userid], userid, action=action, grouped=True)
            Client_disconnected.append(userid)
        for client in self.client_waiting_accept :
            self.stop_client(client, "unknow", action=action, grouped=True)
            Client_disconnected.append(client)
        while len(self.message_send_dict) > 0 : sleep(0.4)
        #Ferme les connexions des clients
        self.main_connection.close()
        for i in Client_disconnected :
            if i in self.connected_client.keys() :
                del self.connected_client[i]
            else :
                self.client_waiting_accept.remove(i)
        #Arrête la boucle principale du serveur
        self.live_server = False
        #Arrête le service d'indexation des adresses mac
        self.mac_service.stop()
        self.mac_service.join()
        while self.live_server != "stopped" : sleep(0.1)
        sys.stdout.write("[stopped] kemenn server !\n")
        sys.stdout.flush()

    def stop_client(self, client, userid, action="shutdown", grouped=False) :
        """ Fonction qui prend le nom d'utilisateur à déconnecter du
        serveur et lui dit de s'arrêter(shutdown)/de se redémarrer (
        restart)/de se mettre en attente maintenance (maintenance)."""
        message = {'type' : "command",
                   'cmd' : action}
        self.message_send_dict[client] = message
        sys.stdout.write("[{}]a send {} for {}\n".format(str(datetime.now()), action, userid))
        sys.stdout.flush()
        #En attente d'envoie des messages vers les clients
        if userid in self.connected_client.keys() and not grouped :
            self.connected_client[userid].close()

    def code(self, *args) :
        """ Fonction qui prend un/des arguments. Si il y en a un seul et de type 'byte' on
        le décode et on le renvoie en type 'str'. Sinon on assemble les arguments (si
        plusieurs) et on retourne une chaine de caractère encodé en 'byte'"""
        if len(args) == 1 and type(args[0]) == bytes :
            return args[0].decode()
        return "".join([str(i) for i in args]).encode()

    def get_userid_from_client(self, client) :
        """ Retourne le nom d'utilisateur dont on a reçus un message sans le nom
        d'utilisateur"""
        for userid in self.connected_client.keys() :
            if client == self.connected_client[userid] :
                return userid
        for userid in self.client_waiting_accept.keys() :
            if client == self.client_waiting_accept[userid] :
                return ("waiting", userid)
        return None


def autochangetype(value) :
    if value.isdigit() :
        return int(value)
    if value.replace('.', ' ').isdigit() :
        return float(value)
    if value == "True" : 
        return True
    if value == "False" :
        return False
    return value
def getdeepconfig() :
    config = {}
    with open(DEEP_CONFIG, 'r') as file :
        for i in file.readlines() :
            line = i[:i.index('#')] if '#' in i else i[:-1]
            line = line.strip(' ')
            if line != '' and line[0] != '#' :
                key, value = [i.strip(' ') for i in line.split('=')]
                config[key] = autochangetype(value)
    return config
def commandhand(server) :
    print("option : [stop|restart|maintenance|send <userid> <message>]")
    commande = ""
    while commande != "stop" :
        commande = str(input(">>> "))
        if commande == "stop" :
            server.stop()
        elif commande == "restart" :
            server.stop(action="restart")
            commande = "stop"
        elif commande == "maintenance" :
            server.stop(action="maintenance")
            commande = "stop"
        elif commande[:4] == "send" :
            infos = commande.split(" ")
            if infos[1] in server.connected_client.keys() :
                message = {'type' : "alert", 'sender' : 'server',
                           'message' : " ".join(infos[2:])}
                server.append_message_send(message, [infos[1].lower(),])
            else : print("{} not connected".format(infos[1]))
        elif commande != "" :
            print("Erreur : commande invalide")
            commande = ""
def commandfile(server) :
    commande_file = "/tmp/kemenn/command"
    if not os.path.exists(commande_file) :
        with open(commande_file, 'w') as file : pass
    commande = ""
    while commande != "stop input" :
        while commande == "" :
            sleep(5)
            with open(commande_file, 'r') as f :
                commande = f.readlines()[0][:-1]

        if commande == "stop" :
            server.stop()
            commande = "stop input"
        elif commande == "restart" :
            server.stop(action="restart")
            commande = "stop input"
        elif commande == "maintenance" :
            server.stop(action="maintenance")
            commande = "stop input"
        elif commande == "request_location start" :
            server.mac_service.switch_config_all_mac(status="start")
        elif commande == "request_location stop" :
            server.mac_service.switch_config_all_mac(status="stop")
        else :
            commande = "error"
            with open(commande_file, 'w') as f :
                f.write("unknow command")

        if commande != "error" :
            with open(commande_file, 'w') as f :
                commande = f.write("success")
        commande = ""

if __name__ == "__main__" :
    server = KemennServer(**getdeepconfig())
    server.start()
    sleep(1)
    if len(sys.argv) > 1 and sys.argv[1] == "command" :
        commandhand(server)
    else :
        commandfile(server)
    server.join()
