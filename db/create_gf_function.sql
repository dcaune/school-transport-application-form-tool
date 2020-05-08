/**
 * Copyright (C) 2020 Majormode.  All rights reserved.
 *
 * This software is the confidential and proprietary information of
 * Majormode or one of its subsidiaries.  You shall not disclose this
 * confidential information and shall use it only in accordance with the
 * terms of the license agreement or other applicable agreement you
 * entered into with Majormode.
 *
 * MAJORMODE MAKES NO REPRESENTATIONS OR WARRANTIES ABOUT THE SUITABILITY
 * OF THE SOFTWARE, EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
 * TO THE IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
 * PURPOSE, OR NON-INFRINGEMENT.  MAJORMODE SHALL NOT BE LIABLE FOR ANY
 * LOSSES OR DAMAGES SUFFERED BY LICENSEE AS A RESULT OF USING, MODIFYING
 * OR DISTRIBUTING THIS SOFTWARE OR ITS DERIVATIVES.
 */

/**
 * Add a parent's contact information.
 *
 *
 * @param account_id: Identification of the account of a parent.
 *
 * @param p_property_name: Name of a contact information, which can be
 *     one of a set of pre-defined strings such as:
 *
 *     * `EMAIL`: e-mail address.
 *
 *     * `PHONE`: phone number in E.164 numbering plan, an ITU-T
 *       recommendation which defines the international public
 *       telecommunication numbering plan used in the Public Switched
 *       Telephone Network (PSTN).
 *
 *     * `WEBSITE`: Uniform Resource Locator (URL) of a Web site.
 *
 * @param property_value: String representation of the value associated
 *     to this contact information.
 *
 * @param p_is_primary: Indicate whether this contact information is the
 *     primary one for the given property.
 *
 * @param p_is_verified: Indicate whether this contact information has
 *     been verified, whether it has been grabbed from a trusted Social
 *     Networking Service (SNS), or whether through a challenge/response
 *     process.
 */
CREATE OR REPLACE FUNCTION gf_add_contact_information(
    IN p_account_id uuid,
    IN p_property_name text,
    IN p_property_value text,
    IN p_is_primary boolean = true,
    IN p_is_verified boolean = true)
  RETURNS void
  VOLATILE
  LANGUAGE PLPGSQL
AS $$
DECLARE
  v_account_id uuid;
BEGIN
  IF NOT EXISTS (
    SELECT
        true
      FROM
        account_contact
      WHERE
        account_id = p_account_id
        AND upper(name) = upper(p_property_name)
        AND lower(value) = lower(p_property_value))
  THEN
    INSERT INTO account_contact(
        account_id,
        name,
        value,
        is_primary,
        is_verified)
      VALUES
        (p_account_id,
         upper(p_property_name),
         lower(p_property_value),
         p_is_primary,
         p_is_verified);
  END IF;
END;
$$;

/**
 * Add a component address to the address information of the residence of
 * a parent.
 *
 *
 * @param p_place_id: Identification of the residence of a parent.
 *
 * @param p_account_id: Identification of the account of this parent.
 *
 * @param p_property_name: Name of the component address to add.
 *
 * @param p_property_value: Value associated to this component address.
 *
 * @param p_locale: Locale of the textual information of the address
 *     that is written in.
 */
CREATE OR REPLACE FUNCTION gf_add_home_address_component(
    IN p_place_id uuid,
    IN p_account_id uuid,
    IN p_property_name text,
    IN p_property_value text,
    IN p_locale text = 'eng')
  RETURNS void
  VOLATILE
  LANGUAGE SQL
AS $$
  INSERT INTO place_address(
      place_id,
      account_id,
      locale,
      property_name,
      property_value)
    VALUES
      (p_place_id,
       p_account_id,
       p_locale,
       p_property_name,
       p_property_value);
$$;

/**
 * Return the identification of a child
 *
 *
 * @param p_full_name: Full name by which the child is known.
 *
 * @param p_dob: Date of birth of the child.
 *
 *
 * @return: Identification of the child, if found.
 */
CREATE OR REPLACE FUNCTION gf_find_child(
    IN p_full_name text,
    IN p_dob date)
  RETURNS uuid
  IMMUTABLE
  LANGUAGE SQL
AS $$
  SELECT
      account_id
    FROM
      child
    WHERE
      account_type = 'ghost'
      AND full_name = p_full_name
      AND dob = p_dob;
$$;

/**
 * Return the identification of the residence of a parent.
 *
 *
 * @param p_account_id: Identification of the account of a parent.
 *
 * @param p_location: Geographic location of the residence of this
 *     parent.
 *
 *
 * @return: Identification of the parent's residence if registered to the
 *     platform.
 */
CREATE OR REPLACE FUNCTION gf_find_home(
    IN p_account_id uuid,
    IN p_location geometry)
  RETURNS uuid
  IMMUTABLE
  LANGUAGE SQL
AS $$
  SELECT
      place_id
    FROM
      place
    WHERE
      account_id = p_account_id
      AND location = p_location;
$$;

/**
 * Return the identification of a user providing his contact information.
 *
 * The function checks that the contact information is associated with a
 * user who has the same full name than the one passed to the function.
 * This prevents the case where a second parent registers to the school
 * bus transportation with the same email address than the primary parent,
 * in which case, the function would have returned the identification of
 * the first parent, and it would not have created an account for the
 * second parent. As consequence, this also means that the second parent
 * won't have email address defined, as it is not allowed for two users
 * to be registered to the platform with a same email address.
 *
 *
 * @param p_full_name: Full name by which the parent is known.
 *
 * @param p_property_name: Name of a contact information, which can be
 *     one of a set of pre-defined strings such as:
 *
 *     * `EMAIL`: e-mail address.
 *
 *     * `PHONE`: phone number in E.164 numbering plan, an ITU-T
 *       recommendation which defines the international public
 *       telecommunication numbering plan used in the Public Switched
 *       Telephone Network (PSTN).
 *
 *     * `WEBSITE`: Uniform Resource Locator (URL) of a Web site.
 *
 * @param property_value: String representation of the value associated
 *     to this contact information.
 *
 *
 * @return: Identification of the account that is associated to this
 *     contact information, if any found.
 */
CREATE OR REPLACE FUNCTION gf_find_parent(
    IN p_full_name text,
    IN p_property_name text,
    IN p_property_value text)
  RETURNS uuid
  IMMUTABLE
  LANGUAGE SQL
AS $$
  SELECT
      account_id
    FROM
      account_contact
    INNER JOIN account
      USING (account_id)
    WHERE
      lower(account.full_name) = lower(p_full_name)
      AND account_contact.name = p_property_name
      AND lower(account_contact.value) = lower(p_property_value);
$$;

/**
 * Insert the information of the child.
 *
 *
 * @param p_first_name: Forename (also known as *given name*) of the
 *     child.
 *
 * @param p_last_name: Surname (also known as *family name*) of the
 *     child.
 *
 * @param p_full_name: Full name by which the child is known.
 *
 * @param p_dob: Date of birth of the child.
 *
 * @oaram p_school_id: Identification of the school this child attends.
 *
 * @param p_grade_level: Number of the year the child has reached in the
 *     educational stage of the school he attends.
 *
 * @param p_locale: Language spoken by the child.
 *
 * @param p_is_allowed_to_get_off_school_bus_alone: Indicate whether the
 *     child is authorised to alight from the school bus that brings him
 *     home without the presence of a guardian of him (e.g., legal
 *     guardian or childminder).
 *
 *
 * @return: Identification of the child as registered to the platform.
 */
CREATE OR REPLACE FUNCTION gf_insert_child(
    IN p_first_name text,
    IN p_last_name text,
    IN p_full_name text,
    IN p_dob date,
    IN p_school_id uuid,
    IN p_grade_level smallint,
    IN p_locale text,
    IN p_is_allowed_to_get_off_school_bus_alone boolean)
  RETURNS uuid
  VOLATILE
  LANGUAGE SQL
AS $$
  INSERT INTO child(
      account_type,
      first_name,
      last_name,
      full_name,
      dob,
      school_id,
      grade_level,
      locale,
      get_off_school_bus_alone)
    VALUES
      ('ghost',
       p_first_name,
       p_last_name,
       p_full_name,
       p_dob,
       p_school_id,
       p_grade_level,
       p_locale,
       p_is_allowed_to_get_off_school_bus_alone)
    RETURNING
      account_id;
$$;

/**
 * Insert the information of the residence of a parent.
 *
 *
 * @param p_account_id: Identification of a parent.
 *
 * @param p_location: Geographic location of the residence of this parent.
 *
 * @param p_formatted_address: Human-readable address of the residence
 *     of this parent.
 *
 * @param p_geocoded_address: Human-readable address of the parent's
 *     residence determined by a geocoder from the address given by the
 *     parent.
 *
 * @param locale: locale which the formatted address is written in.
 *
 *
 * @return: Identification of the parent's residence as registered to the
 *     platform.
 */
CREATE OR REPLACE FUNCTION gf_insert_home(
    IN p_account_id uuid,
    IN p_location geometry,
    IN p_formatted_address text,
    IN p_geocoded_address text,
    IN p_locale text = 'eng')
  RETURNS uuid
  VOLATILE
  LANGUAGE SQL
AS $$
  INSERT INTO place(
      account_id,
      location,
      is_location_edited,
      category,
      is_address_edited)
    VALUES
      (p_account_id,
       p_location,
       false,
       'home',
       true)
    RETURNING
      place_id;
$$;


/**
 * Insert the information of a parent.
 *
 *
 * @param p_first_name: Forename (also known as *given name*) of the
 *     parent.
 *
 * @param p_last_name: Surname (also known as *family name*) of the
 *     parent.
 *
 * @param p_full_name: Full name by which the parent is known.
 *
 * @param p_locale: Primary language spoken by the parent.
 *
 *
 * @return: Identification of the parent as registered to the platform.
 */
CREATE OR REPLACE FUNCTION gf_insert_parent(
    IN p_first_name text,
    IN p_last_name text,
    IN p_full_name text,
    IN p_locale text)
  RETURNS uuid
  VOLATILE
  LANGUAGE SQL
AS $$
  INSERT INTO account(
      first_name,
      last_name,
      full_name,
      locale)
    VALUES (
      p_first_name,
      p_last_name,
      p_full_name,
      p_locale)
    RETURNING
      account_id;
$$;

/**
 * Link a parent with a child.
 *
 *
 * @param p_parent_account_id: Identification of the account of a parent.
 *
 * @param p_child_account_id: Identification of the account of the
 *     parent's child.
 *
 * @param p_home_id: Identification of the residence where the parent
 *     puts his child up.
 */
CREATE OR REPLACE FUNCTION gf_link_parent_child(
    IN p_parent_account_id uuid,
    IN p_child_account_id uuid,
    IN p_home_id uuid)
  RETURNS void
  VOLATILE
  LANGUAGE PLPGSQL
AS $$
BEGIN
  IF NOT EXISTS (
    SELECT
        true
      FROM
        guardian_child
      WHERE
        guardian_account_id = p_parent_account_id
        AND child_account_id = p_child_account_id)
  THEN
    INSERT INTO guardian_child(
        guardian_account_id,
        child_account_id,
        role,
        home_id)
      VALUES (
        p_parent_account_id,
        p_child_account_id,
        'legal',
        p_home_id);
  END IF;
END;
$$;

/**
 * Return a 2D point in the World Geodetic System (WGS84) spatial
 * reference systems EPSG:4326.
 *
 *
 * @param p_location_str: A string representation of a 2D coordinates
 *     '(latitude:float, longitude:float)' where:
 *
 *     * `latitude`: Latitude-angular distance, expressed in decimal degrees
 *       (WGS84 datum), measured from the center of the Earth, of a point north
 *       or south of the Equator.
 *
 *     * `longitude`: longitude-angular distance, expressed in decimal degrees
 *       (WGS84 datum), measured from the center of the Earth, of a point east
 *       or west of the Prime Meridian.
 */
CREATE OR REPLACE FUNCTION gf_parse_location_string(
    IN p_location_str text)
  RETURNS geometry
  IMMUTABLE
  LANGUAGE PLPGSQL
AS $$
DECLARE
  v_latitude float;
  v_location geometry;
  v_longitude float;
  v_matches text[];
BEGIN
  -- The version 9.6 of PostgreSQL doesn't support named capturing group
  -- expression. The regular expression below could be later rewritten as
  -- follows when a further version of PosgreSQ will support this feature:
  --
  --     ^[(]\s*(?<latitude>(\d*\.)?\d+)\s*,\s*(?<longitude>(\d*\.)?\d+)\s*[)]$
  v_matches = regexp_matches(p_location_str, '^[(]\s*((\d*\.)?\d+)\s*,\s*((\d*\.)?\d+)\s*[)]$');
  v_latitude = v_matches[1]::float;
  v_longitude = v_matches[3]::float;

  v_location = ST_SetSRID(ST_MakePoint(v_longitude, v_latitude), 4326);

  RETURN v_location;
END;
$$;

/**
 * Registered a child, if not already registered to the platform.
 *
 *
 * @param p_first_name: Forename (also known as *given name*) of the
 *     child.
 *
 * @param p_last_name: Surname (also known as *family name*) of the
 *     child.
 *
 * @param p_full_name: Full name by which the child is known.
 *
 * @param p_dob: Date of birth of the child.
 *
 * @param p_school_id: Identification of the school this child attends.
 *
 * @param p_grade_level: Number of the year the child has reached in the
 *     educational stage of the school he attends.
 *
 * @param p_minimal_age_for_getting_off_school_bus_alone: Minimal age of
 *     a child to be allowed to get off a school bus  without the
 *     presence of a guardian of him (e.g., legal guardian or childminder).
 *
 * @param p_school_id: Identification of the school this child attends.
 *
 *
 * @param p_locale: Language spoken by the child.
 *
 *
 * @return: Identification of the child as registered to the platform.
 */
CREATE OR REPLACE FUNCTION gf_register_child(
    IN p_first_name text,
    IN p_last_name text,
    IN p_full_name text,
    IN p_dob date,
    IN p_grade_level smallint,
    IN p_locale text = 'fra',
    IN p_minimal_age_for_getting_off_school_bus_alone smallint = 12,
    IN p_school_id uuid = NULL)
  RETURNS uuid
  VOLATILE
  LANGUAGE PLPGSQL
AS $$
DECLARE
  v_account_id uuid;
  v_age_at_school_year_start_date smallint;
  v_is_allowed_to_get_off_school_bus_alone boolean = false;
  v_school_year_start_date date;
BEGIN
  v_account_id = gf_find_child(p_full_name, p_dob);

  IF v_account_id IS NULL THEN
    v_school_year_start_date = (date_part('year', CURRENT_DATE) || '-09-04')::date;
    v_age_at_school_year_start_date = extract(year from age(v_school_year_start_date, p_dob));
    v_is_allowed_to_get_off_school_bus_alone =
        v_age_at_school_year_start_date > p_minimal_age_for_getting_off_school_bus_alone;

    v_account_id = gf_insert_child(
        p_first_name,
        p_last_name,
        p_full_name,
        p_dob,
        p_school_id,
        p_grade_level,
        p_locale,
        v_is_allowed_to_get_off_school_bus_alone);
  ELSE
    RAISE NOTICE '[WARNING] Child % already registered!', p_full_name;
  END IF;

  RETURN v_account_id;
END;
$$;

 /**
 * Register the residence of a parent where he puts his child up, if not
 * already registered.
 *
 *
 * @param p_account_id: Identification of the account of a parent.
 *
 * @param p_location: Geographic location of the residence of this parent.
 *
 * @param p_formatted_address: Human-readable address of the residence
 *     of this parent.
 *
 * @param p_geocoded_address: Human-readable address of the parent's
 *     residence determined by a geocoder from the address given by the
 *     parent.
 *
 * @param locale: locale which the formatted address is written in.
 *
 *
 * @return: Identification of the parent's residence as registered to the
 *     platform.
 */
CREATE OR REPLACE FUNCTION gf_register_home(
    IN p_account_id uuid,
    IN p_location geometry,
    IN p_formatted_address text,
    IN p_geocoded_address text,
    IN p_locale text = 'eng')
  RETURNS uuid
  VOLATILE
  LANGUAGE PLPGSQL
AS $$
DECLARE
  v_place_id uuid;
BEGIN
  v_place_id = gf_find_home(p_account_id, p_location);

  IF v_place_id IS NULL THEN
    v_place_id = gf_insert_home(
        p_account_id,
        p_location,
        p_formatted_address,
        p_geocoded_address);

    PERFORM gf_add_home_address_component(
        v_place_id,
        p_account_id,
        'formatted_address',
        p_formatted_address);

    IF p_geocoded_address IS NOT NULL THEN
      PERFORM gf_add_home_address_component(
          v_place_id,
          p_account_id,
          'geocoded_address',
          p_geocoded_address);
    END IF;
  END IF;

  RETURN v_place_id;
END;
$$;

/**
 * Register a parent if not already registered to the platform.
 *
 *
 * @param p_first_name: Forename (also known as *given name*) of the
 *     parent.
 *
 * @param p_last_name: Surname (also known as *family name*) of the
 *     parent.
 *
 * @param p_full_name: Full name by which the parent is known.
 *
 * @param p_locale: Primary language spoken by the parent.
 *
 * @param p_email_address: E-mail address of the parent.
 *
 * @param p_phone_number: Mobile phome number of the parent
 *
 *
 * @return: Identification of the parent as registered to the platform.
 */
CREATE OR REPLACE FUNCTION gf_register_parent(
    IN p_first_name text,
    IN p_last_name text,
    IN p_full_name text,
    IN p_locale text,
    IN p_email_address text,
    IN p_phone_number text)
  RETURNS uuid
  VOLATILE
  LANGUAGE PLPGSQL
AS $$
DECLARE
  v_account_id uuid;
BEGIN
  v_account_id = gf_find_parent(p_full_name, 'EMAIL', p_email_address);

  IF v_account_id IS NULL THEN
    v_account_id = gf_insert_parent(p_first_name, p_last_name, p_full_name, p_locale);

    IF p_email_address IS NOT NULL THEN
      BEGIN
        PERFORM gf_add_contact_information(v_account_id, 'EMAIL', p_email_address);
      EXCEPTION
        WHEN unique_violation THEN
          RAISE INFO '[WARNING] Email % already used (%)', p_email_address, p_full_name;
      END;
    END IF;

    IF p_phone_number IS NOT NULL THEN
      BEGIN
        PERFORM gf_add_contact_information(v_account_id, 'PHONE', p_phone_number);
      EXCEPTION
        WHEN unique_violation THEN
          RAISE INFO '[WARNING] Phone % already used (%)', p_phone_number, p_full_name;
      END;
    END IF;
  END IF;

  RETURN v_account_id;
END;
$$;


/**
 * Process family applications to school bus transportation service.
 *
 * The function reads family applications in sequence from the table
 * `gf_registration`.
 */
CREATE OR REPLACE FUNCTION gf_main()
  RETURNS smallint
  VOLATILE
  LANGUAGE PLPGSQL
AS $$
DECLARE
  v_record record;
  v_record_count smallint = 0;

  v_registration_id text = NULL;

  v_child_account_id uuid;

  v_parent1_account_id uuid = NULL;
  v_parent1_home_id uuid = NULL;
  v_parent1_home_location geometry;
  v_parent2_account_id uuid = NULL;
  v_parent2_home_id uuid = NULL;
  v_parent2_home_location geometry;
BEGIN
  FOR v_record IN
    SELECT
        *
      FROM
        gf_registration
  LOOP
    -- If this record corresponds to the application of a new family, clear
    -- the previous information cached into local variables.
    IF v_record.registration_id IS NOT NULL THEN
      v_parent1_account_id = NULL;
      v_parent1_home_id  = NULL;
      v_parent1_home_location = NULL;
      v_parent2_account_id = NULL;
      v_parent2_home_id = NULL;
      v_parent2_home_location = NULL;
    END IF;

    -- Retrieve the registration identification of the family that registers
    -- this child to the school bus transportation service.  Reuse the
    -- previous registration identification for children declared after the
    -- first registered child of this family.
    v_registration_id = COALESCE(v_record.registration_id, v_registration_id);
	  RAISE NOTICE '[%] % %', v_registration_id, v_record.child_first_name, v_record.child_last_name;

    -- Register this child if not already done.
    v_child_account_id = gf_register_child(
        v_record.child_first_name,
        v_record.child_last_name,
        v_record.child_full_name,
        v_record.child_dob,
        v_record.grade_level);

    -- Register the first parent when processing the record of the first
    -- registered child of a family.
    IF v_record.parent1_full_name IS NOT NULL THEN
      -- Register the first parent.
      v_parent1_account_id = gf_register_parent(
          v_record.parent1_first_name,
          v_record.parent1_last_name,
          v_record.parent1_full_name,
          v_record.parent1_locale,
          v_record.parent1_email_address,
          v_record.parent1_phone_number);

      IF v_record.parent1_home_location IS NOT NULL THEN
        v_parent1_home_location = gf_parse_location_string(v_record.parent1_home_location);
        v_parent1_home_id = gf_register_home(
            v_parent1_account_id,
            v_parent1_home_location,
            v_record.parent1_home_formatted_address,
            v_record.parent1_home_geocoded_address);
      END IF;
    END IF;

    PERFORM gf_link_parent_child(v_parent1_account_id, v_child_account_id, v_parent1_home_id);

    -- Register the second parent, if any defined, when processing the record
    -- of the first registered child of a family.
    IF v_record.parent2_full_name IS NOT NULL THEN
      -- Register the second parent.
      v_parent2_account_id = gf_register_parent(
          v_record.parent2_first_name,
          v_record.parent2_last_name,
          v_record.parent2_full_name,
          v_record.parent2_locale,
          v_record.parent2_email_address,
          v_record.parent2_phone_number);

      IF v_record.parent2_home_location IS NULL THEN
        v_parent2_home_id = v_parent1_home_id;
      ELSE
        v_parent2_home_location = gf_parse_location_string(v_record.parent2_home_location);

        IF v_parent2_home_location = v_parent1_home_location THEN
          v_parent2_home_id = v_parent1_home_id;
        ELSE
          v_parent2_home_id = gf_register_home(
              v_parent2_account_id,
              v_parent2_home_location,
              v_record.parent2_home_formatted_address,
              v_record.parent2_home_geocoded_address);
        END IF;
      END IF;
    END IF;

    IF v_parent2_account_id IS NOT NULL THEN
      PERFORM gf_link_parent_child(v_parent2_account_id, v_child_account_id, v_parent2_home_id);
    END IF;

	  v_record_count = v_record_count + 1;
  END LOOP;

  RETURN v_record_count;
END;
$$;
