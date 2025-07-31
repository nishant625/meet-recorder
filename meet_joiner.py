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

# Environment detection
IS_GITHUB_ACTIONS = os.environ.get('GITHUB_ACTIONS') == 'true'
IS_RENDER = os.environ.get('RENDER') == 'true'
IS_LOCAL = not (IS_GITHUB_ACTIONS or IS_RENDER)

BOT_EMAIL = os.environ["BOT_EMAIL"]
BOT_PASSWORD = os.environ["BOT_PASSWORD"]

def join_meet(meet_url, meeting_name="meeting"):
    if IS_GITHUB_ACTIONS:
        print("🔧 Running in GitHub Actions environment")
    elif IS_RENDER:
        print("🔧 Running in Render environment")
    else:
        print("🔧 Running in local environment")
    
    chromedriver_autoinstaller.install()
    chrome_options = Options()
    
    # Base Chrome options for headless operation
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    # GitHub Actions specific optimizations
    if IS_GITHUB_ACTIONS:
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--single-process")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--max_old_space_size=4096")
    else:
        chrome_options.add_argument("--remote-debugging-port=9222")
    
    # Media and automation options
    chrome_options.add_argument("--use-fake-ui-for-media-stream")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    # Adjust timeouts based on environment
    timeout_duration = 20 if IS_GITHUB_ACTIONS else 30
    wait = WebDriverWait(driver, timeout_duration)
    
    recorder = AudioRecorder(upload_to_b2=True)
    
    try:
        print("Starting Google login process...")
        
        # Login URL
        login_url = f"https://accounts.google.com/signin/v2/identifier?continue={meet_url}&flowName=GlifWebSignIn&flowEntry=ServiceLogin"
        driver.get(login_url)
        time.sleep(2 if IS_GITHUB_ACTIONS else 3)
        
        # Enter email with human-like typing
        print("Entering email...")
        email_input = wait.until(EC.element_to_be_clickable((By.ID, "identifierId")))
        email_input.clear()
        
        # Faster typing in GitHub Actions
        typing_delay = (0.02, 0.08) if IS_GITHUB_ACTIONS else (0.05, 0.15)
        for char in BOT_EMAIL:
            email_input.send_keys(char)
            time.sleep(random.uniform(*typing_delay))
        
        time.sleep(0.5 if IS_GITHUB_ACTIONS else 1)
        
        # Click Next
        next_button = wait.until(EC.element_to_be_clickable((By.ID, "identifierNext")))
        next_button.click()
        time.sleep(3 if IS_GITHUB_ACTIONS else 4)
        
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
                
                if not skipped and not IS_GITHUB_ACTIONS:
                    print("Could not find skip button. Manual intervention may be needed.")
                    input("Please manually skip the recovery setup and press Enter to continue...")
                elif not skipped and IS_GITHUB_ACTIONS:
                    print("⚠️ Could not skip recovery screen in GitHub Actions - may cause issues")
                
                time.sleep(2 if IS_GITHUB_ACTIONS else 3)
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
        time.sleep(0.5 if IS_GITHUB_ACTIONS else 1)
        
        # Faster password typing in GitHub Actions
        for char in BOT_PASSWORD:
            password_input.send_keys(char)
            time.sleep(random.uniform(*typing_delay))
        
        time.sleep(0.5 if IS_GITHUB_ACTIONS else 1)
        
        # Click Next for password
        password_next = wait.until(EC.element_to_be_clickable((By.ID, "passwordNext")))
        password_next.click()
        time.sleep(4 if IS_GITHUB_ACTIONS else 5)
        
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
                time.sleep(4 if IS_GITHUB_ACTIONS else 5)
        except:
            if IS_GITHUB_ACTIONS:
                print("⚠️ Login verification required - this may fail in GitHub Actions")
                # Try to continue anyway
                driver.get(meet_url)
                time.sleep(4)
            else:
                print("Login may require additional verification. Check the browser window.")
                input("If you see a verification screen, complete it and press Enter to continue...")
                driver.get(meet_url)
                time.sleep(5)
        
        # Join meeting
        print("Attempting to join the meeting...")
        
        try:
            time.sleep(2 if IS_GITHUB_ACTIONS else 3)
            
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
            
            time.sleep(4 if IS_GITHUB_ACTIONS else 5)
            
        except Exception as e:
            print(f"Error during meeting join: {e}")
        
        print("Bot should now be in the Google Meet.")
        
        # START AUDIO RECORDING
        print(f"🎵 Starting audio recording for meeting: {meeting_name}")
        
        # Adjust recording duration based on environment
        max_duration = 45 if IS_GITHUB_ACTIONS else 60  # GitHub Actions timeout protection
        recording_filename = recorder.start_recording(meeting_name, duration_minutes=max_duration)
        print(f"📁 Recording started: {recording_filename}")
        
        if IS_GITHUB_ACTIONS:
            print("⚠️ GitHub Actions mode: Maximum 45-minute recording to avoid timeout")
        
        print("🎧 Audio recording active... Monitoring for meeting end...")
        
        # ENHANCED MEETING END DETECTION with GitHub Actions optimizations
        consecutive_end_checks = 0
        check_interval = 5 if IS_GITHUB_ACTIONS else 3  # Less frequent checks in GitHub Actions
        max_meeting_duration = 45 * 60 if IS_GITHUB_ACTIONS else 60 * 60  # 45 or 60 minutes
        start_time = time.time()
        
        try:
            while True:
                # GitHub Actions timeout protection
                elapsed_time = time.time() - start_time
                if IS_GITHUB_ACTIONS and elapsed_time > max_meeting_duration:
                    print(f"⏰ Reached maximum recording time ({max_meeting_duration/60:.1f} minutes)")
                    print("🛑 Stopping to avoid GitHub Actions timeout...")
                    recorder.stop_recording()
                    return
                
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
                                "//div[@data-meeting-title]",
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
                                participant_indicators = [
                                    "//div[contains(@aria-label, '1 participant')]",
                                    "//span[text()='1']//parent::div[contains(@aria-label, 'participant')]"
                                ]
                                
                                for indicator in participant_indicators:
                                    try:
                                        element = driver.find_element(By.XPATH, indicator)
                                        if element.is_displayed():
                                            consecutive_end_checks += 1
                                            # More lenient threshold in GitHub Actions
                                            threshold = 2 if IS_GITHUB_ACTIONS else 3
                                            if consecutive_end_checks >= threshold:
                                                duration = threshold * check_interval
                                                print(f"🔍 Detected: Only bot remaining in meeting for {duration}+ seconds")
                                                meeting_ended = True
                                            break
                                    except:
                                        continue
                                else:
                                    consecutive_end_checks = 0
                                    
                            except:
                                pass
                                
                    except Exception as e:
                        print(f"Error checking page elements: {e}")
                        consecutive_end_checks += 1
                        # More aggressive timeout in GitHub Actions
                        error_threshold = 6 if IS_GITHUB_ACTIONS else 10
                        if consecutive_end_checks > error_threshold:
                            duration = error_threshold * check_interval
                            print(f"🔍 Unable to verify meeting status for {duration}+ seconds - assuming meeting ended")
                            meeting_ended = True
                
                if meeting_ended:
                    print("🛑 Meeting ended detected! Stopping recording...")
                    recorder.stop_recording()
                    print("✅ Recording stopped and uploaded to B2")
                    return
                else:
                    # Reset consecutive checks if meeting is still active
                    if consecutive_end_checks > 0 and consecutive_end_checks < (2 if IS_GITHUB_ACTIONS else 3):
                        consecutive_end_checks = 0
                        
        except KeyboardInterrupt:
            print("\nManual stop requested...")
        except Exception as e:
            print(f"Error during meeting monitoring: {e}")
        
        # Stop recording before cleanup
        recorder.stop_recording()
            
    except Exception as e:
        print(f"Error occurred: {e}")
        
        # Save screenshot for debugging (but not in GitHub Actions due to space limits)
        if not IS_GITHUB_ACTIONS:
            try:
                driver.save_screenshot("selenium_error.png")
                print("Screenshot saved as selenium_error.png")
            except:
                print("Could not save screenshot")
        
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

def test_meet_join():
    """Test function for verifying Meet joining functionality"""
    if IS_GITHUB_ACTIONS:
        print("⚠️ Cannot run interactive test in GitHub Actions")
        return False
    
    test_url = input("Enter Google Meet URL to test: ")
    test_name = input("Enter meeting name (optional): ") or "test_meeting"
    
    try:
        join_meet(test_url, test_name)
        return True
    except Exception as e:
        print(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    if IS_GITHUB_ACTIONS:
        print("🤖 Meet joiner ready for GitHub Actions")
    else:
        test_meet_join()
