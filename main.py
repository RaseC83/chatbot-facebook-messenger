# encoding: utf-8
import webapp2
import json
import logging
import yaml
from google.appengine.api import urlfetch
from bot import Bot 
from userevents import UserEventsDao

VERIFY_TOKEN = "facebook_verification_token"
ACCESS_TOKEN = "EAAHV39N16YABAKaaWbNVrsyYH9KZCcWX1wJGi8RZBZB5zZApfZBURZABefAcINU4ZC2yNyFX6NTMHqF95uptZBlq9HhdkEAab6iFvVechaZBZCDLFl1F4dJIT2g72HvB1qhVSxZCQOXe927y0VfwZCbePWwXbOFEaCzFIv8atmlYWFYDLgZDZD"

class MainPage(webapp2.RequestHandler):
    def __init__(self, request=None, response=None):
        super(MainPage, self).__init__(request, response)
        logging.info("Instanciando bot")
        tree = yaml.load(open('tree.yaml'))
        #logging.info("Tree: %r", tree)
        self.bot = Bot(send_message, UserEventsDao(), tree)
        dao = UserEventsDao()

    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        mode = self.request.get("hub.mode")
        if mode == "subscribe":
            challenge = self.request.get("hub.challenge")
            verify_token = self.request.get("hub.verify_token")
            if verify_token == VERIFY_TOKEN:
                self.response.write(challenge)
        else:
            self.response.write("Ok")

    def post(self):
        logging.info("Data obtenida desde Messenger: %s", self.request.body)
        data = json.loads(self.request.body)

        if data["object"] == "page":

                for entry in data["entry"]:
                    for messaging_event in entry["messaging"]:
                        sender_id = messaging_event["sender"]["id"]
                        recipient_id = messaging_event["recipient"]["id"]

                        if messaging_event.get("message"):
                            is_admin = False
                            message = messaging_event['message']
                            if message.get('is_echo'):
                                if message.get('app_id'): # es el mismo bot
                                    continue #vamos a la siguiente iteración
                                else: # es el administrador, hay que desactivar el bot
                                    is_admin = True
                            message_text = message.get('text', '')
                            logging.info("Message: %s", message_text)

                            if is_admin:
                                user_id = recipient_id
                            else:
                                user_id = sender_id

                            self.bot.handle(user_id, message_text, is_admin)

                        if messaging_event.get("postback"):
                            message_text = messaging_event['postback']['payload']
                            self.bot.handle(sender_id, message_text)
                            logging.info("Postback: %s", message_text)

def send_message(recipient_id, message_text, possible_answers):
    logging.info("Enviando mensaje a %r: %s", recipient_id, message_text)
    headers = {
        "Content-Type": "application/json"
    }
    # message = {"text": message_text}
    # máxima cantidad de postback buttons 3 
    # máxima cantidad de caracteres en el mensaje 20
    if possible_answers is not None and len(possible_answers) >= 2:
        message = get_postback_buttons_message(message_text, possible_answers)
    elif message_text.startswith('https'):
        message = get_url_buttons_message(message_text)
    else:
        message = {"text": message_text}

    raw_data = {
        "recipient": {
            "id": recipient_id
        },
        "message": message
    }
    data = json.dumps(raw_data)
    r = urlfetch.fetch("https://graph.facebook.com/v2.6/me/messages?access_token=%s" % ACCESS_TOKEN, 
        method=urlfetch.POST, headers=headers, payload=data)
    if r.status_code != 200:
        logging.error("Error %r enviando mensaje: %s", r.status_code, r.content)

def get_postback_buttons_message(message_text, possible_answers):
    buttons = []
    for answer in possible_answers:
        buttons.append({
            "type": "postback",
            "title": answer,
            "payload": answer
        })

    return {
        "attachment": {
            "type":"template",
            "payload": {
                "template_type": "button",
                "text": message_text,
                "buttons": buttons
            }
        }
    }

def get_url_buttons_message(message_text):
    elements = []
    elements.append({
        #"type": "web_url",
        #"title": "Curso",
        "url": message_text
    })
    return {
        "attachment": {
            "type":"template",
            "payload": {
                "template_type": "open_graph",
                "elements": elements
            }
        }
    }

class PrivacyPage(webapp2.RequestHandler):
    def get(self):
        self.response.headers['Content-Type'] = 'text/html'
        htmlContent = open('privacy_policy.html').read()
        self.response.write(htmlContent)

app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/privacy', PrivacyPage),
], debug=True)
