import os
import time
import datetime
import sys
import traceback

def main():
    """
    Single-run version for GitHub Actions with extensive debugging
    Checks calendar once and joins any immediate meetings
    """
    print("🚀 SCRIPT STARTED - Debug point 1")
    print(f"⏰ Current time: {datetime.datetime.now()}")
    print(f"🔧 Python version: {sys.version}")
    print(f"🔧 Working directory: {os.getcwd()}")
    print(f"🔧 Environment: GitHub Actions = {os.environ.get('GITHUB_ACTIONS', 'false')}")
    
    # Check if required files exist
    print("\n📁 Checking required files...")
    required_files = ['credentials.json', 'token.json', 'calendar_reader.py', 'meet_joiner.py']
    for file in required_files:
        exists = os.path.exists(file)
        print(f"{'✅' if exists else '❌'} {file}: {'Found' if exists else 'Missing'}")
    
    print("\n🔧 About to import modules - Debug point 2")
    
    try:
        print("📦 Importing calendar_reader...")
        from calendar_reader import get_upcoming_meetings
        print("✅ calendar_reader imported successfully")
        
        print("📦 Importing meet_joiner...")
        from meet_joiner import join_meet  
        print("✅ meet_joiner imported successfully")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("📦 Available Python modules:")
        import pkg_resources
        installed_packages = [d.project_name for d in pkg_resources.working_set]
        for package in sorted(installed_packages):
            print(f"  - {package}")
        return
    except Exception as e:
        print(f"❌ Unexpected import error: {e}")
        traceback.print_exc()
        return
    
    print("\n🚀 Starting calendar check - Debug point 3")
    
    try:
        print("📅 Checking calendar for meetings to join now...")
        
        # Add timeout protection for the calendar call
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Calendar API call timed out after 30 seconds")
        
        # Set timeout for calendar call (GitHub Actions specific)
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)  # 30 second timeout
        
        print("🔍 Calling get_upcoming_meetings()...")
        meetings = get_upcoming_meetings()
        
        # Cancel timeout
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            signal.alarm(0)
        
        print(f"✅ Calendar check completed. Found {len(meetings)} meetings.")
        
        if not meetings:
            print("ℹ️ No upcoming Google Meet meetings found.")
            print("🔄 GitHub Actions run completed successfully (no meetings)")
            return
        
    except TimeoutError as e:
        print(f"⏰ Calendar API timeout: {e}")
        print("❌ GitHub Actions run failed due to calendar timeout")
        return
    except Exception as e:
        print(f"❌ Error during calendar check: {e}")
        print("📊 Full error traceback:")
        traceback.print_exc()
        return
    
    print(f"\n📋 Processing {len(meetings)} meetings...")
    
    try:
        now = datetime.datetime.now()
        print(f"🕐 Current time for comparison: {now}")
        
        for i, meeting in enumerate(meetings, 1):
            print(f"\n--- Processing Meeting {i}/{len(meetings)} ---")
            
            start_time_str = meeting['start'].get('dateTime', meeting['start'].get('date'))
            print(f"📅 Raw start time: {start_time_str}")
            
            # Parse start time with error handling
            try:
                if 'T' in start_time_str:
                    start_time = datetime.datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                else:
                    start_time = datetime.datetime.fromisoformat(start_time_str)
                print(f"✅ Parsed start time: {start_time}")
            except Exception as parse_error:
                print(f"❌ Error parsing start time '{start_time_str}': {parse_error}")
                continue
            
            # Get current time in same timezone
            if start_time.tzinfo:
                current_time = datetime.datetime.now(start_time.tzinfo)
                print(f"🌍 Using timezone-aware comparison: {current_time}")
            else:
                current_time = datetime.datetime.now()
                print(f"🌍 Using local time comparison: {current_time}")
            
            time_until_meeting = (start_time - current_time).total_seconds()
            meeting_title = meeting.get('summary', 'No Title')
            meet_url = meeting.get('hangoutLink', 'No URL')
            
            print(f"📋 Meeting: '{meeting_title}'")
            print(f"⏰ Scheduled: {start_time}")
            print(f"⏳ Time until meeting: {time_until_meeting/60:.1f} minutes")
            print(f"🔗 Meet URL: {meet_url}")
            
            # Enhanced join logic with more detailed logging
            if -600 <= time_until_meeting <= 180:  # -10 minutes to +3 minutes
                print(f"🎯 MEETING IS IN JOIN WINDOW!")
                print(f"📐 Time window: -10 to +3 minutes (actual: {time_until_meeting/60:.1f} minutes)")
                
                # Create clean title for recording
                clean_title = "".join(c for c in meeting_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                clean_title = clean_title.replace(' ', '_')[:50]  # Limit length and replace spaces
                print(f"📝 Clean title for recording: '{clean_title}'")
                
                print(f"🎯 JOINING MEETING: {meeting_title}")
                print(f"🔗 URL: {meet_url}")
                
                try:
                    print("🚀 About to call join_meet function...")
                    
                    # Add timeout protection for meeting join
                    if os.environ.get('GITHUB_ACTIONS') == 'true':
                        signal.signal(signal.SIGALRM, timeout_handler)
                        signal.alarm(2700)  # 45 minute timeout (safe margin for 50min GitHub limit)
                    
                    # This will record until meeting ends (with 50-minute GitHub Actions timeout)
                    join_meet(meet_url, clean_title)
                    
                    # Cancel timeout
                    if os.environ.get('GITHUB_ACTIONS') == 'true':
                        signal.alarm(0)
                    
                    print(f"✅ Completed recording for: {meeting_title}")
                    print("🔄 Breaking loop - only join one meeting per run")
                    break  # Only join one meeting per run
                    
                except TimeoutError as timeout_error:
                    print(f"⏰ Meeting join timed out: {timeout_error}")
                    print("🔄 Continuing to check other meetings...")
                    continue
                except Exception as join_error:
                    print(f"❌ Error joining meeting '{meeting_title}': {join_error}")
                    print("📊 Full error traceback:")
                    traceback.print_exc()
                    print("🔄 Continuing to check other meetings...")
                    continue
            
            elif time_until_meeting > 180:
                print(f"⏳ Meeting too far in future ({time_until_meeting/60:.1f} minutes)")
                print("⏭️ Skipping - will join on next run if within window")
            else:
                print(f"⏭️ Meeting too far in past ({abs(time_until_meeting)/60:.1f} minutes ago)")
                print("⏭️ Skipping - meeting already happened")
        
        print(f"\n✅ Processed all {len(meetings)} meetings successfully")
        print("🔄 GitHub Actions run completed")
        
    except Exception as e:
        print(f"❌ Error during meeting processing: {e}")
        print("📊 Full error traceback:")
        traceback.print_exc()
        raise

def test_imports():
    """Test function to verify all required modules can be imported"""
    print("🧪 Testing module imports...")
    
    try:
        import selenium
        print(f"✅ selenium: {selenium.__version__}")
    except ImportError as e:
        print(f"❌ selenium import failed: {e}")
    
    try:
        import google.auth
        print("✅ google-auth: Available")
    except ImportError as e:
        print(f"❌ google-auth import failed: {e}")
    
    try:
        import sounddevice
        print(f"✅ sounddevice: Available")
    except ImportError as e:
        print(f"❌ sounddevice import failed: {e}")
    
    try:
        import boto3
        print(f"✅ boto3: {boto3.__version__}")
    except ImportError as e:
        print(f"❌ boto3 import failed: {e}")
    
    try:
        import chromedriver_autoinstaller
        print("✅ chromedriver-autoinstaller: Available")
    except ImportError as e:
        print(f"❌ chromedriver-autoinstaller import failed: {e}")

def check_environment():
    """Check GitHub Actions environment setup"""
    print("🔍 Environment check...")
    
    # Check environment variables
    required_env_vars = ['BOT_EMAIL', 'BOT_PASSWORD', 'B2_ENDPOINT', 'B2_KEY_ID', 'B2_APPLICATION_KEY', 'B2_BUCKET_NAME']
    
    for var in required_env_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: Set ({'*' * 8})")
        else:
            print(f"❌ {var}: Missing")
    
    # Check display
    display = os.environ.get('DISPLAY')
    print(f"🖥️ DISPLAY: {display if display else 'Not set'}")
    
    # Check available disk space
    import shutil
    total, used, free = shutil.disk_usage('/')
    print(f"💾 Disk space: {free // (1024**3)} GB free of {total // (1024**3)} GB total")

if __name__ == "__main__":
    print("=" * 60)
    print("🤖 GOOGLE MEET BOT - GITHUB ACTIONS MODE")
    print("=" * 60)
    
    # Run diagnostics first
    check_environment()
    print()
    test_imports()
    print()
    
    # Run main bot logic
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"\n💥 FATAL ERROR: {e}")
        print("📊 Full traceback:")
        traceback.print_exc()
        sys.exit(1)
    
    print("\n🏁 Script execution completed")
