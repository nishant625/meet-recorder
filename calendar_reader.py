import os.path
import datetime
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

def get_calendar_service():
    print("🔍 Attempting to get calendar service...")
    creds = None
    
    # Check for credentials in Render's secret file location
    credentials_path = '/etc/secrets/credentials.json'
    token_path = '/etc/secrets/token.json'
    
    print(f"🔍 Checking for credentials at: {credentials_path}")
    print(f"🔍 Credentials file exists: {os.path.exists(credentials_path)}")
    
    print(f"🔍 Checking for token at: {token_path}")
    print(f"🔍 Token file exists: {os.path.exists(token_path)}")
    
    # Fallback to local paths for development
    if not os.path.exists(credentials_path):
        credentials_path = 'credentials.json'
        print(f"🔍 Falling back to local credentials: {credentials_path}")
    if not os.path.exists(token_path):
        token_path = 'token.json'
        print(f"🔍 Falling back to local token: {token_path}")
    
    # Load existing token with detailed debugging
    if os.path.exists(token_path):
        print("🔍 Loading existing token...")
        
        try:
            # First, let's read the file content to see if it's valid JSON
            print("🔍 Reading token file content...")
            with open(token_path, 'r') as f:
                token_content = f.read()
            
            print(f"🔍 Token file size: {len(token_content)} characters")
            
            # Try to parse as JSON first
            print("🔍 Parsing token as JSON...")
            token_data = json.loads(token_content)
            print("✅ Token JSON parsed successfully")
            
            # Check if required fields exist
            required_fields = ['client_id', 'client_secret', 'refresh_token']
            for field in required_fields:
                if field in token_data:
                    print(f"✅ Found required field: {field}")
                else:
                    print(f"❌ Missing required field: {field}")
            
            # Now try to create credentials object
            print("🔍 Creating credentials object...")
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            print("✅ Credentials object created successfully")
            
        except json.JSONDecodeError as e:
            print(f"❌ Token file is not valid JSON: {e}")
            return None
        except Exception as e:
            print(f"❌ Error loading token: {e}")
            import traceback
            traceback.print_exc()
            return None
    else:
        print("❌ No token file found")
        return None
    
    if not creds or not creds.valid:
        print("🔍 Token needs refresh or is invalid")
        if creds and creds.expired and creds.refresh_token:
            try:
                print("🔍 Attempting to refresh token...")
                creds.refresh(Request())
                print("✅ Token refreshed successfully")
            except Exception as e:
                print(f"❌ Token refresh failed: {e}")
                return None
        else:
            print("❌ No valid credentials and cannot run interactive OAuth on Render")
            return None
    else:
        print("✅ Token is valid")
    
    try:
        print("🔍 Building calendar service...")
        service = build('calendar', 'v3', credentials=creds)
        print("✅ Calendar service built successfully")
        return service
    except Exception as e:
        print(f"❌ Error building calendar service: {e}")
        return None

def get_upcoming_meetings():
    print("🔍 Starting get_upcoming_meetings function...")
    
    service = get_calendar_service()
    if not service:
        print("❌ Failed to get calendar service")
        return []
        
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    print(f'🔍 Getting meetings from: {now}')
    
    try:
        print("🔍 Making API call to Google Calendar...")
        events_result = service.events().list(
            calendarId='primary', 
            timeMin=now,
            maxResults=10, 
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        print("✅ API call successful")
        
        events = events_result.get('items', [])
        print(f"🔍 Found {len(events)} total events")

        meetings = []
        for event in events:
            if 'hangoutLink' in event:
                start = event['start'].get('dateTime', event['start'].get('date'))
                print(f"Meeting: {event.get('summary', 'No Title')}")
                print(f"Start time: {start}")
                print(f"Google Meet Link: {event['hangoutLink']}\n")
                meetings.append(event)
        
        print(f"🔍 Found {len(meetings)} meetings with Google Meet links")
        
        if not meetings:
            print("No upcoming Google Meet meetings found.")
        
        return meetings
        
    except Exception as e:
        print(f"❌ Error fetching calendar events: {e}")
        import traceback
        traceback.print_exc()
        return []
    
if __name__ == '__main__':
    get_upcoming_meetings()
