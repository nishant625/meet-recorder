import sounddevice as sd
import numpy as np
import wave
import threading
from datetime import datetime
import os
import time
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

# Environment detection
IS_GITHUB_ACTIONS = os.environ.get('GITHUB_ACTIONS') == 'true'
IS_RENDER = os.environ.get('RENDER') == 'true'
IS_LOCAL = not (IS_GITHUB_ACTIONS or IS_RENDER)

class AudioRecorder:
    def __init__(self, sample_rate=44100, channels=1, upload_to_b2=True):
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording = None
        self.is_recording = False
        self.record_thread = None
        self.recorded_data = []
        self.upload_to_b2 = upload_to_b2
        
        # Environment-specific settings
        if IS_GITHUB_ACTIONS:
            print("🔧 AudioRecorder: Running in GitHub Actions mode")
            # Reduce sample rate for GitHub Actions to save memory/processing
            self.sample_rate = min(sample_rate, 22050)  # Max 22kHz in GitHub Actions
            self.max_duration_minutes = 45  # Hard limit for GitHub Actions
        elif IS_RENDER:
            print("🔧 AudioRecorder: Running in Render mode")
            self.max_duration_minutes = 60
        else:
            print("🔧 AudioRecorder: Running in local mode")
            self.max_duration_minutes = 120  # No strict limit locally
        
        # Initialize B2 client if uploading is enabled
        if self.upload_to_b2:
            try:
                self.s3_client = boto3.client(
                    's3',
                    endpoint_url=os.environ.get('B2_ENDPOINT'),
                    aws_access_key_id=os.environ.get('B2_KEY_ID'),
                    aws_secret_access_key=os.environ.get('B2_APPLICATION_KEY')
                )
                self.bucket_name = os.environ.get('B2_BUCKET_NAME')
                print("✅ B2 storage connection initialized")
                
                if IS_GITHUB_ACTIONS:
                    print("📤 GitHub Actions: Will upload recordings to B2 and delete local files")
                    
            except Exception as e:
                print(f"❌ B2 connection failed: {e}")
                print("📁 Will save locally only")
                self.upload_to_b2 = False
                
                if IS_GITHUB_ACTIONS:
                    print("⚠️ GitHub Actions without B2 upload may cause storage issues")
        
    def start_recording(self, meeting_name, duration_minutes=60):
        """Start recording audio for the specified duration"""
        if self.is_recording:
            print("Already recording!")
            return None
        
        # Apply environment-specific duration limits
        if IS_GITHUB_ACTIONS:
            duration_minutes = min(duration_minutes, self.max_duration_minutes)
            print(f"⚠️ GitHub Actions mode: Recording limited to {duration_minutes} minutes")
        elif duration_minutes > self.max_duration_minutes:
            print(f"⚠️ Duration capped at {self.max_duration_minutes} minutes for this environment")
            duration_minutes = self.max_duration_minutes
            
        # Create recordings directory if it doesn't exist (skip in GitHub Actions if no B2)
        if not IS_GITHUB_ACTIONS or self.upload_to_b2:
            os.makedirs("recordings", exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Clean meeting name for filename (GitHub Actions compatible)
        clean_meeting_name = "".join(c for c in meeting_name if c.isalnum() or c in (' ', '-', '_')).strip()
        clean_meeting_name = clean_meeting_name.replace(' ', '_')[:50]  # Limit length
        
        filename = f"recordings/meeting_{clean_meeting_name}_{timestamp}.wav"
        
        print(f"🎵 Starting audio recording: {filename}")
        print(f"🔊 Sample rate: {self.sample_rate} Hz")
        print(f"📊 Channels: {self.channels}")
        print(f"⏱️ Max duration: {duration_minutes} minutes")
        
        if self.upload_to_b2:
            print("📤 Will upload to B2 storage after recording")
        elif IS_GITHUB_ACTIONS:
            print("⚠️ GitHub Actions without B2: Recording will be lost after workflow ends")
        
        self.is_recording = True
        self.recorded_data = []  # Reset recorded data
        self.start_time = time.time()  # Track recording start time
        
        # Start recording in a separate thread with streaming
        def record_audio():
            try:
                print("🎙️ Recording started... Will auto-stop when meeting ends")
                
                # Record in chunks so we can stop dynamically
                chunk_duration = 2.0 if IS_GITHUB_ACTIONS else 1.0  # Larger chunks in GitHub Actions
                chunk_frames = int(chunk_duration * self.sample_rate)
                max_duration_seconds = duration_minutes * 60
                
                while self.is_recording:
                    # Check if we've exceeded maximum duration
                    elapsed_time = time.time() - self.start_time
                    if elapsed_time > max_duration_seconds:
                        print(f"⏰ Maximum recording duration ({duration_minutes} minutes) reached")
                        break
                    
                    try:
                        # Record a chunk with timeout protection
                        chunk = sd.rec(
                            chunk_frames, 
                            samplerate=self.sample_rate, 
                            channels=self.channels,
                            dtype='int16'
                        )
                        sd.wait()  # Wait for this chunk to complete
                        
                        if self.is_recording:  # Check if we should still be recording
                            self.recorded_data.append(chunk)
                            
                            # Progress indicator for longer recordings
                            if IS_GITHUB_ACTIONS and len(self.recorded_data) % 30 == 0:  # Every minute
                                minutes_recorded = len(self.recorded_data) * chunk_duration / 60
                                print(f"🎙️ Recording progress: {minutes_recorded:.1f} minutes")
                    
                    except Exception as chunk_error:
                        print(f"⚠️ Audio chunk recording error: {chunk_error}")
                        if IS_GITHUB_ACTIONS:
                            # In GitHub Actions, audio issues are more common, so be more tolerant
                            print("🔄 Continuing recording despite audio error...")
                            continue
                        else:
                            break
                
                # Save the recording
                if self.recorded_data:
                    self.save_recording(filename)
                else:
                    print("❌ No audio data recorded")
                
            except KeyboardInterrupt:
                print("\n🛑 Recording stopped by user")
                if self.recorded_data:
                    self.save_recording(filename)
            except Exception as e:
                print(f"❌ Recording error: {e}")
                if IS_GITHUB_ACTIONS:
                    print("🔄 GitHub Actions: Attempting to save partial recording...")
                    if self.recorded_data:
                        self.save_recording(filename)
            finally:
                self.is_recording = False
        
        # Start recording thread
        self.record_thread = threading.Thread(target=record_audio, daemon=True)
        self.record_thread.start()
        
        return filename
    
    def save_recording(self, filename):
        """Save the recorded audio to a WAV file and optionally upload to B2"""
        if not self.recorded_data:
            print("❌ No recording data to save")
            return
            
        try:
            print("💾 Saving recording...")
            
            # Combine all chunks
            full_recording = np.concatenate(self.recorded_data, axis=0)
            
            # Calculate file stats
            duration_seconds = len(full_recording) / self.sample_rate
            duration_minutes = duration_seconds / 60
            
            # Save locally first (unless GitHub Actions without B2)
            local_saved = False
            if not IS_GITHUB_ACTIONS or self.upload_to_b2:
                with wave.open(filename, 'wb') as wf:
                    wf.setnchannels(self.channels)
                    wf.setsampwidth(2)  # 16-bit audio
                    wf.setframerate(self.sample_rate)
                    wf.writeframes(full_recording.tobytes())
                
                file_size = os.path.getsize(filename) / (1024 * 1024)  # MB
                local_saved = True
                
                print(f"📁 Recording saved locally: {filename}")
                print(f"📊 File size: {file_size:.2f} MB")
                print(f"⏱️ Duration: {duration_minutes:.2f} minutes ({duration_seconds:.1f} seconds)")
            else:
                # GitHub Actions without B2 - calculate size without saving
                estimated_size = len(full_recording.tobytes()) / (1024 * 1024)
                print(f"📊 Estimated file size: {estimated_size:.2f} MB")
                print(f"⏱️ Duration: {duration_minutes:.2f} minutes ({duration_seconds:.1f} seconds)")
                print("⚠️ GitHub Actions: File not saved locally (no B2 upload configured)")
            
            # Upload to B2 if enabled
            if self.upload_to_b2:
                if local_saved:
                    self.upload_to_b2_storage(filename, file_size)
                else:
                    # Direct upload from memory for GitHub Actions
                    self.upload_to_b2_from_memory(filename, full_recording, duration_minutes)
            
        except Exception as e:
            print(f"❌ Error saving recording: {e}")
            if IS_GITHUB_ACTIONS:
                import traceback
                traceback.print_exc()
    
    def upload_to_b2_from_memory(self, filename, audio_data, duration_minutes):
        """Upload recording directly from memory (for GitHub Actions without local storage)"""
        try:
            print("📤 Uploading directly to B2 from memory...")
            
            # Create temporary in-memory WAV file
            import io
            wav_buffer = io.BytesIO()
            
            with wave.open(wav_buffer, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_data.tobytes())
            
            wav_buffer.seek(0)
            file_size_mb = len(wav_buffer.getvalue()) / (1024 * 1024)
            
            # Upload from memory
            file_basename = os.path.basename(filename)
            b2_key = f"recordings/{file_basename}"
            
            self.s3_client.upload_fileobj(
                wav_buffer,
                self.bucket_name,
                b2_key,
                ExtraArgs={
                    'ContentType': 'audio/wav',
                    'Metadata': {
                        'uploaded_by': 'google-meet-bot-github-actions',
                        'file_size_mb': str(round(file_size_mb, 2)),
                        'duration_minutes': str(round(duration_minutes, 2)),
                        'sample_rate': str(self.sample_rate)
                    }
                }
            )
            
            print(f"✅ Successfully uploaded to B2 from memory: {b2_key}")
            print(f"📊 Uploaded size: {file_size_mb:.2f} MB")
            
        except Exception as e:
            print(f"❌ Memory upload to B2 failed: {e}")
            import traceback
            traceback.print_exc()
    
    def upload_to_b2_storage(self, filename, file_size_mb):
        """Upload the recording to Backblaze B2"""
        try:
            print("📤 Uploading to B2 storage...")
            
            # Create B2 key (path in bucket)
            file_basename = os.path.basename(filename)
            b2_key = f"recordings/{file_basename}"
            
            # Upload file with environment metadata
            upload_metadata = {
                'uploaded_by': f'google-meet-bot-{("github-actions" if IS_GITHUB_ACTIONS else "render" if IS_RENDER else "local")}',
                'file_size_mb': str(round(file_size_mb, 2)),
                'sample_rate': str(self.sample_rate)
            }
            
            self.s3_client.upload_file(
                filename, 
                self.bucket_name, 
                b2_key,
                ExtraArgs={
                    'ContentType': 'audio/wav',
                    'Metadata': upload_metadata
                }
            )
            
            print(f"✅ Successfully uploaded to B2: {b2_key}")
            
            # Delete local file to save space (always in GitHub Actions, optional elsewhere)
            if IS_GITHUB_ACTIONS or IS_RENDER:
                try:
                    os.remove(filename)
                    print(f"🗑️ Local file deleted: {filename}")
                except Exception as delete_error:
                    print(f"⚠️ Could not delete local file: {delete_error}")
            elif not IS_LOCAL:
                print("🗑️ Deleting local file to save space...")
                os.remove(filename)
                print(f"🗑️ Local file deleted: {filename}")
            else:
                print("📁 Local file kept for development")
            
        except ClientError as e:
            print(f"❌ B2 upload failed: {e}")
            print("📁 Recording saved locally only")
        except Exception as e:
            print(f"❌ Upload error: {e}")
            print("📁 Recording saved locally only")
    
    def stop_recording(self):
        """Stop the current recording"""
        if self.is_recording:
            print("🛑 Stopping recording...")
            self.is_recording = False
            
            # Wait for the recording thread to finish
            if self.record_thread:
                timeout = 10 if IS_GITHUB_ACTIONS else 3  # Longer timeout in GitHub Actions
                self.record_thread.join(timeout=timeout)
                
                if self.record_thread.is_alive():
                    print("⚠️ Recording thread did not stop cleanly")
                else:
                    print("✅ Recording stopped successfully")
        else:
            print("ℹ️ No active recording to stop")

def test_audio_system():
    """Test audio recording system"""
    print("🧪 Testing audio recording system...")
    
    if IS_GITHUB_ACTIONS:
        print("⚠️ GitHub Actions: Audio testing may not work in headless environment")
        return False
    
    try:
        # Test audio device availability
        devices = sd.query_devices()
        print(f"📱 Found {len(devices)} audio devices")
        
        # Test short recording
        print("🎙️ Testing 2-second recording...")
        test_data = sd.rec(int(2 * 22050), samplerate=22050, channels=1, dtype='int16')
        sd.wait()
        
        if len(test_data) > 0:
            print("✅ Audio recording test successful")
            return True
        else:
            print("❌ Audio recording test failed: No data")
            return False
            
    except Exception as e:
        print(f"❌ Audio system test failed: {e}")
        return False

# Test the recorder with B2 upload
if __name__ == "__main__":
    print("🚀 AudioRecorder Test")
    
    # Test audio system first
    if not IS_GITHUB_ACTIONS:
        audio_works = test_audio_system()
        if not audio_works:
            print("❌ Audio system test failed - recording may not work")
    
    # Initialize recorder
    recorder = AudioRecorder(upload_to_b2=True)
    
    if IS_GITHUB_ACTIONS:
        print("🤖 GitHub Actions: AudioRecorder initialized for automated use")
    else:
        # Interactive test for local/Render environments
        print("Testing audio recorder with B2 upload...")
        filename = recorder.start_recording("test", duration_minutes=0.17)  # ~10 seconds
        
        input("Press Enter to stop recording...")
        recorder.stop_recording()
