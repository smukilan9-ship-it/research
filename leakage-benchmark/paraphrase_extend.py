"""Extend the paraphrase map from Stratum A to the two Stratum B datasets it
can honestly cover, and record why the third cannot be covered at all.

WHY MI IS EXCLUDED, AND WHY THAT IS A FINDING RATHER THAN A GAP

  The control renames columns to strings the model cannot have memorised while
  holding the semantic difficulty fixed.  C3 enforces the second half: an alias
  must carry a marker of the same strength as the original, because making a
  positive easier flatters the result exactly as much as making it harder
  distorts it.

  MI's column names are transliterated Russian clinical abbreviations --
  RAZRIV (rupture), LET_IS (lethal outcome), FIBR_JELUD (ventricular
  fibrillation), JELUD_TAH (ventricular tachycardia).  To a model reading the
  header, these are close to opaque: the semantic content that would let you
  judge RAZRIV is not IN the string, it is in domain knowledge attached to the
  string.  Any alias in ordinary English -- `cardiac_rupture_event` -- ADDS the
  information the original withheld, and would make eleven positives easier
  while the run was labelled a robustness control.  There is no English alias
  that is both string-distinct and equally opaque, because opacity here comes
  from the language barrier, not from the naming convention.

  So MI is reported as out of the control's scope with the reason stated,
  rather than mapped badly and counted.  This is a limitation of paraphrase
  controls generally on datasets whose original names are already uninformative
  and is worth one line in the paper's limitations.

STUDENT IS COVERED BUT CARRIES NO POSITIVES

  After the ground-truth audit withdrew G1 and G2 (§4.7), STUDENT has zero
  positive columns.  Its paraphrase cell therefore has undefined precision and
  recall and contributes only false positives.  It is run anyway -- a control
  that only runs where the answer is interesting is not a control -- but it is
  reported as a false-positive-only cell so nobody averages an undefined recall
  into a headline.

CRIME IS THE ONE THAT MATTERS

  Seventeen positives, transparent English names, and it is in the HELD-OUT
  stratum.  The existing control covers only datasets whose ground truth this
  project coded; CRIME's is source-licensed.  If memorisation were doing the
  work, the held-out stratum is where a paraphrase decrement should be largest.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"

# ---------------------------------------------------------------- CRIME
# Rule followed for the positives: the marker is the CRIME TYPE plus, where
# present, the per-capita framing.  Each alias carries a synonym of equal
# strength ("homicide" for "murders") and keeps or drops the rate framing
# exactly as the original does.  None makes the column easier to spot than the
# name it replaces, and none makes it harder.
CRIME = {
    "State": "admin_region_code", "countyCode": "district_id",
    "communityCode": "locality_id", "pop": "resident_total",
    "perHoush": "avg_dwelling_occupancy",
    "pctBlack": "share_afro_descent", "pctWhite": "share_euro_descent",
    "pctAsian": "share_asian_descent", "pctHisp": "share_latino_origin",
    "pct12-21": "share_aged_12_to_21", "pct12-29": "share_aged_12_to_29",
    "pct16-24": "share_aged_16_to_24", "pct65up": "share_aged_65_plus",
    "persUrban": "residents_in_builtup_areas",
    "pctUrban": "share_in_builtup_areas",
    "medIncome": "midpoint_earnings",
    "pctWwage": "share_with_salary_income",
    "pctWfarm": "share_with_agricultural_income",
    "pctWdiv": "share_with_investment_income",
    "pctWsocsec": "share_with_state_pension",
    "pctPubAsst": "share_on_welfare_support",
    "pctRetire": "share_with_retirement_income",
    "medFamIncome": "midpoint_household_earnings",
    "perCapInc": "earnings_per_resident",
    "whitePerCap": "euro_descent_earnings_per_resident",
    "blackPerCap": "afro_descent_earnings_per_resident",
    "NAperCap": "indigenous_earnings_per_resident",
    "asianPerCap": "asian_descent_earnings_per_resident",
    "otherPerCap": "unlisted_group_earnings_per_resident",
    "hispPerCap": "latino_origin_earnings_per_resident",
    "persPoverty": "residents_below_hardship_line",
    "pctPoverty": "share_below_hardship_line",
    "pctLowEdu": "share_limited_schooling",
    "pctNotHSgrad": "share_without_secondary_diploma",
    "pctCollGrad": "share_with_tertiary_degree",
    "pctUnemploy": "share_seeking_work",
    "pctEmploy": "share_in_work",
    "pctEmployMfg": "share_in_factory_work",
    "pctEmployProfServ": "share_in_professional_services",
    "pctOccupManu": "share_in_industrial_roles",
    "pctOccupMgmt": "share_in_executive_roles",
    "pctMaleDivorc": "share_men_separated",
    "pctMaleNevMar": "share_men_never_wed",
    "pctFemDivorc": "share_women_separated",
    "pctAllDivorc": "share_adults_separated",
    "persPerFam": "avg_household_size",
    "pct2Par": "share_dual_guardian_homes",
    "pctKids2Par": "share_minors_dual_guardian",
    "pctKids-4w2Par": "share_under4_dual_guardian",
    "pct12-17w2Par": "share_teens_dual_guardian",
    "pctWorkMom-6": "share_working_mothers_under6",
    "pctWorkMom-18": "share_working_mothers_under18",
    "kidsBornNevrMarr": "minors_born_outside_marriage",
    "pctKidsBornNevrMarr": "share_minors_born_outside_marriage",
    "numForeignBorn": "residents_born_abroad",
    "pctFgnImmig-3": "share_arrived_abroad_last3y",
    "pctFgnImmig-5": "share_arrived_abroad_last5y",
    "pctFgnImmig-8": "share_arrived_abroad_last8y",
    "pctFgnImmig-10": "share_arrived_abroad_last10y",
    "pctImmig-3": "share_newcomers_last3y",
    "pctImmig-5": "share_newcomers_last5y",
    "pctImmig-8": "share_newcomers_last8y",
    "pctImmig-10": "share_newcomers_last10y",
    "pctSpeakOnlyEng": "share_monolingual_english",
    "pctNotSpeakEng": "share_no_english",
    "pctLargHousFam": "share_large_families",
    "pctLargHous": "share_large_dwellings",
    "persPerOccupHous": "occupants_per_tenanted_dwelling",
    "persPerOwnOccup": "occupants_per_owned_dwelling",
    "persPerRenterOccup": "occupants_per_leased_dwelling",
    "pctPersOwnOccup": "share_residents_in_owned_dwelling",
    "pctPopDenseHous": "share_in_crowded_dwellings",
    "pctSmallHousUnits": "share_compact_dwellings",
    "medNumBedrm": "midpoint_sleeping_rooms",
    "houseVacant": "unoccupied_dwellings",
    "pctHousOccup": "share_dwellings_tenanted",
    "pctHousOwnerOccup": "share_dwellings_owner_lived",
    "pctVacantBoarded": "share_unoccupied_sealed",
    "pctVacant6up": "share_unoccupied_over6mo",
    "medYrHousBuilt": "midpoint_construction_year",
    "pctHousWOphone": "share_dwellings_no_telephone",
    "pctHousWOplumb": "share_dwellings_no_plumbing",
    "ownHousLowQ": "owned_value_lower_quartile",
    "ownHousMed": "owned_value_midpoint",
    "ownHousUperQ": "owned_value_upper_quartile",
    "ownHousQrange": "owned_value_quartile_spread",
    "rentLowQ": "lease_price_lower_quartile",
    "rentMed": "lease_price_midpoint",
    "rentUpperQ": "lease_price_upper_quartile",
    "rentQrange": "lease_price_quartile_spread",
    "medGrossRent": "midpoint_total_lease_cost",
    "medRentpctHousInc": "midpoint_lease_share_of_earnings",
    "medOwnCostpct": "midpoint_ownership_share_of_earnings",
    "medOwnCostPctWO": "midpoint_ownership_share_no_mortgage",
    "persEmergShelt": "residents_in_emergency_housing",
    "persHomeless": "residents_without_shelter",
    "pctForeignBorn": "share_born_abroad",
    "pctBornStateResid": "share_born_in_region",
    "pctSameHouse-5": "share_same_dwelling_5y",
    "pctSameCounty-5": "share_same_district_5y",
    "pctSameState-5": "share_same_region_5y",
    "numPolice": "sworn_officers",
    "policePerPop": "sworn_officers_per_resident",
    "policeField": "officers_on_patrol_duty",
    "policeFieldPerPop": "patrol_officers_per_resident",
    "policeCalls": "dispatch_requests",
    "policCallPerPop": "dispatch_requests_per_resident",
    "policCallPerOffic": "dispatch_requests_per_officer",
    "policePerPop2": "sworn_officers_per_resident_alt",
    "racialMatch": "force_community_ethnic_alignment",
    "pctPolicWhite": "share_officers_euro_descent",
    "pctPolicBlack": "share_officers_afro_descent",
    "pctPolicHisp": "share_officers_latino_origin",
    "pctPolicAsian": "share_officers_asian_descent",
    "pctPolicMinority": "share_officers_minority_group",
    "officDrugUnits": "narcotics_squad_officers",
    "numDiffDrugsSeiz": "distinct_substances_confiscated",
    "policAveOT": "mean_officer_overtime",
    "landArea": "territory_size",
    "popDensity": "residents_per_area",
    "pctUsePubTrans": "share_using_transit",
    "policCarsAvail": "patrol_vehicles_available",
    "policOperBudget": "force_running_costs",
    "pctPolicPatrol": "share_officers_assigned_patrol",
    "gangUnit": "organised_crime_squad_present",
    "pctOfficDrugUnit": "share_officers_narcotics_squad",
    "policBudgetPerPop": "force_running_costs_per_resident",
    # ---- the seventeen positives.  Marker strength preserved exactly.
    "murders": "homicide_count",
    "murdPerPop": "homicide_rate_per_resident",
    "rapes": "sexual_assault_count",
    "rapesPerPop": "sexual_assault_rate_per_resident",
    "robberies": "mugging_count",
    "robbbPerPop": "mugging_rate_per_resident",
    "assaults": "battery_count",
    "assaultPerPop": "battery_rate_per_resident",
    "burglaries": "housebreaking_count",
    "burglPerPop": "housebreaking_rate_per_resident",
    "larcenies": "theft_count",
    "larcPerPop": "theft_rate_per_resident",
    "autoTheft": "vehicle_theft_count",
    "autoTheftPerPop": "vehicle_theft_rate_per_resident",
    "arsons": "deliberate_fire_count",
    "arsonsPerPop": "deliberate_fire_rate_per_resident",
    "nonViolPerPop": "nonaggressive_offence_rate_per_resident",
}
CRIME_META = dict(dataset="MUNICIPAL_SAFETY_SURVEY",
                  target="aggressive_offence_rate_per_resident",
                  prediction_point=("from the 1990 census and 1990 policing "
                                    "survey, before the 1995 offence figures "
                                    "are published"))

# ---------------------------------------------------------------- STUDENT
STUDENT = {
    "school": "institution_code", "sex": "gender", "age": "years_old",
    "address": "residence_setting", "famsize": "household_headcount_band",
    "Pstatus": "guardian_cohabitation", "Medu": "mother_schooling_level",
    "Fedu": "father_schooling_level", "Mjob": "mother_occupation",
    "Fjob": "father_occupation", "reason": "enrolment_motive",
    "guardian": "primary_carer", "traveltime": "commute_duration_band",
    "studytime": "weekly_revision_band", "failures": "prior_retakes",
    "schoolsup": "institution_tutoring", "famsup": "household_tutoring",
    "paid": "private_tuition", "activities": "clubs_participation",
    "nursery": "attended_preschool", "higher": "intends_university",
    "internet": "home_connectivity", "romantic": "partnered",
    "famrel": "household_relations_score", "freetime": "leisure_hours_score",
    "goout": "socialising_score", "Dalc": "weekday_drinking_score",
    "Walc": "weekend_drinking_score", "health": "wellbeing_score",
    "absences": "sessions_missed",
    "G1": "term1_mark", "G2": "term2_mark",
}
STUDENT_META = dict(dataset="SECONDARY_SCHOOL_COHORT",
                    target="term3_final_mark",
                    prediction_point=("before the third-period final grade is "
                                      "issued"))


def main():
    p = HERE + "paraphrase.json"
    m = json.load(open(p))
    for name, cols, meta in (("CRIME", CRIME, CRIME_META),
                             ("STUDENT", STUDENT, STUDENT_META)):
        m[name] = dict(columns=cols, **meta)
    m.setdefault("_doc", "")
    m["_out_of_scope"] = {
        "MI": ("Original column names are transliterated Russian clinical "
               "abbreviations (RAZRIV, LET_IS, FIBR_JELUD). Any string-distinct "
               "English alias ADDS semantic information the original withheld, "
               "which violates C3 in the direction that makes positives easier. "
               "No equally-opaque distinct alias exists, so MI is outside the "
               "control's scope rather than mapped and counted.")
    }
    json.dump(m, open(p, "w"), indent=1)
    print(f"wrote {p}: CRIME {len(CRIME)} cols, STUDENT {len(STUDENT)} cols")


if __name__ == "__main__":
    main()
