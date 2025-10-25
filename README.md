# IVR Project with Twilio Integration

## Overview
This project implements an Interactive Voice Response (IVR) system using FastAPI and Twilio. The system allows users to interact with a restaurant reservation system via phone calls. Key features include:

- Handling incoming calls via Twilio webhooks.
- Collecting user input using Twilio's `<Gather>` functionality.
- Providing options for making, checking, and canceling reservations.
- Logging and error handling for robust operation.

## Project Structure
```
IVR Project
├── backend.py          # Main FastAPI application with Twilio integration
├── .gitignore          # Git ignore file for sensitive and unnecessary files
├── venv/               # Virtual environment (ignored in version control)
└── static/favicon.ico  # Favicon for the application
```

## Prerequisites
1. **Python 3.8+**
2. **Twilio Account**:
   - Sign up at [Twilio](https://www.twilio.com/).
   - Get your `Account SID`, `Auth Token`, and a Twilio phone number.
3. **Ngrok**:
   - Download and install [Ngrok](https://ngrok.com/) to expose your local server to the internet.

## Setup Instructions

### 1. Clone the Repository
```bash
git clone <repository-url>
cd IVR-Project
```

### 2. Create a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables
Create a `.env` file in the project root and add the following:
```
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=your_twilio_phone_number
```

### 5. Run the Application
```bash
uvicorn backend:app --reload
```

### 6. Expose the Server with Ngrok
```bash
ngrok http 8000
```
Copy the public URL provided by Ngrok and configure it as your Twilio webhook.

### 7. Configure Twilio Webhook
1. Go to the [Twilio Console](https://www.twilio.com/console).
2. Navigate to **Phone Numbers** > **Manage Numbers** > Select your number.
3. Set the **Webhook URL** to:
   ```
   https://<ngrok-public-url>/twilio/incoming_call
   ```
4. Save the changes.

## Endpoints

### 1. Health Check
- **URL**: `/`
- **Method**: `GET`
- **Description**: Verifies that the server is running.

### 2. Incoming Call Webhook
- **URL**: `/twilio/incoming_call`
- **Method**: `POST`
- **Description**: Handles incoming calls and provides options to the user.

### 3. Gather Input
- **URL**: `/twilio/gather`
- **Method**: `POST`
- **Description**: Processes user input and redirects to the appropriate menu.

### 4. Reservation Menu
- **URL**: `/twilio/reservation_menu`
- **Method**: `POST`
- **Description**: Provides options for making or canceling reservations.

### 5. Check Reservation
- **URL**: `/twilio/check_reservation`
- **Method**: `POST`
- **Description**: Provides instructions to check a reservation.

### 6. Cancel Reservation
- **URL**: `/cancel_reservation/{reservation_id}`
- **Method**: `DELETE`
- **Description**: Cancels a reservation by ID.

## Error Handling
- All exceptions are logged, and a generic `500 Internal Server Error` response is returned for unhandled exceptions.

## Future Enhancements
- Implement persistent session storage (e.g., Redis or PostgreSQL).
- Add support for speech-to-text and text-to-speech using Twilio Media Streams.
- Write unit tests for all endpoints.

## License
This project is licensed under the MIT License.