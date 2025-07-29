from calendar_reader import get_upcoming_meetings
from meet_joiner import join_meet
from audio_recorder import AudioRecorder  # Add this import
import datetime


def main():
    meetings = get_upcoming_meetings()

    if not meetings:
        print("No upcoming Google Meet meetings found.")
        return

    # For this example, just join the first upcoming meeting
    meeting = meetings[0]
    meet_url = meeting.get('hangoutLink')
    meeting_title = meeting.get('summary', 'No Title')
    start_time = meeting['start'].get('dateTime', meeting['start'].get('date'))

    print(f"Joining meeting '{meeting_title}' scheduled at {start_time} with link: {meet_url}")
    
    # Create a clean filename for the recording
    clean_title = "".join(c for c in meeting_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    
    # Pass both the URL and meeting title to join_meet
    join_meet(meet_url, clean_title)


if __name__ == "__main__":
    main()
