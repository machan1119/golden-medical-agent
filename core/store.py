from typing import Dict
from google.oauth2.service_account import Credentials
from googleapiclient.errors import HttpError
import gspread
import requests
from config import settings
import json
import os
import tempfile


# 1. Build the credentials dict from environment variables
sa_info = {
    "type": os.environ["SA_TYPE"],
    "project_id": os.environ["SA_PROJECT_ID"],
    "private_key_id": os.environ["SA_PRIVATE_KEY_ID"],
    "private_key": os.environ["SA_PRIVATE_KEY"].replace("\\n", "\n"),
    "client_email": os.environ["SA_CLIENT_EMAIL"],
    "client_id": os.environ["SA_CLIENT_ID"],
    "auth_uri": os.environ["SA_AUTH_URI"],
    "token_uri": os.environ["SA_TOKEN_URI"],
    "auth_provider_x509_cert_url": os.environ["SA_AUTH_PROVIDER_CERT_URL"],
    "client_x509_cert_url": os.environ["SA_CLIENT_CERT_URL"],
    "universe_domain": os.environ["SA_DOMAIN"],
}

# 2. Write to a temporary file and set GOOGLE_APPLICATION_CREDENTIALS
with tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".json") as tempf:
    json.dump(sa_info, tempf)
    tempf.flush()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tempf.name


class FormService:
    def __init__(self):
        self.sheets_service = None
        self.jotform_api_key = settings.JOTFORM_API_KEY

    def get_sheets_service(self):
        """Get or create Google Sheets service."""
        # Path to your service account key file
        spreadsheet_url = "https://docs.google.com/spreadsheets/d/1Zb-Wj_7ofYbsyVxztFSTgmUJkHrLBnCddEs9s6NbeEQ/edit?usp=sharing"
        # Define the scope
        SCOPES = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        print("Initializing Google Sheets service...")
        credentials = Credentials.from_service_account_file(
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"], scopes=SCOPES
        )
        client = gspread.authorize(credentials)
        print("Credentials authorized successfully.", client)
        spreadsheet = client.open_by_url(spreadsheet_url)
        print("Google Sheets service initialized successfully.", spreadsheet)
        self.sheets_service = spreadsheet
        return self.sheets_service

    def store_intake_data(self, data: Dict, intent: str) -> bool:
        """Store intake data in Google Sheets and optionally JotForm."""
        # try:

        # Store in Google Sheets
        sheets_success = self._store_in_sheets(data, intent)

        jotform_success = True
        # if self.jotform_api_key:
        #     jotform_success = await self._store_in_jotform(formatted_data)

        return sheets_success and jotform_success

        # except Exception as e:
        #     print(f"Error storing intake data: {str(e)}")
        #     return False

    def _store_in_sheets(self, data: Dict, intent: str) -> bool:
        """Store data in Google Sheets."""
        try:
            sheet = self.get_sheets_service()
            print("intent", intent)
            worksheet = sheet.worksheet(intent)
            contact_info = data.get("contact_info")
            all_rows = worksheet.get_all_values()
            header = all_rows[0]
            try:
                contact_info_col_index = (
                    header.index("Contact_Info") + 1
                )  # gspread is 1-indexed for columns
            except ValueError:
                print("contact_info column not found in sheet header.")
                return False

            # Search for the row with matching contact_info
            row_to_update = None
            for i, row in enumerate(
                all_rows[1:], start=2
            ):  # start=2 because sheet rows start at 1 and first row is header
                if (
                    len(row) >= contact_info_col_index
                    and row[contact_info_col_index - 1] == contact_info
                ):
                    row_to_update = i
                    break

            # Prepare the row data in the order of the header columns
            row_data = []
            for col_name in header:
                row_data.append(
                    data.get(col_name, "")
                )  # fill with empty string if key missing

            if row_to_update:
                # Update the existing row
                worksheet.update(
                    f"A{row_to_update}:{chr(64 + len(header))}{row_to_update}",
                    [row_data],
                )
                print(f"Updated row {row_to_update} for contact_info: {contact_info}")
            else:
                # Append new row
                worksheet.append_row(row_data)
                print(f"Appended new row for contact_info: {contact_info}")

            row = list(data.values())
            worksheet.append_row(row)
            return True

        except HttpError as e:
            print(f"Error storing in Google Sheets: {str(e)}")
            return False

    def _store_in_jotform(self, data: Dict) -> bool:
        """Store data in JotForm."""
        if not self.jotform_api_key:
            return True  # Skip if no API key

        try:
            # Map the data to JotForm fields
            # You'll need to adjust these field IDs based on your JotForm setup
            jotform_data = {
                "q3_name": data.get("name", ""),
                "q4_phone": data.get("phone", ""),
                "q5_email": data.get("email", ""),
                "q6_address": data.get("address", ""),
                "q7_appointmentDate": data.get("appointment_date", ""),
                "q8_appointmentTime": data.get("appointment_time", ""),
                "q9_pickupAddress": data.get("pickup_address", ""),
                "q10_dropoffAddress": data.get("dropoff_address", ""),
                "q11_authNumber": data.get("auth_number", ""),
                "q12_notes": data.get("notes", ""),
                "q13_intent": data.get("intent", ""),
            }

            # Submit to JotForm
            response = requests.post(
                "https://api.jotform.com/form/your-form-id/submissions",
                headers={
                    "APIKEY": self.jotform_api_key,
                    "Content-Type": "application/json",
                },
                json=jotform_data,
            )

            return response.status_code == 200

        except Exception as e:
            print(f"Error storing in JotForm: {str(e)}")
            return False


# Create a singleton instance
form_service = FormService()
