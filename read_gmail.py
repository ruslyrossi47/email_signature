# Lib
# https://spacy.io/usage

from __future__ import print_function

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from bs4 import BeautifulSoup
from pprint import pprint
from spacy.matcher import Matcher

import os.path
import pickle
import pybase64
import email
import sys
import re
import csv
import spacy

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def main():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        # Call the Gmail API
        service = build('gmail', 'v1', credentials=creds)
        result = service.users().messages().list(maxResults=100, userId='me').execute()
        messages = result.get('messages')

        # Open and read 'position_titles.csv'
        with open('position_titles.csv', newline='') as csvfile:
            reader = csv.reader(csvfile)
            # convert the reader object to a list
            data = list(reader)
  
        # Open data.csv file in write mode
        with open('eml/data.csv', 'w', newline='') as csvfile:

            # Load English tokenizer, tagger, parser and NER
            nlp = spacy.load("en_core_web_sm")
        
            # iterate through all the messages
            for msg in messages:

                # Get the message from its id
                txt = service.users().messages().get(userId='me', id=msg['id']).execute()
        
                # Use try-except to avoid any Errors
                try:
                    # Get payload from message
                    payload = txt['payload']
                    headers = payload['headers']

                    # Get email id
                    email_id = txt['id']

                    # Loop header meta data and try to fetch sender email and name
                    for d in headers:
                        if d['name'] == 'Subject':
                            subject = d['value']
                            
                        if d['name'] == 'From':
                            sender_from = d['value']

                            name = re.sub('<(.*)>', '', sender_from)
                            person_name = name

                            # define a regular expression pattern that matches the content inside angle brackets
                            pattern = r'<(.*)>'

                            # search the string for the content inside angle brackets using the regular expression
                            match = re.search(pattern, sender_from)

                            # extract the content inside angle brackets from the match
                            person_email = match.group(1)

                    # if email is no-reply skip
                    if person_email.lower().find('no-reply') != -1 or person_email.lower().find('noreply') != -1:
                        continue

                    # Remove whitespace at the beginning and end of the string
                    name = re.sub(r"^\s*|\s*$", "", name)

                    # Convert the string into a list of words
                    name_array = name.split(" ")
                            
                    # Skip below code if person name has .com domain
                    if name.lower().find('.com') != -1:
                        continue
                    
                    # Decode the base64 encoded data in the payload body
                    decoded_data = pybase64.urlsafe_b64decode(payload['parts'][0]['body']['data']).decode("utf-8")

                    # Split the string at each newline character
                    lines = decoded_data.splitlines()

                    # Join the resulting list of strings back together using "\n" as the separator
                    text = "\n".join(lines)

                    body_array = text.split("\r\n")

                    # Split the string at each newline character
                    lines = text.splitlines()

                    # Join the resulting list of strings back together using "\n" as the separator
                    text = "\n".join(lines)

                    # Convert the string into an array using the newline character as the delimiter
                    body_array = text.split("\n")

                    # This code reverses the body_array list and search from bottom to top because the person name. It searches name array for each entry. If a match is found, it sets name pos to the element's index and name to the element. Name pos > 0 breaks the inner loop.
                    name_pos = 0
                    for element in reversed(body_array):
                        for name_element in name_array:
                            # Check if the current element is equal to the sender name
                            if name_element.lower().find(element.lower()) != -1 or element.lower().find(name_element.lower()) != -1:
                                name_pos = body_array.index(element)
                                name = element
                                break
                        
                        if name_pos != 0:
                            break

                    
                    if name_pos == 0:
                        break
                    
                    # Set the starting key
                    key = name_pos+1

                    # Find job position
                    position = ''
                    for array_value in body_array:
                        
                        for element in data:
                            if element[0].lower().find(array_value.lower()) != -1:
                                position = array_value
                                break
                        
                        if position != '':
                            break

                    # Use NLP to detect the person name in an body_array of strings. If a person name is found, it is stored in a variable and the search ends.
                    doc = nlp(person_name)
                    for entity in doc.ents:
                        if entity.label_ == 'PERSON':
                            name = entity.text
                            break

                    # Detect the phone number in an body_array of strings using a regular expression for a specified phone number. If a phone number is found, it is stored in a variable and the search ends.
                    phone_regex_1 = re.compile(r'[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}')
                    phone_regex_2 = re.compile(r'\+\d+(.*?)$')
                    phone_number = ''
                    for element in body_array:
                        match_regex_1 = phone_regex_1.search(element.lower())
                        match_regex_2 = phone_regex_2.search(element.lower())
                        if match_regex_1:
                            phone_number = match_regex_1.group()
                            break
                        if match_regex_2:
                            phone_number = match_regex_2.group()
                            break

                    data_csv = [
                        [name or person_name, person_email, position, phone_number]
                    ]

                    # Write data to csv file
                    writer = csv.writer(csvfile, delimiter=',')
                    writer.writerows(data_csv)
                    
                except:
                    pass

    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f'An error occurred: {error}')


if __name__ == '__main__':
    main()