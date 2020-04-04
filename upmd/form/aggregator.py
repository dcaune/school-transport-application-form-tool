#!/usr/bin/env python
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

import argparse
import csv
import datetime
import enum
import hashlib
import logging
import pickle
import os
import re
import string
import sys
from builtins import super

import googleapiclient.discovery
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from majormode.perseus.model.locale import Locale
from majormode.perseus.utils import string_util
import unidecode


LOGGING_FORMATTER = logging.Formatter("%(message)s")


ENGLISH_LOCALE = Locale('eng')
FRENCH_LOCALE = Locale('fra')
KOREAN_LOCALE = Locale('kor')


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

# If modifying these scopes, delete the file token.pickle.
GOOGLE_SPREADSHEET_SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']


class Person:
    def __init__(self, last_name, first_name, locale):
        self.__last_name = self.normalize_last_name(last_name, locale)
        self.__first_name = self.normalize_first_name(first_name, locale)
        self.__fullname = self.normalize_fullname(self.__last_name, self.__first_name, locale)

    @classmethod
    def normalize_first_name(cls, first_name, locale):
        """

        :param name:
        :return:
        """
        first_name_ = cls.normalize_name(first_name)
        return first_name_ if locale not in (FRENCH_LOCALE, ENGLISH_LOCALE) \
            else ' '.join([
                component.lower().capitalize()
                for component in first_name_.split()
            ])

    @staticmethod
    def normalize_fullname(last_name, first_name, locale):
        """

        :param last_name:

        :param first_name:

        :param locale:


        :return:
        """
        return f'{first_name} {last_name}' if locale == FRENCH_LOCALE \
            else f'{last_name} {first_name}'

    @classmethod
    def normalize_last_name(cls, last_name, locale):
        """

        :param last_name:

        :param locale: An object `Locale`.


        :return:
        """
        last_name_ = cls.normalize_name(last_name)
        return last_name_ if locale not in (FRENCH_LOCALE, ENGLISH_LOCALE) \
            else last_name_.upper()

    @staticmethod
    def normalize_name(name):
        """

        :param name:
        :return:
        """
        # Replace any punctuation character with space.
        punctuationless_string = re.sub(r'[.,\\/#!$%^&*;:{}=\-_`~()<>"\']', ' ', name)

        # Remove any duplicate space characters.
        return ' '.join(punctuationless_string.split())

    @property
    def first_name(self):
        return self.__first_name

    @property
    def fullname(self):
        return self.__fullname

    @property
    def last_name(self):
        return self.__last_name


class Child(Person):
    def __init__(self, last_name, first_name, dob, grade_name, locale):
        """

        :param last_name:
        :param first_name:
        :param dob:
        :param grade_name:
        :param locale:
        """
        super().__init__(last_name, first_name, locale)

        self.__dob = datetime.datetime.strptime(dob, '%m/%d/%Y')
        self.__grade_level = self.parse_grade_level(grade_name)
        self.__parents = None

    @property
    def dob(self):
        return self.__dob

    @property
    def grade_level(self):
        return self.__grade_level

    @staticmethod
    def parse_grade_level(grade_name):
        """
        Return the education grade level corresponding to the specified name


        :param grade_name: The formatted name of an education grade.


        :return: An integer of the corresponding grade level.
        """
        for grade_name_, grade_level in GRADE_NAMES.items():
            if grade_name_ in grade_name:
                return grade_level


class Parent(Person):
    def __init__(self, last_name, first_name, email_address, phone_number, home_address, locale):
        """

        :param last_name:
        :param first_name:
        :param email_address:
        :param phone_number:
        :param home_address:
        :param locale:
        """
        super().__init__(last_name, first_name, locale)
        self.__email_address = self.__parse_email_address(email_address)
        self.__phone_number = self.__parse_phone_number(phone_number)
        self.__home_address = self.__parse_home_address(home_address)

    @staticmethod
    def __parse_email_address(email_address):
        if not string_util.is_email_address(email_address):
            raise ValueError(f"invalid email address {email_address}")

        return email_address

    @staticmethod
    def __parse_home_address(home_address):
        return ' '.join(home_address.split())

    @staticmethod
    def __parse_phone_number(phone_number):
        if not phone_number.isdigit():
            raise ValueError(f"invalid phone number {phone_number}")

        if len(phone_number) < 9:
            raise ValueError(f"the phone number {phone_number} is missing digits")

        return f'+84.{phone_number.zfill(10)}'

    @property
    def email_address(self):
        return self.__email_address

    @property
    def home_address(self):
        return self.__home_address

    @property
    def phone_number(self):
        return self.__phone_number


class RegistrationForm:
    RegistrationFields = enum.Enum(
        'RegistrationFields',
        """
        REGISTRATION_TIME
        CHILD1_LAST_NAME
        CHILD1_FIRST_NAME
        CHILD1_DOB
        CHILD1_GRADE_NAME
        HAS_CHILD2
        CHILD2_LAST_NAME
        CHILD2_FIRST_NAME
        CHILD2_DOB
        CHILD2_GRADE_NAME
        HAS_CHILD3
        CHILD3_LAST_NAME
        CHILD3_FIRST_NAME
        CHILD3_DOB
        CHILD3_GRADE_NAME
        HAS_CHILD4
        CHILD4_LAST_NAME
        CHILD4_FIRST_NAME
        CHILD4_DOB
        CHILD4_GRADE_NAME
        PARENT1_LAST_NAME
        PARENT1_FIRST_NAME
        PARENT1_EMAIL_ADDRESS
        PARENT1_PHONE_NUMBER
        PARENT1_HOME_ADDRESS
        HAS_PARENT2
        PARENT2_LAST_NAME
        PARENT2_FIRST_NAME
        PARENT2_EMAIL_ADDRESS
        PARENT2_PHONE_NUMBER
        PARENT2_HOME_ADDRESS
        REGISTRATION_TYPE
        """
    )

    CHILDREN_FIELDS = [
        (
            RegistrationFields.CHILD1_LAST_NAME,
            RegistrationFields.CHILD1_FIRST_NAME,
            RegistrationFields.CHILD1_DOB,
            RegistrationFields.CHILD1_GRADE_NAME
        ),
        (
            RegistrationFields.CHILD2_LAST_NAME,
            RegistrationFields.CHILD2_FIRST_NAME,
            RegistrationFields.CHILD2_DOB,
            RegistrationFields.CHILD2_GRADE_NAME),
        (
            RegistrationFields.CHILD3_LAST_NAME,
            RegistrationFields.CHILD3_FIRST_NAME,
            RegistrationFields.CHILD3_DOB,
            RegistrationFields.CHILD3_GRADE_NAME
        ),
        (
            RegistrationFields.CHILD4_LAST_NAME,
            RegistrationFields.CHILD4_FIRST_NAME,
            RegistrationFields.CHILD4_DOB,
            RegistrationFields.CHILD4_GRADE_NAME
        ),
    ]

    PARENTS_FIELDS = [
        (
            RegistrationFields.PARENT1_LAST_NAME,
            RegistrationFields.PARENT1_FIRST_NAME,
            RegistrationFields.PARENT1_EMAIL_ADDRESS,
            RegistrationFields.PARENT1_PHONE_NUMBER,
            RegistrationFields.PARENT1_HOME_ADDRESS
        ),
        (
            RegistrationFields.PARENT2_LAST_NAME,
            RegistrationFields.PARENT2_FIRST_NAME,
            RegistrationFields.PARENT2_EMAIL_ADDRESS,
            RegistrationFields.PARENT2_PHONE_NUMBER,
            RegistrationFields.PARENT2_HOME_ADDRESS
        )
    ]

    #
    REGISTRATION_ID_DEFAULT_DIGIT_NUMBER = 9

    #
    SUBSCRIPTION_AGREEMENTS = {
        '200': False,
        '100': True
    }

    __registration_ids_cache = set()

    def __init__(self, registration_time, children, parents, is_ape_member):
        self.__registration_id = self.__generate_registration_id(parents)
        self.__registration_time = registration_time
        self.__children = children
        self.__parents = parents
        self.__is_ape_member = is_ape_member

    @classmethod
    def __generate_registration_id(cls, parents, digit_number=REGISTRATION_ID_DEFAULT_DIGIT_NUMBER):
        parent_email_addresses = ', '.join(sorted([parent.email_address for parent in parents]))

        checksum = hashlib.md5(parent_email_addresses.encode()).hexdigest()
        registration_id = int(checksum, 16) % (10 ** digit_number)

        if registration_id in cls.__registration_ids_cache:
            raise ValueError(f"the generated registration ID {registration_id} is already used ({parent_email_addresses})")

        cls.__registration_ids_cache.add(registration_id)

        return registration_id

    @classmethod
    def __parse_child(cls, row, fields, locale):
        first_field_index = fields[0].value - 1
        if len(row[first_field_index].strip()) == 0:
            return None

        return Child(*[row[field.value - 1] for field in fields], locale)

    @classmethod
    def __parse_parent(cls, row, fields, locale):
        first_field_index = fields[0].value - 1
        if len(row[first_field_index].strip()) == 0:
            return None

        return Parent(*[row[field.value - 1] for field in fields], locale)

    @classmethod
    def __parse_registration_type(cls, row, field):
        """
        Indicate whether the family agrees to become a member of the APE

        :param row:
        :param field:


        :return: `True` if the family agrees to become a member of the APE;
            `False` otherwise.
        """
        field_index = field.value - 1
        registration_type = row[field_index].strip()

        for keyword, agreed in cls.SUBSCRIPTION_AGREEMENTS.items():
            if keyword in registration_type:
                return agreed
        else:
            return False

    @property
    def children(self):
        return self.__children

    @classmethod
    def from_row(cls, row, locale):
        if not row:
            raise ValueError('empty row')

        if len(row) < len(cls.RegistrationFields):
            row.extend([''] * (len(cls.RegistrationFields) - len(row)))

        registration_time = datetime.datetime.strptime(
            row[cls.RegistrationFields.REGISTRATION_TIME.value - 1],
            '%m/%d/%Y %H:%M:%S')

        children = []
        for child_fields in cls.CHILDREN_FIELDS:
            child = cls.__parse_child(row, child_fields, locale)
            if child is not None:
                children.append(child)

        parents = []
        for parent_fields in cls.PARENTS_FIELDS:
            parent = cls.__parse_parent(row, parent_fields, locale)
            if parent is not None:
                parents.append(parent)

        is_ape_member = cls.__parse_registration_type(row, cls.RegistrationFields.REGISTRATION_TYPE)

        return RegistrationForm(registration_time, children, parents, is_ape_member)

    @property
    def is_ape_member(self):
        return self.__is_ape_member

    @property
    def parents(self):
        return self.__parents

    @property
    def registration_id(self):
        return self.__registration_id

    @property
    def registration_time(self):
        return self.__registration_time


def flatten_list(l):
    """
    Flatten the elements contained in the sub-lists of a list.


    :param l: A list containing sub-lists of elements.


    :return: A list with all the elements flattened from the sub-lists of
        the list `l`.
    """
    return [e for sublist in l for e in sublist]


def get_console_handler(logging_formatter=LOGGING_FORMATTER):
    """
    Return a logging handler that sends logging output to the system's
    standard output.


    :param logging_formatter: An object `Formatter` to set for this handler.


    :return: An instance of the `StreamHandler` class.
    """
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging_formatter)
    return console_handler


def get_google_user_credentials(scopes, google_credentials_file_path_name):
    credentials = None

    # The file token.pickle stores the user's access and refresh tokens, and
    # is created automatically when the authorization flow completes for the
    # first time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            credentials = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(google_credentials_file_path_name, scopes)
            credentials = flow.run_local_server(port=0)

        # Save the credentials for the next run.
        with open('token.pickle', 'wb') as token:
            pickle.dump(credentials, token)

    return credentials


def get_grade_name(grade_level):
    for grade_name, grade_level_ in GRADE_NAMES.items():
        if grade_level_ == grade_level:
            return grade_name


def get_sheet_names(credentials, spreadsheet_id):
    service = googleapiclient.discovery.build('sheets', 'v4', credentials=credentials)
    spreadsheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = spreadsheet_metadata['sheets']
    return [sheet.get('properties', {})['title'] for sheet in sheets]


def main():
    arguments = parse_arguments()

    csv_file_path_name = arguments.csv_file_path_name

    google_credentials_file_path_name = os.path.abspath(
        os.path.expanduser(arguments.google_credentials_file_path_name))
    input_google_spreadsheet_id = arguments.input_google_spreadsheet_id

    if csv_file_path_name:
        # if arguments.locale is None:
        #     raise ValueError("a locale must be passed")
        #
        # locale = Locale(arguments.locale)
        values = read_csv_file_values(csv_file_path_name)

    elif google_credentials_file_path_name and input_google_spreadsheet_id:
        credentials = get_google_user_credentials(
            GOOGLE_SPREADSHEET_SCOPES,
            google_credentials_file_path_name)
        sheet_names = get_sheet_names(credentials, input_google_spreadsheet_id)
        values = flatten_list([
            read_google_sheet_values(credentials, input_google_spreadsheet_id, sheet_name)
            for sheet_name in sheet_names
        ])

    else:
        raise ValueError('a CSV file or a Google spreadsheet ID must be identified')

    registration_forms = [RegistrationForm.from_row(row, Locale('fra')) for row in values if row]

    # registration_forms = parse_csv_file(os.path.abspath(os.path.expanduser(csv_file_path_name)), locale)
    # print_registration_forms(registration_forms)
    generate_registration_csv(registration_forms)




def prettify_id(id_):
    segments = []

    while id_ > 0:
        segments.append(str(id_ % 1000))
        id_ //= 1000

    return '-'.join(segments)


def print_registration_forms(forms):
    for form in forms:
        print(f"===== Registration {prettify_id(form.registration_id)} as {'UPMD' if form.is_ape_member else 'NOT UPMD'} =====")

        print('CHILDREN:')
        for i, child in enumerate(form.children, 1):
            print(f"{i}. {child.fullname}, classe de {get_grade_name(child.grade_level)}")

        print('PARENTS:')
        for i, parent in enumerate(form.parents, 1):
            print(f"{i}. {parent.fullname}, {parent.email_address}, {parent.phone_number}, {parent.home_address}")


def generate_registration_csv(forms):
    writer = csv.writer(sys.stdout, quoting=csv.QUOTE_ALL)

    for form in forms:
        for i, child in enumerate(form.children):
            row = [form.registration_id if i == 0 else '', child.fullname, child.dob, get_grade_name(child.grade_level)]

            for j, fields in enumerate(RegistrationForm.PARENTS_FIELDS):
                if i == 0 and j < len(form.parents):
                    parent = form.parents[j]
                    row += [parent.fullname, parent.email_address, parent.phone_number, parent.home_address]
                else:
                    row += ['' for k in range(len(fields))]

            row.append(('Y' if form.is_ape_member else 'N') if i == 0 else '')

            writer.writerow(row)
            sys.stdin.flush()


def parse_arguments():
    """
    Convert argument strings to objects and assign them as attributes of
    the namespace.


    @return: an instance ``argparse.Namespace`` corresponding to the
        populated namespace.
    """
    parser = argparse.ArgumentParser(description="School Data Importer")

    parser.add_argument(
        '-f',
        '--file',
        dest='csv_file_path_name',
        metavar='FILE',
        required=False,
        help="specify the path and name of the CSV file containing information about children and parents")

    parser.add_argument(
        '-l',
        '--locale',
        dest='locale',
        metavar='LOCALE',
        required=False,
        help="specify the locale (ISO 639-3 code) corresponding to the language of the registration form")

    parser.add_argument(
        '-c',
        '--google-credentials',
        dest='google_credentials_file_path_name',
        metavar='FILE',
        required=False,
        default='credentials.json',
        help="absolute path and name of the Google credentials file")

    parser.add_argument(
        '-i',
        '--input-google-spreadsheet_id',
        dest='input_google_spreadsheet_id',
        metavar='ID',
        required=False,
        help="specify the identification of the Google spreadsheet containing the responses to the registration forms"
    )

    return parser.parse_args()


# def parse_csv_file(csv_file_path_name, locale, has_header=True):
#     """
#     Return the list of children and parents parsed from a CSV file
#
#
#     :param csv_file_path_name: Absolute path and name of a CVS file from
#         the French International School Marguerite Duras.
#
#         This file contains a row per child with the following columns:
#
#         01. Registration Time
#         02. Child 1 Last Name
#         03. Child 1 First Name
#         04. Child 1 Date of Birth
#         05. Child 1 Grade Name
#
#         06. Second Child?
#
#         07. Child 2 Last Name
#         08. Child 2 First Name
#         09. Child 2 Date of Birth
#         10. Child 2 Grade Name
#
#         11. Third Child?
#
#         12. Child 3 Last Name
#         13. Child 3 First Name
#         14. Child 3 Date of Birth
#         15. Child 3 Grade Name
#
#         17. Fourth Child?
#
#         18. Child 4 Last Name
#         19. Child 4 First Name
#         20. Child 4 Date of Birth
#         21. Child 4 Grade Name
#
#         22. Parent 1 Last Name
#         23. Parent 1 First Name
#         24. Parent 1 Email Address
#         25. Parent 1 Phone Number
#         26. Parent 1 Home Address
#
#         27. Second Parent?
#
#         28. Parent 2 Last Name
#         29. Parent 2 First Name
#         30. Parent 2 Email Address
#         31. Parent 2 Phone Number
#         32. Parent 2 Home Address (if different from Parent 1's)
#
#         33. Registration Type
#
#     :param has_header: Indicate whether the very first row of the CSV file
#         corresponds to the header containing a list of field names.
#
#
#     :return: A list of objects `RegistrationForm`.
#     """
#     with open(csv_file_path_name) as fd:
#         reader = csv.reader(fd)
#
#         # Skip the very first header row.
#         if has_header:
#             next(reader)
#
#         return [parse_csv_row(row, locale) for row in reader]
#
#
# def parse_csv_row(row, locale):
#     """
#     Return an object `Child` corresponding to the specified information
#
#
#     :param row: A row of the registration form CSV file.
#
#     :param locale: An object `Locale` representing the language of the
#         registration form.
#
#
#     :return: An object `RegistrationForm`.
#     """
#     return RegistrationForm.from_csv_row(row, locale)


def read_csv_file_values(csv_file_path_name, has_header=True):
    with open(csv_file_path_name) as fd:
        reader = csv.reader(fd)

        # Skip the very first header row.
        if has_header:
            next(reader)

        return [values for values in reader]


def read_google_sheet_values(
        credentials,
        spreadsheet_id,
        sheet_name,
        sheet_range='A2:AF'):
    service = googleapiclient.discovery.build('sheets', 'v4', credentials=credentials)
    spreadsheets_resource = service.spreadsheets()
    sheet_range_values = spreadsheets_resource.values().get(
        spreadsheetId=spreadsheet_id,
        range=f'{sheet_name}!{sheet_range}').execute()
    return sheet_range_values.get('values', [])


def setup_logger(
        logging_formatter=LOGGING_FORMATTER,
        logging_level=logging.INFO,
        logger_name=None):
    """
    Setup a logging handler that sends logging output to the system's
    standard output.


    :param logging_formatter: An object `Formatter` to set for this handler.

    :param logger_name: Name of the logger to add the logging handler to.
        If `logger_name` is `None`, the function attaches the logging
        handler to the root logger of the hierarchy.

    :param logging_level: The threshold for the logger to `level`.  Logging
        messages which are less severe than `level` will be ignored;
        logging messages which have severity level or higher will be
        emitted by whichever handler or handlers service this logger,
        unless a handler’s level has been set to a higher severity level
        than `level`.


    :return: An object `Logger`.
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging_level)
    logger.addHandler(get_console_handler(logging_formatter=logging_formatter))
    logger.propagate = False
    return logger


if __name__ == "__main__":
    main()
