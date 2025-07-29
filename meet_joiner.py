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
from audio_recorder import AudioRecorder  # Add this import

load_dotenv()

BOT_EMAIL = os.environ["BOT_EMAIL"]
BOT_PASSWORD = os.environ["BOT_PASSWORD"]

def join_meet(meet_url, meeting_name="meeting"):  # Add meeting_name parameter
    chrome_options = Options()
    chrome_options.add_argument("--use-fake-ui-for-media-stream")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    wait = WebDriverWait(driver, 30)
    recorder = AudioRecorder()  # Initialize recorder
    
    try:
        print("Starting Google login process...")
        
        # Go directly to Google accounts with the meet URL as continue parameter
        login_url = f"https://accounts.google.com/signin/v2/identifier?continue={meet_url}&flowName=GlifWebSignIn&flowEntry=ServiceLogin"
        driver.get(login_url)
        time.sleep(3)
        
        # Enter email with human-like typing
        print("Entering email...")
        email_input = wait.until(
            EC.element_to_be_clickable((By.ID, "identifierId"))
        )
        email_input.clear()
        
        # Type email with random delays to mimic human behavior
        for char in BOT_EMAIL:
            email_input.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))  # Random delay between keystrokes
        
        time.sleep(1)
        
        # Click Next
        next_button = wait.until(
            EC.element_to_be_clickable((By.ID, "identifierNext"))
        )
        next_button.click()
        time.sleep(4)  # Wait longer for the password page to load
        
        # Handle recovery setup screen if it appears
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
        
        # Wait for password page and try multiple selectors
        print("Waiting for password field...")
        password_input = None
        
        # Try different selectors for password field
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
                password_input = wait.until(
                    EC.element_to_be_clickable((selector_type, selector_value))
                )
                print(f"Found password field with selector: {selector_type}, {selector_value}")
                break
            except:
                continue
        
        if not password_input:
            raise Exception("Could not find password input field with any selector")
        
        # Enter password with human-like typing
        print("Entering password...")
        password_input.clear()
        time.sleep(1)
        
        for char in BOT_PASSWORD:
            password_input.send_keys(char)
            time.sleep(random.uniform(0.05, 0.12))  # Random delay between keystrokes
        
        time.sleep(1)
        
        # Click Next for password
        password_next = wait.until(
            EC.element_to_be_clickable((By.ID, "passwordNext"))
        )
        password_next.click()
        time.sleep(5)
        
        # Check if we're redirected to the Meet URL or need additional steps
        print("Checking login status...")
        
        # Wait for either Meet URL or account verification
        try:
            wait.until(lambda driver: 
                "meet.google.com" in driver.current_url or 
                "myaccount.google.com" in driver.current_url or
                "accounts.google.com" not in driver.current_url
            )
            
            # If not already on Meet, navigate there
            if "meet.google.com" not in driver.current_url:
                print(f"Navigating to Meet URL: {meet_url}")
                driver.get(meet_url)
                time.sleep(5)
        except:
            print("Login may require additional verification. Check the browser window.")
            input("If you see a verification screen, complete it and press Enter to continue...")
            driver.get(meet_url)
            time.sleep(5)
        
        # Meet joining and recording logic
        print("Attempting to join the meeting...")
        
        # Turn off camera and mic, then join
        try:
            # Wait a bit for Meet to load
            time.sleep(3)
            

            
            # Try to join the meeting
            join_selectors = [
                "//span[contains(text(), 'Join now')]/parent::button",
                "//span[contains(text(), 'Ask to join')]/parent::button",
                "[aria-label*='Join']",
                "button[jsname='Qx7uuf']"  # Common Google Meet join button
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
            
        except Exception as e:
            print(f"Error during meeting join: {e}")
        
        print("Bot should now be in the Google Meet.")
        
        # START AUDIO RECORDING HERE
        print(f"Starting audio recording for meeting: {meeting_name}")
        recording_filename = recorder.start_recording(meeting_name, duration_minutes=60)
        print(f"Recording started: {recording_filename}")
        
        print("Press Ctrl+C to stop the bot and leave the meeting...")
        
        # Keep the browser open and recording
        try:
            while True:
                time.sleep(1)
                # Optional: Check if we're still in the meeting
                if "meet.google.com" not in driver.current_url:
                    print("Detected that meeting may have ended or we were disconnected")
                    break
        except KeyboardInterrupt:
            print("\nStopping bot and recording...")
            recorder.stop_recording()
            
    except Exception as e:
        print(f"Error occurred: {e}")
        # Take screenshot for debugging
        driver.save_screenshot("selenium_error.png")
        print("Screenshot saved as selenium_error.png")
        
        # Stop recording if there's an error
        if recorder.is_recording:
            print("Stopping recording due to error...")
            recorder.stop_recording()
        
        # Print current URL and page source for debugging
        print(f"Current URL: {driver.current_url}")
        print("Page title:", driver.title)
        raise
    finally:
        # Ensure recording stops and browser closes
        if recorder.is_recording:
            recorder.stop_recording()
        driver.quit()

if __name__ == "__main__":
    test_url = input("Enter Google Meet URL to test: ")
    test_name = input("Enter meeting name (optional): ") or "test_meeting"
    join_meet(test_url, test_name)
