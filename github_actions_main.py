import os
import time
import datetime
from calendar_reader import get_upcoming_meetings
from meet_joiner import join_meet

def main():
    """
    Single-run version for GitHub Actions
    Checks calendar once and joins any immediate meetings
    """
    print("🤖 Google Meet Bot - GitHub Actions Mode")
    print(f"⏰ Current time: {datetime.datetime.now()}")
    
    try:
        print("📅 Checking calendar for meetings to join now...")
        meetings = get_upcoming_meetings()
        
        if not meetings:
            print("No upcoming Google Meet meetings found.")
            return
        
        now = datetime.datetime.now()
        
        for meeting in meetings:
            start_time_str = meeting['start'].get('dateTime', meeting['start'].get('date'))
            
            # Parse start time
            if 'T' in start_time_str:
                start_time = datetime.datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            else:
                start_time = datetime.datetime.fromisoformat(start_time_str)
            
            # Get current time in same timezone
            if start_time.tzinfo:
                current_time = datetime.datetime.now(start_time.tzinfo)
            else:
                current_time = datetime.datetime.now()
            
            time_until_meeting = (start_time - current_time).total_seconds()
            meeting_title = meeting.get('summary', 'No Title')
            meet_url = meeting.get('hangoutLink')
            
            print(f"📋 Meeting: '{meeting_title}'")
            print(f"⏰ Scheduled: {start_time}")
            print(f"⏳ Time until meeting: {time_until_meeting/60:.1f} minutes")
            
            # Join if meeting should start within next 3 minutes or started less than 10 minutes ago
            if -600 <= time_until_meeting <= 180:  # -10 minutes to +3 minutes
                clean_title = "".join(c for c in meeting_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                
                print(f"🎯 JOINING MEETING: {meeting_title}")
                print(f"🔗 URL: {meet_url}")
                
                try:
                    # This will record until meeting ends (with 50-minute GitHub Actions timeout)
                    join_meet(meet_url, clean_title)
                    print(f"✅ Completed recording for: {meeting_title}")
                    break  # Only join one meeting per run
                    
                except Exception as e:
                    print(f"❌ Error joining meeting '{meeting_title}': {e}")
                    continue
            
            elif time_until_meeting > 180:
                print(f"⏳ Meeting too far in future ({time_until_meeting/60:.1f} minutes)")
            else:
                print(f"⏭️  Meeting too far in past ({abs(time_until_meeting)/60:.1f} minutes ago)")
        
        print("🔄 GitHub Actions run completed")
        
    except Exception as e:
        print(f"❌ Error in GitHub Actions bot: {e}")
        raise

if __name__ == "__main__":
    main()
