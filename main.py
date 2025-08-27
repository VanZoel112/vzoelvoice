#!/usr/bin/env python3
"""
Voice Clone Userbot with Real-time Voice Modification
Supports character voices: Jokowi, Squidward, SpongeBob, Ganjar, Clara
"""

import os
import sys
import asyncio
import threading
import numpy as np
import sounddevice as sd
from scipy.signal import resample, butter, filtfilt
import logging
from pyrogram import Client, filters
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid, PhoneNumberInvalid
import json
from pathlib import Path

# ================================
# ENVIRONMENT CONFIGURATION
# ================================

class Config:
    # Telegram API Configuration
    API_ID = 29919905
    API_HASH = "717957f0e3ae20a7db004d08b66bfd30"
    PHONE_NUMBER = "+6283199218067"
    
    # Voice Configuration
    SAMPLE_RATE = 44100
    BUFFER_SIZE = 1024
    
    # Session Configuration
    SESSION_NAME = "voice_clone_userbot"
    
    # Voice Characters Database
    VOICE_CHARACTERS = {
        "jokowi": {
            "name": "Joko Widodo",
            "pitch_factor": 0.85,
            "formant_shift": 0.9,
            "speaking_rate": 0.9,
            "tone_profile": "authoritative"
        },
        "squidward": {
            "name": "Squidward Tentacles", 
            "pitch_factor": 0.7,
            "formant_shift": 1.1,
            "speaking_rate": 0.8,
            "tone_profile": "nasal"
        },
        "spongebob": {
            "name": "SpongeBob SquarePants",
            "pitch_factor": 1.4,
            "formant_shift": 1.3,
            "speaking_rate": 1.2,
            "tone_profile": "excited"
        },
        "ganjar": {
            "name": "Ganjar Pranowo",
            "pitch_factor": 0.9,
            "formant_shift": 0.95,
            "speaking_rate": 1.0,
            "tone_profile": "friendly"
        },
        "clara": {
            "name": "Clara Mongstar",
            "pitch_factor": 1.2,
            "formant_shift": 1.15,
            "speaking_rate": 1.1,
            "tone_profile": "energetic"
        }
    }

# ================================
# VOICE PROCESSING ENGINE
# ================================

class VoiceCloneEngine:
    def __init__(self):
        self.is_active = False
        self.current_character = "normal"
        self.audio_thread = None
        self.input_stream = None
        self.output_stream = None
        self.processing_lock = threading.Lock()
        
        # Audio processing parameters
        self.sample_rate = Config.SAMPLE_RATE
        self.buffer_size = Config.BUFFER_SIZE
        
        # Voice modification buffers
        self.audio_buffer = np.zeros(self.buffer_size * 4)
        self.buffer_index = 0
        
    def apply_character_voice(self, audio_data, character):
        """Apply specific character voice transformation"""
        if character == "normal" or character not in Config.VOICE_CHARACTERS:
            return audio_data
            
        char_config = Config.VOICE_CHARACTERS[character]
        processed = audio_data.copy()
        
        try:
            # Pitch modification
            if char_config["pitch_factor"] != 1.0:
                processed = self.pitch_shift(processed, char_config["pitch_factor"])
            
            # Formant shifting for voice character
            if char_config["formant_shift"] != 1.0:
                processed = self.formant_shift(processed, char_config["formant_shift"])
            
            # Apply tone profile specific effects
            tone = char_config["tone_profile"]
            if tone == "nasal":
                processed = self.apply_nasal_effect(processed)
            elif tone == "excited":
                processed = self.apply_excitement_effect(processed)
            elif tone == "authoritative":
                processed = self.apply_authority_effect(processed)
            elif tone == "friendly":
                processed = self.apply_warmth_effect(processed)
            elif tone == "energetic":
                processed = self.apply_energy_effect(processed)
                
            return processed
            
        except Exception as e:
            logging.error(f"Character voice processing error: {e}")
            return audio_data
    
    def pitch_shift(self, audio_data, factor):
        """Advanced pitch shifting with quality preservation"""
        if factor == 1.0:
            return audio_data
            
        # Use phase vocoder approach for better quality
        hop_length = 256
        window_size = 1024
        
        # Simple resampling approach for real-time processing
        new_length = int(len(audio_data) * factor)
        if new_length > 0:
            shifted = resample(audio_data, new_length)
            
            # Adjust length to match original
            if len(shifted) < len(audio_data):
                padded = np.zeros(len(audio_data))
                padded[:len(shifted)] = shifted
                return padded
            else:
                return shifted[:len(audio_data)]
        return audio_data
    
    def formant_shift(self, audio_data, factor):
        """Formant frequency shifting for voice character"""
        if factor == 1.0:
            return audio_data
            
        # Apply spectral envelope modification
        # Simplified approach using filtering
        nyquist = self.sample_rate / 2
        
        if factor > 1.0:
            # Higher formants - brighter voice
            low = 200 / nyquist
            high = min(3000 * factor, nyquist - 100) / nyquist
            b, a = butter(4, [low, high], btype='band')
            return filtfilt(b, a, audio_data)
        else:
            # Lower formants - deeper voice
            cutoff = min(2000 * factor, nyquist - 100) / nyquist
            b, a = butter(4, cutoff, btype='low')
            return filtfilt(b, a, audio_data)
    
    def apply_nasal_effect(self, audio_data):
        """Squidward's nasal effect"""
        # Emphasize nasal frequencies (1000-2000 Hz)
        nyquist = self.sample_rate / 2
        low = 1000 / nyquist
        high = 2000 / nyquist
        b, a = butter(2, [low, high], btype='band')
        filtered = filtfilt(b, a, audio_data)
        return audio_data + 0.3 * filtered
    
    def apply_excitement_effect(self, audio_data):
        """SpongeBob's excited effect"""
        # Add slight tremolo and boost high frequencies
        t = np.arange(len(audio_data)) / self.sample_rate
        tremolo = 1 + 0.1 * np.sin(2 * np.pi * 5 * t)  # 5 Hz tremolo
        
        # High frequency boost
        nyquist = self.sample_rate / 2
        cutoff = 2000 / nyquist
        b, a = butter(2, cutoff, btype='high')
        high_boost = filtfilt(b, a, audio_data)
        
        return (audio_data + 0.2 * high_boost) * tremolo
    
    def apply_authority_effect(self, audio_data):
        """Jokowi's authoritative effect"""
        # Boost low-mid frequencies for authority
        nyquist = self.sample_rate / 2
        low = 150 / nyquist  
        high = 800 / nyquist
        b, a = butter(3, [low, high], btype='band')
        filtered = filtfilt(b, a, audio_data)
        return audio_data + 0.25 * filtered
    
    def apply_warmth_effect(self, audio_data):
        """Ganjar's friendly warmth effect"""
        # Gentle low-frequency warmth
        nyquist = self.sample_rate / 2
        cutoff = 500 / nyquist
        b, a = butter(2, cutoff, btype='low')
        warm = filtfilt(b, a, audio_data)
        return audio_data + 0.15 * warm
    
    def apply_energy_effect(self, audio_data):
        """Clara's energetic effect"""
        # Brightness and slight compression
        nyquist = self.sample_rate / 2
        cutoff = 1500 / nyquist
        b, a = butter(2, cutoff, btype='high')
        bright = filtfilt(b, a, audio_data)
        
        # Simple compression effect
        threshold = 0.3
        compressed = np.where(np.abs(audio_data) > threshold,
                            threshold + (audio_data - threshold) * 0.5,
                            audio_data)
        
        return compressed + 0.2 * bright
    
    def audio_callback(self, indata, outdata, frames, time, status):
        """Real-time audio processing callback"""
        if status:
            logging.warning(f"Audio status: {status}")
        
        try:
            with self.processing_lock:
                # Convert to mono
                mono_input = indata[:, 0] if len(indata.shape) > 1 else indata
                
                # Apply character voice transformation
                processed = self.apply_character_voice(mono_input, self.current_character)
                
                # Prevent clipping
                processed = np.clip(processed, -0.95, 0.95)
                
                # Output
                outdata[:, 0] = processed
                
        except Exception as e:
            logging.error(f"Audio callback error: {e}")
            outdata[:] = indata  # Fallback to original
    
    def start_voice_clone(self, character="normal"):
        """Start real-time voice cloning"""
        if self.is_active:
            self.stop_voice_clone()
            
        try:
            self.current_character = character
            self.is_active = True
            
            # Start audio streams
            with sd.InputStream(callback=self.audio_callback,
                              channels=1,
                              samplerate=self.sample_rate,
                              blocksize=self.buffer_size):
                with sd.OutputStream(callback=self.audio_callback,
                                   channels=1,
                                   samplerate=self.sample_rate,
                                   blocksize=self.buffer_size):
                    
                    logging.info(f"Voice clone started with character: {character}")
                    
                    # Keep streams alive
                    while self.is_active:
                        sd.sleep(100)
                        
        except Exception as e:
            logging.error(f"Voice clone start error: {e}")
            self.is_active = False
            
    def stop_voice_clone(self):
        """Stop voice cloning"""
        self.is_active = False
        logging.info("Voice clone stopped")

# ================================
# TELEGRAM SESSION MANAGER
# ================================

class SessionManager:
    def __init__(self):
        self.session_path = Path(f"{Config.SESSION_NAME}.session")
        self.client = None
        
    def session_exists(self):
        """Check if session file exists"""
        return self.session_path.exists()
    
    async def create_new_session(self):
        """Create new session with phone verification"""
        print("🔐 Creating new session...")
        print(f"📱 Phone Number: {Config.PHONE_NUMBER}")
        
        try:
            # Initialize client
            self.client = Client(
                name=Config.SESSION_NAME,
                api_id=Config.API_ID,
                api_hash=Config.API_HASH,
                phone_number=Config.PHONE_NUMBER,
                workdir="."
            )
            
            # Connect and request phone code
            await self.client.connect()
            sent_code = await self.client.send_code(Config.PHONE_NUMBER)
            
            # Request verification code from user
            print(f"📨 Verification code sent to {Config.PHONE_NUMBER}")
            phone_code = input("🔑 Enter the verification code: ").strip()
            
            try:
                # Sign in with phone code
                await self.client.sign_in(Config.PHONE_NUMBER, sent_code.phone_code_hash, phone_code)
                print("✅ Phone verification successful!")
                
            except SessionPasswordNeeded:
                # Handle 2FA if enabled
                print("🔐 Two-Factor Authentication required")
                password = input("🔑 Enter your 2FA password: ").strip()
                await self.client.check_password(password)
                print("✅ 2FA verification successful!")
            
            # Save session info
            session_info = {
                "phone_number": Config.PHONE_NUMBER,
                "session_created": True,
                "session_file": str(self.session_path)
            }
            
            with open("session_info.json", "w") as f:
                json.dump(session_info, f, indent=2)
            
            print(f"💾 Session saved as: {self.session_path}")
            return True
            
        except PhoneCodeInvalid:
            print("❌ Invalid verification code!")
            return False
        except PhoneNumberInvalid:
            print("❌ Invalid phone number!")
            return False
        except Exception as e:
            print(f"❌ Session creation failed: {e}")
            return False
    
    async def load_existing_session(self):
        """Load existing session file"""
        try:
            print("📂 Loading existing session...")
            
            self.client = Client(
                name=Config.SESSION_NAME,
                api_id=Config.API_ID,
                api_hash=Config.API_HASH,
                workdir="."
            )
            
            await self.client.start()
            print("✅ Session loaded successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to load session: {e}")
            print("🔄 Session file may be corrupted, creating new session...")
            # Remove corrupted session file
            if self.session_path.exists():
                self.session_path.unlink()
            return False
    
    async def get_client(self):
        """Get authenticated Telegram client"""
        # Check if session exists
        if self.session_exists():
            print("🔍 Existing session found")
            if await self.load_existing_session():
                return self.client
        
        # Create new session if not exists or loading failed
        print("🆕 Creating new session...")
        if await self.create_new_session():
            return self.client
        
        return None

# ================================
# MAIN USERBOT APPLICATION
# ================================

class VoiceCloneUserBot:
    def __init__(self):
        self.voice_engine = VoiceCloneEngine()
        self.session_manager = SessionManager()
        self.client = None
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
    async def initialize(self):
        """Initialize userbot client"""
        print("🚀 Initializing Voice Clone UserBot...")
        print("=" * 50)
        
        # Get authenticated client
        self.client = await self.session_manager.get_client()
        if not self.client:
            print("❌ Failed to authenticate with Telegram!")
            return False
        
        # Get user info
        me = await self.client.get_me()
        print(f"👤 Logged in as: {me.first_name} {me.last_name or ''}")
        print(f"📱 Phone: {me.phone_number}")
        print(f"🆔 User ID: {me.id}")
        print("=" * 50)
        
        self.setup_handlers()
        return True
    
    def setup_handlers(self):
        """Setup message handlers"""
        
        @self.client.on_message(filters.command("voice") & filters.me)
        async def voice_command(client, message):
            """Voice control command"""
            try:
                args = message.text.split()[1:] if len(message.text.split()) > 1 else []
                
                if not args:
                    await message.edit("🎤 **Voice Clone Commands:**\n\n"
                                     "`.voice start <character>` - Start voice clone\n"
                                     "`.voice stop` - Stop voice clone\n"
                                     "`.voice list` - List characters\n"
                                     "`.voice status` - Show status")
                    return
                
                if args[0] == "start":
                    character = args[1] if len(args) > 1 else "normal"
                    
                    if character not in ["normal"] + list(Config.VOICE_CHARACTERS.keys()):
                        await message.edit(f"❌ Character '{character}' not found!\n"
                                         f"Available: {', '.join(['normal'] + list(Config.VOICE_CHARACTERS.keys()))}")
                        return
                    
                    # Start voice clone in background thread
                    def start_clone():
                        self.voice_engine.start_voice_clone(character)
                    
                    if not self.voice_engine.is_active:
                        threading.Thread(target=start_clone, daemon=True).start()
                        
                        char_name = Config.VOICE_CHARACTERS.get(character, {}).get("name", character)
                        await message.edit(f"🎭 **Voice Clone Started!**\n"
                                         f"Character: **{char_name}**\n"
                                         f"Status: **Active** ✅")
                    else:
                        await message.edit("⚠️ Voice clone already active!")
                
                elif args[0] == "stop":
                    self.voice_engine.stop_voice_clone()
                    await message.edit("🛑 **Voice Clone Stopped!**")
                
                elif args[0] == "list":
                    char_list = "🎭 **Available Characters:**\n\n"
                    for key, info in Config.VOICE_CHARACTERS.items():
                        char_list += f"• `{key}` - {info['name']}\n"
                    char_list += f"• `normal` - Original Voice"
                    await message.edit(char_list)
                
                elif args[0] == "status":
                    status = "Active ✅" if self.voice_engine.is_active else "Inactive ❌"
                    char_name = Config.VOICE_CHARACTERS.get(
                        self.voice_engine.current_character, {}
                    ).get("name", self.voice_engine.current_character)
                    
                    await message.edit(f"🎤 **Voice Clone Status:**\n\n"
                                     f"Status: **{status}**\n"
                                     f"Character: **{char_name}**\n"
                                     f"Sample Rate: {Config.SAMPLE_RATE} Hz")
                
            except Exception as e:
                await message.edit(f"❌ Error: {str(e)}")
        
        @self.client.on_message(filters.command("quick") & filters.me)
        async def quick_voice_change(client, message):
            """Quick character change"""
            args = message.text.split()[1:] if len(message.text.split()) > 1 else []
            
            if not args:
                await message.edit("Usage: `.quick <character>`")
                return
            
            character = args[0]
            if character in Config.VOICE_CHARACTERS:
                self.voice_engine.current_character = character
                char_name = Config.VOICE_CHARACTERS[character]["name"]
                await message.edit(f"🎭 Switched to: **{char_name}**", delete_in=3)
            else:
                await message.edit(f"❌ Character not found: {character}", delete_in=3)
        
        @self.client.on_message(filters.command("session") & filters.me)
        async def session_command(client, message):
            """Session management command"""
            try:
                args = message.text.split()[1:] if len(message.text.split()) > 1 else []
                
                if not args or args[0] == "info":
                    # Show session i
