from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import openai
from core.prompts import SYSTEM_PROMPT
from core.helpers import data_parse_from_chat, complete_reply, extract_json_from_reply
from core.store import form_service

router = APIRouter()


@router.post("/")
async def chat_endpoint(request: Request):
    body = await request.json()
    messages = body["messages"]
    if not any(msg.get("role") == "system" for msg in messages):
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    client = openai.OpenAI(api_key=openai.api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.2,
        stream=True,
    )

    def stream_generator():
        collected = []
        for chunk in response:
            chunk_message = chunk.choices[0].delta.content
            if chunk_message:
                collected.append(chunk_message)
                current_reply = "".join(collected)
                complete_flag = complete_reply(current_reply)
                if not complete_flag:
                    yield chunk_message
                collected_data = extract_json_from_reply(current_reply)
                if collected_data:
                    print(collected_data)
                    if collected_data.get("intent") == "PRIVATE_PAY":
                        yield "\nThanks! We’ll prepare your quote and send a credit card form shortly to confirm."
                    elif collected_data.get("intent") == "INSURANCE_CASE_MANAGERS":
                        yield "\nThank you! We’ll forward this to dispatch and confirm shortly."
                    elif collected_data.get("intent") == "DISCHARGE":
                        yield "\nGot it! Our dispatch team will review this now and follow up shortly."
                    parsed_data = data_parse_from_chat(collected_data, "chat", "user")
                    success = form_service.store_intake_data(
                        parsed_data, collected_data.get("intent")
                    )
                    if success:
                        print("State stored successfully.")

    return StreamingResponse(stream_generator(), media_type="text/plain")
