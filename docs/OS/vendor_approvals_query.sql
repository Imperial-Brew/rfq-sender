-- vendor_approvals_query.sql
--
-- Extracts approved vendor history from M2M JODRTG.
-- "Approved" = vendor has at least one completed outside-operation PO
-- for a given FPRO_ID in our process_master.json.
--
-- Run this in SSMS against the M2M database.
-- Export results as CSV and save to docs/OS/vendor_approvals_raw.csv
-- then run scripts/bootstrap_vendor_master.py to build vendor_master.json.

SELECT
    LTRIM(RTRIM(fpro_id))   AS fpro_id,
    LTRIM(RTRIM(fvendno))   AS fvendno,
    COUNT(DISTINCT fjobno)  AS job_count,
    MAX(fddue_date)         AS last_used
FROM JODRTG
WHERE LTRIM(RTRIM(fpro_id)) IN (
    -- Primary FPRO_IDs
    'SUB-B02', 'SUB-B06', 'SUB-B15', 'SUB-B16',
    'SUB-C00', 'SUB-C05', 'SUB-C06', 'SUB-C07', 'SUB-C09', 'SUB-C10',
    'SUB-C11', 'SUB-C12', 'SUB-C14', 'SUB-C22', 'SUB-C27', 'SUB-C32',
    'SUB-C33', 'SUB-C38', 'SUB-C48', 'SUB-C49', 'SUB-C50', 'SUB-C51',
    'SUB-C52', 'SUB-C55', 'SUB-C56', 'SUB-C57', 'SUB-C59', 'SUB-C63',
    'SUB-C67', 'SUB-C75', 'SUB-F01', 'SUB-F12', 'SUB-F30', 'SUB-F39',
    'SUB-F74', 'SUB-G36', 'SUB-G37', 'SUB-G64', 'SUB-H00', 'SUB-H04',
    -- Legacy FPRO_IDs (duplicate workcenter entries, kept for historical vendor data)
    'SUB-A77', 'SUB-C19'
)
  AND LTRIM(RTRIM(fvendno)) <> ''
GROUP BY
    LTRIM(RTRIM(fpro_id)),
    LTRIM(RTRIM(fvendno))
ORDER BY
    fpro_id,
    job_count DESC
