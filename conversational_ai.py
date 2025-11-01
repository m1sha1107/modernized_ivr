"""
Conversational AI Module for IVR System
Implements rule-based intent recognition and dialogue flow management
"""
import re
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class Intent(Enum):
    """Supported conversation intents"""
    MAKE_RESERVATION = "make_reservation"
    CHECK_RESERVATION = "check_reservation"
    CANCEL_RESERVATION = "cancel_reservation"
    GREETING = "greeting"
    HELP = "help"
    GOODBYE = "goodbye"
    UNKNOWN = "unknown"


class ConversationState(Enum):
    """Conversation state machine states"""
    INITIAL = "initial"
    COLLECTING_NAME = "collecting_name"
    COLLECTING_CONTACT = "collecting_contact"
    COLLECTING_DATE = "collecting_date"
    COLLECTING_TIME = "collecting_time"
    COLLECTING_GUESTS = "collecting_guests"
    COLLECTING_RESERVATION_ID = "collecting_reservation_id"
    CONFIRMING_RESERVATION = "confirming_reservation"
    COMPLETED = "completed"


class IntentRecognizer:
    """Rule-based intent recognition using pattern matching"""
    
    def __init__(self):
        # Intent patterns - keywords and phrases that indicate user intent
        self.intent_patterns = {
            Intent.MAKE_RESERVATION: [
                r'\b(make|create|book|reserve|new reservation|want to reserve|need a table)\b',
                r'\b(table for|reservation for|book a table)\b',
            ],
            Intent.CHECK_RESERVATION: [
                r'\b(check|view|see|look up|find|status of|details of)\s+(my |the )?reservation\b',
                r'\breservation (status|details|info)\b',
                r'\bwhat is (my |the )?reservation\b',
            ],
            Intent.CANCEL_RESERVATION: [
                r'\b(cancel|delete|remove|cancel my|cancel the|remove my)\s+(reservation|booking)\b',
                r'\bcancel\b',
            ],
            Intent.GREETING: [
                r'\b(hi|hello|hey|greetings|good morning|good afternoon|good evening)\b',
            ],
            Intent.HELP: [
                r'\b(help|what can you do|options|menu|assistance|support)\b',
            ],
            Intent.GOODBYE: [
                r'\b(bye|goodbye|thanks|thank you|done|finish|exit|end)\b',
            ],
        }
        
        # Compile regex patterns for efficiency
        self.compiled_patterns = {
            intent: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
            for intent, patterns in self.intent_patterns.items()
        }
    
    def recognize_intent(self, user_input: str) -> Tuple[Intent, float]:
        """
        Recognize user intent from speech input.
        Returns: (Intent, confidence_score)
        """
        if not user_input:
            return Intent.UNKNOWN, 0.0
        
        user_input_lower = user_input.lower().strip()
        intent_scores = {}
        
        # Calculate confidence scores for each intent
        for intent, patterns in self.compiled_patterns.items():
            score = 0.0
            matches = 0
            
            for pattern in patterns:
                if pattern.search(user_input_lower):
                    matches += 1
                    # Calculate score based on match position and length
                    match = pattern.search(user_input_lower)
                    if match:
                        # Prefer matches at the beginning of the utterance
                        position_weight = 1.0 if match.start() < len(user_input_lower) * 0.3 else 0.7
                        score += position_weight
            
            if matches > 0:
                # Normalize score by number of patterns matched
                intent_scores[intent] = min(score / len(patterns) * matches, 1.0)
        
        # Return intent with highest score
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            confidence = intent_scores[best_intent]
            
            # Threshold: require at least 0.3 confidence
            if confidence >= 0.3:
                logger.info(f"Recognized intent: {best_intent.value} (confidence: {confidence:.2f})")
                return best_intent, confidence
        
        logger.info(f"No intent recognized for: '{user_input}'")
        return Intent.UNKNOWN, 0.0
    
    def extract_entities(self, user_input: str, current_state: ConversationState) -> Dict[str, Optional[str]]:
        """
        Extract entities (dates, times, numbers, names) from user input.
        Returns dictionary of extracted entities.
        """
        entities = {}
        user_input_lower = user_input.lower()
        
        # Extract date patterns - comprehensive patterns for various date formats
        date_patterns = [
            # Relative dates
            r'\b(today|tomorrow|next week|this week|next monday|next tuesday|next wednesday|next thursday|next friday|next saturday|next sunday)\b',
            # Month + day with ordinal (e.g., "November 20th", "november twentieth")
            r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2}(?:st|nd|rd|th)?|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth|thirteenth|fourteenth|fifteenth|sixteenth|seventeenth|eighteenth|nineteenth|twentieth|twenty[- ]first|twenty[- ]second|twenty[- ]third|twenty[- ]fourth|twenty[- ]fifth|twenty[- ]sixth|twenty[- ]seventh|twenty[- ]eighth|twenty[- ]ninth|thirtieth|thirty[- ]first)\b',
            # Day + "of" + month (e.g., "20th of november", "the 20th of november")
            r'\b(the\s+)?(\d{1,2}(?:st|nd|rd|th)?|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth|thirteenth|fourteenth|fifteenth|sixteenth|seventeenth|eighteenth|nineteenth|twentieth|twenty[- ]first|twenty[- ]second|twenty[- ]third|twenty[- ]fourth|twenty[- ]fifth|twenty[- ]sixth|twenty[- ]seventh|twenty[- ]eighth|twenty[- ]ninth|thirtieth|thirty[- ]first)\s+of\s+(january|february|march|april|may|june|july|august|september|october|november|december)\b',
            # Numeric formats (MM/DD/YYYY or DD/MM/YYYY)
            r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b',
            # Month + day without ordinal (e.g., "November 20")
            r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})\b',
            # Day names
            r'\b(next\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, user_input_lower)
            if match:
                # Extract the full match or reconstruct for better formatting
                matched_text = match.group(0)
                # Normalize common variations
                if 'of' in matched_text:
                    # Reorder "20th of november" to "november 20th" format
                    parts = matched_text.split()
                    if 'of' in parts:
                        of_index = parts.index('of')
                        if of_index > 0 and of_index < len(parts) - 1:
                            day_part = ' '.join(parts[:of_index])
                            month_part = parts[of_index + 1]
                            entities['date'] = f"{month_part} {day_part}".strip()
                        else:
                            entities['date'] = matched_text
                    else:
                        entities['date'] = matched_text
                else:
                    entities['date'] = matched_text
                break
        
        # Extract time patterns - comprehensive patterns for various time formats
        time_patterns = [
            # Format: "1:30pm", "12:45am"
            r'\b(\d{1,2}):(\d{2})\s*(am|pm)\b',
            # Format: "1pm", "12am", "9am"
            r'\b(\d{1,2})\s*(am|pm)\b',
            # Format: "1 o'clock", "one o'clock", "12 o'clock"
            r'\b(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s*o[\'\-]?clock\s*(am|pm)?\b',
            # Format: "at 1", "by 1" (assume PM if ambiguous and reasonable, otherwise context-dependent)
            r'\b(at|by|around|about)\s+(\d{1,2})\b',
            # Format: just a number "1", "12" (context: if state is collecting_time)
            r'^\s*(\d{1,2})\s*$',
            # Relative times
            r'\b(morning|afternoon|evening|night|noon|midnight|lunch|dinner)\b',
            # Format: "half past 1", "quarter past 2", etc.
            r'\b(half|quarter)\s+(past|to)\s+(\d{1,2})\s*(am|pm)?\b',
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, user_input_lower)
            if match:
                matched_text = match.group(0)
                
                # Handle "o'clock" format
                if "o'clock" in matched_text or "oclock" in matched_text:
                    # Extract the number part
                    number_part = re.search(r'\b(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\b', matched_text)
                    ampm_part = re.search(r'\b(am|pm)\b', matched_text)
                    
                    if number_part:
                        number = number_part.group(1)
                        # Convert word numbers to digits
                        word_to_num = {
                            'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5',
                            'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'ten': '10',
                            'eleven': '11', 'twelve': '12'
                        }
                        number = word_to_num.get(number, number)
                        
                        if ampm_part:
                            entities['time'] = f"{number} {ampm_part.group(1)}"
                        else:
                            # Default to PM if no am/pm specified (reasonable for dinner times)
                            entities['time'] = f"{number} pm"
                else:
                    entities['time'] = matched_text
                break
        
        # Extract number of guests
        guest_patterns = [
            r'\b(\d+)\s*(people|guests|persons|pax)\b',
            r'\b(table for|reservation for)\s+(\d+)\b',
            r'\b(\d+)\b',  # Simple number (context-dependent)
        ]
        
        for pattern in guest_patterns:
            match = re.search(pattern, user_input_lower)
            if match:
                num = match.group(1) if match.groups() else match.group(0)
                try:
                    guests = int(num)
                    if 1 <= guests <= 20:  # Reasonable range
                        entities['guests'] = str(guests)
                        break
                except ValueError:
                    pass
        
        # Extract reservation ID (alphanumeric)
        reservation_id_pattern = r'\b([A-Z0-9]{6,10})\b'
        match = re.search(reservation_id_pattern, user_input.upper())
        if match:
            entities['reservation_id'] = match.group(1)
        
        # Extract name (simple heuristic: if state is collecting_name and input looks like a name)
        if current_state == ConversationState.COLLECTING_NAME:
            # Remove common words and check if remaining looks like a name
            words = user_input.split()
            if len(words) >= 1 and len(words) <= 3:
                name_candidates = [w.capitalize() for w in words if len(w) > 2]
                if name_candidates:
                    entities['name'] = ' '.join(name_candidates)
        
        # Extract contact (phone number or email pattern)
        # First, convert number words to digits (e.g., "five five five" -> "555")
        number_word_map = {
            'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
            'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
            'oh': '0', 'o': '0'  # Common spoken representations
        }
        
        # Convert spoken numbers to digits
        normalized_input = user_input_lower
        for word, digit in number_word_map.items():
            normalized_input = normalized_input.replace(f' {word} ', f' {digit} ')
            normalized_input = normalized_input.replace(f' {word}', f' {digit}')
            normalized_input = normalized_input.replace(f'{word} ', f'{digit} ')
        
        # Try multiple phone number patterns
        phone_patterns = [
            r'\b(\d{10,15})\b',  # Standard: 10-15 digits
            r'\b(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})\b',  # US format: 555-123-4567
            r'\b(\d{3}[-.\s]?\d{7})\b',  # Alternative format
            r'\b(\(\d{3}\)[-.\s]?\d{3}[-.\s]?\d{4})\b',  # (555) 123-4567
        ]
        
        phone_match = None
        for pattern in phone_patterns:
            phone_match = re.search(pattern, normalized_input)
            if phone_match:
                # Clean up the phone number (remove spaces, dashes, parentheses)
                phone = re.sub(r'[^\d]', '', phone_match.group(1))
                if len(phone) >= 10:  # Valid phone number length
                    entities['contact'] = phone
                    break
        
        # Try email pattern if no phone found
        if 'contact' not in entities:
            email_pattern = r'\b[\w\.-]+@[\w\.-]+\.\w+\b'
            email_match = re.search(email_pattern, user_input_lower)
            if email_match:
                entities['contact'] = email_match.group(0)
        
        return entities


class DialogueFlowManager:
    """Manages conversational flow and state"""
    
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.intent_recognizer = IntentRecognizer()
    
    def _validate_time_within_hours(self, time_str: str) -> bool:
        """Validate that time is within restaurant hours (9am-10pm)"""
        time_lower = time_str.lower().strip()
        
        # Extract hour and am/pm
        hour_match = re.search(r'(\d{1,2})', time_lower)
        if not hour_match:
            return True  # Can't validate, assume OK
        
        hour = int(hour_match.group(1))
        
        # Check for am/pm
        if 'am' in time_lower:
            # AM hours: 9am-11am are valid
            return 9 <= hour <= 11
        elif 'pm' in time_lower:
            # PM hours: 12pm-10pm are valid (12pm = noon, 10pm = closing)
            return hour == 12 or (1 <= hour <= 10)
        else:
            # No am/pm specified - if it's 9-10, might be ambiguous but allow it
            # The confirmation step will help
            return True
    
    def format_phone_for_speech(self, phone_number: str) -> str:
        """Format phone number to be read digit-by-digit by TTS"""
        # Remove any non-digit characters
        digits = re.sub(r'[^\d]', '', phone_number)
        
        # Map digits to words for clearer speech
        digit_words = {
            '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four',
            '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine'
        }
        
        # Format as "five five five, one two three, four five six seven"
        if len(digits) == 10:
            # US format: (555) 123-4567
            part1 = ' '.join([digit_words[d] for d in digits[:3]])
            part2 = ' '.join([digit_words[d] for d in digits[3:6]])
            part3 = ' '.join([digit_words[d] for d in digits[6:]])
            return f"{part1}, {part2}, {part3}"
        else:
            # For other lengths, just space them out
            return ', '.join([digit_words.get(d, d) for d in digits])
    
    def get_conversation_state(self, call_sid: str) -> ConversationState:
        """Get current conversation state from Redis"""
        state_str = self.redis_client.hget(f"call_session:{call_sid}", "conversation_state")
        if state_str:
            try:
                return ConversationState(state_str)
            except ValueError:
                pass
        return ConversationState.INITIAL
    
    def set_conversation_state(self, call_sid: str, state: ConversationState):
        """Set conversation state in Redis"""
        self.redis_client.hset(f"call_session:{call_sid}", "conversation_state", state.value)
    
    def get_reservation_data(self, call_sid: str) -> Dict[str, Optional[str]]:
        """Get collected reservation data from Redis"""
        data = self.redis_client.hgetall(f"reservation_data:{call_sid}")
        return data if data else {}
    
    def update_reservation_data(self, call_sid: str, entities: Dict[str, str]):
        """Update reservation data in Redis"""
        for key, value in entities.items():
            if value:
                self.redis_client.hset(f"reservation_data:{call_sid}", key, value)
    
    def process_user_input(self, call_sid: str, user_input: str) -> Dict:
        """
        Process user input and return response data.
        Returns: {
            'intent': Intent,
            'response_text': str,
            'next_action': str,
            'needs_more_info': bool
        }
        """
        current_state = self.get_conversation_state(call_sid)
        intent, confidence = self.intent_recognizer.recognize_intent(user_input)
        entities = self.intent_recognizer.extract_entities(user_input, current_state)
        
        # Update reservation data with extracted entities
        if entities:
            self.update_reservation_data(call_sid, entities)
        
        response_data = {
            'intent': intent,
            'confidence': confidence,
            'entities': entities,
            'current_state': current_state,
            'response_text': '',
            'next_action': '',
            'needs_more_info': False,
        }
        
        # Store action type for reservation ID collection
        if intent == Intent.CHECK_RESERVATION:
            self.redis_client.hset(f"call_session:{call_sid}", "action_type", "check")
        elif intent == Intent.CANCEL_RESERVATION:
            self.redis_client.hset(f"call_session:{call_sid}", "action_type", "cancel")
        
        # Handle based on current state and intent
        if current_state == ConversationState.INITIAL:
            response_data = self._handle_initial_state(intent, response_data)
        elif current_state in [ConversationState.COLLECTING_NAME, ConversationState.COLLECTING_CONTACT,
                               ConversationState.COLLECTING_DATE, ConversationState.COLLECTING_TIME,
                               ConversationState.COLLECTING_GUESTS]:
            # Check for contact confirmation first
            pending_contact = self.redis_client.hget(f"call_session:{call_sid}", "pending_contact")
            if pending_contact and current_state == ConversationState.COLLECTING_CONTACT:
                confirmation_words = ['yes', 'yeah', 'yep', 'correct', 'right', 'that\'s right', 'that is correct', 'yup']
                rejection_words = ['no', 'nope', 'incorrect', 'wrong', 'try again', 'that\'s wrong']
                user_input_lower = user_input.lower()
                
                if any(word in user_input_lower for word in confirmation_words):
                    # Confirmed - save contact and move to next step
                    self.update_reservation_data(call_sid, {'contact': pending_contact})
                    self.redis_client.hdel(f"call_session:{call_sid}", "pending_contact")
                    response_data['response_text'] = "Great! What date would you like to make the reservation for? " \
                                                     "For example, you can say 'tomorrow', 'next Friday', " \
                                                     "or a specific date like 'January fifteenth' or 'the fifteenth of January'."
                    self.set_conversation_state(call_sid, ConversationState.COLLECTING_DATE)
                    response_data['next_action'] = 'collect_date'
                    response_data['needs_more_info'] = True
                elif any(word in user_input_lower for word in rejection_words):
                    # Rejected - ask again
                    self.redis_client.hdel(f"call_session:{call_sid}", "pending_contact")
                    response_data['response_text'] = "No problem. Please say your phone number again, or you can say it digit by digit."
                    response_data['next_action'] = 'collect_contact'
                    response_data['needs_more_info'] = True
                else:
                    # Might be a new phone number - process normally
                    response_data = self._handle_collecting_state(call_sid, current_state, user_input, entities, response_data)
            # Check for time confirmation
            elif current_state == ConversationState.COLLECTING_TIME:
                pending_time = self.redis_client.hget(f"call_session:{call_sid}", "pending_time")
                if pending_time and response_data.get('next_action') == 'confirm_time':
                    confirmation_words = ['yes', 'yeah', 'yep', 'correct', 'right', 'that\'s right', 'that is correct', 'yup']
                    rejection_words = ['no', 'nope', 'incorrect', 'wrong', 'try again', 'that\'s wrong']
                    user_input_lower = user_input.lower()
                    
                    if any(word in user_input_lower for word in confirmation_words):
                        # Confirmed - save time and move to next step
                        self.update_reservation_data(call_sid, {'time': pending_time})
                        self.redis_client.hdel(f"call_session:{call_sid}", "pending_time")
                        response_data['response_text'] = f"Perfect! Time: {pending_time}. How many people will be dining?"
                        self.set_conversation_state(call_sid, ConversationState.COLLECTING_GUESTS)
                        response_data['next_action'] = 'collect_guests'
                        response_data['needs_more_info'] = True
                        self.redis_client.hdel(f"call_session:{call_sid}", "time_retry_count")
                    elif any(word in user_input_lower for word in rejection_words):
                        # Rejected - ask again
                        self.redis_client.hdel(f"call_session:{call_sid}", "pending_time")
                        response_data['response_text'] = "No problem. Please say the time again. Remember, we're open from 9am to 10pm."
                        response_data['next_action'] = 'collect_time'
                        response_data['needs_more_info'] = True
                    else:
                        # Might be a new time - process normally
                        response_data = self._handle_collecting_state(call_sid, current_state, user_input, entities, response_data)
                else:
                    response_data = self._handle_collecting_state(call_sid, current_state, user_input, entities, response_data)
            else:
                response_data = self._handle_collecting_state(call_sid, current_state, user_input, entities, response_data)
        elif current_state == ConversationState.COLLECTING_RESERVATION_ID:
            # Check if we're checking or canceling
            action_type = self.redis_client.hget(f"call_session:{call_sid}", "action_type")
            response_data = self._handle_reservation_id_state(call_sid, user_input, entities, response_data, action_type)
        else:
            response_data = self._handle_other_states(intent, response_data)
        
        return response_data
    
    def _handle_initial_state(self, intent: Intent, response_data: Dict) -> Dict:
        """Handle user input in initial state"""
        if intent == Intent.MAKE_RESERVATION:
            response_data['response_text'] = "Great! I'd be happy to help you make a reservation. " \
                                             "May I please have your name?"
            response_data['next_action'] = 'collect_name'
            response_data['needs_more_info'] = True
        elif intent == Intent.CHECK_RESERVATION:
            response_data['response_text'] = "I can help you check your reservation. " \
                                             "Please provide your reservation ID."
            response_data['next_action'] = 'collect_reservation_id'
            response_data['needs_more_info'] = True
            # Store action type for later reference
            response_data['action_type'] = 'check'
        elif intent == Intent.CANCEL_RESERVATION:
            response_data['response_text'] = "I can help you cancel your reservation. " \
                                             "Please provide your reservation ID."
            response_data['next_action'] = 'collect_reservation_id_for_cancel'
            response_data['needs_more_info'] = True
            # Store action type for later reference
            response_data['action_type'] = 'cancel'
        elif intent == Intent.HELP:
            response_data['response_text'] = "I can help you make a new reservation, " \
                                             "check an existing reservation, or cancel a reservation. " \
                                             "What would you like to do?"
        elif intent == Intent.GREETING:
            response_data['response_text'] = "Hello! Welcome to our Restaurant Reservation System. " \
                                             "I can help you make a reservation, check an existing reservation, " \
                                             "or cancel a reservation. What would you like to do?"
        elif intent == Intent.GOODBYE:
            response_data['response_text'] = "Thank you for calling. Have a great day!"
            response_data['next_action'] = 'hangup'
        else:
            response_data['response_text'] = "I didn't quite understand that. " \
                                           "You can say 'make a reservation', 'check reservation', " \
                                           "or 'cancel reservation'. How may I help you?"
        
        return response_data
    
    def _handle_collecting_state(self, call_sid: str, current_state: ConversationState, 
                                user_input: str, entities: Dict, response_data: Dict) -> Dict:
        """Handle input while collecting reservation information"""
        reservation_data = self.get_reservation_data(call_sid)
        
        if current_state == ConversationState.COLLECTING_NAME:
            if 'name' in entities:
                name = entities['name']
                response_data['response_text'] = f"Thank you, {name}. What's the best phone number to reach you?"
                self.set_conversation_state(call_sid, ConversationState.COLLECTING_CONTACT)
                response_data['next_action'] = 'collect_contact'
                response_data['needs_more_info'] = True
            else:
                # Try to extract name from raw input
                words = user_input.strip().split()
                if len(words) >= 1:
                    name = ' '.join([w.capitalize() for w in words if len(w) > 1])
                    self.update_reservation_data(call_sid, {'name': name})
                    response_data['response_text'] = f"Thank you, {name}. What's the best phone number to reach you?"
                    self.set_conversation_state(call_sid, ConversationState.COLLECTING_CONTACT)
                    response_data['next_action'] = 'collect_contact'
                    response_data['needs_more_info'] = True
                else:
                    response_data['response_text'] = "I didn't catch your name. Could you please say your name again?"
        
        elif current_state == ConversationState.COLLECTING_CONTACT:
            if 'contact' in entities:
                contact = entities['contact']
                # Confirm the number back to user - format for speech
                contact_spoken = self.format_phone_for_speech(contact)
                response_data['response_text'] = f"I have {contact_spoken}. Is that correct? Say yes to continue, or no to try again."
                response_data['next_action'] = 'confirm_contact'
                response_data['needs_more_info'] = True
                # Store temporarily for confirmation
                self.redis_client.hset(f"call_session:{call_sid}", "pending_contact", contact)
            else:
                # Try more aggressive extraction - convert any sequence of digits or number words
                # Remove common words and extract any remaining digits/number patterns
                cleaned = user_input.lower()
                # Remove common filler words
                for word in ['my', 'phone', 'number', 'is', 'contact', 'reach', 'me', 'at']:
                    cleaned = cleaned.replace(word, ' ')
                
                # Try to extract any sequence of 10+ characters that might be a phone number
                digits_only = re.sub(r'[^\d]', '', cleaned)
                if len(digits_only) >= 10:
                    contact = digits_only[:15]  # Max 15 digits
                    contact_spoken = self.format_phone_for_speech(contact)
                    response_data['response_text'] = f"I have {contact_spoken}. Is that correct? Say yes to continue, or no to try again."
                    response_data['next_action'] = 'confirm_contact'
                    response_data['needs_more_info'] = True
                    self.redis_client.hset(f"call_session:{call_sid}", "pending_contact", contact)
                else:
                    # Convert number words to digits and try again
                    number_word_map = {
                        'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
                        'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
                        'oh': '0', 'o': '0'
                    }
                    for word, digit in number_word_map.items():
                        cleaned = cleaned.replace(word, digit)
                    
                    digits_from_words = re.sub(r'[^\d]', '', cleaned)
                    if len(digits_from_words) >= 10:
                        contact = digits_from_words[:15]
                        contact_spoken = self.format_phone_for_speech(contact)
                        response_data['response_text'] = f"I have {contact_spoken}. Is that correct? Say yes to continue, or no to try again."
                        response_data['next_action'] = 'confirm_contact'
                        response_data['needs_more_info'] = True
                        self.redis_client.hset(f"call_session:{call_sid}", "pending_contact", contact)
                    else:
                        response_data['response_text'] = "I'm having trouble catching your phone number. " \
                                                       "Could you please say it slowly, digit by digit? " \
                                                       "For example, say 'five five five, one two three, four five six seven'."
                        response_data['needs_more_info'] = True
        
        elif current_state == ConversationState.COLLECTING_DATE:
            if 'date' in entities:
                date = entities['date']
                response_data['response_text'] = f"Reservation for {date}. " \
                                                 f"What time would you like? " \
                                                 f"Please note our restaurant is open from 9am to 10pm. " \
                                                 f"You can say the time in any format, like '1pm', '1 o'clock', or just '1'."
                self.set_conversation_state(call_sid, ConversationState.COLLECTING_TIME)
                response_data['next_action'] = 'collect_time'
                response_data['needs_more_info'] = True
                # Reset retry counter on success
                self.redis_client.hdel(f"call_session:{call_sid}", "date_retry_count")
            else:
                # Track retry attempts
                retry_count = self.redis_client.hget(f"call_session:{call_sid}", "date_retry_count")
                retry_count = int(retry_count) if retry_count else 0
                retry_count += 1
                self.redis_client.hset(f"call_session:{call_sid}", "date_retry_count", retry_count)
                
                # Try to extract date from raw input as fallback
                # Check for month names followed by numbers
                user_input_lower = user_input.lower()
                month_pattern = r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{1,2})\w*\b'
                match = re.search(month_pattern, user_input_lower)
                
                if match:
                    month = match.group(1)
                    day = match.group(2)
                    date_extracted = f"{month} {day}"
                    entities['date'] = date_extracted
                    response_data['response_text'] = f"Reservation for {date_extracted}. " \
                                                     f"What time would you like? " \
                                                     f"Please note our restaurant is open from 9am to 10pm. " \
                                                     f"You can say the time in any format, like '1pm', '1 o'clock', or just '1'."
                    self.set_conversation_state(call_sid, ConversationState.COLLECTING_TIME)
                    response_data['next_action'] = 'collect_time'
                    response_data['needs_more_info'] = True
                    self.redis_client.hdel(f"call_session:{call_sid}", "date_retry_count")
                else:
                    # Provide increasingly helpful guidance based on retry count
                    if retry_count == 1:
                        response_data['response_text'] = "I didn't catch the date clearly. " \
                                                       "Please say the date again. " \
                                                       "You can say it like 'November twentieth' or 'November 20th' or just 'tomorrow'."
                    elif retry_count == 2:
                        response_data['response_text'] = "Let me try a different way. " \
                                                       "Please say the month first, then the day. " \
                                                       "For example: 'November' pause 'twenty' or 'November' pause 'twenty zero'."
                    else:
                        response_data['response_text'] = "I'm still having trouble. " \
                                                       "Please try saying the date in this format: " \
                                                       "Say the month name, then pause, then say the day number. " \
                                                       "For example, say: 'November' pause 'twenty'."
                    response_data['needs_more_info'] = True
        
        elif current_state == ConversationState.COLLECTING_TIME:
            if 'time' in entities:
                time = entities['time']
                # Validate time is within restaurant hours (9am-10pm)
                time_valid = self._validate_time_within_hours(time)
                
                if time_valid:
                    response_data['response_text'] = f"Time: {time}. How many people will be dining?"
                    self.set_conversation_state(call_sid, ConversationState.COLLECTING_GUESTS)
                    response_data['next_action'] = 'collect_guests'
                    response_data['needs_more_info'] = True
                    # Reset retry counter on success
                    self.redis_client.hdel(f"call_session:{call_sid}", "time_retry_count")
                else:
                    response_data['response_text'] = f"I'm sorry, but our restaurant is only open from 9am to 10pm. " \
                                                     f"You requested {time}. " \
                                                     f"Please choose a time between 9am and 10pm."
                    response_data['needs_more_info'] = True
            else:
                # Track retry attempts
                retry_count = self.redis_client.hget(f"call_session:{call_sid}", "time_retry_count")
                retry_count = int(retry_count) if retry_count else 0
                retry_count += 1
                self.redis_client.hset(f"call_session:{call_sid}", "time_retry_count", retry_count)
                
                # Try to extract time from raw input as fallback
                user_input_lower = user_input.lower()
                
                # Look for standalone numbers that might be time
                number_match = re.search(r'\b(\d{1,2})\b', user_input_lower)
                ampm_match = re.search(r'\b(am|pm)\b', user_input_lower)
                
                if number_match:
                    hour = int(number_match.group(1))
                    if ampm_match:
                        time_extracted = f"{hour} {ampm_match.group(1)}"
                        # Validate
                        if self._validate_time_within_hours(time_extracted):
                            entities['time'] = time_extracted
                            response_data['response_text'] = f"Time: {time_extracted}. How many people will be dining?"
                            self.set_conversation_state(call_sid, ConversationState.COLLECTING_GUESTS)
                            response_data['next_action'] = 'collect_guests'
                            response_data['needs_more_info'] = True
                            self.redis_client.hdel(f"call_session:{call_sid}", "time_retry_count")
                        else:
                            response_data['response_text'] = f"I'm sorry, but our restaurant is only open from 9am to 10pm. " \
                                                           f"You requested {time_extracted}. " \
                                                           f"Please choose a time between 9am and 10pm."
                            response_data['needs_more_info'] = True
                    elif 1 <= hour <= 12:
                        # Ambiguous time - assume PM for dinner hours, but ask for clarification if too late
                        if hour >= 9:
                            time_extracted = f"{hour} pm"
                            entities['time'] = time_extracted
                            response_data['response_text'] = f"I have {time_extracted}. Is that correct? Say yes to continue."
                            response_data['next_action'] = 'confirm_time'
                            response_data['needs_more_info'] = True
                            self.redis_client.hset(f"call_session:{call_sid}", "pending_time", time_extracted)
                        else:
                            response_data['response_text'] = f"I heard {hour}. Is that in the morning or evening? " \
                                                           f"Please say '{hour}am' or '{hour}pm'. " \
                                                           f"Remember, we're open from 9am to 10pm."
                            response_data['needs_more_info'] = True
                    else:
                        response_data['response_text'] = f"I heard {hour}, but that doesn't seem like a valid time. " \
                                                         f"Please say a time between 9am and 10pm, " \
                                                         f"like '1pm', '1 o'clock', or '7pm'."
                        response_data['needs_more_info'] = True
                else:
                    # Provide guidance based on retry count
                    if retry_count == 1:
                        response_data['response_text'] = "I didn't catch the time clearly. " \
                                                       "Please say the time again. " \
                                                       "You can say '1pm', '1 o'clock', or just '1'. " \
                                                       "Remember, we're open from 9am to 10pm."
                    elif retry_count == 2:
                        response_data['response_text'] = "Let me try a different way. " \
                                                       "Please say the hour first, then whether it's morning or evening. " \
                                                       "For example: 'one' pause 'PM' or 'seven' pause 'PM'. " \
                                                       "We're open from 9am to 10pm."
                    else:
                        response_data['response_text'] = "I'm still having trouble. " \
                                                       "Please try saying just the hour number and whether it's AM or PM. " \
                                                       "For example: '1' pause 'PM' or '9' pause 'AM'. " \
                                                       "Our restaurant is open from 9am to 10pm."
                    response_data['needs_more_info'] = True
        
        elif current_state == ConversationState.COLLECTING_GUESTS:
            if 'guests' in entities:
                guests = entities['guests']
                # Complete reservation collection
                reservation_data = self.get_reservation_data(call_sid)
                reservation_data['guests'] = guests
                
                response_data['response_text'] = self._format_reservation_confirmation(reservation_data)
                self.set_conversation_state(call_sid, ConversationState.CONFIRMING_RESERVATION)
                response_data['next_action'] = 'confirm_reservation'
                response_data['needs_more_info'] = False
            else:
                response_data['response_text'] = "How many people will be dining? Please say the number."
        
        return response_data
    
    def _handle_reservation_id_state(self, call_sid: str, user_input: str, 
                                    entities: Dict, response_data: Dict, action_type: str = None) -> Dict:
        """Handle reservation ID collection for both checking and canceling"""
        if 'reservation_id' in entities:
            reservation_id = entities['reservation_id'].upper()
            
            # Check if reservation exists
            reservation_exists = self.redis_client.exists(f"reservation:{reservation_id}")
            
            if action_type == 'cancel':
                if reservation_exists:
                    # Cancel the reservation
                    reservation_data = self.redis_client.hgetall(f"reservation:{reservation_id}")
                    self.redis_client.delete(f"reservation:{reservation_id}")
                    response_data['response_text'] = f"Your reservation {reservation_id} has been successfully cancelled. " \
                                                   f"Thank you for letting us know."
                    response_data['next_action'] = 'complete'
                    response_data['needs_more_info'] = False
                else:
                    response_data['response_text'] = f"I couldn't find a reservation with ID {reservation_id}. " \
                                                   f"Please double-check your reservation ID and try again, " \
                                                   f"or contact our staff for assistance."
                    response_data['needs_more_info'] = True
            else:
                # Check reservation
                if reservation_exists:
                    reservation_data = self.redis_client.hgetall(f"reservation:{reservation_id}")
                    name = reservation_data.get('name', 'N/A')
                    date = reservation_data.get('date', 'N/A')
                    time = reservation_data.get('time', 'N/A')
                    guests = reservation_data.get('guests', 'N/A')
                    
                    response_data['response_text'] = f"I found your reservation. " \
                                                   f"Reservation ID: {reservation_id}. " \
                                                   f"Name: {name}. " \
                                                   f"Date: {date}. " \
                                                   f"Time: {time}. " \
                                                   f"Number of guests: {guests}. " \
                                                   f"Is there anything else I can help you with?"
                else:
                    response_data['response_text'] = f"I couldn't find a reservation with ID {reservation_id}. " \
                                                   f"Please verify your reservation ID and try again."
                
                response_data['next_action'] = 'complete'
                response_data['needs_more_info'] = False
            
            self.set_conversation_state(call_sid, ConversationState.COMPLETED)
        else:
            # Try to extract reservation ID from raw input (alphanumeric codes)
            potential_id = re.search(r'\b([A-Z0-9]{4,10})\b', user_input.upper())
            if potential_id:
                reservation_id = potential_id.group(1)
                entities['reservation_id'] = reservation_id
                return self._handle_reservation_id_state(call_sid, user_input, entities, response_data, action_type)
            else:
                response_data['response_text'] = "I didn't catch your reservation ID. " \
                                               "Please say your reservation ID again, or spell it out."
                response_data['needs_more_info'] = True
        
        return response_data
    
    def _handle_other_states(self, intent: Intent, response_data: Dict) -> Dict:
        """Handle other conversation states"""
        if intent == Intent.GOODBYE:
            response_data['response_text'] = "Thank you for calling. Have a great day!"
            response_data['next_action'] = 'hangup'
        else:
            response_data['response_text'] = "Is there anything else I can help you with?"
        
        return response_data
    
    def _format_reservation_confirmation(self, reservation_data: Dict) -> str:
        """Format reservation confirmation message"""
        name = reservation_data.get('name', 'Customer')
        date = reservation_data.get('date', 'the selected date')
        time = reservation_data.get('time', 'the selected time')
        guests = reservation_data.get('guests', 'N/A')
        
        return f"Perfect! Let me confirm your reservation details. " \
               f"Name: {name}, Date: {date}, Time: {time}, Number of guests: {guests}. " \
               f"Your reservation has been recorded. Is this correct?"

