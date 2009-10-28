from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import users

import os
import datetime

import bot

class MainPage(webapp.RequestHandler):
  def get(self):
    user = users.get_current_user()
    chat_user = bot.ChatUser.gql("WHERE jid = :1", user.email()).get()
    if not chat_user:
      self.response.out.write("access denied")
    else:
      chat_log = bot.MessageLog.all().order('-created_at').fetch(500)
      
      template_values = { 'chat_log': chat_log }
      path = os.path.join(os.path.dirname(__file__), 'templates/index.html')
      self.response.out.write(template.render(path, template_values))
    
application = webapp.WSGIApplication([('/', MainPage)])

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()