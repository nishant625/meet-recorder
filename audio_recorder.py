import sounddevice as sd
import numpy as np
import wave
import threading
from datetime import datetime
import os
import time

class AudioRecorder:
    def __init__(self, sample_rate=44100, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording = None
        self.is_recording = False
        self.record_thread = None
        self.recorded_data = []
        
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
        """Save the recorded audio to a WAV file"""
        if not self.recorded_data:
            print("No recording data to save")
            return
            
        try:
            # Combine all chunks
            full_recording = np.concatenate(self.recorded_data, axis=0)
            
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)  # 16-bit audio
                wf.setframerate(self.sample_rate)
                wf.writeframes(full_recording.tobytes())
            
            duration_seconds = len(full_recording) / self.sample_rate
            duration_minutes = duration_seconds / 60
            
            print(f"Recording saved: {filename}")
            file_size = os.path.getsize(filename) / (1024 * 1024)  # MB
            print(f"File size: {file_size:.2f} MB")
            print(f"Actual duration: {duration_minutes:.2f} minutes ({duration_seconds:.1f} seconds)")
            
        except Exception as e:
            print(f"Error saving recording: {e}")
    
    def stop_recording(self):
        """Stop the current recording"""
        if self.is_recording:
            print("Stopping recording...")
            self.is_recording = False
            
            # Wait a moment for the recording thread to finish
            if self.record_thread:
                self.record_thread.join(timeout=3)
