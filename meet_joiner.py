import os
import time
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from dotenv import load_dotenv
from audio_recorder import AudioRecorder
import chromedriver_autoinstaller

load_dotenv()

BOT_EMAIL = os.environ["BOT_EMAIL"]
BOT_PASSWORD = os.environ["BOT_PASSWORD"]

def join_meet(meet_url, meeting_name="meeting"):
    chromedriver_autoinstaller.install()
    chrome_options = Options()
    # Add headless mode for container deployment
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--remote-debugging-port=9222")
    
    chrome_options.add_argument("--use-fake-ui-for-media-stream")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    wait = WebDriverWait(driver, 30)
    recorder = AudioRecorder(upload_to_b2=True)
    
    try:
        print("Starting Google login process...")
        
        # Your existing login code stays the same
        login_url = f"https://accounts.google.com/signin/v2/identifier?continue={meet_url}&flowName=GlifWebSignIn&flowEntry=ServiceLogin"
        driver.get(login_url)
        time.sleep(3)
        
        # Enter email with human-like typing
        print("Entering email...")
        email_input = wait.until(EC.element_to_be_clickable((By.ID, "identifierId")))
        email_input.clear()
        
        for char in BOT_EMAIL:
            email_input.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
        
        time.sleep(1)
        
        # Click Next
        next_button = wait.until(EC.element_to_be_clickable((By.ID, "identifierNext")))
        next_button.click()
        time.sleep(4)
        
        # Handle recovery setup screen
        print("Checking for recovery setup screen...")
        try:
            if "recovery" in driver.current_url.lower() or "backup" in driver.current_url.lower():
                print("Recovery setup screen detected. Trying to skip...")
                
                skip_buttons = [
                    "//span[contains(text(), 'Skip')]/parent::button",
                    "//span[contains(text(), 'Not now')]/parent::button", 
                    "//span[contains(text(), 'Maybe later')]/parent::button",
                    "//button[contains(@aria-label, 'Skip')]",
                    "[data-value='skip']"
                ]
                
                skipped = False
                for selector in skip_buttons:
                    try:
                        if selector.startswith("//"):
                            skip_button = driver.find_element(By.XPATH, selector)
                        else:
                            skip_button = driver.find_element(By.CSS_SELECTOR, selector)
                        skip_button.click()
                        print(f"Clicked skip button: {selector}")
                        skipped = True
                        break
                    except:
                        continue
                
                if not skipped:
                    print("Could not find skip button. Manual intervention may be needed.")
                    input("Please manually skip the recovery setup and press Enter to continue...")
                
                time.sleep(3)
        except Exception as e:
            print(f"Recovery screen handling: {e}")
        
        # Password entry
        print("Waiting for password field...")
        password_input = None
        
        password_selectors = [
            (By.NAME, "password"),
            (By.XPATH, "//input[@type='password']"),
            (By.XPATH, "//input[@name='password']"),
            (By.CSS_SELECTOR, "input[type='password']"),
            (By.XPATH, "//div[@id='password']//input"),
            (By.XPATH, "//*[@id='password']/div[1]/div/div[1]/input")
        ]
        
        for selector_type, selector_value in password_selectors:
            try:
                password_input = wait.until(EC.element_to_be_clickable((selector_type, selector_value)))
                print(f"Found password field with selector: {selector_type}, {selector_value}")
                break
            except:
                continue
        
        if not password_input:
            raise Exception("Could not find password input field with any selector")
        
        print("Entering password...")
        password_input.clear()
        time.sleep(1)
        
        for char in BOT_PASSWORD:
            password_input.send_keys(char)
            time.sleep(random.uniform(0.05, 0.12))
        
        time.sleep(1)
        
        # Click Next for password
        password_next = wait.until(EC.element_to_be_clickable((By.ID, "passwordNext")))
        password_next.click()
        time.sleep(5)
        
        # Check login status
        print("Checking login status...")
        
        try:
            wait.until(lambda driver: 
                "meet.google.com" in driver.current_url or 
                "myaccount.google.com" in driver.current_url or
                "accounts.google.com" not in driver.current_url
            )
            
            if "meet.google.com" not in driver.current_url:
                print(f"Navigating to Meet URL: {meet_url}")
                driver.get(meet_url)
                time.sleep(5)
        except:
            print("Login may require additional verification. Check the browser window.")
            input("If you see a verification screen, complete it and press Enter to continue...")
            driver.get(meet_url)
            time.sleep(5)
        
        # Join meeting
        print("Attempting to join the meeting...")
        
        try:
            time.sleep(3)
            
            print("Camera and microphone are disabled by default - joining as recording bot")
            
            join_selectors = [
                "//span[contains(text(), 'Join now')]/parent::button",
                "//span[contains(text(), 'Ask to join')]/parent::button",
                "[aria-label*='Join']",
                "button[jsname='Qx7uuf']"
            ]
            
            joined = False
            for selector in join_selectors:
                try:
                    if selector.startswith("//"):
                        join_button = driver.find_element(By.XPATH, selector)
                    else:
                        join_button = driver.find_element(By.CSS_SELECTOR, selector)
                    join_button.click()
                    print(f"Clicked join button with selector: {selector}")
                    joined = True
                    break
                except:
                    continue
            
            if not joined:
                print("Could not find join button, trying Enter key...")
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ENTER)
            
            time.sleep(5)
            
        except Exception as e:
            print(f"Error during meeting join: {e}")
        
        print("Bot should now be in the Google Meet.")
        
        # START AUDIO RECORDING
        print(f"🎵 Starting audio recording for meeting: {meeting_name}")
        recording_filename = recorder.start_recording(meeting_name, duration_minutes=60)
        print(f"📁 Recording started: {recording_filename}")
        
        print("🎧 Audio recording active... Monitoring for meeting end...")
        
        # ENHANCED MEETING END DETECTION
        consecutive_end_checks = 0
        check_interval = 3  # Check every 3 seconds
        
        try:
            while True:
                time.sleep(check_interval)
                
                current_url = driver.current_url
                page_title = driver.title.lower()
                meeting_ended = False
                
                # Method 1: URL change detection
                if "meet.google.com" not in current_url:
                    print(f"🔍 Detected URL change: {current_url}")
                    meeting_ended = True
                
                # Method 2: Check for meeting end indicators
                elif "meet.google.com" in current_url:
                    try:
                        # Look for specific meeting end messages
                        end_indicators = [
                            "//div[contains(text(), 'You left the meeting')]",
                            "//div[contains(text(), 'left the meeting')]",
                            "//div[contains(text(), 'Meeting ended')]",
                            "//div[contains(text(), 'meeting has ended')]",
                            "//div[contains(text(), 'This meeting has ended')]",
                            "//span[contains(text(), 'meeting has ended')]",
                            "//div[contains(text(), 'Thanks for joining')]",
                            "//button[contains(text(), 'Return to home screen')]",
                            "//button[contains(text(), 'Join or start a meeting')]",
                            "//div[contains(text(), 'Rejoin')]",
                            "//button[contains(@aria-label, 'Leave call')][@aria-pressed='true']"
                        ]
                        
                        for indicator in end_indicators:
                            try:
                                element = driver.find_element(By.XPATH, indicator)
                                if element.is_displayed():
                                    print(f"🔍 Detected meeting end indicator: '{element.text.strip()}'")
                                    meeting_ended = True
                                    break
                            except:
                                continue
                        
                        # Method 3: Check if we're back on main Meet page
                        if not meeting_ended:
                            main_page_indicators = [
                                "//div[contains(text(), 'Start a meeting')]",
                                "//button[contains(text(), 'New meeting')]",
                                "//input[@placeholder='Enter a code or link']",
                                "//div[@data-meeting-title]",  # Main page meeting title area
                                "//div[contains(@aria-label, 'Start a meeting')]"
                            ]
                            
                            for indicator in main_page_indicators:
                                try:
                                    element = driver.find_element(By.XPATH, indicator)
                                    if element.is_displayed():
                                        print("🔍 Detected: Back at Google Meet main page")
                                        meeting_ended = True
                                        break
                                except:
                                    continue
                        
                        # Method 4: Check for participant count = 1 (only bot left)
                        if not meeting_ended:
                            try:
                                # Look for participant indicators showing only 1 person
                                participant_indicators = [
                                    "//div[contains(@aria-label, '1 participant')]",
                                    "//span[text()='1']//parent::div[contains(@aria-label, 'participant')]"
                                ]
                                
                                for indicator in participant_indicators:
                                    try:
                                        element = driver.find_element(By.XPATH, indicator)
                                        if element.is_displayed():
                                            consecutive_end_checks += 1
                                            if consecutive_end_checks >= 3:  # Only bot left for 9 seconds
                                                print("🔍 Detected: Only bot remaining in meeting for 9+ seconds")
                                                meeting_ended = True
                                            break
                                    except:
                                        continue
                                else:
                                    consecutive_end_checks = 0  # Reset if more participants found
                                    
                            except:
                                pass
                                
                    except Exception as e:
                        print(f"Error checking page elements: {e}")
                        # If we can't check elements consistently, something may be wrong
                        consecutive_end_checks += 1
                        if consecutive_end_checks > 10:  # 30 seconds of errors
                            print("🔍 Unable to verify meeting status for 30+ seconds - assuming meeting ended")
                            meeting_ended = True
                
                if meeting_ended:
                    print("🛑 Meeting ended detected! Stopping recording...")
                    recorder.stop_recording()
                    print("✅ Recording stopped and uploaded to B2")
                    return  # Exit function to return to calendar monitoring
                else:
                    # Reset consecutive checks if meeting is still active
                    if consecutive_end_checks > 0 and consecutive_end_checks < 3:
                        consecutive_end_checks = 0
                        
        except KeyboardInterrupt:
            print("\nManual stop requested...")
        except Exception as e:
            print(f"Error during meeting monitoring: {e}")
        
        # Stop recording before cleanup
        recorder.stop_recording()
            
    except Exception as e:
        print(f"Error occurred: {e}")
        driver.save_screenshot("selenium_error.png")
        print("Screenshot saved as selenium_error.png")
        
        if recorder.is_recording:
            print("Stopping recording due to error...")
            recorder.stop_recording()
        
        print(f"Current URL: {driver.current_url}")
        print("Page title:", driver.title)
        raise
    finally:
        if recorder.is_recording:
            recorder.stop_recording()
        driver.quit()
        print("🔄 Returning to calendar monitoring...")

if __name__ == "__main__":
    test_url = input("Enter Google Meet URL to test: ")
    test_name = input("Enter meeting name (optional): ") or "test_meeting"
    join_meet(test_url, test_name)
