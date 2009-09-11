from google.appengine.api import xmpp
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

from google.appengine.ext import db
from google.appengine.api import users

import re
import datetime
from xml.sax.saxutils import escape

class ChatUser(db.Model):
  jid = db.StringProperty(required=True)
  nick = db.StringProperty(required=True)
  status = db.StringProperty(required=True)
  created_at = db.DateTimeProperty()
  last_online_at = db.DateTimeProperty()

class MessageLog(db.Model):
  from_jid = db.StringProperty()
  from_full_jid = db.StringProperty()
  body = db.StringProperty()
  created_at = db.DateTimeProperty()

class XMPPHandler(webapp.RequestHandler):
  def post(self):
    message = xmpp.Message(self.request.POST)
    stripped_jid = message.sender.partition('/')[0]
    
    # Is this a user that we know about? If not then add this user to our user list
    from_user = db.GqlQuery("SELECT * FROM ChatUser WHERE jid = :1", stripped_jid).get()
    if from_user == None:
      from_user = ChatUser(jid = stripped_jid, nick = stripped_jid, status = 'online')
      from_user.last_online_at = from_user.created_at = datetime.datetime.now()
      from_user.put()
    
    reply = self.parse_command(message.body, from_user)
    
    if reply:
      message.reply(reply)
    else:
      all_users = db.GqlQuery("SELECT * FROM ChatUser")
      jids = []
      for user in all_users:
        if xmpp.get_presence(user.jid):
          if user.jid != from_user.jid:
            jids.append(user.jid)
          user.status = 'online'
        else:
          user.status = 'offline'
        user.put()
      
      MessageLog(from_jid = stripped_jid, from_full_jid = message.sender, body = message.body, created_at = datetime.datetime.now()).put()
      
      reply = "<body>" + escape(from_user.nick) + ": " + escape(message.body) + "</body>"
      reply += "<html xmlns='http://jabber.org/protocol/xhtml-im'><body xmlns='http://www.w3.org/1999/xhtml'>"
      reply += "<strong>" + escape(from_user.nick) + ":</strong> " + escape(message.body)
      reply += "</body></html>"
      
      if len(jids) > 0:
        xmpp.send_message(jids, reply, None, xmpp.MESSAGE_TYPE_CHAT, True)
  
  def parse_command(self, message, from_user):
    reply = None
    match = re.match(r"(\/\w+)(?:\s|$)(.*)", message)
    
    # if the message starts with a / and has the format '/command option'
    if match:
      command = match.group(1)
      if command == "/add":
        jid = match.group(2)
        send_invite(jid)
        reply = "Sent invitation"
      elif command == "/remove":
        reply = "Command not implemented yet"
      elif command == "/help":
        reply = "commands are /hist [1,1..100], /nick [new nick name], /who, /quiet, /resume, /search [string]"
      elif command == "/h" or command == "/hist" or command == "/history":
        reply = "Command not implemented yet"
      elif command == "/n" or command == "/nick" or command == "/nickname":
        from_user.nick = match.group(2)
        from_user.put()
        reply = "nickname set to " + from_user.nick
      elif command == "/w" or command == "/who":
        all_users = db.GqlQuery("SELECT * FROM ChatUser")
        reply = "User Statuses:\n"
        for user in all_users:
          if xmpp.get_presence(user.jid):
            user.status = 'online'
          else:
            user.status = 'offline'
          reply += user.nick + ": " + user.status + "\n"
          user.put()
      elif command == "/q" or command == "/quiet":
        reply = "Command not implemented yet"
      elif command == "/r" or command == "/resume":
        reply = "Command not implemented yet"
      elif command == "/s" or command == "/search":
        reply = "Command not implemented yet"
      else:
        reply = "Unknown command"
    
    return reply

application = webapp.WSGIApplication([('/_ah/xmpp/message/chat/', XMPPHandler)], debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()