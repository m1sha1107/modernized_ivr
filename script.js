// Configuration: Update this if your FastAPI server is running elsewhere
const API_BASE_URL = 'http://localhost:8000';

// =========================================================================
// CREATE RESERVATION LOGIC
// =========================================================================
document.getElementById('createReservationForm').addEventListener('submit', async function(event) {
    event.preventDefault();
    
    const createMessage = document.getElementById('createMessage');
    createMessage.textContent = '';
    
    const reservationData = {
        customer_name: document.getElementById('name').value,
        customer_contact: document.getElementById('contact').value,
        reservation_date: document.getElementById('date').value,
        reservation_time: document.getElementById('time').value,
        number_of_people: parseInt(document.getElementById('guests').value, 10)
    };

    try {
        // NOTE: This endpoint assumes you have added a standard REST endpoint 
        // in your backend.py file for web reservations, like: 
        // @app.post("/api/reservations")
        const response = await fetch(`${API_BASE_URL}/api/reservations`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(reservationData)
        });

        const result = await response.json();

        if (response.ok) {
            createMessage.style.color = 'green';
            createMessage.textContent = `✅ Reservation successful! ID: ${result.reservation_id}.`;
            // Clear the form
            this.reset();
        } else {
            createMessage.style.color = 'red';
            createMessage.textContent = `❌ Error booking: ${result.detail || 'Server error'}`;
        }
    } catch (error) {
        createMessage.style.color = 'red';
        createMessage.textContent = `❌ Network error: Could not connect to the API.`;
        console.error('Error:', error);
    }
});

// =========================================================================
// MANAGE RESERVATION LOGIC
// =========================================================================

document.getElementById('checkButton').addEventListener('click', checkReservation);
document.getElementById('cancelButton').addEventListener('click', cancelReservation);

async function checkReservation() {
    const reservationId = document.getElementById('reservationId').value.trim().toUpperCase();
    const detailsDiv = document.getElementById('reservationDetails');
    const manageMessage = document.getElementById('manageMessage');
    
    detailsDiv.style.display = 'none';
    manageMessage.textContent = '';
    
    if (!reservationId) {
        manageMessage.textContent = 'Please enter a Reservation ID.';
        return;
    }

    try {
        // Uses the existing endpoint: @app.get("/get_reservation/{reservation_id}")
        const response = await fetch(`${API_BASE_URL}/get_reservation/${reservationId}`);
        const result = await response.json();

        if (response.ok) {
            document.getElementById('detailsContent').textContent = JSON.stringify(result, null, 2);
            detailsDiv.style.display = 'block';
            manageMessage.style.color = 'green';
            manageMessage.textContent = `Found details for reservation: ${reservationId}`;
        } else {
            detailsDiv.style.display = 'none';
            manageMessage.style.color = 'red';
            // Specific 404 handler based on your backend logic
            manageMessage.textContent = `❌ Error: Reservation ID ${reservationId} not found.`;
        }
    } catch (error) {
        manageMessage.style.color = 'red';
        manageMessage.textContent = `❌ Network error: Could not connect to the API.`;
        console.error('Error:', error);
    }
}

async function cancelReservation() {
    const reservationId = document.getElementById('reservationId').value.trim().toUpperCase();
    const detailsDiv = document.getElementById('reservationDetails');
    const manageMessage = document.getElementById('manageMessage');
    
    detailsDiv.style.display = 'none';
    manageMessage.textContent = '';

    if (!reservationId) {
        manageMessage.textContent = 'Please enter a Reservation ID.';
        return;
    }
    
    if (!confirm(`Are you sure you want to cancel reservation ID: ${reservationId}?`)) {
        return;
    }

    try {
        // Uses the existing endpoint: @app.delete("/cancel_reservation/{reservation_id}")
        const response = await fetch(`${API_BASE_URL}/cancel_reservation/${reservationId}`, {
            method: 'DELETE'
        });

        const result = await response.json();
        
        if (response.ok) {
            manageMessage.style.color = 'green';
            manageMessage.textContent = `✅ Successfully cancelled reservation: ${reservationId}.`;
            document.getElementById('reservationId').value = '';
        } else {
            manageMessage.style.color = 'red';
            manageMessage.textContent = `❌ Error canceling: ${result.detail || 'Reservation not found or server error'}`;
        }

    } catch (error) {
        manageMessage.style.color = 'red';
        manageMessage.textContent = `❌ Network error: Could not connect to the API.`;
        console.error('Error:', error);
    }
}