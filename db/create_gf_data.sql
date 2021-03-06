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
UPDATE child SET grade_level = 1 WHERE grade_level IS NULL;
SELECT gf_set_parents_password();
\copy (SELECT * FROM gf_export_upmd_database()) TO ./tmp/upmd_database_YYYYMMDD.csv WITH HEADER CSV;
