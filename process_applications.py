#!/usr/bin/env python
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

import argparse
import logging
import sys

from intek.application import etl


# Default format to use by the logger.
DEFAULT_LOGGING_FORMATTER = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

# Default port number of the Simple Mail Transfer Protocol (SMTP) server
# to connect to in order to send confirmation e-mails to the parents who
# subscribe to the school bus transportation service.
DEFAULT_SMTP_PORT = 587


def get_console_handler(logging_formatter=DEFAULT_LOGGING_FORMATTER):
    """
    Return a logging handler that sends logging output to the system's
    standard output.


    :param logging_formatter: An object `Formatter` to set for this handler.


    :return: An instance of the `StreamHandler` class.
    """
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging_formatter)
    return console_handler


def main():
    arguments = parse_arguments()
    setup_logger()
    etl.run(arguments)


def parse_arguments():
    """
    Convert argument strings to objects and assign them as attributes of
    the namespace.


    @return: an instance `argparse.Namespace` corresponding to the
        populated namespace.
    """
    parser = argparse.ArgumentParser(description="School Transport Application Form Tool")

    # Path and name of the Comma-Separated Values (CSV) file that contains
    # the responses to a Google Forms registration document, and the
    # locale which the text of this form is written in.
    parser.add_argument(
        '-f',
        '--file',
        dest='csv_file_path_name',
        metavar='FILE',
        required=False,
        help="specify the path and name of the CSV file containing information about "
             "children and parents")

    parser.add_argument(
        '-l',
        '--locale',
        metavar='LOCALE',
        required=False,
        help="specify the locale (ISO 639-3 code) corresponding to the language of "
             "the application form")

    # Path and name of the file that contains the Google service account
    # key.
    parser.add_argument(
        '-c',
        '--google-credentials',
        dest='google_credentials_file_path_name',
        metavar='FILE',
        required=False,
        default='credentials.json',
        help="absolute path and name of the Google credentials file")

    # Identification of the Google Sheets document where the responses to
    # the Google Forms are stored in.
    parser.add_argument(
        '-i',
        '--input-google-spreadsheet-id',
        metavar='ID',
        required=False,
        help="specify the identification of the Google spreadsheet containing the "
             "responses to the application forms"
    )

    # Identification of the Google Sheets document where the responses to
    # the Google Forms needs to be aggregated in.
    parser.add_argument(
        '-o',
        '--output-google-spreadsheet-id',
        metavar='ID',
        required=False,
        help="specify the identification of the Google spreadsheet to populate "
             "children and parents from the application forms")

    # Settings to geocode the home addresses of parents.
    parser.add_argument(
        '-k',
        '--google-api-key',
        metavar='KEY',
        required=False,
        help="specify the key to use Google Geocoding API")

    parser.add_argument(
        '--no-geocoding',
        action='store_true',
        required=False,
        help="request the script no to geocode parents' home address(es)")

    # Properties to connect to the Simple Mail Transfer Protocol (SMTP)
    # server.
    parser.add_argument(
        '--smtp-hostname',
        required=False,
        help="specify the host name of the machine on which the SMTP server is "
             "running"
    )

    parser.add_argument(
        '--smtp-username',
        required=False,
        help="specify the username/email address to connect to the SMTP server"
    )

    parser.add_argument(
        '--smtp-port',
        required=False,
        type=int,
        default=DEFAULT_SMTP_PORT,
        help="specify the TCP port or the local Unix-domain socket file extension on "
             "which the SMTP server is listening for connections")

    # Path of the folder where the localized HTML e-mail templates are
    # saved in.  These templates are used to generate and send e-mail to
    # the parents depending on their preferred language.
    parser.add_argument(
        '--email-author-name',
        dest='author_name',
        metavar='NAME',
        required=False,
        help="specify the name of the author of the e-mail to send to the parents")

    parser.add_argument(
        '--email-author-address',
        dest='author_email_address',
        metavar='EMAIL',
        required=False,
        help="specify the mailbox to which the author of the e-mail suggests that "
             "replies be sent.")

    parser.add_argument(
        '--email-template-path',
        required=False,
        help="specify the absolute path name of the localized HTML e-mail templates")

    # Settings to request the script not to send e-mail to parents.
    parser.add_argument(
        '--no-email',
        action='store_true',
        required=False,
        help="require the script not to send e-mails to the parents who registered")

    # Settings of the KML file to generate
    parser.add_argument(
        '--no-kml',
        action='store_true',
        required=False,
        help="require the script not to generate a KML file with children's home")

    parser.add_argument(
        '--output-kml-file-path-name',
        metavar='FILE',
        required=False,
        help="absolute path and name of the KML file to build with children' home")

    # Settings to request the script to keep running for ever.
    parser.add_argument(
        '--loop',
        action='store_true',
        required=False,
        help="require the script to loop for ever until the user terminates it with Ctrl-C")

    return parser.parse_args()


def setup_logger(
        logging_formatter=DEFAULT_LOGGING_FORMATTER,
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
        unless a handler's level has been set to a higher severity level
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
