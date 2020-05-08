/**
 * Copyright (C) 2020 Majormode.  All rights reserved.
 *
 * This software is the confidential and proprietary information of
 * Majormode or one of its subsidiaries.  You shall not disclose this
 * confidential information and shall use it only accordance with the
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

CREATE TABLE gf_registration (
  registration_id text NULL,
  registration_time timestamp NULL,

  child_first_name text NOT NULL,
  child_last_name text NOT NULL,
  child_full_name text NOT NULL,
  child_dob date NOT NULL,
  grade_level smallint NULL,

  parent1_first_name text NULL,
  parent1_last_name text NULL,
  parent1_full_name text NULL,
  parent1_locale text NULL,
  parent1_email_address text NULL,
  parent1_phone_number text NULL,
  parent1_home_formatted_address text NULL,
  parent1_home_geocoded_address text NULL,
  parent1_home_location text NULL,

  parent2_first_name text NULL,
  parent2_last_name text NULL,
  parent2_full_name text NULL,
  parent2_locale text NULL,
  parent2_email_address text NULL,
  parent2_phone_number text NULL,
  parent2_home_formatted_address text NULL,
  parent2_home_geocoded_address text NULL,
  parent2_home_location text NULL
);
