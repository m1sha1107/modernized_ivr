from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
from typing import Dict, List
import logging
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
import os
from dotenv import load_dotenv

# Initialize FastAPI app
app = FastAPI()

# Load environment variables from .env file
load_dotenv()

# Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
    raise EnvironmentError("Twilio credentials are not fully set in environment variables.")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# In-memory storage for sessions and bookings
call_sessions: Dict[str, Dict] = {}
booking_db: List[Dict] = []

# Logging configuration
logging.basicConfig(level=logging.INFO)

# Pydantic model for booking
class BookingMenu(BaseModel):
    booking_id: str
    trans_id: str
    passenger_fullname: str
    passenger_contact: str

# Health check endpoint
@app.get("/")
def read_root():
    return {"status": "IVR system is running", "platform": "Twilio"}

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

    # Store call session
    call_sessions[call_sid] = {"from": from_number, "status": "in-progress"}

    # Create TwiML response
    response = VoiceResponse()
    gather = Gather(num_digits=1, action="/twilio/gather", method="POST")
    gather.say("Welcome to Air India Customer Support. Press 1 for booking menu. Press 2 for flight status.")
    response.append(gather)
    response.say("We did not receive any input. Goodbye.")
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
        response.redirect("/twilio/booking_menu", method="POST")
    elif digits == "2":
        response.redirect("/twilio/status_menu", method="POST")
    else:
        response.say("Invalid input. Please try again.")
        response.redirect("/twilio/incoming_call", method="POST")

    return Response(content=str(response), media_type="application/xml")

# Booking menu
@app.post("/twilio/booking_menu")
async def booking_menu():
    response = VoiceResponse()
    gather = Gather(num_digits=1, action="/twilio/booking_option", method="POST")
    gather.say("Press 1 for domestic booking. Press 2 for international booking.")
    response.append(gather)
    response.say("We did not receive any input. Goodbye.")
    response.hangup()

    return Response(content=str(response), media_type="application/xml")

# Handle booking option
@app.post("/twilio/booking_option")
async def booking_option(request: Request):
    form_data = await request.form()
    digits = form_data.get("Digits")

    response = VoiceResponse()

    if digits == "1":
        response.say("You selected domestic booking. Please visit our website for more details.")
    elif digits == "2":
        response.say("You selected international booking. Please visit our website for more details.")
    else:
        response.say("Invalid input. Returning to the main menu.")
        response.redirect("/twilio/incoming_call", method="POST")

    response.hangup()
    return Response(content=str(response), media_type="application/xml")

# Status menu
@app.post("/twilio/status_menu")
async def status_menu():
    response = VoiceResponse()
    response.say("Please visit our website to check flight status.")
    response.hangup()
    return Response(content=str(response), media_type="application/xml")

# Cancel booking
@app.delete("/cancel_booking/{booking_id}")
def cancel_booking(booking_id: str):
    for booking in booking_db:
        if booking["booking_id"] == booking_id:
            booking_db.remove(booking)
            return {"message": "Booking cancelled successfully."}

    raise HTTPException(status_code=404, detail="Booking not found.")

# Exception handler
@app.exception_handler(Exception)
def handle_exceptions(request: Request, exc: Exception):
    logging.error(f"Error occurred: {exc}")
    return Response(content="Internal server error", status_code=500)