from typing import Dict, List, Tuple, TypedDict
from langgraph.graph import Graph, StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import OpenAIEmbeddings
from langchain.output_parsers.boolean import BooleanOutputParser
import json
from config import settings
from core.helpers import data_parse
from core.store import form_service
from core.messages import (
    JOTFORM_LINK_MESSAGE,
    COMPLETE_MESSAGE,
    COMPLETE_DISCHARGE_MESSAGE,
)
import re

# Validate API keys first
if not settings.OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in settings")

llm = ChatOpenAI(model="gpt-4o", temperature=0.0, api_key=settings.OPENAI_API_KEY)

embeddings = OpenAIEmbeddings(
    model="text-embedding-ada-002", api_key=settings.OPENAI_API_KEY
)


# Define state types
class IntakeState(TypedDict):
    messages: List[Tuple[str, str]]
    contact_info: str
    intent: str
    required_fields: List[str]
    collected_fields: Dict[str, str]
    channel: str
    status: str


# Define prompts
INTENT_CLASSIFICATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are an intent classification system for a healthcare intake process.
Classify the user's intent into one of these categories:
- PRIVATE_PAY: For private pay patients
- CASE_MANAGER: For case manager referrals
- DISCHARGE: For hospital discharge transportation

Respond with ONLY the category name.""",
        ),
        ("human", "{input}"),
    ]
)

JOTFORM_IS_REQUIRED_CLASSIFICATION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are an assistant that determines if the user wants to fill out a form.
Read the user’s message carefully.
If only the user explicitly asks to fill out a form, requests a form, or expresses intent to complete a form, answer "YES".
If the user does not show intent to fill out a form, provide information for a form, or request a form, answer "NO".

Only answer "YES" or "NO".
Do not include any other words or explanations.""",
        ),
        ("human", "{input}"),
    ]
)

FIELD_EXTRACTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a healthcare intake assistant. Your task is to extract relevant, explicitly provided information from the user's message based on the identified intent and conversation history. Only extract information that is directly and clearly stated by the user—do not infer, guess, or fill in missing details.
Extraction Rules:
- Extract only the fields listed for the identified intent (see below).
- If a field is not explicitly mentioned or is ambiguous, omit it from your output.
- Do not include fields with placeholders, generic phrases, or inferred values.
- Ensure all extracted data is plausible and logically consistent.
- For any field that is a yes/no question (such as is_infectious_disease), always extract the value as the string "yes" or "no".

Field Extraction Guidelines:
- Names: Extract only proper human names (e.g., "John Smith"). Exclude titles, roles, or generic phrases.
- Phone Numbers: Extract valid phone numbers in standard formats (e.g., "123-456-7890", "(123) 456 7890", "+1 123 456 7890"). Exclude extensions or unrelated numbers.
- Dates: Convert all dates to ISO format (YYYY-MM-DD). Omit incomplete or ambiguous dates.
- Addresses and Facilities: Extract exact names and addresses as provided. Omit if the user says "unknown", "not provided", etc.
- Equipment/Medical Needs: Extract details only if explicitly stated (e.g., "wheelchair", "gurney", "oxygen_is_needed").
- Yes/No Fields: Always extract as "yes" or "no" (strings).
- Other Fields: Extract only if clearly and explicitly provided by the user.

Intents and Their Fields to Extract:

- PRIVATE_PAY:
    patient_name: Full human name(Patient name)
    weight: Human weight
    pickup_address: Address
    drop_off_address: Address
    appointment_date: Date
    one_way_or_round_trip: one way or round trip(Yes/No)
    equipment_needed: wheelchair or gurney or if don't need, 'No'
    any_stairs_and_accompanying_passengers: any stairs and accompanying passengers
    user_name: Full human name(Your name)
    phone_number: Phone number
    email: valid email

- INSURANCE_CASE_MANAGERS:
    patient_name: Full human name(Patient name)
    pickup_address: Address
    drop_off_address: Address
    authorization_number: Number (if applicable)
    appointment_date: Date

- DISCHARGE:
    patient_name: Full human name(Patient name)
    pickup_facility_name: Pick-Up facility name
    pickup_facility_address: Pick-Up facility address
    pickup_facility_room_number: Pick-Up facility room number
    drop_off_facility_name: Drop-Off facility name
    drop_off_facility_address: Drop-Off facility address
    drop_off_facility_room_number: Drop-Off facility room number
    appointment_date: Date
    oxygen_is_needed: Is oxygen needed? ("yes" or "no")
    oxygen_amount: Oxygen amount (number)
    is_infectious_disease: Is infectious disease? ("yes" or "no")
    weight: Human weight

Formatting Instructions:
- Return your output as a JSON object containing only the fields relevant to the identified intent.
- Exclude any fields not explicitly mentioned in the user's message.
- Do not include any explanatory text, only the JSON object.
- The JSON keys must exactly match the field names above.""",
        ),
        (
            "human",
            """Intent: {intent}
Conversation: {conversation}
Message: {input}""",
        ),
    ]
)

NEXT_QUESTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a healthcare intake assistant. Based on the intent and the fields collected so far, identify which required fields are still missing (i.e., those in required_fields but not in collected_fields).
Generate one clear, concise, and polite question that asks the user to provide all the missing information at once.
In this case, the patient name is just patient name, not 'your name'.
List the missing fields in a natural and user-friendly way.
If all required fields are collected, respond with 'COMPLETE'.""",
        ),
        (
            "human",
            """Intent: {intent}
Required fields: {required_fields}
Collected fields: {collected_fields}
Conversation history: {conversation}""",
        ),
    ]
)


# Define nodes
def classify_intent(state: IntakeState) -> IntakeState:
    """Classify the user's intent from their message."""
    print("Classifying intent...")
    if state["intent"]:
        print("Intent already classified:", state["intent"])
        return state
    messages = state["messages"]
    last_message = messages[-1][1] if messages else ""

    response = llm.invoke(
        INTENT_CLASSIFICATION_PROMPT.format_messages(input=last_message)
    )
    print("Classify result:", response.content.strip())
    state["intent"] = response.content.strip()
    return state


def classify_intent_router(state: IntakeState):
    """Router to handle intent classification."""
    if state["intent"] == "PRIVATE_PAY":
        print(
            "Intent classified as PRIVATE_PAY, proceeding to classify_jotform_is_required."
        )
        return "classify_jotform_is_required"
    else:
        return "get_required_fields"


def classify_jotform_is_required(state: IntakeState) -> bool:
    messages = state["messages"]
    last_message = messages[-1][1] if messages else ""

    response = llm.invoke(
        JOTFORM_IS_REQUIRED_CLASSIFICATION_PROMPT.format_messages(input=last_message)
    )
    parser = BooleanOutputParser()
    result = parser.parse(response.content.strip())
    if result:
        print("User wants to fill out the form.")
        state["status"] = "jotform_used"
    return state


def classify_jotform_is_required_router(state: IntakeState):
    if state["status"] == "jotform_used":
        state["messages"].append(("assistant", JOTFORM_LINK_MESSAGE))
        print("Jotform used, skipping further classification.")
        return END
    else:
        return "get_required_fields"


def get_required_fields(state: IntakeState) -> IntakeState:
    """Retrieve required fields for the detected intent."""
    print("Retrieving required fields...")
    intent = state["intent"]

    default_fields = {
        "PRIVATE_PAY": [
            "patient_name",
            "weight",
            "pickup_address",
            "drop_off_address",
            "appointment_date",
            "one_way_or_round_trip",
            "equipment_needed",
            "any_stairs_and_accompanying_passengers",
            "user_name",
            "phone_number",
            "email",
        ],
        "CASE_MANAGER": [
            "patient_name",
            "pickup_address",
            "drop_off_address",
            "authorization_number",
            "appointment_date",
        ],
        "DISCHARGE": [
            "patient_name",
            "pickup_facility_name",
            "pickup_facility_address",
            "pickup_facility_room_number",
            "drop_off_facility_name",
            "drop_off_facility_address",
            "drop_off_facility_room_number",
            "appointment_date",
            "oxygen_is_needed",
            "oxygen_amount",
            "is_infectious_disease",
            "weight",
        ],
    }

    state["required_fields"] = default_fields.get(intent, [])

    print("required fields:", state["required_fields"])
    return state


def extract_fields(state: IntakeState) -> IntakeState:
    """Extract relevant fields from the user's message."""
    print("Extracting fields...")
    messages = state["messages"]
    conversation = "\n".join([f"{role}: {content}" for role, content in messages])
    user_message = messages[-1][1] if messages else ""
    response = llm.invoke(
        FIELD_EXTRACTION_PROMPT.format_messages(
            intent=state["intent"], conversation=conversation, input=user_message
        )
    )

    try:
        json_fields = re.search(r"\{[\s\S]*\}", response.content.strip())
        if json_fields:
            extracted_fields = json.loads(json_fields.group(0))
        if isinstance(extracted_fields, dict):
            state["collected_fields"].update(extracted_fields)
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON of extracted_fields: {e}")
        # Continue without updating fields
    print("Extracted fields:", response.content)
    return state


def determine_next_question(state: IntakeState) -> IntakeState:
    """Determine what information is still needed."""
    print("Determining next question...")
    messages = state["messages"]
    conversation = "\n".join([f"{role}: {content}" for role, content in messages])

    response = llm.invoke(
        NEXT_QUESTION_PROMPT.format_messages(
            intent=state["intent"],
            required_fields=state["required_fields"],
            collected_fields=state["collected_fields"],
            conversation=conversation,
        )
    )

    if response.content.strip() == "COMPLETE":
        state["status"] = "complete"
        if state["intent"] == "DISCHARGE":
            state["messages"].append(
                (
                    "assistant",
                    COMPLETE_DISCHARGE_MESSAGE.format(
                        patient_name=state["collected_fields"].get("patient_name")
                    ),
                )
            )
        else:
            state["messages"].append(
                (
                    "assistant",
                    COMPLETE_MESSAGE.format(
                        patient_name=state["collected_fields"].get("patient_name")
                    ),
                )
            )
    else:
        state["status"] = "in_progress"
        state["messages"].append(("assistant", response.content))
    print("Next question:", response.content.strip())
    return state


def store_current_state(state: IntakeState) -> bool:
    """Store the current state of the intake process."""
    print("Storing current state...")
    store_data = data_parse(state)
    success = form_service.store_intake_data(store_data, state.get("intent"))
    if success:
        print("State stored successfully.")
    return state


def create_intake_workflow() -> Graph:
    """Create the LangGraph workflow for the intake process."""
    print("Creating intake workflow...")
    workflow = StateGraph(IntakeState)

    workflow.add_node("classify_intent", classify_intent)
    workflow.add_node("classify_jotform_is_required", classify_jotform_is_required)
    workflow.add_node("get_required_fields", get_required_fields)
    workflow.add_node("extract_fields", extract_fields)
    workflow.add_node("determine_next_question", determine_next_question)
    workflow.add_node("store_current_state", store_current_state)

    workflow.add_conditional_edges(
        "classify_intent",
        classify_intent_router,
    )
    workflow.add_conditional_edges(
        "classify_jotform_is_required",
        classify_jotform_is_required_router,  # This function returns "determine_next_question" or END
        workflow.add_edge("get_required_fields", "extract_fields"),
    )
    workflow.add_edge("extract_fields", "determine_next_question")
    workflow.add_edge("determine_next_question", "store_current_state")

    workflow.set_entry_point("classify_intent")
    return workflow.compile()


# Create the workflow instance
intake_workflow = create_intake_workflow()
