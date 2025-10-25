from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
from typing import Dict, List
import logging
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
import os
from dotenv import load_dotenv
from fastapi.responses import FileResponse

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

# In-memory storage for sessions and reservations
call_sessions: Dict[str, Dict] = {}
reservation_db: List[Dict] = []

# Logging configuration
logging.basicConfig(level=logging.INFO)

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

    # Store call session
    call_sessions[call_sid] = {"from": from_number, "status": "in-progress"}

    # Create TwiML response
    response = VoiceResponse()
    gather = Gather(num_digits=1, action="/twilio/gather", method="POST")
    gather.say("Welcome to our Restaurant Reservation System. Press 1 to make a reservation. Press 2 to check an existing reservation.")
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
        response.redirect("/twilio/reservation_menu", method="POST")
    elif digits == "2":
        response.redirect("/twilio/check_reservation", method="POST")
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

    response = VoiceResponse()

    if digits == "1":
        response.say("You selected to make a new reservation. Please visit our website or call our staff for assistance.")
    elif digits == "2":
        response.say("You selected to cancel a reservation. Please provide your reservation ID to our staff.")
    else:
        response.say("Invalid input. Returning to the main menu.")
        response.redirect("/twilio/incoming_call", method="POST")

    response.hangup()
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
    for reservation in reservation_db:
        if reservation["reservation_id"] == reservation_id:
            reservation_db.remove(reservation)
            return {"message": "Reservation cancelled successfully."}

    raise HTTPException(status_code=404, detail="Reservation not found.")

# Exception handler
@app.exception_handler(Exception)
def handle_exceptions(request: Request, exc: Exception):
    """Log and handle exceptions."""
    logging.error(f"Error occurred: {exc}")
    return Response(content="Internal server error", status_code=500)

# Serve favicon
@app.get("/favicon.ico")
async def favicon():
    """Serve the favicon.ico file."""
    return FileResponse("static/favicon.ico")