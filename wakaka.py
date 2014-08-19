"""
Wakaka - a Whatsapp bot to link
Copyright 2014 Dody Suria Wijaya <dodysw@gmail.com>
MIT License
"""
import sys, base64, datetime, traceback, signal, threading, time
import config
sys.path.append('yowsup/src')
from Yowsup.connectionmanager import YowsupConnectionManager
from Yowsup.Common.debugger import Debugger

class Wakaka:
    disconnected = False
    
    def __init__(self):
        self.sendReceipts = True 
        self.groupMembership = {}
        self.groupParticipants = {}
        
        connectionManager = YowsupConnectionManager()
        connectionManager.setAutoPong(True)

        self.signalsInterface = connectionManager.getSignalsInterface()
        self.methodsInterface = connectionManager.getMethodsInterface()
        
        self.signalsInterface.registerListener("message_received", self.onMessageReceived)
        self.signalsInterface.registerListener("group_messageReceived", self.onGroupMessageReceived)
        self.signalsInterface.registerListener("group_subjectReceived", self.onGroupSubjectReceived)
        self.signalsInterface.registerListener("group_gotInfo", self.onGroupGotInfo)
        self.signalsInterface.registerListener("group_gotParticipants", self.onGroupGotParticipants)
        self.signalsInterface.registerListener("group_imageReceived", self.onGroupImageReceived)
        self.signalsInterface.registerListener("group_videoReceived", self.onGroupVideoReceived)
        self.signalsInterface.registerListener("group_audioReceived", self.onGroupAudioReceived)
        self.signalsInterface.registerListener("group_locationReceived", self.onGroupLocationReceived)
        self.signalsInterface.registerListener("group_vcardReceived", self.onGroupVcardReceived)

        self.signalsInterface.registerListener("notification_groupParticipantRemoved", self.onNotificationGroupParticipantRemoved)
        self.signalsInterface.registerListener("auth_success", self.onAuthSuccess)
        self.signalsInterface.registerListener("auth_fail", self.onAuthFailed)
        self.signalsInterface.registerListener("disconnected", self.onDisconnected)
        
        self.cm = connectionManager
    
    def login(self, username, password):
        self.username = username
        self.password = password
        self.methodsInterface.call("auth_login", (self.username, self.password))
        
        while True:
            time.sleep(5)
            if self.disconnected:
                self.disconnected = False
                self.methodsInterface.call("auth_login", (self.username, self.password))

    def onAuthSuccess(self, username):
        print("Authed %s" % username)
        self.methodsInterface.call("ready")
        self.methodsInterface.call("group_getGroups", ('participating',))

    def onAuthFailed(self, username, err):
        print("Auth Failed!")

    def onDisconnected(self, reason):
        print("Disconnected because %s" %reason)
        self.disconnected = True

    def onMessageReceived(self, messageId, jid, messageContent, timestamp, wantsReceipt, pushName, isBroadCast):
        formattedDate = datetime.datetime.fromtimestamp(timestamp).strftime('%d-%m-%Y %H:%M')
        print("%s [%s]: MESSAGE RECEIVED: %s"%(jid, formattedDate, messageContent))

        if wantsReceipt and self.sendReceipts:
            self.methodsInterface.call("message_ack", (jid, messageId))

        if messageContent == 'info':
            #self.methodsInterface.call("group_getInfo", (self.username + '@s.whatsapp.net',))
            #self.methodsInterface.call("presence_request", (self.username + '@s.whatsapp.net',))
            pass


    def onGroupMessageReceived(self, messageId, jid, author, messageContent, timestamp, wantsReceipt, pushName):
        formattedDate = datetime.datetime.fromtimestamp(timestamp).strftime('%d-%m-%Y %H:%M')
        print("%s [%s]: GROUP MESSAGE RECEIVED: %s (%s | %s | %s)" % (jid, formattedDate, messageContent, messageId, author, pushName))

        #distributing message to the rest of the memberships
        if author != (self.username + '@s.whatsapp.net'):
            for gid in self.groupMembership:
                if gid != jid:
                    msgId = self.methodsInterface.call("message_send", (gid, "%s: %s" % (pushName, messageContent)))

        if wantsReceipt and self.sendReceipts:
            self.methodsInterface.call("message_ack", (jid, messageId))

    def onGroupImageReceived(self, messageId, jid, author, preview, url, size, receiptRequested):
        if author != (self.username + '@s.whatsapp.net'):
            for gid in self.groupMembership:
                if gid != jid:
                    self.methodsInterface.call("message_imageSend", (gid, url, author, size, preview))

    def onGroupVideoReceived(self, messageId, jid, author, preview, url, size, receiptRequested):
        if author != (self.username + '@s.whatsapp.net'):
            for gid in self.groupMembership:
                if gid != jid:
                    self.methodsInterface.call("message_videoSend", (gid, url, author, size, preview))

    def onGroupAudioReceived(self, messageId, jid, author, url, size, receiptRequested):
        if author != (self.username + '@s.whatsapp.net'):
            for gid in self.groupMembership:
                if gid != jid:
                    self.methodsInterface.call("message_audioSend", (gid, url, author, size))

    def onGroupLocationReceived(self, messageId, jid, author, name, preview, latitude, longitude, receiptRequested):
        if author != (self.username + '@s.whatsapp.net'):
            for gid in self.groupMembership:
                if gid != jid:
                    self.methodsInterface.call("message_locationSend", (gid, latitude, longitude, preview))

    def onGroupVcardReceived(self, messageId, jid, author, name, data, receiptRequested):
        if author != (self.username + '@s.whatsapp.net'):
            for gid in self.groupMembership:
                if gid != jid:
                    self.methodsInterface.call("message_vcardSend", (gid, data, name))

    def onGroupSubjectReceived(self, messageId, jid, author, subject, timestamp, receiptRequested):
        formattedDate = datetime.datetime.fromtimestamp(timestamp).strftime('%d-%m-%Y %H:%M')
        print("%s [%s]: SUBJECT RECEIVED: %s (%s | %s)" % (jid, formattedDate, subject, messageId, author))

        self.groupMembership[jid] = subject

        print "Members: %s" % ','.join(self.groupMembership.values())

        if receiptRequested and self.sendReceipts:
            self.methodsInterface.call("message_ack", (jid, messageId))

    def onNotificationGroupParticipantRemoved(self, groupJid, jid, author, timestamp, messageId, receiptRequested):
        if groupJid in self.groupMembership:
            print "Deleting membership from ", self.groupMembership[groupJid]
            del self.groupMembership[groupJid]

    def onGroupGotInfo(self, jid, owner, subject, subjectOwner, subjectTimestamp, creationTimestamp):
        self.groupMembership[jid] = subject
        print "Members: %s" % ','.join(self.groupMembership.values())
        self.methodsInterface.call("group_getParticipants", (jid,))

    def onGroupGotParticipants(self, jid, jids):
        self.groupParticipants[jid] = jids
        print "Group %s participants: %s" % (jid, jids)


def dumpstacks(signal, frame):
    id2name = dict([(th.ident, th.name) for th in threading.enumerate()])
    code = []
    for threadId, stack in sys._current_frames().items():
        code.append("\n# Thread: %s(%d)" % (id2name.get(threadId,""), threadId))
        for filename, lineno, name, line in traceback.extract_stack(stack):
            code.append('File: "%s", line %d, in %s' % (filename, lineno, name))
            if line:
                code.append("  %s" % (line.strip()))
    print "\n".join(code)

if __name__ == "__main__":
    password = base64.b64decode(bytes(config.password.encode('utf-8')))
    Debugger.enabled = True

    signal.signal(signal.SIGQUIT, dumpstacks)

    w = Wakaka()
    w.login(config.phone, password)
