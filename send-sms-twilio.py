# This is just end sms to twilio phone number for testing.

import os
from twilio.rest import Client

account_sid = os.environ["TWILIO_ACCOUNT_SID"]
auth_token = os.environ["TWILIO_AUTH_TOKEN"]
client = Client(account_sid, auth_token)

message = client.messages.create(
    body="I would like to know the payment options available for patients who pay privately.",
    from_="12132216322",
    to="+12132211556",
)

print(message.body)
