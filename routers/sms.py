from fastapi import APIRouter, Request, HTTPException
import asyncio
from twilio.rest import Client
from config import settings
from typing import Dict
from core.workflow import intake_workflow, IntakeState

router = APIRouter()
twilio_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

# Store active SMS conversations
active_sms: Dict[str, IntakeState] = {}


@router.post("/")
async def handle_incoming_sms(request: Request):
    """Handle incoming SMS messages."""
    response = ""
    form = await request.form()
    # Get the message details
    from_number = form.get("From")
    message_body = form.get("Body", "").strip()
    print(f"Processing sms from {from_number}: {message_body}")

    if not from_number or not message_body:
        raise HTTPException(status_code=400, detail="Missing required parameters")

    # Initialize or get existing conversation state
    if from_number not in active_sms:
        active_sms[from_number] = IntakeState(
            messages=[],
            intent="",
            required_fields=[],
            collected_fields={},
            contact_info=from_number,
            channel="sms",
            status="initialized",
        )

    # Update the state with the new message
    state = active_sms[from_number]
    state["messages"].append(("user", message_body))

    try:
        # Run the workflow
        print("Run the workflow")
        new_state = await asyncio.to_thread(intake_workflow.invoke, state)
        active_sms[from_number] = new_state

        # Get the last assistant message
        last_message = next(
            (
                msg
                for role, msg in reversed(new_state["messages"])
                if role == "assistant"
            ),
            None,
        )
        if new_state["status"] == "jotform_used":
            print(f"JotForm required for {from_number}, sending link")
            # If JotForm is required, send the link
            response = last_message
            del active_sms[from_number]
            return
        elif new_state["status"] == "complete":
            # Handle completion
            if new_state["intent"] == "PRIVATE_PAY":
                reply = "Thanks! We’ll prepare your quote and send a credit card form shortly to confirm."
            elif new_state["intent"] == "INSURANCE_CASE_MANAGERS":
                reply = "Thank you! We’ll forward this to dispatch and confirm shortly."
            elif new_state["intent"] == "DISCHARGES":
                reply = "Got it! Our dispatch team will review this now and follow up shortly."
            response = reply
            # Clean up
            del active_sms[from_number]
        else:
            # Continue the conversation
            response = last_message or "Could you please provide more information?"
    except Exception as e:
        response = "I apologize, but I encountered an error. Please try again later."
        del active_sms[from_number]
        raise HTTPException(status_code=500, detail=str(e))
    await send_sms(from_number, response)
    return response


async def send_sms(to: str, message: str):
    """Send an SMS message."""
    print("Sending response message to:", to)
    try:
        message = twilio_client.messages.create(
            body=message, from_=settings.TWILIO_PHONE_NUMBER, to=to
        )
        return {"status": "success", "message_sid": message.sid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/status")
async def handle_sms_status(request: Request):
    """Handle SMS status callbacks."""
    form = await request.form()
    message_sid = form.get("MessageSid")
    message_status = form.get("MessageStatus")

    # Log the status update
    print(f"Message {message_sid} status: {message_status}")

    return {"status": "success"}


@router.post("/check")
async def handle_sms_check(request: Request):
    """Handle SMS check."""
    form = await request.form()
    # Get the message details
    from_number = form.get("From")
    message_body = form.get("Body", "").strip()
    print(f"Received sms from {from_number}: {message_body}")

    return {"status": "success"}
