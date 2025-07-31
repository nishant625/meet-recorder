import os.path
import datetime
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

# Detect runtime environment
IS_GITHUB_ACTIONS = os.environ.get('GITHUB_ACTIONS') == 'true'
IS_RENDER = os.environ.get('RENDER') == 'true'
IS_LOCAL = not (IS_GITHUB_ACTIONS or IS_RENDER)

def get_calendar_service():
    print("🔍 Attempting to get calendar service...")
    
    if IS_GITHUB_ACTIONS:
        print("🔧 Running in GitHub Actions environment")
    elif IS_RENDER:
        print("🔧 Running in Render environment")
    else:
        print("🔧 Running in local environment")
    
    creds = None
    
    # Environment-specific credential paths
    if IS_RENDER:
        # Render's secret file location
        credentials_path = '/etc/secrets/credentials.json'
        token_path = '/etc/secrets/token.json'
    else:
        # GitHub Actions and local development use root directory
        credentials_path = 'credentials.json'
        token_path = 'token.json'
    
    print(f"🔍 Checking for credentials at: {credentials_path}")
    print(f"🔍 Credentials file exists: {os.path.exists(credentials_path)}")
    
    print(f"🔍 Checking for token at: {token_path}")
    print(f"🔍 Token file exists: {os.path.exists(token_path)}")
    
    # Fallback paths for development
    if not os.path.exists(credentials_path) and not IS_GITHUB_ACTIONS:
        backup_credentials = 'credentials.json'
        if os.path.exists(backup_credentials):
            credentials_path = backup_credentials
            print(f"🔍 Using fallback credentials: {credentials_path}")
        
    if not os.path.exists(token_path) and not IS_GITHUB_ACTIONS:
        backup_token = 'token.json'
        if os.path.exists(backup_token):
            token_path = backup_token
            print(f"🔍 Using fallback token: {token_path}")
    
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
        if IS_GITHUB_ACTIONS:
            print("❌ GitHub Actions requires pre-generated token in secrets")
        return None
    
    if not creds or not creds.valid:
        print("🔍 Token needs refresh or is invalid")
        if creds and creds.expired and creds.refresh_token:
            try:
                print("🔍 Attempting to refresh token...")
                creds.refresh(Request())
                print("✅ Token refreshed successfully")
                
                # Save refreshed token for future use (except in GitHub Actions)
                if not IS_GITHUB_ACTIONS:
                    try:
                        with open(token_path, 'w') as token_file:
                            token_file.write(creds.to_json())
                        print("✅ Refreshed token saved")
                    except Exception as e:
                        print(f"⚠️ Could not save refreshed token: {e}")
                        
            except Exception as e:
                print(f"❌ Token refresh failed: {e}")
                if IS_GITHUB_ACTIONS:
                    print("❌ GitHub Actions cannot perform interactive OAuth")
                return None
        else:
            if IS_GITHUB_ACTIONS:
                print("❌ No valid credentials and cannot run interactive OAuth in GitHub Actions")
            else:
                print("❌ No valid credentials - interactive OAuth may be needed")
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
    """
    Get upcoming Google Meet meetings from the calendar
    Returns list of meetings with Google Meet links
    """
    print("🔍 Starting get_upcoming_meetings function...")
    
    service = get_calendar_service()
    if not service:
        print("❌ Failed to get calendar service")
        return []
        
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    print(f'🔍 Getting meetings from: {now}')
    
    # Adjust time window based on environment
    if IS_GITHUB_ACTIONS:
        # GitHub Actions: Look ahead only 4 hours (since it runs frequently)
        time_max = (datetime.datetime.utcnow() + datetime.timedelta(hours=4)).isoformat() + 'Z'
        max_results = 5  # Fewer results for faster processing
    else:
        # Other environments: Look ahead 24 hours
        time_max = (datetime.datetime.utcnow() + datetime.timedelta(hours=24)).isoformat() + 'Z'
        max_results = 10
    
    try:
        print("🔍 Making API call to Google Calendar...")
        print(f"🔍 Time window: {now} to {time_max}")
        
        events_result = service.events().list(
            calendarId='primary', 
            timeMin=now,
            timeMax=time_max,
            maxResults=max_results, 
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        print("✅ API call successful")
        
        events = events_result.get('items', [])
        print(f"🔍 Found {len(events)} total events in time window")

        meetings = []
        for event in events:
            # Only include events with Google Meet links
            if 'hangoutLink' in event:
                start = event['start'].get('dateTime', event['start'].get('date'))
                meeting_title = event.get('summary', 'No Title')
                meet_url = event['hangoutLink']
                
                print(f"📅 Meeting: {meeting_title}")
                print(f"⏰ Start time: {start}")
                print(f"🔗 Google Meet Link: {meet_url}")
                
                # Add additional metadata for GitHub Actions
                if IS_GITHUB_ACTIONS:
                    # Calculate time until meeting for logging
                    try:
                        if 'T' in start:
                            start_dt = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
                        else:
                            start_dt = datetime.datetime.fromisoformat(start)
                        
                        current_time = datetime.datetime.now(start_dt.tzinfo) if start_dt.tzinfo else datetime.datetime.now()
                        time_diff = (start_dt - current_time).total_seconds() / 60
                        print(f"⏳ Time until meeting: {time_diff:.1f} minutes")
                    except Exception as e:
                        print(f"⚠️ Could not calculate time difference: {e}")
                
                print()  # Empty line for readability
                meetings.append(event)
        
        print(f"🔍 Found {len(meetings)} meetings with Google Meet links")
        
        if not meetings:
            print("ℹ️ No upcoming Google Meet meetings found in the specified time window.")
        
        return meetings
        
    except Exception as e:
        print(f"❌ Error fetching calendar events: {e}")
        import traceback
        traceback.print_exc()
        return []

def test_calendar_access():
    """
    Test function to verify calendar access is working
    """
    print("🧪 Testing calendar access...")
    meetings = get_upcoming_meetings()
    
    if meetings:
        print(f"✅ Calendar access test successful! Found {len(meetings)} meetings.")
        return True
    else:
        print("⚠️ Calendar access test: No meetings found (this might be normal)")
        # Still return True if we could connect (no meetings might be normal)
        service = get_calendar_service()
        return service is not None

if __name__ == '__main__':
    print("🚀 Running calendar reader test...")
    success = test_calendar_access()
    if success:
        print("✅ Calendar reader is working correctly!")
    else:
        print("❌ Calendar reader test failed!")
        exit(1)
