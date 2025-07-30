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
    token_path = '/etc/secrets/token.json'  # Add this for Render
    
    # Fallback to local paths for development
    if not os.path.exists(credentials_path):
        credentials_path = 'credentials.json'
    if not os.path.exists(token_path):
        token_path = 'token.json'
    
    # Load existing token from Render's secret file location
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                print("✅ Token refreshed successfully")
                
                # Save refreshed token (this might not work in Render's read-only secrets)
                # But the refreshed token will work for the current session
                try:
                    with open(token_path, 'w') as token:
                        token.write(creds.to_json())
                except Exception as e:
                    print(f"⚠️ Could not save refreshed token: {e}")
                    print("This is normal on Render - token will work for current session")
                    
            except Exception as e:
                print(f"❌ Token refresh failed: {e}")
                return None
        else:
            # This won't work on Render (headless environment)
            print("❌ No valid credentials and cannot run interactive OAuth on Render")
            print("Please ensure your token.json is valid and uploaded to Render Secret Files")
            return None
    
    service = build('calendar', 'v3', credentials=creds)
    return service

def get_upcoming_meetings():
    service = get_calendar_service()
    if not service:
        print("❌ Failed to get calendar service")
        return []
        
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    print('Getting the upcoming 10 meetings with Google Meet links')
    
    try:
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
        
    except Exception as e:
        print(f"❌ Error fetching calendar events: {e}")
        return []
    
if __name__ == '__main__':
    get_upcoming_meetings()
