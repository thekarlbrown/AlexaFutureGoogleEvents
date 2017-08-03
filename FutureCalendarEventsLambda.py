from __future__ import print_function
import httplib2
import os

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

import datetime
from dateutil import parser, tz

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Calendar API Python Quickstart'

def get_credentials():
    target_dir = '/tmp/'
    credential_dir = os.path.join(target_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'calendar-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        print('Storing credentials to ' + credential_path)
    return credentials

credentials = get_credentials()
http = credentials.authorize(httplib2.Http())
service = discovery.build('calendar', 'v3', http=http)

conversion_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
conversion_months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

def returnFullAlexaCalendarResponse(future_events_to_display):
    now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time

    eventsResult = service.events().list(
            calendarId='primary', timeMin=now, maxResults=future_events_to_display, singleEvents=True,
            orderBy='startTime').execute()

    events = eventsResult.get('items', [])
    alexaSpeechToReturn = ''
    if not events:
        alexaSpeechToReturn = 'No upcoming events found.'
    else:
        startTimeInDateTime = datetime.datetime.utcnow()
        for event in events:
            start = parser.parse(event['start'].get('dateTime', event['start'].get('date')))
            start = start.replace(tzinfo = tz.gettz('UTC'))
            start = start.astimezone(tz.gettz('America/New_York'))
            timeDifference = start.replace(tzinfo=None) - startTimeInDateTime.replace(tzinfo=None)
            alexaSpeechToReturn += f"In {datetime.timedelta(timeDifference.days).days} days from now. "
            alexaSpeechToReturn += f"{conversion_days[start.weekday()]}, {conversion_months[start.month-1]} {start.day} {start.year}. "
            alexaSpeechToReturn += f"{event['summary']}. "

    return alexaSpeechToReturn

def lambda_handler(event, context):
    if (event["session"]["application"]["applicationId"] !=
            "amzn1.ask.skill.e36d5c7c-db76-4d38-b7e3-fbc30b94c498"):
        raise ValueError("Invalid Application ID")

    if event["session"]["new"]:
        on_session_started({"requestId": event["request"]["requestId"]}, event["session"])

    if event["request"]["type"] == "LaunchRequest":
        return on_launch(event["request"], event["session"])
    elif event["request"]["type"] == "IntentRequest":
        return on_intent(event["request"], event["session"])
    elif event["request"]["type"] == "SessionEndedRequest":
        return on_session_ended(event["request"], event["session"])

def on_session_started(session_started_request, session):
    print ('Starting new session.')

def on_launch(launch_request, session):
    return get_welcome_response()

def on_intent(intent_request, session):
    intent = intent_request["intent"]
    intent_name = intent_request["intent"]["name"]

    if intent_name == "GetInfo":
        return get_app_info()
    elif intent_name == "GetFutureEvents":
        return get_future_events(intent)
    elif intent_name == "AMAZON.HelpIntent":
        return get_app_info()
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    else:
        raise ValueError("Invalid intent")

def on_session_ended(session_ended_request, session):
    print ('Ending session.')
    # Cleanup goes here...

def handle_session_end_request():
    card_title = "Future Calendar Events - Goodbye"
    speech_output = "Goodbye"
    should_end_session = True

    return build_response({}, build_speechlet_response(card_title, speech_output, None, should_end_session))

def get_app_info():
    session_attributes = {}
    card_title = "About Future Calendar Events"
    reprompt_text = ""
    should_end_session = False

    speech_output = "This is the Alexa Skill to provide you with a number of events coming up in your Google Calendar. The output was designed to meet Karl Brown's specifications. For example, ask Alexa for the next 5 events."

    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))

def get_future_events(intent):
            session_attributes = {}
            card_title = "Future Calendar Events Info"
            speech_output = "I'm not sure how many future events you want to hear about. " \
                            "Please try asking for 4 events, for example."
            reprompt_text = "I'm not sure how many future events you want to hear about. " \
                            "Please try asking for 4 events, for example."
            should_end_session = False

            if "NumberOfEvents" in intent["slots"]:
                number_of_events = intent["slots"]["NumberOfEvents"]["value"].lower()

                speech_output = returnFullAlexaCalendarResponse(number_of_events)
                reprompt_text = ""

            return build_response(session_attributes, build_speechlet_response(
                card_title, speech_output, reprompt_text, should_end_session))

def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        "outputSpeech": {
            "type": "PlainText",
            "text": output
        },
        "card": {
            "type": "Simple",
            "title": title,
            "content": output
        },
        "reprompt": {
            "outputSpeech": {
                "type": "PlainText",
                "text": reprompt_text
            }
        },
        "shouldEndSession": should_end_session
    }

def build_response(session_attributes, speechlet_response):
    return {
        "version": "1.0",
        "sessionAttributes": session_attributes,
        "response": speechlet_response
    }
