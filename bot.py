from google.appengine.api import xmpp
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.api import users

import os
import re
import datetime

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
  body = db.TextProperty()
  created_at = db.DateTimeProperty()

class XMPPHandler(webapp.RequestHandler):
  def post(self):
    message = xmpp.Message(self.request.POST)
    stripped_jid = message.sender.partition('/')[0]
    
    # Is this a user that we know about? If not then add this user to our user list
    from_user = db.GqlQuery("SELECT * FROM ChatUser WHERE jid = :1", stripped_jid).get()
    if from_user == None:
      from_user = ChatUser(jid = stripped_jid, nick = stripped_jid, status = 'online', created_at = datetime.datetime.now()).put()
      message.reply("Welcome to Panoptibot, komrade!")
      message.reply("commands are /hist, /nick [new nick name], /who, /timezone, /add [jabber id], /remove [nick] /img [url]")
      message.reply("Source code at: http://github.com/conorh/panoptibot-gae/")
      message.reply("")
      message.reply("Remeber to set your nickname with /nick")
      
    self.process_message(message, from_user)

  def update_users_status(self):
    all_users = ChatUser.all().fetch(100)
    for user in all_users:
      if user.status != 'quiet':
        if xmpp.get_presence(user.jid):
          user.status = 'online'
        else:
          user.status = 'offline'
        user.put()
    return all_users

  def output_history(self, messages, from_user):
    reply = ""
    for m in messages:
      reply += m.created_at.strftime("%I:%M%p UTC") + " " + m.nick + ": " + m.body + "\n"  
    return reply
  
  def html_message(self, from_user, body, escape_message=True):
    if(escape_message):
      body = escape(body)
    
    reply = "<body>" + escape(from_user.nick) + ": " + body + "</body>"
    reply += "<html xmlns='http://jabber.org/protocol/xhtml-im'><body xmlns='http://www.w3.org/1999/xhtml'>"
    reply += "<strong>" + escape(from_user.nick) + ":</strong> " + body
    reply += "</body></html>"
    return reply

  def send_to_all(self, from_user, message, escape_message=True, html_message=True):
    all_users = self.update_users_status()
    jids = [user.jid for user in all_users if user.status == 'online' and user.jid != from_user.jid]
    if len(jids) > 0:
      if html_message:
        reply = self.html_message(from_user, message, escape_message)
      elif escape_message:
        reply = escape(message)
      else:
        reply = message

      xmpp.send_message(jids, reply, None, xmpp.MESSAGE_TYPE_CHAT, html_message)

  def process_message(self, message, from_user):
    reply = None

    # message starts with a / and has the format '/command option'
    match = re.match(r"(\/\w+)(?:\s|$)(.*)", message.body)

    if not match:
      MessageLog(nick = from_user.nick, from_jid = message.sender, body = message.body, created_at = datetime.datetime.now()).put()
      self.send_to_all(from_user, message.body)
      return

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
      reply = "commands are /hist, /nick [new nick name], /who, /timezone, /add [jabber id], /remove [nick] /quiet /resume /img [url]"
    elif command == "/h" or command == "/hist" or command == "/history":
      history = MessageLog.gql("ORDER BY created_at DESC").fetch(20)
      reply = self.output_history(history, from_user)
    elif command == "/img":
      MessageLog(nick = from_user.nick, from_jid = message.sender, body = message.body, created_at = datetime.datetime.now()).put()
      self.send_to_all(from_user, "<img src='" + match.group(2) + "'/>", False)
    elif command == "/n" or command == "/nick" or command == "/nickname":
      from_user.nick = match.group(2)
      from_user.put()
      reply = "nickname set to " + from_user.nick
    elif command == "/w" or command == "/who":
      reply = "User Statuses:\n"
      for user in self.update_users_status():
        reply += " " + user.nick + ": " + user.status + " (" + user.jid + ")\n"
    elif command == "/q" or command == "/quiet":
      from_user.status = 'quiet'
      from_user.put()
      reply = "Your status has been set to quiet. You will no longer receive messages from the bot until you /resume"
    elif command == "/r" or command == "/resume":
      from_user.status = 'online'
      from_user.put()
      reply = "You will start receiving messages from the bot again."
    elif command == "/s" or command == "/search":
      reply = "Not implemented yet"
      #messages = MessageLog.search(match.group(2))
      #reply = self.output_history(messages, from_user)
    elif command == "/timezone":
      new_zone = tz_helper.timezone(match.group(2))
    elif command == "/ver":
      reply = "0.1"
    else:
      reply = "Unknown command"

    message.reply(escape(reply))

application = webapp.WSGIApplication([('/_ah/xmpp/message/chat/', XMPPHandler)], debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()