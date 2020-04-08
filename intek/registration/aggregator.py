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
import datetime
import enum
import getpass
import hashlib
import logging
import pickle
import os
import re
import time
import traceback

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from langdetect.lang_detect_exception import LangDetectException
from majormode.perseus.model.smtp import SmtpConnectionProperties
from majormode.perseus.model.locale import DEFAULT_LOCALE
from majormode.perseus.model.locale import Locale
from majormode.perseus.utils import email_util
from majormode.perseus.utils import string_util
import googleapiclient.discovery
import googleapiclient.errors
import langdetect
import unidecode

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

# Fee that the parents need to pay in order to subscribe to the school
# bus transportation service, depending on whether they are willing to
# become members or not of the parents association.
PAYMENT_AMOUNT_UPMD = '100,000'
PAYMENT_AMOUNT_NON_UPMD = '200,000'

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


class Person:
    def __init__(self, last_name, first_name, locale=None):
        """
        Build a new object `Person`


        :param last_name: Surname (also known as *family name*) of the person.
            The last name can be used to alphabetically sort a list of users.

        :param first_name: Forename (also known as *given name*) of the person.
            The first name can be used to alphabetically sort a list of users.

        :param locale: An object `Locale` that refers to the preferred
            language of this person.
        """
        if locale is None:
            locale = DEFAULT_LOCALE

        self.__last_name = self.format_last_name(last_name, locale)
        self.__first_name = self.format_first_name(first_name, locale)
        self.__fullname = self.format_fullname(self.__last_name, self.__first_name, locale)
        self.__locale = locale

    @classmethod
    def format_first_name(cls, first_name, locale):
        """
        Format the first name according to the locale.

        All the name components of French, English, and Vietnamese first names
        are capitalized, while the rest of the words are lower cased.  Korean
        personal names are not transformed.


        :param first_name: Forename (also known as *given name*) of the person.
            The first name can be used to alphabetically sort a list of users.

        :param locale: An object `Locale` that supposedly refers to the name
            of this person.


        :return: The formatted first name of the person.
        """
        first_name_ = cls.normalize_name(first_name)
        return ' '.join([
            component.lower().capitalize()
            for component in first_name_.split()
        ])

    @staticmethod
    def format_fullname(last_name, first_name, locale):
        """
        Format the full name according to the locale.

        For French and English personal names, first name comes first, and
        last name comes last.  While for Vietnamese and Korean, this order is
        reversed.


        :param last_name: Surname (also known as *family name*) of the person.
            The last name can be used to alphabetically sort a list of users.

        :param first_name: Forename (also known as *given name*) of the person.
            The first name can be used to alphabetically sort a list of users.

        :param locale: An object `Locale` that supposedly refers to the name
            of this person.


        :return: The formatted full name of the person.
        """
        return f'{first_name} {last_name}' if locale in (FRENCH_LOCALE, ENGLISH_LOCALE) \
            else f'{last_name} {first_name}'

    @classmethod
    def format_last_name(cls, last_name, locale):
        """
        Format the last name according to the locale.

        French, English, and Vietnamese personal names are converted to upper
        case.  However, Korean personal names are not upper cased.


        :param last_name: Surname (also known as *family name*) of the person.
            The last name can be used to alphabetically sort a list of users.

        :param locale: An object `Locale` that supposedly refers to the name
            of this person.


        :return: The formatted last name of the person.
        """
        last_name_ = cls.normalize_name(last_name)
        return last_name_.upper()

    @staticmethod
    def normalize_name(name):
        """
        Remove any punctuation and duplicated space characters.


        :param name: A surname, a forename, or a full name of a person.


        :return: The given name that has been cleansed from useless characters.
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

    @property
    def locale(self):
        """
         Return the supposedly preferred language of this person.

        :return: An object `Locale`.
        """
        return self.__locale


class Child(Person):
    def __init__(self, last_name, first_name, dob, grade_name, locale):
        """
        Build a new object `Child`.


        :param last_name: Surname (also known as *family name*) of the child.
            The last name can be used to alphabetically sort a list of users.

        :param first_name: Forename (also known as *given name*) of the child.
            The first name can be used to alphabetically sort a list of users.

        :param dob: Date of birth of this child.

        :param grade_name: Name of the educational stage this child has
            reached.

        :param locale: The locale of the online form that the family used to
            register to the school bus transportation service.  By default,
            this locale is supposed to be the preferred language of the child.
        """
        super().__init__(last_name, first_name, locale)
        self.__dob = datetime.datetime.strptime(dob, '%m/%d/%Y')
        self.__grade_level = self.parse_grade_level(grade_name)

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
    def __init__(
            self,
            last_name,
            first_name,
            email_address,
            phone_number,
            home_address,
            locale,
            is_secondary_parent):
        """
        Build a new object `Parent`.


        :param last_name: Surname (also known as *family name*) of the parent.
            The last name can be used to alphabetically sort a list of users.

        :param first_name: Forename (also known as *given name*) of the parent.
            The first name can be used to alphabetically sort a list of users.

        :param email_address: E-mail address of the user.

        :param phone_number: Mobile phone number of the parent.  This number
            MUST be composed of 10 digits.

        :param home_address: Postal address of the parent's residence.  The
            home address of the secondary parent is optional, supposedly the
            same than the primary parent's home address.

        :param locale: The locale of the online form that the family used to
            register to the school bus transportation service.  By default,
            this locale is supposed to be the preferred language of the parent.

        :param is_secondary_parent: Indicate whether this parent is the
            secondary parent.

            The primary parent is supposed to be the parent who entered the
            information into the registration form. This parent is supposed to
            have selected the online form that corresponds to his preferred
            language.

            On another hand, the secondary parent is supposed to have been
            referred by the primary parent, and because their are mixed family,
            the language of the secondary parent may differ from the language
            of the primary parent. Therefore, the function tries to detect the
            language of this secondary parent.
        """
        if is_secondary_parent:
            # @patch: Secondary parent of a mixed family is often a Vietnamese
            #    person in Vietnam. Also the detection result for Vietnamese
            #    personal names is highly trustable, while the result for other
            #    name in the world is quite hazardous.  Therefore, we handle
            #    Vietnamese personal names only.
            if detect_locale(f'{last_name} {first_name}') == VIETNAMESE_LOCALE:
                locale = VIETNAMESE_LOCALE

        super().__init__(last_name, first_name, locale)
        self.__email_address = self.__format_email_address(email_address)
        self.__phone_number = self.__format_phone_number(phone_number)

        if not home_address:
            if not is_secondary_parent:
                ValueError('the home address of the primary parent must be passed')

        self.__home_address = home_address and self.__cleanse_postal_address(home_address)

    @staticmethod
    def __cleanse_postal_address(home_address):
        """
        Cleanse a home address.


        :param home_address: A string representing the address of a person or
            business.


        :return: A string which the leading, trailing, and duplicated space
            characters were removed.
        """
        return ' '.join(home_address.split())

    @staticmethod
    def __format_email_address(email_address):
        """
        Normalize an email address.


        :param email_address: A string representing an e-mail address
            compliant with RFC 2822.


        :return: The e-mail address removed from leading and trailing space
            characters, and all the letters lower cased.
        """
        email_address_ = email_address.strip().lower()
        if not string_util.is_email_address(email_address_):
            raise ValueError(f"invalid email address {email_address_}")

        return email_address_

    @staticmethod
    def __format_phone_number(phone_number):
        """
        Format a local Vietnamese phone number to its international
        representation.

        The function adds a leading digit `0` if the argument `phone_number`
        is only composed of 9 digits.


        :param phone_number: A local Vietnamese phone number composed of 9 or
            10 digits.


        :return: A string representation of an international phone number,
            starting with `+84.`.


        :raise ValueError: If the argument `phone_number` is not composed of
            9 or 10 digits only.
        """
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


class Registration:
    """
    The registration of a family to the school bus transportation service.
    """
    # Enumeration of the columns (fields) of the sheet containing the
    # registrations of families to the school bus transportation service.
    #
    # This fields MUST be declared in the exact same order than they appear
    # in the CSV or Google Sheets document.
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

    # List of the fields of the sheet containing information about the
    # children of a family who registered to the school bus transportation
    # service.
    #
    # This list MUST contain as many children that a family can possibly
    # to register (4).
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

    # List of the fields of the sheet containing information about the
    # parents of a family who registered to the school bus transportation
    # service.
    #
    # This list MUST contain as many parents that a family can possibly
    # to register (2).
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

    # Number of digits that composes a registration ID.
    REGISTRATION_ID_DEFAULT_DIGIT_NUMBER = 9

    # Subscription fees of the family to register to the school bus
    # transportation service, depending on whether the family becomes a
    # member of the parents association or not.
    #
    # @patch: The script detects whether a family agrees to become a member
    #     or not of the parents association by checking the payment amount
    #     the family is willing to pay as proposed on the registration form.
    #     However because the form is localized in several languages (e.g.,
    #     French and English), the decimal separator for the subscription
    #     fees is different from the responses to a form from another.
    #     Therefore the script compares the group (period) of thousands
    #     only (e.g, 200, 100).
    SUBSCRIPTION_AGREEMENTS = {
        PAYMENT_AMOUNT_UPMD.split(',')[0]: True,
        PAYMENT_AMOUNT_NON_UPMD.split(',')[0]: False
    }

    # Cache of the registration IDs already generated.  This cache is used
    # to detect possible duplicates, and to generate other registration IDs.
    __registration_ids_cache = set()

    def __init__(
            self,
            registration_time,
            children,
            parents,
            is_ape_member,
            locale):
        """
        Build a new object `Registration`.

        :param registration_time: Date and time when the family submitted its
            registration form.

        :param children: A list of objects `Child` of the children registered
            to the school bus transportation service.

        :param parents: A list of objects `Parent` of the primary and possibly
            secondary parents of these children.

        :param is_ape_member: Indicate whether this family is willing to
            become a member of the parents association.

        :param locale: An object `locale` corresponding to the language of the
            registration form that the family has selected.
        """
        self.__registration_id = self.__generate_registration_id(parents)
        self.__registration_time = registration_time
        self.__children = children
        self.__parents = parents
        self.__is_ape_member = is_ape_member
        self.__locale = locale or ENGLISH_LOCALE

    @classmethod
    def __generate_registration_id(
            cls,
            parents,
            digit_number=REGISTRATION_ID_DEFAULT_DIGIT_NUMBER):
        """
        Return an identification for this registration.


        :param parents: A list of objects `Parent`.

        :param digit_number: The number of digits to define the registration
            ID.


        :return: An integer corresponding to the registration ID.
        """
        parent_email_addresses = ', '.join(sorted([parent.email_address for parent in parents]))

        checksum = hashlib.md5(parent_email_addresses.encode()).hexdigest()
        registration_id = int(checksum, 16) % (10 ** digit_number)

        # @todo: Check elsewhere
        # if registration_id in cls.__registration_ids_cache:
        #     raise ValueError(f"the generated registration ID {registration_id} is already used ({parent_email_addresses})")

        cls.__registration_ids_cache.add(registration_id)

        return registration_id

    @classmethod
    def __parse_child(cls, row, fields, locale):
        """
        Return the information of a child registered to the school bus
        transportation service.


        :param row: A list of values corresponding to a row of the sheet
            document containing information about the family that registers to
            the school bus transportation service.

        :param fields: A list of items of the enumeration `RegistrationFields`
            corresponding to the positional fields in the row that refer to
            the information of the child.

        :param locale: The locale of the online form that the family used to
            register to the school bus transportation service.


        :return: An object `Child`.
        """
        first_field_index = fields[0].value - 1
        if len(row[first_field_index].strip()) == 0:
            return None

        return Child(*[row[field.value - 1] for field in fields], locale)

    @classmethod
    def __parse_parent(cls, row, fields, locale, is_secondary_parent=True):
        """
        Return the information of a parent who registered one or more children
        to the school bus transportation service.


        :param row: A list of values corresponding to a row of the sheet
            document containing information about the family that registers to
            the school bus transportation service.

        :param fields: A list of items of the enumeration `RegistrationFields`
            corresponding to the positional fields in the row that refer to
            the information of the parent.

        :param locale: The locale of the online form that the family used to
            register to the school bus transportation service.

        :param is_secondary_parent: Indicate whether this parent is the
            secondary parent.

            The primary parent is supposed to be the parent who entered the
            information into the registration form. This parent is supposed to
            have selected the online form that corresponds to his preferred
            language.

            On another hand, the secondary parent is supposed to have been
            referred by the primary parent, and because their are mixed family,
            the language of the secondary parent may differ from the language
            of the primary parent. Therefore, the function tries to detect the
            language of this secondary parent.


        :return: An object `Parent`.
        """
        first_field_index = fields[0].value - 1
        if len(row[first_field_index].strip()) == 0:
            if is_secondary_parent:
                return None

            raise ValueError('The primary parent has not been defined')

        return Parent(*[row[field.value - 1] for field in fields], locale, is_secondary_parent)

    @classmethod
    def __parse_registration_type(cls, row, field):
        """
        Indicate whether the family agrees to become a member of the APE.


        :param row: A list of values corresponding to a row of the sheet
            document containing information about the family that registers to
            the school bus transportation service.

        :param field: An item of the enumeration `RegistrationFields`
            corresponding to the positional fields in the row that refer to
            the fees that the family is going to pay to register to the the
            school bus transportation service.

            There are two different fees depending on whether a family accepts
            to become or not a member of the parents association.


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
        """
        Return the registration of a family who registered by entering
        information to an online form.


        :param row: A list of values corresponding to a row of the sheet
            document containing information about the family that registers to
            the school bus transportation service.

        :param locale: The locale of the online form that the family used to
            register to the school bus transportation service.


        :return: An object `Registration`.
        """
        if not row:
            return None

        # Google Sheets truncates a row to the last column containing a value
        # not empty.  When a family registers several children, the first row
        # corresponds to the first child, the other rows corresponds to the
        # other children. The first row also contains the information about the
        # parent(s), while this information is not duplicated in the next rows,
        # meaning that these other rows have not the same number of values than
        # the first row. For this case, we extend the row returns by Google
        # Sheet to the expected number of values.
        if len(row) < len(cls.RegistrationFields):
            row.extend([''] * (len(cls.RegistrationFields) - len(row)))

        # Parse the date and time when the family submitted the registration
        # form.
        registration_time = datetime.datetime.strptime(
            row[cls.RegistrationFields.REGISTRATION_TIME.value - 1],
            '%m/%d/%Y %H:%M:%S')

        # List the children registered to the school bus transportation service.
        children = []
        for child_fields in cls.CHILDREN_FIELDS:
            child = cls.__parse_child(row, child_fields, locale)
            if child is not None:
                children.append(child)

        # List the parent(s) who submitted the registration form.
        parents = []
        for i, parent_fields in enumerate(cls.PARENTS_FIELDS):
            parent = cls.__parse_parent(row, parent_fields, locale, is_secondary_parent=i > 0)
            if parent is not None:
                parents.append(parent)

        # Check whether the family is willing to become a member of the parents
        # association.
        is_ape_member = cls.__parse_registration_type(row, cls.RegistrationFields.REGISTRATION_TYPE)

        return Registration(registration_time, children, parents, is_ape_member, locale)

    @property
    def is_ape_member(self):
        return self.__is_ape_member

    @property
    def locale(self):
        return self.__locale

    @property
    def parents(self):
        return self.__parents

    @property
    def registration_id(self):
        return self.__registration_id

    @property
    def registration_time(self):
        return self.__registration_time


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
    Build the localized content of a registration confirmation e-mail to
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
    Build the rows of values of the registration of a family to the school
    bus transportation service.

    There are as many rows as the number of children registered to the
    transportation service.  The first row corresponds to a first child of
    the family, and some other information that is not duplicated over the
    other rows:

    - identification of the registration;
    - date and time when the family submitted its registration;
    - information about the primary parent;
    - information about a possible secondary parent;
    - a flag that indicates whether the family is willing to become or not
      a member of the parents association.


    :param registration: An object `Registration`.


    :return: A list of registration's rows to be inserted in the master
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


def detect_locale(text):
    """
    Detect the language of a text.


    :param text: A human-readable text.


    :return: An instance `Locale` representing the language used to write in
        the specified text.
    """
    try:
        return Locale.from_string(langdetect.detect(text), strict=False)
    except langdetect.lang_detect_exception.LangDetectException:
        return DEFAULT_LOCALE


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
    registration confirmation e-mail to be sent to the parent(s) of a
    family.


    :param locale: An object `Locale` that references that language of the
        file to attache to the registration confirmation e-mail template.
        If no file corresponds to the specified locale, the functions
        returns the file corresponding to the English language.

    :param template_path: The absolute path of the folder where the
        localized files to attached to a registration confirmation e-mail
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

    This template corresponds to registration confirmation e-mail that is
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
    Insert the information of a registration to the school bus
    transportation service to the master list.


    :param registration: An object `Registration`.

    :param spreadsheets_resource: An object `googleapiclient.discovery.Resource`
        returned by the Google API client library.

    :param spreadsheet_id: Identification of the Google Sheets document
        used as the master list of the registrations of all the families
        to the school bus transportation service.

    :param sheet_range: Range (a row) in the master list sheet where to
        start inserting the information of this registration.


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
        online form from which the registration information have been
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
        contains the sheet where the responses to the localized registration
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
    # references the language in which the related registration form was
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
    Convert a registration ID to human-readable string.


    :param id_: Identification of a registration.


    :return: A string version of the registration ID decomposed in groups
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
    Process a new registration.


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
        start inserting the information of this registration.
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
    # the information from all the registration forms submitted by the
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

    # Execute the main loop of the
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
                    # the number of registrations as a registration may contain several
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
                            'transport@intek.fr',
                            spreadsheets_resource,
                            output_google_spreadsheet_id,
                            f'A{row_count + 1}')

                        row_count += len(registration.children)

            if not does_loop:
                break

            logging.info("Breathing a little bit...")
            time.sleep(DEFAULT_IDLE_TIME_BETWEEN_CONSECUTIVE_EXECUTION)

        except googleapiclient.errors.HttpError:
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
    registration to the school bus transportation service.

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
        email_util.send_email(
            smtp_connection_properties.hostname,
            smtp_connection_properties.username,
            smtp_connection_properties.password,
            author_name,
            author_email_address,
            parent_email_addresses,
            email_subject,
            email_content,
            file_path_names=get_registration_confirmation_email_attachment_file_path_name(
                registration.locale,
                template_path),
            port_number=smtp_connection_properties.port_number)
