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

-- Remove the first 2 header rows from the CSV file.

DELETE FROM gf_registration;

\copy gf_registration FROM './tmp/registrations.csv' DELIMITER ',' CSV;
SELECT gf_main('836dff6a-bd7b-11e7-b6f1-0008a20c190f');
SELECT gf_set_parents_password();

-- Set parent's account password.
UPDATE
    account
  SET
    password = md5(replace(foo.registration_id, '-', ''))
  FROM (
    SELECT
      account_id,
      registration_id
    FROM
      account_contact
    INNER JOIN (
      SELECT
          registration_id,
          parent1_email_address AS email_address
        FROM
          gf_registration
      UNION
      SELECT
          registration_id,
          parent2_email_address AS email_address
        FROM
          gf_registration) AS foo
      ON (account_contact.value = foo.email_address)
    WHERE
      account_contact.name = 'EMAIL'
  ) AS foo
  WHERE
    account.account_id = foo.account_id;








SELECT SUM(is_signed::int) AS signed, SUM(1-is_signed::int) AS not_signed FROM gf_contract;

SELECT
    '(' || ST_X(location)::text || ', ' || ST_Y(location)::text || ')' AS coordinates,
    (SELECT registration_id FROM gf_contract WHERE primary_account_id = account_id) AS registration_id
  FROM
    place
  INNER JOIN (
    -- Find the location of the families who has signed yet.
    SELECT
        COUNT(*) AS family_count,
        location
      FROM
        gf_contract
      INNER JOIN place
        ON place.account_id = primary_account_id
      WHERE
        NOT is_signed
      GROUP BY
        location
      HAVING
        COUNT(*) > 5
  ) AS contract_location
    USING (location)
  WHERE
    account_id IN (
      SELECT
          primary_account_id
        FROM
          gf_contract
        WHERE
          NOT is_signed)
  ORDER BY
    coordinates,
    registration_id;


