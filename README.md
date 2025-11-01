# IVR Restaurant Reservation System (Twilio + FastAPI + Redis + AI)

## Overview

This project implements an **AI-driven Interactive Voice Response (IVR)** system for a restaurant reservation service.
It integrates **FastAPI**, **Twilio**, **Redis**, and a **Conversational AI layer** to handle voice-based interactions in real time.

### Core Features

* Handles incoming phone calls using Twilio webhooks.
* Supports both DTMF input (keypad) and speech recognition.
* Conversational flow for:

  * Making new reservations
  * Checking existing reservations
  * Canceling reservations
* Natural language understanding for name, date, time, and party size.
* Smart time logic that correctly understands times like “1pm”, “one in the afternoon”, etc.
* Persists call sessions and reservations in Redis.
* Built-in error handling and logging.

---

## Architecture Overview

```
        ┌────────────────────┐
        │     Caller         │
        │  (Phone / Voice)   │
        └────────┬───────────┘
                 │
                 ▼
         ┌──────────────┐
         │   Twilio     │
         │ Voice & STT  │
         └──────┬───────┘
                │ Webhook
                ▼
        ┌────────────────────┐
        │   FastAPI Server   │
        │   (backend.py)     │
        └──────┬─────────────┘
               │ Calls
               ▼
        ┌────────────────────┐
        │ DialogueFlowManager│
        │ (conversational_ai)│
        └──────┬─────────────┘
               │ State + Data
               ▼
        ┌────────────────────┐
        │       Redis        │
        │ Session & Storage  │
        └────────────────────┘
```

---

## Project Structure

```
IVR Project
├── backend.py                # FastAPI app handling Twilio routes and call flow
├── conversational_ai.py      # AI conversation manager and logic
├── .env                      # Environment variables (not committed)
├── .gitignore                # Ignore sensitive and unnecessary files
├── static/favicon.ico        # Application favicon
└── venv/                     # Virtual environment (ignored in version control)
```

---

## Prerequisites

1. **Python 3.8+**
   Install from [python.org](https://www.python.org/).

2. **Twilio Account**

   * Sign up at [Twilio Console](https://www.twilio.com/console).
   * Get your **Account SID**, **Auth Token**, and **Phone Number**.

3. **Redis**
   Used for session tracking and reservation persistence.

   ```bash
   sudo apt install redis-server
   sudo service redis-server start
   ```

4. **Ngrok**
   Download and install [Ngrok](https://ngrok.com/) to expose your local FastAPI server to the internet.

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd IVR-Project
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### 5. Run the Application

```bash
uvicorn backend:app --reload
```

### 6. Expose the Server via Ngrok

```bash
ngrok http 8000
```

Copy the **public URL** from Ngrok.

### 7. Configure Twilio Webhook

1. Go to the [Twilio Console](https://www.twilio.com/console).
2. Navigate to **Phone Numbers → Manage Numbers → Active Numbers**.
3. Under **Voice & Fax**, set the webhook URL to:

   ```
   https://<ngrok-public-url>/twilio/incoming_call
   ```
4. Save the configuration.

---

## Endpoints

### 1. Health Check

* **URL**: `/`
* **Method**: `GET`
* **Description**: Verifies that the IVR system is running.
* **Response**:

  ```json
  { "status": "Reservation system is running", "platform": "Twilio" }
  ```

### 2. Incoming Call Webhook

* **URL**: `/twilio/incoming_call`
* **Method**: `POST`
* **Description**: Handles incoming calls and plays the main menu.

### 3. Gather Input

* **URL**: `/twilio/gather`
* **Method**: `POST`
* **Description**: Processes keypad input and routes users accordingly.

### 4. Conversational Flow

* **URL**: `/twilio/conversational_call`
* **Method**: `POST`
  Starts a speech-enabled conversation.
* **URL**: `/twilio/conversational_gather`
* **Method**: `POST`
  Processes speech input through the DialogueFlowManager.

### 5. Smart (Hybrid) Input Mode

* **URL**: `/twilio/smart_call`
* **URL**: `/twilio/smart_gather`
  Handles both **speech** and **DTMF** input for flexibility.

### 6. Reservation Management

* **POST** `/twilio/reservation_menu` — Menu for reservation actions
* **POST** `/twilio/check_reservation` — Guides users to check reservations
* **DELETE** `/cancel_reservation/{reservation_id}` — Cancels a reservation by ID

---

## Conversational AI Logic

* **State Management:** Tracks progress (name, date, time, guests) in Redis.
* **Intent Recognition:** Detects “make”, “check”, or “cancel” reservation.
* **Entity Extraction:** Captures name, date, time, and party size from speech.
* **Dynamic Prompts:** Adapts responses based on what user said or missed.

### Smart Time Handling

* Recognizes spoken AM/PM (“morning”, “evening”, “night”).
* Detects context when users only say “1” or “seven”.
* Validates times between **9 AM – 10 PM**.
* Prevents infinite clarification loops.
* If ambiguous, asks once:
  *“I heard 1. Is that in the morning or evening?”*

---

## Error Handling

* All exceptions are logged.
* Generic **500 Internal Server Error** returned for unhandled exceptions.
* Redis/Twilio connection errors return descriptive **400 Bad Request** messages.

---

## Testing Locally

Use Twilio’s **Voice Simulator** or call your **Twilio number** after linking it to your Ngrok endpoint.

**Example Interaction**

```
User: "I want to make a reservation."
System: "Sure, what's your name?"
User: "Misha."
System: "Thanks, Misha. What date would you like?"
User: "Tomorrow at 1pm."
System: "Time: 1pm. How many people will be dining?"
User: "Two."
System: "Perfect. Your reservation ID is AB1234. Thank you for calling!"
```

---

## Logging

All interactions are logged, including:

* Incoming Twilio requests
* Extracted entities (name, date, time)
* Redis state transitions
* Errors and exceptions

---

## License

## This project is licensed under the **MIT License**.

