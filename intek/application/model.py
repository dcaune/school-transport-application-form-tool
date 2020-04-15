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

import datetime
import enum
import hashlib
import re

from langdetect.lang_detect_exception import LangDetectException
from majormode.perseus.model.locale import DEFAULT_LOCALE
from majormode.perseus.model.locale import Locale
from majormode.perseus.utils import string_util
import langdetect


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

# Fee that the parents need to pay in order to subscribe to the school
# bus transportation service, depending on whether they are willing to
# become members or not of the parents association.
PAYMENT_AMOUNT_UPMD = '100,000'
PAYMENT_AMOUNT_NON_UPMD = '200,000'


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
            information into the application form. This parent is supposed to
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
    The application of a family to the school bus transportation service.
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

    # Number of digits that composes a application ID.
    REGISTRATION_ID_DEFAULT_DIGIT_NUMBER = 9

    # Subscription fees of the family to register to the school bus
    # transportation service, depending on whether the family becomes a
    # member of the parents association or not.
    #
    # @patch: The script detects whether a family agrees to become a member
    #     or not of the parents association by checking the payment amount
    #     the family is willing to pay as proposed on the application form.
    #     However because the form is localized in several languages (e.g.,
    #     French and English), the decimal separator for the subscription
    #     fees is different from the responses to a form from another.
    #     Therefore the script compares the group (period) of thousands
    #     only (e.g, 200, 100).
    SUBSCRIPTION_AGREEMENTS = {
        PAYMENT_AMOUNT_UPMD.split(',')[0]: True,
        PAYMENT_AMOUNT_NON_UPMD.split(',')[0]: False
    }

    # Cache of the application IDs already generated.  This cache is used
    # to detect possible duplicates, and to generate other application IDs.
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
            application form.

        :param children: A list of objects `Child` of the children registered
            to the school bus transportation service.

        :param parents: A list of objects `Parent` of the primary and possibly
            secondary parents of these children.

        :param is_ape_member: Indicate whether this family is willing to
            become a member of the parents association.

        :param locale: An object `locale` corresponding to the language of the
            application form that the family has selected.
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
        Return an identification for this application.


        :param parents: A list of objects `Parent`.

        :param digit_number: The number of digits to define the application
            ID.


        :return: An integer corresponding to the application ID.
        """
        parent_email_addresses = ', '.join(sorted([parent.email_address for parent in parents]))

        checksum = hashlib.md5(parent_email_addresses.encode()).hexdigest()
        registration_id = int(checksum, 16) % (10 ** digit_number)

        # @todo: Check elsewhere
        # if registration_id in cls.__registration_ids_cache:
        #     raise ValueError(f"the generated application ID {registration_id} is already used ({parent_email_addresses})")

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
            information into the application form. This parent is supposed to
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
        Return the application of a family who registered by entering
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

        # Parse the date and time when the family submitted the application
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

        # List the parent(s) who submitted the application form.
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
