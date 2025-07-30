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

class AudioRecorder:
    def __init__(self, sample_rate=44100, channels=1, upload_to_b2=True):
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording = None
        self.is_recording = False
        self.record_thread = None
        self.recorded_data = []
        self.upload_to_b2 = upload_to_b2
        
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
            except Exception as e:
                print(f"❌ B2 connection failed: {e}")
                print("📁 Will save locally only")
                self.upload_to_b2 = False
        
    def start_recording(self, meeting_name, duration_minutes=60):
        """Start recording audio for the specified duration"""
        if self.is_recording:
            print("Already recording!")
            return None
            
        # Create recordings directory if it doesn't exist
        os.makedirs("recordings", exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"recordings/meeting_{meeting_name}_{timestamp}.wav"
        
        print(f"Starting audio recording: {filename}")
        if self.upload_to_b2:
            print("📤 Will upload to B2 storage after recording")
        print(f"Max duration: {duration_minutes} minutes")
        
        self.is_recording = True
        self.recorded_data = []  # Reset recorded data
        
        # Start recording in a separate thread with streaming
        def record_audio():
            try:
                print("Recording started... Will auto-stop when meeting ends")
                
                # Record in chunks so we can stop dynamically
                chunk_duration = 1.0  # 1 second chunks
                chunk_frames = int(chunk_duration * self.sample_rate)
                
                while self.is_recording:
                    # Record a small chunk
                    chunk = sd.rec(
                        chunk_frames, 
                        samplerate=self.sample_rate, 
                        channels=self.channels,
                        dtype='int16'
                    )
                    sd.wait()  # Wait for this chunk to complete
                    
                    if self.is_recording:  # Check if we should still be recording
                        self.recorded_data.append(chunk)
                
                # Save the recording
                self.save_recording(filename)
                
            except KeyboardInterrupt:
                print("\nRecording stopped by user")
                self.save_recording(filename)
            except Exception as e:
                print(f"Recording error: {e}")
            finally:
                self.is_recording = False
        
        # Start recording thread
        self.record_thread = threading.Thread(target=record_audio, daemon=True)
        self.record_thread.start()
        
        return filename
    
    def save_recording(self, filename):
        """Save the recorded audio to a WAV file and optionally upload to B2"""
        if not self.recorded_data:
            print("No recording data to save")
            return
            
        try:
            # Combine all chunks
            full_recording = np.concatenate(self.recorded_data, axis=0)
            
            # Save locally first
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)  # 16-bit audio
                wf.setframerate(self.sample_rate)
                wf.writeframes(full_recording.tobytes())
            
            duration_seconds = len(full_recording) / self.sample_rate
            duration_minutes = duration_seconds / 60
            file_size = os.path.getsize(filename) / (1024 * 1024)  # MB
            
            print(f"📁 Recording saved locally: {filename}")
            print(f"📊 File size: {file_size:.2f} MB")
            print(f"⏱️  Duration: {duration_minutes:.2f} minutes ({duration_seconds:.1f} seconds)")
            
            # Upload to B2 if enabled
            if self.upload_to_b2:
                self.upload_to_b2_storage(filename, file_size)
            
        except Exception as e:
            print(f"❌ Error saving recording: {e}")
    
    def upload_to_b2_storage(self, filename, file_size_mb):
        """Upload the recording to Backblaze B2"""
        try:
            print("📤 Uploading to B2 storage...")
            
            # Create B2 key (path in bucket)
            file_basename = os.path.basename(filename)
            b2_key = f"recordings/{file_basename}"
            
            # Upload file
            self.s3_client.upload_file(
                filename, 
                self.bucket_name, 
                b2_key,
                ExtraArgs={
                    'ContentType': 'audio/wav',
                    'Metadata': {
                        'uploaded_by': 'google-meet-bot',
                        'file_size_mb': str(round(file_size_mb, 2))
                    }
                }
            )
            
            print(f"✅ Successfully uploaded to B2: {b2_key}")
            
            # Delete local file to save space (automatic in production)
            print("🗑️  Deleting local file to save space...")
            os.remove(filename)
            print(f"🗑️  Local file deleted: {filename}")
            
        except ClientError as e:
            print(f"❌ B2 upload failed: {e}")
            print("📁 Recording saved locally only")
        except Exception as e:
            print(f"❌ Upload error: {e}")
            print("📁 Recording saved locally only")
    
    def stop_recording(self):
        """Stop the current recording"""
        if self.is_recording:
            print("Stopping recording...")
            self.is_recording = False
            
            # Wait a moment for the recording thread to finish
            if self.record_thread:
                self.record_thread.join(timeout=3)

# Test the recorder with B2 upload
if __name__ == "__main__":
    recorder = AudioRecorder(upload_to_b2=True)
    
    # Test recording for 10 seconds
    print("Testing audio recorder with B2 upload...")
    filename = recorder.start_recording("test", duration_minutes=0.17)  # ~10 seconds
    
    input("Press Enter to stop recording...")
    recorder.stop_recording()
