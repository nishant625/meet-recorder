from calendar_reader import get_upcoming_meetings
from meet_joiner import join_meet
import datetime
import time
from flask import Flask
import threading
import os

app = Flask(__name__)

@app.route('/')
def health():
    return {"status": "Google Meet Bot Running", "version": "1.0"}

@app.route('/status')
def status():
    return {"bot": "monitoring calendar", "timestamp": datetime.datetime.now().isoformat()}

def monitor_calendar():
    """Continuously monitor calendar and join meetings at the right time"""
    print("🤖 Google Meet Bot - Starting calendar monitoring...")
    print("⏰ Will join meetings 1-2 minutes before they start")
    print("🛑 Press Ctrl+C to stop monitoring\n")
    
    while True:
        try:
            print("📅 Checking calendar for upcoming meetings...")
            meetings = get_upcoming_meetings()
            
            if not meetings:
                print("No upcoming Google Meet meetings found.")
                print("⏳ Checking again in 1 minute...\n")
                time.sleep(60)
                continue
            
            # Get current time for filtering
            now = datetime.datetime.now()
            upcoming_meetings = []
            
            # Filter out past meetings and show only upcoming ones
            for meeting in meetings:
                start_time_str = meeting['start'].get('dateTime', meeting['start'].get('date'))
                
                # Parse the start time properly
                if 'T' in start_time_str:  # DateTime format
                    start_time = datetime.datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                else:  # Date only format
                    start_time = datetime.datetime.fromisoformat(start_time_str)
                
                # Get current time in the same timezone
                if start_time.tzinfo:
                    current_time = datetime.datetime.now(start_time.tzinfo)
                else:
                    current_time = datetime.datetime.now()
                
                time_until_meeting = (start_time - current_time).total_seconds()
                
                # Only consider meetings that haven't started yet or started less than 5 minutes ago
                if time_until_meeting > -300:  # -300 seconds = -5 minutes
                    upcoming_meetings.append({
                        'meeting': meeting,
                        'start_time': start_time,
                        'time_until': time_until_meeting,
                        'current_time': current_time
                    })
                else:
                    meeting_title = meeting.get('summary', 'No Title')
                    print(f"⏭️  Skipping past meeting: '{meeting_title}' (started {abs(time_until_meeting)/60:.1f} minutes ago)")
            
            if not upcoming_meetings:
                print("No upcoming meetings found (all are in the past).")
                print("⏳ Checking again in 5 minutes...\n")
                time.sleep(300)
                continue
            
            # Process upcoming meetings
            for meeting_data in upcoming_meetings:
                meeting = meeting_data['meeting']
                start_time = meeting_data['start_time']
                time_until_meeting = meeting_data['time_until']
                
                meeting_title = meeting.get('summary', 'No Title')
                meet_url = meeting.get('hangoutLink')
                
                print(f"📋 Meeting: '{meeting_title}'")
                print(f"⏰ Scheduled: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Join if meeting starts within next 60-120 seconds (1-2 minutes before)
                if 60 <= time_until_meeting <= 120:
                    print(f"🎯 TIME TO JOIN! Meeting starts in {time_until_meeting/60:.1f} minutes")
                    print(f"🔗 URL: {meet_url}")
                    
                    # Create clean filename for recording
                    clean_title = "".join(c for c in meeting_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                    
                    try:
                        print(f"🚀 Joining meeting: {meeting_title}")
                        
                        # This will block until meeting ends and recording stops
                        join_meet(meet_url, clean_title)
                        
                        print(f"✅ Successfully completed recording for: {meeting_title}")
                        print("🔄 Resuming calendar monitoring...\n")
                        
                        # Break out of meeting loop and restart calendar check
                        break
                        
                    except Exception as e:
                        print(f"❌ Error joining meeting '{meeting_title}': {e}")
                        print("🔄 Continuing to monitor other meetings...\n")
                        break
                
                elif time_until_meeting > 0:
                    minutes_until = time_until_meeting / 60
                    hours_until = minutes_until / 60
                    
                    if minutes_until < 60:
                        print(f"⏳ Meeting starts in {minutes_until:.1f} minutes")
                    else:
                        print(f"⏳ Meeting starts in {hours_until:.1f} hours")
                        
                elif time_until_meeting > -300:  # Meeting started but less than 5 minutes ago
                    print(f"🏃 Meeting started {abs(time_until_meeting)/60:.1f} minutes ago - joining late!")
                    clean_title = "".join(c for c in meeting_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                    
                    try:
                        print(f"🚀 Joining meeting late: {meeting_title}")
                        join_meet(meet_url, clean_title)
                        print(f"✅ Successfully completed recording for: {meeting_title}")
                        break
                    except Exception as e:
                        print(f"❌ Error joining meeting '{meeting_title}': {e}")
                        break
                
                print()  # Empty line for readability
            
            # Check again in 2 minutes (reduced frequency for free tier)
            print("⏱️  Checking again in 2 minutes...")
            time.sleep(120)
            print("-" * 50)
            
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
            break
        except Exception as e:
            print(f"❌ Error in calendar monitoring: {e}")
            print("⏳ Retrying in 1 minute...")
            time.sleep(60)

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

def main():
    # Start calendar monitoring in background thread
    calendar_thread = threading.Thread(target=monitor_calendar, daemon=True)
    calendar_thread.start()
    
    # Start Flask app (this keeps the service alive)
    run_flask()

if __name__ == "__main__":
    main()
