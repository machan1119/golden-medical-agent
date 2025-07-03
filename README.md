# Multichannel AI Agent Backend

**A FastAPI backend for a multichannel AI agent, powered by LangGraph, OpenAI, Twilio, and Composio.**  
This backend enables users to interact via email, SMS, or web chat, intelligently gathers required information based on user goals, and stores the results in Google Sheets.

---

## Features

- **Multichannel Support:** Accepts user input via email, SMS, and web chat.
- **Goal-Oriented Dialog:** Detects user goals (private pay, insurance case manager, discharge) and dynamically requests necessary information.
- **AI-Powered Understanding:** Uses OpenAI LLM and LangGraph for intent recognition, dialog management, and data extraction[1][3][4].
- **Data Storage:** Automatically saves structured data to Google Sheets via backend integration.
- **Extensible Architecture:** Built with FastAPI for easy deployment and scalability.

---

## Workflow

1. **User Interaction**  
   Users reach the agent through email, SMS (Twilio), or web chat.

2. **Goal Identification**  
   The backend uses LangGraph and OpenAI to interpret the user's message, identify the goal, and determine required fields[1][3][4].

3. **Data Gathering**  
   The agent requests and collects all necessary information from the user, adapting questions based on the identified goal.

4. **Data Storage**  
   Once all required data is collected, it is stored in a Google Sheet via a backend API request.

---

## Tech Stack

| Component          | Technology      | Purpose                                              |
|--------------------|----------------|------------------------------------------------------|
| Backend            | FastAPI         | RESTful API and orchestration                        |
| AI Agent           | LangGraph       | Dialog management and workflow logic                 |
| Language Model     | OpenAI GPT      | Natural language understanding and generation        |
| Messaging          | Twilio, Email   | SMS and email channel integration                    |
| Automation         | Composio        | Workflow and integration automation                  |
| Data Storage       | Google Sheets   | Stores collected user data                           |

---

## Quick Start

### Prerequisites

- OpenAI API key
- Twilio account credentials
- Composio credentials (if required)
- Google Sheets API credentials

### Setup

1. **Clone the repository**

   ```
   git clone https://github.com/machan1119/golden-medical-agent.git
   cd golden-medical-agent
   ```

2. **Install dependencies**

   ```
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   
   Create a `.env` file with your credentials:

   ```
    OPENAI_API_KEY=your_openai_key
    TWILIO_ACCOUNT_SID=your_twilio_sid
    TWILIO_AUTH_TOKEN=your_twilio_token
    GOOGLE_SHEETS_CREDENTIALS_JSON=path/to/creds.json
    COMPOSIO_API_KEY=your_composio_key
   ```

4. **Run the FastAPI server**

   ```
   python main.py
   ```


---

## Example Use Case

> **User (via SMS):** "I need to talk to the case manager about my insurance discharge."
>
> **Agent:** "Sure, can you provide your policy number and discharge date?"

The backend identifies the user's intent, requests the relevant fields, and stores the information in Google Sheets.

---

## Customization

- **Add new user goals:** Update LangGraph node logic and OpenAI prompts to support additional workflows.
- **Integrate more channels:** Extend with additional communication platforms (e.g., WhatsApp, Slack).
- **Change storage backend:** Replace Google Sheets integration with another database or service as needed.

---

## Contributing

Contributions and feature requests are welcome!

---
