from google.appengine.api import xmpp
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
import re

class XMPPHandler(webapp.RequestHandler):
  def post(self):
    message = xmpp.Message(self.request.POST)
    reply = self.parse_command(message.body, message.sender)
    if True:
      message.reply(reply)
    else:
      message.reply("No command")

  def parse_command(self, message, sender):
    reply = "unknown command"
    match = re.match(r"^(\/.*?)(?:\s|$)(.*)", message)
    
    # if the message starts with a / and has the format '/command option'
    if len(match.groups()) >= 1:
      command = match.group(0)
      if command == "/add":
        reply = "add"
      elif command == "/remove":
	      reply = "/remove"
      elif command == "/help":
	      reply = "/help"	
      elif command == "/h" or command == "/hist" or command == "/history":
	      reply = "/history"	
      elif command == "/n" or command == "/nick" or command == "/nickname":
	      reply = "/nickname"	
      elif command == "/w" or command == "/who":
	      reply = "/who"	
      elif command == "/q" or command == "/quiet":
	      reply = "/quiet"	
      elif command == "/r" or command == "/resume":
	      reply = "/resume"	
      elif command == "/s" or command == "/search":
	      reply = "/search"	

    return reply

application = webapp.WSGIApplication([('/_ah/xmpp/message/chat/', XMPPHandler)], debug=True)	

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()