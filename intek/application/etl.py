# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Intek Institute.  All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import collections
import csv
import getpass
import logging
import pickle
import os
import re
import socket
import time
import traceback

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from majormode.perseus.model.smtp import SmtpConnectionProperties
from majormode.perseus.model.locale import Locale
from majormode.perseus.utils import email_util
import googleapiclient.discovery
import googleapiclient.errors

from .model import PAYMENT_AMOUNT_NON_UPMD
from .model import PAYMENT_AMOUNT_UPMD
from .model import Registration


# Default name of the file where the OAuth2 token to access Google
# Sheets API is stored in.
DEFAULT_GOOGLE_OAUTH2_TOKEN_FILE_NAME = 'oauth2_token.pickle'

# Default name of the file where the client application secrets
# (credentials) to access Google Sheets API are stored in.
# [https://console.cloud.google.com/apis/credentials]
DEFAULT_GOOGLE_CREDENTIALS_FILE_NAME = 'google_credentials.json'

# Default time in seconds between two consecutive executions.
DEFAULT_IDLE_TIME_BETWEEN_CONSECUTIVE_EXECUTION = 60 * 5

# Default name of the file where the connection properties to the
# Simple Mail Transfer Protocol (SMTP) is stored in.
DEFAULT_SMTP_CONNECTION_PROPERTIES_FILE_NAME = 'smtp_connection_properties.pickle'

# Default relative path of the folder where the e-mail templates and
# attachment files are stored in.
DEFAULT_TEMPLATE_RELATIVE_PATH = 'templates'

# Supported locale to format parents and children' fullname.
ENGLISH_LOCALE = Locale('eng')
FRENCH_LOCALE = Locale('fra')
KOREAN_LOCALE = Locale('kor')
VIETNAMESE_LOCALE = Locale('vie')

# Mapping between education grade names and their corresponding levels.
GRADE_NAMES = {
    'TPS': 1,
    'PS': 2,
    'MS': 3,
    'GS': 4,
    'CP': 5,
    'CE1': 6,
    'CE2': 7,
    'CM1': 8,
    'CM2': 9,
    'Sixième': 10,
    'Cinquième': 11,
    'Quatrième': 12,
    'Troisième': 13,
    'Seconde': 14,
    'Première': 15,
    'Terminale': 16,
}

# OAuth2 scope information for the Google Sheets API: the script needs
# that the owner(s) of the Google Sheets documents allows read/write
# access to these sheets and their properties.
#
# @note: if modifying these scopes, delete the file the local OAuth2
#     token file (cf. `DEFAULT_GOOGLE_OAUTH2_TOKEN_FILE_NAME`).
GOOGLE_SPREADSHEET_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Placeholders to replaces with their respective values in the email to
# be sent to the parents who registered to the school bus transportation
# service.
PLACEHOLDER_PARENT_NAME = 'parent_name'
PLACEHOLDER_REGISTRATION_ID = 'registration_id'
PLACEHOLDER_PAYMENT_AMOUNT = 'payment_amount'
PLACEHOLDER_IS_APE_MEMBER = 'is_ape_member'

# Regular expression matching the pattern of a placeholder where its
# name needs to be replaced by its corresponding value.
#
# Placeholder names are surrounded by "::" and "::".  Placeholder names
# must consist of any letter (A-Z), any digit (0-9), an underscore, or
# a dot.  Placeholder names must start with a letter.
REGEX_PLACEHOLDER_NAME = re.compile(r'::((?i)[a-z][a-z0-9_.]*)::')


def build_current_directory_path_name(file_name):
    """
    Return the absolute path and name of a file located in the current
    directory of the user.


    :param file_name: the name of a file.


    :return: Absolute path and name of the file.
    """
    return os.path.join(os.getcwd(), file_name)


def build_registration_confirmation_email_content(registration, locale, template_path):
    """
    Build the localized content of a application confirmation e-mail to
    send to a family.


    :param registration: An object `Registration`.

    :paran locale: An object `Locale` that refers to the language to
        return the e-mail template and the file to attach to.

    :param template_path: The absolute path of the folder where localized
        e-mail templates and files to attach are stored in.


    :return: The localized content of the email.
    """
    template_content = get_registration_confirmation_email_template(locale, template_path)

    placeholders = {
        PLACEHOLDER_PARENT_NAME: ' / '.join([parent.fullname for parent in registration.parents]),
        PLACEHOLDER_PAYMENT_AMOUNT: PAYMENT_AMOUNT_UPMD if registration.is_ape_member else PAYMENT_AMOUNT_NON_UPMD,
        PLACEHOLDER_REGISTRATION_ID: prettify_registration_id(registration.registration_id),
    }

    email_content = expand_placeholders_value(template_content, placeholders)
    email_subject = get_email_subject(email_content)

    return email_subject, email_content


def build_registration_rows(registration):
    """
    Build the rows of values of the application of a family to the school
    bus transportation service.

    There are as many rows as the number of children registered to the
    transportation service.  The first row corresponds to a first child of
    the family, and some other information that is not duplicated over the
    other rows:

    - identification of the application;
    - date and time when the family submitted its application;
    - information about the primary parent;
    - information about a possible secondary parent;
    - a flag that indicates whether the family is willing to become or not
      a member of the parents association.


    :param registration: An object `Registration`.


    :return: A list of application's rows to be inserted in the master
        list.
    """
    rows = []

    for i, child in enumerate(registration.children):
        row = [
            registration.registration_id if i == 0 else '',
            registration.registration_time.strftime("%Y-%m-%d %H:%M:%S") if i == 0 else '',
            child.fullname,
            child.dob.strftime('%Y-%m-%d'),
            get_grade_name(child.grade_level)
        ]

        for j, fields in enumerate(Registration.PARENTS_FIELDS):
            if i == 0 and j < len(registration.parents):
                parent = registration.parents[j]
                row.extend([
                    parent.fullname,
                    parent.email_address,
                    parent.phone_number,
                    parent.home_address
                ])
            else:
                row.extend([''] * 4)  # Fullname, email, phone, address

        row.append(('Y' if registration.is_ape_member else 'N') if i == 0 else '')
        rows.append(row)

    return rows


def build_smtp_connection_properties(
        arguments,
        smtp_connection_properties_file_path_name=None):
    """
    Return the connection properties to the Simple Mail Transfer Protocol
    (SMTP) server.


    :param arguments: an instance `argparse.Namespace` corresponding to
        the populated namespace from the options passed to the command line.

    :param smtp_connection_properties_file_path_name: The absolute path
        and file where the SMTP connection properties are stored in.


    :return: An object `SmtpConnectionProperties`.
    """
    if smtp_connection_properties_file_path_name is None:
        smtp_connection_properties_file_path_name = \
            build_current_directory_path_name(DEFAULT_SMTP_CONNECTION_PROPERTIES_FILE_NAME)

    properties = None

    # Load the connection properties from the file if it exists.
    if os.path.exists(smtp_connection_properties_file_path_name):
        with open(smtp_connection_properties_file_path_name, 'rb') as fd:
            properties = pickle.load(fd)

    # Override properties the would have been passed as arguments on the
    # command line, or prompt the user for entering the properties that are
    # missing.
    username = arguments.smtp_username \
        or (properties and properties.username) \
        or input("Enter your SMTP username: ")

    password = (properties and properties.password) \
        or getpass.getpass("Enter your SMTP password: ")

    hostname = (properties and properties.hostname) \
        or arguments.smtp_hostname or input("Enter the SMTP hostname: ")

    port_number = (properties and properties.port_number) \
        or arguments.smtp_port

    new_properties = SmtpConnectionProperties(hostname, username, password, port_number)

    # Save the properties to the file for the next run.
    if properties is None or properties != new_properties:
        with open(smtp_connection_properties_file_path_name, 'wb') as fd:
            pickle.dump(new_properties, fd)

    return new_properties


def expand_placeholders_value(content, placeholders, ignore_unused_placeholders=False):
    """
    Replace the placeholders defined in the given content with their
    corresponding values.


    :param content: The content with placeholders {{placeholder}} to be
        replaced with their corresponding values.

    :param placeholders: A dictionary where the key corresponds to the
        name of a placeholder, the value corresponding to the value of the
        placeholder.

    :param ignore_unused_placeholders: Indicate whether to ignore
        placeholders that would have been defined but that would have not
        been declared in the given content.


    :return: The content where the placeholders have been replaced with
        their corresponding values.
    """
    # Find the list of placeholder names that have been used in the given
    # document but that have not been defined with a corresponding value.
    used_placeholders = set([
        (match.group(0), match.group(1))
        for match in REGEX_PLACEHOLDER_NAME.finditer(content)
    ])

    used_placeholder_names = [name for (_, name) in used_placeholders]

    if used_placeholders:
        undefined_placeholder_names = [
            name
            for name in used_placeholder_names
            if name not in placeholders
        ]

        assert len(undefined_placeholder_names) == 0, \
            "the following placeholders are declared but have not been defined: " \
            f"{','.join(undefined_placeholder_names)}"

    # Find the list of placeholder names that have been defined but have not
    # been used in the given document.
    if placeholders:
        unused_placeholder_names = [
            name
            for name in placeholders
            if name not in used_placeholder_names
        ]

        if len(unused_placeholder_names) > 0:
            assert ignore_unused_placeholders, \
                "the following placeholders are defined but have not been declared: " \
                f"{','.join(unused_placeholder_names)}"

    # Replace the placeholders referred in the content by their
    # corresponding value.
    for (placeholder_expression, placeholder_name) in used_placeholders:
        content = content.replace(placeholder_expression, placeholders[placeholder_name])

    return content


def fetch_processed_registration_ids(spreadsheets_resource, spreadsheet_id):
    """
    Return the list of identifications of the registrations that have been
    already processed and stored in the master list.


    :param spreadsheets_resource: An object `googleapiclient.discovery.Resource`
        returned by the Google API client library.

    :param spreadsheet_id: Identification of the Google Sheets document
        where all the family registrations have been stored in.


    :return: A list of integers representing all the registrations that
        have been already processed so far.


    :raise ValueError: if the Google Sheets has more than one sheet.
    """
    sheet_names = get_sheet_names(spreadsheets_resource, spreadsheet_id)
    if len(sheet_names) > 1:
        raise ValueError(f"the output Google spreadsheet must contain one sheet only: {', '.join(sheet_names)}")

    sheet_name = sheet_names[0]
    rows = read_google_sheet_values(spreadsheets_resource, spreadsheet_id, sheet_name, 'A3:M')
    return [int(''.join([c for c in values[0] if c.isdigit()])) for values in rows if values[0]]


def flatten_list(l):
    """
    Flatten the elements contained in the sub-lists of a list.


    :param l: A list containing sub-lists of elements.


    :return: A list with all the elements flattened from the sub-lists of
        the list `l`.
    """
    return [e for sublist in l for e in sublist]


def get_registration_confirmation_email_attachment_file_path_name(locale, template_path):
    """
    Return the absolute path and name of the file to attach to the
    application confirmation e-mail to be sent to the parent(s) of a
    family.


    :param locale: An object `Locale` that references that language of the
        file to attache to the application confirmation e-mail template.
        If no file corresponds to the specified locale, the functions
        returns the file corresponding to the English language.

    :param template_path: The absolute path of the folder where the
        localized files to attached to a application confirmation e-mail
        are stored in.


    :return: The content of the localized e-mail template.
    """
    attachment_file_path_name = os.path.join(template_path, f'{locale}.jpg')
    if not os.path.exists(attachment_file_path_name):
        attachment_file_path_name = os.path.join(template_path, f'{ENGLISH_LOCALE}.jpg')

    return attachment_file_path_name


def get_email_subject(content):
    """
    Return the subject of the HTML email taken from the title of the HTML
    template.


    :return: the subject of the HTML email template.


    :raise AssertError: If the content of the HTML email template has not
        been read, of if this HTML has no title defined.
    """
    start_offset = content.find('<title>')
    assert start_offset > 0, "The HTML template has no title defined"
    start_offset = content.find('>', start_offset) + 1

    end_offset = content.find('</title>', start_offset)
    assert end_offset > 0, "The HTML template has no title end tag."

    return content[start_offset:end_offset]


def get_google_oauth2_token(
        scopes,
        google_credentials_file_path_name=None,
        google_oauth2_token_file_path_name=None):
    """
    Return the OAuth2 credentials to access Google Sheets API.


    :param scopes: OAuth2 scope information to access Google Sheets.

    :param google_credentials_file_path_name: The absolute path and name
        of the file where the client application secrets are stored in.

    :param google_oauth2_token_file_path_name: The absolute path and name
        of the file where the OAuth2 token is loaded from, if it exists,
        and stored in.


    :return: The OAuth2 credentials.
    """
    if google_credentials_file_path_name is None:
        google_credentials_file_path_name = \
            build_current_directory_path_name(DEFAULT_GOOGLE_CREDENTIALS_FILE_NAME)

    if google_oauth2_token_file_path_name is None:
        google_oauth2_token_file_path_name = \
            build_current_directory_path_name(DEFAULT_GOOGLE_OAUTH2_TOKEN_FILE_NAME)

    oauth2_token = None

    # The OAuth2 token file stores the user's access and refresh tokens, and
    # is created automatically when the authorization flow completes for the
    # first time.
    if os.path.exists(google_oauth2_token_file_path_name):
        with open(google_oauth2_token_file_path_name, 'rb') as fd:
            oauth2_token = pickle.load(fd)

    # If there are no (valid) credentials available, let the user log in.
    if not oauth2_token or not oauth2_token.valid:
        if oauth2_token and oauth2_token.expired and oauth2_token.refresh_token:
            oauth2_token.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(google_credentials_file_path_name, scopes)
            oauth2_token = flow.run_local_server(port=0)

        # Save the credentials for the next run.
        with open(google_oauth2_token_file_path_name, 'wb') as fd:
            pickle.dump(oauth2_token, fd)

    return oauth2_token


def get_grade_name(grade_level):
    """
    Return the name of an education grade.


    :param grade_level: Level of the education grade to return the name.


    :return: Name of the specified education grade.
    """
    for grade_name, grade_level_ in GRADE_NAMES.items():
        if grade_level_ == grade_level:
            return grade_name


def get_registration_confirmation_email_template(locale, template_path):
    """
    Return a localized e-mail template.

    This template corresponds to application confirmation e-mail that is
    sent to the parent(s) of the family.


    :param locale: An object `Locale` that references that language of the
        e-mail template to return.  If no template corresponds to the
        specified locale, the functions returns the e-mail template
        written in English.

    :param template_path: The absolute path of the folder where localized
        e-mail templates are stored in.


    :return: The content of the localized e-mail template.
    """
    template_file_path_name = os.path.join(template_path, f'{locale}.html')
    if not os.path.exists(template_file_path_name):
        template_file_path_name = os.path.join(template_path, f'{ENGLISH_LOCALE}.html')

    with open(template_file_path_name, 'rt') as fd:
        return fd.read()


def get_sheet_names(spreadsheets_resource, spreadsheet_id):
    """
    Return the names of all the sheets of a Google Sheets document.


    :param spreadsheets_resource: An object `googleapiclient.discovery.Resource`
        returned by the Google API client library.

    :param spreadsheet_id: Identification of a Google Sheet document.


    :return: A list of the names of the sheets that this Google Sheets
        document contains.
    """
    spreadsheet_metadata = spreadsheets_resource.get(spreadsheetId=spreadsheet_id).execute()
    sheets = spreadsheet_metadata['sheets']
    return [sheet.get('properties', {})['title'] for sheet in sheets]


def get_sheet_used_row_count(
        spreadsheets_resource,
        spreadsheet_id,
        sheet_name=None):
    """
    Return the number of rows already used in the specified sheet.

    A row is used when at least one of its columns is not empty.


    :param spreadsheets_resource: An object `googleapiclient.discovery.Resource`
        returned by the Google API client library.

    :param spreadsheet_id: Identification of a Google Sheets document.

    :param sheet_name: Name of the sheet to count the number of rows
        already used, or `None` if the Google Sheets contains just one
        sheet.


    :return: The number of rows already used in the specified sheet of a
        Google Sheets document.
    """
    # Determine the name of the sheet, if not passed.
    if sheet_name is None:
        sheet_names = get_sheet_names(spreadsheets_resource, spreadsheet_id)
        if len(sheet_names) > 1:
            raise ValueError(f"the argument 'sheet_name' has not been passed while the Google Sheets contain several sheets: {', '.join(sheet_names)}")
        sheet_name = sheet_names[0]

    # @patch: Reading each individual row of a sheet is time consuming as
    #    this sends one request per row to fetch.  For optimization purpose,
    #    we consider that the first column of each row of a sheet always
    #    contains a value when the row is not empty.  Therefore, we fetch
    #    the range composed of the first column of the sheet.  Google Sheets
    #    return the values of the first columns of every non-empty row.  The
    #    number of rows returned corresponds to the index of the last row
    #    that is not empty.
    row_index = len(read_google_sheet_values(
        spreadsheets_resource,
        spreadsheet_id,
        sheet_name,
        'A1:A')) + 1

    # Read the column values of each consecutive row until a row is empty.
    while True:
        values = read_google_sheet_values(
            spreadsheets_resource,
            spreadsheet_id,
            sheet_name,
            f'A{row_index}:M{row_index}')
        if not values:
            break
        row_index += 1

    return row_index - 1


def insert_registration_to_master_list(
        registration,
        spreadsheets_resource,
        spreadsheet_id,
        sheet_range):
    """
    Insert the information of a application to the school bus
    transportation service to the master list.


    :param registration: An object `Registration`.

    :param spreadsheets_resource: An object `googleapiclient.discovery.Resource`
        returned by the Google API client library.

    :param spreadsheet_id: Identification of the Google Sheets document
        used as the master list of the registrations of all the families
        to the school bus transportation service.

    :param sheet_range: Range (a row) in the master list sheet where to
        start inserting the information of this application.


    :raise ValueError: If the Google Sheets document contains more than
        one sheet.
    """
    # Find the name of the unique sheet contained in this spreadsheet.
    sheet_names = get_sheet_names(spreadsheets_resource, spreadsheet_id)
    if len(sheet_names) > 1:
        raise ValueError(f"the output Google spreadsheet must contain one sheet only: {', '.join(sheet_names)}")
    sheet_name = sheet_names[0]

    spreadsheets_resource.values().update(
        spreadsheetId=spreadsheet_id,
        range=f'{sheet_name}!{sheet_range}',
        valueInputOption='RAW',
        body={
            'values': build_registration_rows(registration)
        }) \
        .execute()


def load_registrations_from_csv_file(csv_file_path_name, locale):
    """
    Load the information of the family registrations from a CSV file.


    :param csv_file_path_name: Absolute path and name of the CSV file.

    :param locale: An object `Locale` corresponding to the language of the
        online form from which the application information have been
        exported to the CSV file.


    :return: A list of objects `Registration`.
    """
    values = read_csv_file_values(csv_file_path_name)
    return [
        Registration.from_row(row, locale)
        for row in values
        if row
    ]


def load_registrations_from_google_sheet(spreadsheet_id, spreadsheets_resource, oauth2_token):
    """
    Load the information of the family registrations from the all sheets
    of a Google Sheets document.


    :param spreadsheet_id: Identification of the Google Sheets document that
        contains the sheet where the responses to the localized application
        forms have been stored in.

    :param spreadsheets_resource: An object `googleapiclient.discovery.Resource`
        returned by the Google API client library.

    :param oauth2_token: A valid OAuth2 token that allows access to the
        specified Google Sheets document.


    :return: A list of objects `Registration`.


    :raise ValueError: If a sheet is not named after a locale.
    """
    # Retrieve the names of all the sheets contained in the specified Google
    # Sheets document. These sheets MUST have been named after a locale that
    # references the language in which the related application form was
    # written in.
    sheet_names = get_sheet_names(spreadsheets_resource, spreadsheet_id)

    # Load the registrations from the sheets contained in the specified
    # Google Sheets document.
    registrations = []

    for sheet_name in sheet_names:
        logging.info(f'Fetching registrations from the sheet "{sheet_name}"...')

        # Retrieve the locale associated to this sheet.
        try:
            locale = Locale(sheet_name)
        except Locale.MalformedLocaleException:
            raise ValueError(f"the Google sheet name {sheet_name} doesn't correspond to a locale")

        registrations.extend([
            Registration.from_row(row, locale)
            for row in [
                values
                for values in read_google_sheet_values(
                    spreadsheets_resource, spreadsheet_id, sheet_name, 'A2:AF')
                if values
            ]
        ])

    return registrations


def prettify_registration_id(id_):
    """
    Convert a application ID to human-readable string.


    :param id_: Identification of a application.


    :return: A string version of the application ID decomposed in groups
        of 3 digits separated with a dash character.
    """
    segments = []
    while id_ > 0:
        segments.append(str(id_ % 1000).zfill(3))
        id_ //= 1000

    return '-'.join(reversed(segments))


def process_registration(
        registration,
        smtp_connection_properties,
        template_path,
        author_name,
        author_email_address,
        spreadsheets_resource,
        spreadsheet_id,
        sheet_range):
    """
    Process a new application.


    :param registration: An object `Registration`.

    :param smtp_connection_properties: Properties to connect to the Simple
        Mail Transfer Protocol (SMTP) server.

    :param template_path: The absolute path of the folder where localized
        e-mail templates and files to attach are stored in.

    :param author_name: Complete name of the originator of the message.

    :param author_email_address: Address of the mailbox to which the author
        of the message suggests that replies be sent.

    :param spreadsheets_resource: An object `googleapiclient.discovery.Resource`
        returned by the Google API client library.

    :param spreadsheet_id: Identification of a Google Sheet document.

    :param sheet_range: Range (a row) in the master list sheet where to
        start inserting the information of this application.
    """
    send_registration_confirmation_email(registration, smtp_connection_properties, template_path, author_name, author_email_address)
    insert_registration_to_master_list(registration, spreadsheets_resource, spreadsheet_id, sheet_range)


def read_csv_file_values(csv_file_path_name, has_header=True):
    """
    Read the values of the rows of a CSV file.


    :param csv_file_path_name: Absolute path and name of the CSV file.

    :param has_header: Indicate whether the very first row of the CSV file
        corresponds to an header and needs to be ignored.


    :return: A list of arrays (lists) of values
    """
    with open(csv_file_path_name) as fd:
        reader = csv.reader(fd)

        # Skip the very first header row.
        if has_header:
            next(reader)

        rows = [values for values in reader]

        return rows


def read_google_sheet_values(
        spreadsheets_resource,
        spreadsheet_id,
        sheet_name,
        sheet_range):
    """
    Return the values of the ranges of the sheet of a Google Sheets document.


    :param spreadsheets_resource: An object `googleapiclient.discovery.Resource`
        returned by the Google API client library.

    :param spreadsheet_id: Identification of a Google Sheet document.

    :param sheet_name: Name of a sheet in this Google Sheet document.

    :param sheet_range: String representation of the range to return
        values.


    :return: A list of a arrays (lists) of values.
    """
    sheet_range_values = spreadsheets_resource.values().get(
        spreadsheetId=spreadsheet_id,
        range=f'{sheet_name}!{sheet_range}').execute()

    range_values = sheet_range_values.get('values', [])

    return range_values


def run(arguments):
    # Get the absolute file path name where the client application secrets
    # (credentials) to access Google Sheets APi are stored in.
    google_credentials_file_path_name = \
        build_current_directory_path_name(DEFAULT_GOOGLE_CREDENTIALS_FILE_NAME) if not arguments.google_credentials_file_path_name \
        else os.path.realpath(os.path.expanduser(arguments.google_credentials_file_path_name))

    # Read the properties to connect to the Simple Mail Transfer Protocol
    # (SMTP).
    smtp_connection_properties = build_smtp_connection_properties(arguments)

    # Get the absolute path of the folder where the e-mail templates and
    # attachment files are stored in.
    email_template_path = \
        os.path.join(os.path.dirname(__file__), DEFAULT_TEMPLATE_RELATIVE_PATH) if not arguments.email_template_path \
        else os.path.realpath(os.path.expanduser(arguments.email_template_path))

    # Get the absolute path and name of a CSV file that contains the
    # information entered by families to register to the school bus
    # transportation service.  This CSV file has been exported from 1 sheet
    # of the Google Sheets that collects the responses from the localized
    # Google Forms (Korean, English, French, Vietnamese).
    #
    # Or get the identification of the Google Sheets itself that contains
    # all the sheets the responses of all the localized Google Forms (this
    # should be the preferred method).
    csv_file_path_name = arguments.csv_file_path_name \
        and os.path.realpath(os.path.expanduser(arguments.csv_file_path_name))

    input_google_spreadsheet_id = arguments.input_google_spreadsheet_id

    if csv_file_path_name and input_google_spreadsheet_id:
        raise ValueError("Either a CSV file or a Google Sheet ID must be passed; not both")

    if not csv_file_path_name and not input_google_spreadsheet_id:
        raise ValueError("a CSV file or a Google spreadsheet ID must be passed")

    # Check whether the script needs to loop for even until the user
    # decides to stop it
    does_loop = arguments.loop and input_google_spreadsheet_id

    # Get the identification of the Google Sheets where the script stores
    # the information from all the application forms submitted by the
    # families.  If the user doesn't specify an identification, the script
    # will print this information to the standard output.
    output_google_spreadsheet_id = arguments.output_google_spreadsheet_id

    # If an access to the input and/or output Google Sheets needs to be
    # performed, retrieve the Oauth2 token that allows access to these
    # documents.
    if input_google_spreadsheet_id or output_google_spreadsheet_id:
        if not google_credentials_file_path_name:
            ValueError('a Google credentials file must be provided')

        oauth2_token = get_google_oauth2_token(
            GOOGLE_SPREADSHEET_SCOPES,
            google_credentials_file_path_name)

        service = googleapiclient.discovery.build('sheets', 'v4', credentials=oauth2_token)
        spreadsheets_resource = service.spreadsheets()

    # Execute the main loop of the application.
    while True:
        try:
            # Load the registrations from the CSV file, if specified.
            if csv_file_path_name:
                if arguments.locale is None:
                    raise ValueError("a locale must be passed")

                registrations = load_registrations_from_csv_file(
                    csv_file_path_name,
                    Locale(arguments.locale))

            # Load the registrations from the input Google Sheets document, if
            # specified.
            elif input_google_spreadsheet_id:
                if not google_credentials_file_path_name:
                    ValueError('a Google credentials file must be provided')

                registrations = load_registrations_from_google_sheet(
                    input_google_spreadsheet_id,
                    spreadsheets_resource,
                    oauth2_token)

            # Process and store the registrations in the master list.
            if output_google_spreadsheet_id:
                # Retrieve the list of the registrations that have been already
                # processed and stored in the master list (the ouput Google Sheets
                # document).
                processed_registration_ids = fetch_processed_registration_ids(
                    spreadsheets_resource,
                    output_google_spreadsheet_id)

                # Determine the list of recent registrations not already processed.
                new_registrations = [
                    registration
                    for registration in registrations
                    if registration.registration_id not in processed_registration_ids
                ]

                if new_registrations:
                    # Determine the number of rows that are currently used in the master
                    # list Google Sheets.  This number doesn't necessarily correspond to
                    # the number of registrations as a application may contain several
                    # children.
                    row_count = get_sheet_used_row_count(
                        spreadsheets_resource,
                        output_google_spreadsheet_id)

                    for registration in new_registrations:
                        process_registration(
                            registration,
                            smtp_connection_properties,
                            email_template_path,
                            'UPMD',
                            'transport@upmd.fr',
                            spreadsheets_resource,
                            output_google_spreadsheet_id,
                            f'A{row_count + 1}')

                        row_count += len(registration.children)

            if not does_loop:
                break

            logging.info("Breathing a little bit...")
            time.sleep(DEFAULT_IDLE_TIME_BETWEEN_CONSECUTIVE_EXECUTION)

        except (googleapiclient.errors.HttpError, socket.timeout):
            traceback.print_exc()
            time.sleep(DEFAULT_IDLE_TIME_BETWEEN_CONSECUTIVE_EXECUTION)

        except KeyboardInterrupt:
            logging.info('Stopping the script...')


def send_registration_confirmation_email(
        registration,
        smtp_connection_properties,
        template_path,
        author_name,
        author_email_address):
    """
    Send a confirmation e-mail to the parents of a family who submitted a
    application to the school bus transportation service.

    The function optimizes the number of e-mail to be sent to the parents,
    by grouping parents by their preferred languages.  If two parents (or
    more) share the same preferred language, the function groups them in
    a same list of recipients which one email, written in this language,
    is sent to.


    :param registration: An object `Registration`.

    :param smtp_connection_properties: Properties to connect to the Simple
        Mail Transfer Protocol (SMTP) server.

    :param template_path: The absolute path of the folder where localized
        e-mail templates and files to attach are stored in.

    :param author_name: Complete name of the originator of the message.

    :param author_email_address: Address of the mailbox to which the author
        of the message suggests that replies be sent.
    """
    # Group the parents by their preferred languages. Well, they are
    # supposed to be only 2 parents, but who knows in the future.
    parents_locale_mapping = collections.defaultdict(list)
    for parent in registration.parents:
        parents_locale_mapping[parent.locale].append(parent)

    for locale, parents in parents_locale_mapping.items():
        email_subject, email_content = \
            build_registration_confirmation_email_content(registration, locale, template_path)

        parent_email_addresses = [parent.email_address for parent in parents]

        logging.info(f'Sending email in "{locale}" to {", ".join(parent_email_addresses)}...')

        instructions_image_file_path_name = os.path.join(template_path, 'instructions.jpg')
        instructions_text_file_path_name = os.path.join(template_path, '20200702 - Paiement ete 2020.pdf')

        email_util.send_email(
            smtp_connection_properties.hostname,
            smtp_connection_properties.username,
            smtp_connection_properties.password,
            author_name,
            author_email_address,
            parent_email_addresses,
            email_subject,
            email_content,
            file_path_names=[
                instructions_image_file_path_name,
                instructions_text_file_path_name
            ],
            port_number=smtp_connection_properties.port_number)
