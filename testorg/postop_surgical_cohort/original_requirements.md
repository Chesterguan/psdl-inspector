# Postoperative Surgical Cohort - Original Requirements

*Captured: 2026-04-09*

## Data Elements

| Domain | Notes |
|--------|-------|
| Clinical Encounters | Primary encounter tracking |
| OR Cases | Surgical case records |
| Labs | Laboratory results |
| Diagnoses | ICD-based diagnosis codes |
| Dialysis (with CRRT) | Includes continuous renal replacement therapy |
| Procedures (ICD + CPT) | Split into ICD procedure codes and CPT codes |
| Mortality / SSDI | Contained by encounters |
| Billing Accounts | Contained by encounters |
| Height / Weight | Contained by encounters |
| Meds | Medication administration/orders |
| Provider Info | Attending/surgical provider details |

## Inclusion Criteria

- Adult patients (>= 18 years old)
- Scheduled surgeries within 2 days OR currently undergoing surgery
- Postoperative hospitalization period
- All patients who will, are, or had surgeries before hospitalization discharge

## Exclusion Criteria

- Comfort-care / palliative-only goals of care documented prior to surgery
- Transferred directly from an outside institution to ICU

## Key Questions

### 1. primary_encounter_id across daily pipeline runs

> Will the daily pipeline for post-op contain the primary_encounter_id?
> This column is valuable for ETL pipelines. Is it able to be used across days?

This is a cross-day encounter linkage question. The primary_encounter_id must
persist as a stable identifier across daily pipeline executions so that
post-op records from day 1, day 2, ... day N all link back to the same
surgical encounter.

## Pipeline Context

This is a **daily batch pipeline** that identifies perioperative patients.
The cohort window is dynamic: a patient enters the cohort when surgery is
scheduled (T-2 days) and exits at hospital discharge.
