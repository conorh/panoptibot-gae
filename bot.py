from google.appengine.api import xmpp
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache

from google.appengine.ext import db
from google.appengine.api import users

import re
import datetime

import tz_helper
from xml.sax.saxutils import escape

class ChatUser(db.Model):
  jid = db.StringProperty(required=True)
  nick = db.StringProperty(required=True)
  status = db.StringProperty(required=True)
  timezone = db.StringProperty()
  created_at = db.DateTimeProperty()

class MessageLog(db.Model):
  from_jid = db.StringProperty()
  nick = db.StringProperty()
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
      message.reply("Welcome to Panoptibot, komrade!")
      message.reply("commands are /hist, /nick [new nick name], /who, /timezone, /add [jabber id], /remove [nick]")
    
    if not self.parse_command(message, from_user):
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
      
      MessageLog(nick = from_user.nick, from_jid = message.sender, body = message.body, created_at = datetime.datetime.now()).put()
      
      reply = "<body>" + escape(from_user.nick) + ": " + escape(message.body) + "</body>"
      reply += "<html xmlns='http://jabber.org/protocol/xhtml-im'><body xmlns='http://www.w3.org/1999/xhtml'>"
      reply += "<strong>" + escape(from_user.nick) + ":</strong> " + escape(message.body)
      reply += "</body></html>"
      
      if len(jids) > 0:
        xmpp.send_message(jids, reply, None, xmpp.MESSAGE_TYPE_CHAT, True)

  def parse_command(self, message, from_user):
    reply = None
    
    match = re.match(r"(\/\w+)(?:\s|$)(.*)", message.body)
    
    # if the message starts with a / and has the format '/command option'
    if match:
      command = match.group(1)
      if command == "/add":
        jid = match.group(2)
        xmpp.send_invite(jid)
        reply = "Sent invitation to " + jid
      elif command == "/remove":
        user = ChatUser.gql("WHERE nick = :1", match.group(2)).get()
        if user != None:
          user.delete()
          reply = "Removed user"
        else:
          reply = "User not found"
      elif command == "/help":
        reply = "commands are /hist, /nick [new nick name], /who, /timezone, /add [jabber id], /remove [nick]"
      elif command == "/h" or command == "/hist" or command == "/history":
        history = MessageLog.gql("ORDER BY created_at DESC").fetch(20)
        reply = ""
        utc = tz_helper.timezone('UTC')
        if from_user.timezone != None:
          new_zone = tz_helper.timezone(from_user.timezone)
        else:
          new_zone = tz_helper.timezone('US/Eastern')
        for hist_message in history:
          reply += hist_message.created_at.replace(tzinfo=utc).astimezone(new_zone).strftime("%I:%M%p %Z") + " " + hist_message.nick + ": " + hist_message.body + "\n"
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
      elif command == "/timezone":
        new_zone = tz_helper.timezone(match.group(2))
        if new_zone:
          from_user.timezone = new_zone.zone
          from_user.put()
          reply = "timezone set to " + from_user.timezone
        else:
          reply = "Unknown timezone"
      else:
        reply = "Unknown command"
    
    if reply != None:
      message.reply(escape(reply))
      return True
    else:
      return False

application = webapp.WSGIApplication([('/_ah/xmpp/message/chat/', XMPPHandler)], debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()