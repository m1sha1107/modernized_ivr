from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
from typing import Dict, List
import logging
import uuid
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
import os
from dotenv import load_dotenv
from fastapi.responses import FileResponse
from redis import Redis
from conversational_ai import DialogueFlowManager, ConversationState, Intent

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
    raise EnvironmentError("Twilio credentials are not fully set in environment variables.")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Initialize Redis connection
redis_client = Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("REDIS_DB", 0)),
    decode_responses=True  # Ensures Redis returns strings instead of bytes
)

# Logging configuration
logging.basicConfig(level=logging.INFO)

# Initialize Conversational AI
dialogue_manager = DialogueFlowManager(redis_client)

# Voice configuration constant
TTS_VOICE = "Polly.Joanna"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_speech_gather(action: str, timeout: int = 10, language: str = "en-US") -> Gather:
    """Create a standardized speech Gather object."""
    return Gather(
        input="speech",
        action=action,
        method="POST",
        speech_timeout="auto",
        timeout=timeout,
        language=language
    )

def store_call_session(call_sid: str, from_number: str):
    """Store call session information in Redis."""
    redis_client.hset(f"call_session:{call_sid}", "from_number", from_number)
    redis_client.hset(f"call_session:{call_sid}", "status", "in-progress")

def save_reservation(call_sid: str) -> str:
    """Save reservation data to Redis and return reservation ID."""
    reservation_data = dialogue_manager.get_reservation_data(call_sid)
    if reservation_data:
        reservation_id = str(uuid.uuid4())[:8].upper()
        # Use individual hset calls for compatibility with older Redis versions
        for key, value in reservation_data.items():
            redis_client.hset(f"reservation:{reservation_id}", key, value)
        redis_client.hset(f"reservation:{reservation_id}", "reservation_id", reservation_id)
        return reservation_id
    return None

# Pydantic model for reservation
class ReservationMenu(BaseModel):
    reservation_id: str
    customer_name: str
    customer_contact: str
    reservation_date: str
    reservation_time: str
    number_of_people: int

# Health check endpoint
@app.get("/")
def read_root():
    """Health check endpoint."""
    return {"status": "Reservation system is running", "platform": "Twilio"}

# Incoming call webhook
@app.post("/twilio/incoming_call")
async def handle_incoming_call(request: Request):
    """Handle incoming calls from Twilio."""
    logging.info("Incoming call received")

    # Parse Twilio request
    form_data = await request.form()
    call_sid = form_data.get("CallSid")
    from_number = form_data.get("From")

    if not call_sid or not from_number:
        raise HTTPException(status_code=400, detail="Invalid Twilio request")

    # Store call session in Redis
    store_call_session(call_sid, from_number)

    # Create TwiML response
    response = VoiceResponse()
    gather = Gather(num_digits=1, action="/twilio/gather", method="POST")
    gather.say("Welcome to our Restaurant Reservation System. Press 1 to make a reservation. Press 2 to check an existing reservation.")
    response.append(gather)
    response.say("We did not receive any input. Thank you for calling. Goodbye.")
    response.hangup()

    return Response(content=str(response), media_type="application/xml")

# Handle Gather input
@app.post("/twilio/gather")
async def handle_gather(request: Request):
    """Handle user input from Twilio Gather."""
    form_data = await request.form()
    digits = form_data.get("Digits")
    call_sid = form_data.get("CallSid")

    if not call_sid or not digits:
        raise HTTPException(status_code=400, detail="Invalid Twilio request")

    response = VoiceResponse()

    if digits == "1":
        # Route to conversational AI flow for making reservation
        dialogue_manager.set_conversation_state(call_sid, ConversationState.INITIAL)
        gather = create_speech_gather("/twilio/conversational_gather")
        gather.say(
            "Great! I'd be happy to help you make a reservation. "
            "Please speak naturally. What's your name?",
            voice=TTS_VOICE
        )
        dialogue_manager.set_conversation_state(call_sid, ConversationState.COLLECTING_NAME)
        response.append(gather)
        response.say("I didn't catch that. Please try again.", voice=TTS_VOICE)
        response.redirect("/twilio/gather", method="POST")
    elif digits == "2":
        # Route to conversational AI flow for checking reservation
        dialogue_manager.set_conversation_state(call_sid, ConversationState.COLLECTING_RESERVATION_ID)
        redis_client.hset(f"call_session:{call_sid}", "action_type", "check")
        gather = create_speech_gather("/twilio/conversational_gather")
        gather.say(
            "I can help you check your reservation. "
            "Please provide your reservation ID. You can say it or spell it out.",
            voice=TTS_VOICE
        )
        response.append(gather)
        response.say("I didn't catch that. Please try again.", voice=TTS_VOICE)
        response.redirect("/twilio/gather", method="POST")
    else:
        response.say("Invalid input. Please try again.")
        response.redirect("/twilio/incoming_call", method="POST")

    return Response(content=str(response), media_type="application/xml")

# Reservation menu
@app.post("/twilio/reservation_menu")
async def reservation_menu():
    """Provide options for reservation management."""
    response = VoiceResponse()
    gather = Gather(num_digits=1, action="/twilio/reservation_option", method="POST")
    gather.say("Press 1 to make a new reservation. Press 2 to cancel a reservation.")
    response.append(gather)
    response.say("We did not receive any input. Goodbye.")
    response.hangup()

    return Response(content=str(response), media_type="application/xml")

# Handle reservation option
@app.post("/twilio/reservation_option")
async def reservation_option(request: Request):
    """Handle user selection for reservation options."""
    form_data = await request.form()
    digits = form_data.get("Digits")
    call_sid = form_data.get("CallSid")

    response = VoiceResponse()

    if digits == "1":
        # Route to conversational AI for making reservation
        if call_sid:
            dialogue_manager.set_conversation_state(call_sid, ConversationState.INITIAL)
        gather = create_speech_gather("/twilio/conversational_gather")
        gather.say(
            "Perfect! Let's make your reservation. Please speak naturally. "
            "What's your name?",
            voice=TTS_VOICE
        )
        if call_sid:
            dialogue_manager.set_conversation_state(call_sid, ConversationState.COLLECTING_NAME)
        response.append(gather)
        response.say("I didn't catch that. Please try again.", voice=TTS_VOICE)
        response.redirect("/twilio/reservation_option", method="POST")
    elif digits == "2":
        # Route to conversational AI for canceling reservation
        if call_sid:
            dialogue_manager.set_conversation_state(call_sid, ConversationState.COLLECTING_RESERVATION_ID)
            redis_client.hset(f"call_session:{call_sid}", "action_type", "cancel")
        gather = create_speech_gather("/twilio/conversational_gather")
        gather.say(
            "I can help you cancel your reservation. "
            "Please provide your reservation ID.",
            voice=TTS_VOICE
        )
        response.append(gather)
        response.say("I didn't catch that. Please try again.", voice=TTS_VOICE)
        response.redirect("/twilio/reservation_option", method="POST")
    else:
        response.say("Invalid input. Returning to the main menu.")
        response.redirect("/twilio/incoming_call", method="POST")

    return Response(content=str(response), media_type="application/xml")

# Check reservation
@app.post("/twilio/check_reservation")
async def check_reservation():
    """Provide instructions to check a reservation."""
    response = VoiceResponse()
    response.say("Please provide your reservation ID to our staff to check your reservation details.")
    response.hangup()
    return Response(content=str(response), media_type="application/xml")

# Cancel reservation
@app.delete("/cancel_reservation/{reservation_id}")
def cancel_reservation(reservation_id: str):
    """Cancel a reservation by ID."""
    # Check if reservation exists in Redis
    if not redis_client.exists(f"reservation:{reservation_id}"):
        raise HTTPException(status_code=404, detail="Reservation not found.")

    # Delete reservation from Redis
    redis_client.delete(f"reservation:{reservation_id}")
    return {"message": "Reservation cancelled successfully."}

# Exception handler
@app.exception_handler(Exception)
def handle_exceptions(request: Request, exc: Exception):
    """Log and handle exceptions."""
    logging.error(f"Error occurred: {exc}")
    return Response(content="Internal server error", status_code=500)

# ============================================================================
# CONVERSATIONAL AI ENDPOINTS (Module 3)
# ============================================================================

# Conversational incoming call handler (speech-enabled)
@app.post("/twilio/conversational_call")
async def handle_conversational_call(request: Request):
    """Handle incoming calls with conversational AI (speech input)."""
    logging.info("Conversational call received")
    
    # Parse Twilio request
    form_data = await request.form()
    call_sid = form_data.get("CallSid")
    from_number = form_data.get("From")
    
    if not call_sid or not from_number:
        raise HTTPException(status_code=400, detail="Invalid Twilio request")
    
    # Store call session in Redis
    store_call_session(call_sid, from_number)
    
    # Initialize conversation state
    dialogue_manager.set_conversation_state(call_sid, ConversationState.INITIAL)
    
    # Create TwiML response with speech recognition
    response = VoiceResponse()
    
    # Use Gather with speech input instead of digits
    gather = create_speech_gather("/twilio/conversational_gather")
    gather.say(
        "Hello! Welcome to our Restaurant Reservation System. "
        "I can help you make a reservation, check an existing reservation, "
        "or cancel a reservation. How may I assist you today?",
        voice=TTS_VOICE
    )
    response.append(gather)
    
    # Fallback if no speech detected
    response.say("I didn't catch that. Please try calling again. Goodbye.")
    response.hangup()
    
    return Response(content=str(response), media_type="application/xml")


# Handle conversational speech input
@app.post("/twilio/conversational_gather")
async def handle_conversational_gather(request: Request):
    """Process speech input using conversational AI."""
    form_data = await request.form()
    call_sid = form_data.get("CallSid")
    speech_result = form_data.get("SpeechResult", "")  # Transcribed speech
    confidence = form_data.get("Confidence", "0")
    
    logging.info(f"Speech input received - CallSid: {call_sid}, Speech: '{speech_result}', Confidence: {confidence}")
    
    if not call_sid:
        raise HTTPException(status_code=400, detail="Invalid Twilio request")
    
    # Process user input through conversational AI
    response_data = dialogue_manager.process_user_input(call_sid, speech_result)
    
    # Create TwiML response
    response = VoiceResponse()
    
    # Handle based on conversation flow response
    if response_data.get('next_action') == 'hangup':
        response.say(response_data['response_text'], voice=TTS_VOICE)
        response.hangup()
    elif response_data.get('needs_more_info'):
        # Continue conversation - gather more information
        gather = create_speech_gather("/twilio/conversational_gather", timeout=10)
        gather.say(response_data['response_text'], voice=TTS_VOICE)
        response.append(gather)
        
        # Fallback if no response - redirect back to keep conversation alive
        response.say("I didn't catch that. Please try again.", voice=TTS_VOICE)
        # Create another gather to retry
        fallback_gather = create_speech_gather("/twilio/conversational_gather", timeout=10)
        fallback_gather.say(response_data['response_text'], voice=TTS_VOICE)
        response.append(fallback_gather)
        
        # Only hangup if multiple failures (shouldn't reach here normally)
        response.say("I'm having trouble understanding. Please call back later or speak to our staff. Goodbye.", voice=TTS_VOICE)
        response.hangup()
    else:
        # Complete the flow
        response.say(response_data['response_text'], voice=TTS_VOICE)
        
        # If reservation was confirmed, save it
        if response_data.get('next_action') == 'confirm_reservation':
            reservation_id = save_reservation(call_sid)
            if reservation_id:
                response.say(
                    f"Your reservation ID is {reservation_id}. "
                    f"Please save this for your records. Thank you for calling and have a great day!",
                    voice=TTS_VOICE
                )
        
        response.hangup()
    
    return Response(content=str(response), media_type="application/xml")


# Hybrid endpoint: Support both DTMF and speech
@app.post("/twilio/smart_call")
async def handle_smart_call(request: Request):
    """Handle incoming calls with support for both DTMF and speech."""
    logging.info("Smart call received (DTMF + Speech)")
    
    form_data = await request.form()
    call_sid = form_data.get("CallSid")
    from_number = form_data.get("From")
    
    if not call_sid or not from_number:
        raise HTTPException(status_code=400, detail="Invalid Twilio request")
    
    # Store call session
    store_call_session(call_sid, from_number)
    dialogue_manager.set_conversation_state(call_sid, ConversationState.INITIAL)
    
    response = VoiceResponse()
    
    # Gather with both speech and DTMF support
    gather = Gather(
        input="speech dtmf",  # Accept both
        action="/twilio/smart_gather",
        method="POST",
        speech_timeout="auto",
        num_digits=1,  # For DTMF fallback
        language="en-US"
    )
    gather.say(
        "Welcome! You can speak or press a number. "
        "Say 'make a reservation', or press 1. "
        "Say 'check reservation', or press 2. "
        "How can I help you?",
        voice=TTS_VOICE
    )
    response.append(gather)
    response.say("We didn't receive any input. Goodbye.")
    response.hangup()
    
    return Response(content=str(response), media_type="application/xml")


@app.post("/twilio/smart_gather")
async def handle_smart_gather(request: Request):
    """Handle input from smart call (both speech and DTMF)."""
    form_data = await request.form()
    call_sid = form_data.get("CallSid")
    speech_result = form_data.get("SpeechResult", "")
    digits = form_data.get("Digits", "")
    
    logging.info(f"Smart input - CallSid: {call_sid}, Speech: '{speech_result}', Digits: '{digits}'")
    
    if not call_sid:
        raise HTTPException(status_code=400, detail="Invalid Twilio request")
    
    response = VoiceResponse()
    
    # Prioritize speech if available, fall back to DTMF
    user_input = speech_result if speech_result else (digits if digits else "")
    
    if digits:
        # DTMF fallback - use existing logic
        if digits == "1":
            response.redirect("/twilio/conversational_call", method="POST")
        elif digits == "2":
            dialogue_manager.set_conversation_state(call_sid, ConversationState.COLLECTING_RESERVATION_ID)
            gather = create_speech_gather("/twilio/conversational_gather")
            gather.say("Please provide your reservation ID.", voice=TTS_VOICE)
            response.append(gather)
        else:
            response.say("Invalid option. Please try again.")
            response.redirect("/twilio/smart_call", method="POST")
    elif speech_result:
        # Process speech input
        response_data = dialogue_manager.process_user_input(call_sid, speech_result)
        
        if response_data.get('next_action') == 'hangup':
            response.say(response_data['response_text'], voice=TTS_VOICE)
            response.hangup()
        elif response_data.get('needs_more_info'):
            gather = Gather(
                input="speech dtmf",
                action="/twilio/smart_gather",
                method="POST",
                speech_timeout="auto",
                language="en-US"
            )
            gather.say(response_data['response_text'], voice=TTS_VOICE)
            response.append(gather)
        else:
            response.say(response_data['response_text'], voice=TTS_VOICE)
            
            if response_data.get('next_action') == 'confirm_reservation':
                reservation_id = save_reservation(call_sid)
                if reservation_id:
                    response.say(
                        f"Your reservation ID is {reservation_id}. Thank you!",
                        voice=TTS_VOICE
                    )
            response.hangup()
    else:
        response.say("I didn't catch that. Please try again.")
        response.redirect("/twilio/smart_call", method="POST")
    
    return Response(content=str(response), media_type="application/xml")


# Serve favicon
@app.get("/favicon.ico")
async def favicon():
    """Serve the favicon.ico file."""
    return FileResponse("static/favicon.ico")