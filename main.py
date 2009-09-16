import os
import datetime

from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import bot
from google.appengine.api import users

class MainPage(webapp.RequestHandler):
  def get(self):
    chat_log = bot.MessageLog.all().order('-created_at').fetch(500)
    user = users.get_current_user()
    if user:
      greeting = ("Welcome, %s! (<a href=\"%s\">sign out</a>)" % (user.nickname(), users.create_logout_url("/")))
    else:
      greeting = ("<a href=\"%s\">Sign in or register</a>." % users.create_login_url("/"))
    
    template_values = { 'chat_log': chat_log }
    path = os.path.join(os.path.dirname(__file__), 'templates/index.html')
    self.response.out.write(template.render(path, template_values))

application = webapp.WSGIApplication([('/', MainPage)])

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()