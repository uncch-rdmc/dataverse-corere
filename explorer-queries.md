# Queries

These queries are for use inside the django-sql-explorer plugin

## Manuscript Report All
Provides a list of all the Manuscripts, with columns detailing each Submission and corresponding Curation/Verification info. For reporting to publications.

```
select pub_id as "Manuscript Number", m_status, pub_name as "Manuscript Ttitle", contents_restricted as "OpenData",  
	sub_dates[1] as "Submission Initial Date", ver_dates[1] as "Verification Initial Date", cur_statuses[1] as "Curation Initial Result", ver_statuses[1] as "Verification Initial Result",
    sub_dates[2] as "Submission 2 Date", ver_dates[2] as "Verification 2 Date", cur_statuses[2] as "Curation 2 Result", ver_statuses[2] as "Verification 2 Result",
	sub_dates[3] as "Submission 3 Date", ver_dates[3] as "Verification 3 Date", cur_statuses[3] as "Curation 3 Result", ver_statuses[3] as "Verification 3 Result",
	sub_dates[4] as "Submission 4 Date", ver_dates[4] as "Verification 4 Date", cur_statuses[4] as "Curation 4 Result", ver_statuses[4] as "Verification 4 Result",
	sub_dates[5] as "Submission 5 Date", ver_dates[5] as "Verification 5 Date", cur_statuses[5] as "Curation 5 Result", ver_statuses[5] as "Verification 5 Result",
	sub_dates[6] as "Submission 6 Date", ver_dates[6] as "Verification 6 Date", cur_statuses[6] as "Curation 6 Result", ver_statuses[6] as "Verification 6 Result",
	sub_dates[7] as "Submission 7 Date", ver_dates[7] as "Verification 7 Date", cur_statuses[7] as "Curation 7 Result", ver_statuses[7] as "Verification 7 Result",
	sub_dates[8] as "Submission 8 Date", ver_dates[8] as "Verification 8 Date", cur_statuses[8] as "Curation 8 Result", ver_statuses[8] as "Verification 8 Result",
	sub_dates[9] as "Submission 9 Date", ver_dates[9] as "Verification 9 Date", cur_statuses[9] as "Curation 9 Result", ver_statuses[9] as "Verification 9 Result",
	sub_dates[10] as "Submission 10 Date", ver_dates[10] as "Verification 10 Date", cur_statuses[10] as "Curation 10 Result", ver_statuses[10] as "Verification 10 Result",
    resubmits
from (
  select m.id, INITCAP(REPLACE(m._status, '_', ' ')) as m_status, m.pub_name, m.pub_id, m.contents_restricted, 
      array_agg(s.updated_at) as sub_dates,
  	  array_agg(c.updated_at) as cur_dates,
  	  array_agg(INITCAP(REPLACE(c._status, '_', ' '))) as cur_statuses,
      array_agg(v.updated_at) as ver_dates,
  	  array_agg(INITCAP(REPLACE(v._status, '_', ' '))) as ver_statuses,
  	  max(s.version_id) as resubmits
  	  --array_agg(s.version_id) as sub_numbers
  from main_manuscript m
  left join main_submission s on m.id=s.manuscript_id
  LEFT JOIN main_curation c ON c.submission_id=s.id
  LEFT JOIN main_verification v ON v.submission_id=s.id
  group by m.id, m.pub_name, m.pub_id, m.contents_restricted
) as r2
order by id
```
