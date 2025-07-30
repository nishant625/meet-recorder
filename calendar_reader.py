import os.path
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def get_calendar_service():
    creds = None
    # Check for credentials in Render's secret file location
    credentials_path = '/etc/secrets/credentials.json'
    
    # Fallback to local path for development
    if not os.path.exists(credentials_path):
        credentials_path = 'credentials.json'
    
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    service = build('calendar', 'v3', credentials=creds)
    return service

    creds = None
    # The file token.json stores the user's access and refresh tokens.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no valid credentials available, have the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    service = build('calendar', 'v3', credentials=creds)
    return service

def get_upcoming_meetings():
    service = get_calendar_service()
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    print('Getting the upcoming 10 meetings with Google Meet links')
    events_result = service.events().list(calendarId='primary', timeMin=now,
                                          maxResults=10, singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])

    meetings = []
    for event in events:
        if 'hangoutLink' in event:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(f"Meeting: {event.get('summary', 'No Title')}")
            print(f"Start time: {start}")
            print(f"Google Meet Link: {event['hangoutLink']}\n")
            meetings.append(event)
    
    if not meetings:
        print("No upcoming Google Meet meetings found.")
    
    return meetings
    
if __name__ == '__main__':
    get_upcoming_meetings()
