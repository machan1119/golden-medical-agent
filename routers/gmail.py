from fastapi import APIRouter, Request
import asyncio
from typing import Dict
from core.workflow import (
    intake_workflow,
    IntakeState,
)
from core.helpers import extract_email
from config import settings
from openai import OpenAI
from composio_openai import ComposioToolSet, Action

router = APIRouter()

# Store active email conversations
active_emails: Dict[str, IntakeState] = {}


@router.post("/")
async def handle_incoming_gmail(request: Request):
    print("Received incoming Gmail request")
    # Placeholder for Gmail intake logic
    try:
        payload = await request.json()
        message = payload["data"]["preview"]["body"]
        email_username = payload["data"]["sender"]
        from_email = extract_email(email_username)
        # Initialize or get existing conversation state
        print("Active emails:", active_emails)
        if from_email not in active_emails:
            active_emails[from_email] = IntakeState(
                messages=[],
                contact_info=from_email,
                intent="",
                required_fields=[],
                collected_fields={},
                channel="email",
                status="initialized",
            )
        # Update the state with the new message
        state = active_emails[from_email]
        state["messages"].append(("user", message))
        print(f"Processing email from {from_email}: {message}")
        # Run the workflow
        current_state = await asyncio.to_thread(intake_workflow.invoke, state)
        last_message = next(
            (
                msg
                for role, msg in reversed(current_state["messages"])
                if role == "assistant"
            ),
            None,
        )
        if current_state["status"] == "jotform_used":
            print(f"JotForm required for {from_email}, sending link")
            # If JotForm is required, send the link
            message = {
                "to": from_email,
                "subject": "Re: Your Healthcare Intake Request",
                "message_text": last_message,
            }
            print(f"Sending JotForm link to {from_email}: {last_message}")
            send_message(message)
            del active_emails[from_email]
            return
        elif current_state["status"] == "in_progress":
            message = {
                "to": from_email,
                "subject": "Re: Your Healthcare Intake Request",
                "message_text": last_message,
            }
            print(
                f"Form is not required and not completed, sending response to {from_email}: {last_message}"
            )
            send_message(message)
            return
        elif current_state["status"] == "complete":
            message = {
                "to": from_email,
                "subject": "Re: Your Healthcare Intake Request",
                "message_text": last_message,
            }
            print(f"Sending completed message to {from_email}: {last_message}")
            send_message(message)
            del active_emails[from_email]
            return

        active_emails[from_email] = current_state

    except Exception as e:
        print(f"Error processing email: {str(e)}")
        # Send error notification
        error_message = {
            "to": from_email,
            "subject": "Error Processing Your Request",
            "message_text": "I apologize, but I encountered an error processing your request. Please try again later.",
        }
        del active_emails[from_email]
        send_message(error_message)


def send_message(message: dict[str, str]) -> Dict:
    """
    Send an email message using Composio's Gmail tool via OpenAI Assistant.
    """
    # Initialize OpenAI and Composio toolset
    openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    composio_tool_set = ComposioToolSet(api_key=settings.COMPOSIO_API_KEY)

    # Get Gmail send email action
    actions = composio_tool_set.get_actions(actions=[Action.GMAIL_CREATE_EMAIL_DRAFT])

    # Define the task for the assistant
    my_task = (
        f"Send an email to {message["to"]} with subject '{message["subject"]}' "
        f"and body '{message["message_text"]}'"
    )

    # Create the assistant with Gmail tool
    assistant = openai_client.beta.assistants.create(
        name="Gmail Assistant",
        instructions="You can send emails via Gmail.",
        model="gpt-4o",  # or any supported model
        tools=actions,
    )

    # Create a thread and add the user message
    thread = openai_client.beta.threads.create()
    openai_client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=my_task,
    )

    # Run the assistant
    run = openai_client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
    )

    # Handle tool calls and process the response
    response = composio_tool_set.wait_and_handle_assistant_tool_calls(
        client=openai_client,
        run=run,
        thread=thread,
    )
    return response
