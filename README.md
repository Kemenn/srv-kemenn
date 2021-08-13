# Kemenn Server

The server for Kemenn project.

This server allows to manage the client connections and their configurations in a centralized way. A simple web interface is proposed.

You can found more technical details on documentation : https://github.com/Kemenn/documentation.git

- [DESCRIPTION](#description)
- [INSTALLATION](#installation)
- [CONFIGURATION](#configuration)
- [TODO TASKS](#todo-tasks)



## Description


### Web interface

#### · messages management
There is the message send display on window of clients. The alert message is the message that appears for users who are asked for help. The confirm message is the message that appears when you have send an alert. The error message is the message that will be displayed if the alert that has just been sent is an error on the part of the user.

The following variables will be replaced by the information of the person from whom the message comes.

  - $FIRSTNAME : replace by firstname
  - $LASTNAME : replace by lasttname
  - $LOCATION : replace by location

#### · groups management

To understand the utility, [read the client documentation](https://github.com/Kemenn/clt-kemenn#user-group-)
There is no space before or after the commas that separate the usernames composing the group.

`groupname = user1,user2,etc...`

#### · Location management
mac address is configure in lower case without the separation by ":".

`mac_adress = description of location`

#### · Contact management
Makes the correspondence between the user name and the human first name.

#### · Management of the kemenn server parameters
First, you can set the password to access at web interface.

Then, there is the necessary informations to send requests at LDAP service when there is an alert.

Information needed to keep the list of active sessions up to date when using a thin client infrastructure. If you do not use such an infrastructure, you can leave this section blank.

You are more parameters in files. [See documentation.](#configuration)


### Command interface

There is lot of command to control the kemenn service (is not a system service...).

| Command name | Description of action |
| :----------- | :-------------------- |
| kemenn start | Start the kemenn service. If there is started, return an error. |
| kemenn stop  | Stop connection with all clients. Client is shutting down. Then the service is stopped. |
| kemenn restart | Ask at client to stop connection few seconds. The the service is stopped. You are a little time to restart it with first command |
| kemenn maintenance | Ask at client to stop connection few minute before retry to connect. You are few minute to make a maintenance |

You can start kemenn service at the hand with this command : `python3 /usr/share/kemenn/kemenn_appserver.py command`

The same commands as described above are then available without the first word "kemenn". But there is an other command available to send a message to a specific user : `send [username] [a message for username]`. This command not yet available from alert command.

*Note* : you can set many parameters in client before installation to configure time for maintenance, number of try to connect, etc... [documentation here](https://github.com/Kemenn/clt-kemenn#configuration)



## Installation

The installation is done in two steps: creating a debian package, then installing it.

**Python dependancy :**
`ast, configparser, datetime, flask, getmac, hashlib, ldap, os, pypsrp, random, re, select, socket, sys, threading, time`


### Linux (debian based) :

- Download and create the debian package :

```
apt install -y git
git clone https://github.com/Kemenn/srv-kemenn.git
cd srv-kemenn/
chmod +x srv-kemenn_to_deb.sh
./srv-kemenn_to_deb.sh
```
- Install the package on your system :

```
apt install -y ./srv-kemenn.deb
```
*Note* : Installation tested only on debian. It should not be a problem on a derived system. On the other hand for the other linux some modifications may be necessary.


### Windows :
I have no time. Install Linux and refer to the previous step...



## Configuration

You can set many parameters in web interface. [Read this](#web-interface) to configure.

There is 3 configurations files in */etc/kemenn* directory :

 * **kemenn** : The configuration need a restart of service.
  * HOST : the ip or hostname used by kemenn service.
  * PORT : the port used by kemenn service.
  * SEARCH_MAC _RDP _CLIENTS : if you use rds system, set this value to True.
  * MAC _SERVICE _TIME : time between two scan of session on rds servers.
  * USE _LDAP _SERVICE : set this value to True if you want to use an ldap directory to found firstname and lastname of users.

 * **clt-kemenn** : The informations used to display message on client.
  * Message (alert, confirm, error) : You can set the message display in graphical window by type.
  * Groups : To set groups of users.
  * Location : To set the correspondance between a mac with a human location. When a users connect with a computer for the first time, a localisation name is asked and save in this part.
  * Contact : To set the correspondance between a username with the humans name of a person when not in ldap.

 * **srv-kemenn** : The informations used by server service.
  * password : the hash of password used for access configuration webpage.
  * Ldap (adress or ip, username, password, base) : the necessary informations to use an ldap services. Users can be a simple user without admin rights.
  * Rds (adress or ip list, username, password) : the necessary informations needed to keep the list of current rds server sessions up to date.



## Todo Tasks

 - Send another message when there is no receivers of the alert.

 - Allow possibility to send message to a specific client by command interface.
 
 - Remake the indexation of current session of rds...