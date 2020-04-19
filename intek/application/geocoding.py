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

import requests

from majormode.perseus.constant.place import AddressComponentType
from majormode.perseus.model.geolocation import GeoPoint
from majormode.perseus.model.place import Place


GOOGLE_GEOCODING_API_URL = 'https://maps.googleapis.com/maps/api/geocode/json'

GOOGLE_PERSEUS_ADDRESS_COMPONENTS_MAPPING = {
    'street_number': AddressComponentType.house_number,
    'route': AddressComponentType.street_name,
    'administrative_area_level_1': AddressComponentType.city,
    'administrative_area_level_2': AddressComponentType.district,
    'administrative_area_level_3': AddressComponentType.ward,
    'country': AddressComponentType.country
}


class GoogleGeocoder:
    __places_cache = dict()

    @staticmethod
    def __cleanse_place_address(address):
        """
        Cleanse a place's address.


        :param address: A string representing the address of a person or
            business.


        :return: A string which the leading, trailing, and duplicated space
            characters were removed, and all the words lower-cased.
        """
        return ' '.join([w.lower() for w in address.split()])

    def __init__(self, api_key):
        self.__api_key = api_key

    @staticmethod
    def __parse_geometry(data):
        if data:
            location_data = data.get('location')
            location = GeoPoint(location_data.get('lat'), location_data.get('lng'))
            return location

    def __parse_place(self, data):
        address = self.__parse_address_components(data.get('address_components'))

        formatted_address = data.get('formatted_address')
        address[AddressComponentType.geocoded_address] = formatted_address

        location = self.__parse_geometry(data.get('geometry'))

        place = Place(location, address=address)

        return place

    @staticmethod
    def __parse_address_components(data):
        address_components = {}

        if data:
            for address_component in data:
                component_value = address_component.get(
                    'long_name',
                    address_component.get('short_name'))

                for google_component_type in address_component['types']:
                    component_type = GOOGLE_PERSEUS_ADDRESS_COMPONENTS_MAPPING.get(google_component_type)
                    address_components[component_type] = component_value
                    break

        return address_components

    def __convert_address_to_place(self, formatted_address):
        response = requests.get(
            GOOGLE_GEOCODING_API_URL,
            params={
                'address': formatted_address,
                'key': self.__api_key
            })

        if response.status_code != requests.codes.ok:
            response.raise_for_status()

        data = response.json()
        status = data['status']

        if status not in ('OK', 'ZERO_RESULTS'):
            raise Exception(data['error_message'])

        results = data['results']
        return None if len(results) == 0 \
            else self.__parse_place(results[0])

    def geocode(self, formatted_address):
        cleansed_address = self.__cleanse_place_address(formatted_address)

        if cleansed_address in self.__places_cache:
            return self.__places_cache.get(cleansed_address)

        place = self.__convert_address_to_place(cleansed_address)
        self.__places_cache[cleansed_address] = place

        return place
