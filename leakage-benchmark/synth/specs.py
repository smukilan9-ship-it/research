"""Table specifications.

SIZING, FROM THE REAL CORPUS

  Stratum A is 40 leaking columns in 306 -- 13%.  Matching that matters: the
  precision denominator is the legitimate columns, so a synthetic table that is
  half leaks makes precision trivially easy and the comparison meaningless.

  20 tables x ~45 columns = ~900 columns, 6 leaks each = 120 positives, 13.3%.
  Two per mechanism per table gives 40 per mechanism, which PREREG.md fixes as
  the floor.  20 clusters also exceeds the real corpus's 12, so the bootstrap
  is not weaker than the result being compared against.

WHY EACH MECHANISM APPEARS TWICE, LOUD AND FAINT

  The first generator made every leak strongly correlated with the target and
  every legitimate column weak.  B3 -- a bare correlation threshold -- scored
  1.000, so the tables were solvable without reading a single column name and
  the run would have been void under PREREG.md section 6.

  The real corpus is not separable that way, and section 24 pins why:

      TITANIC.sex                     |r| 0.529   legitimate
      LC.recoveries                   |r| 0.340   LEAK
      LC.collection_recovery_fee      |r| 0.205   LEAK
      TITANIC.body                    |r| 0.014   LEAK

  Leaks span 0.014 to 0.340 while a legitimate column reaches 0.529.  The
  distributions OVERLAP, which is exactly why B3 tops out at 0.630.  So each
  table carries a loud and a faint instance of every mechanism, and several
  legitimate columns are more predictive than the faint leaks:

      `_rate` on a CONSEQUENCE column is the share of positives it is
      populated for -- 0.80 is an expedite fee, 0.05 is TITANIC's `body`.
      `sep` on a TIMING column is the post-hoc signal's separation.
      the number on a legit_predictive column is its NOISE: 0.30 is a
      strongly predictive legitimate feature, 2.10 is nearly noise.

LEGITIMATE COLUMN FAMILIES

  Real wide tables are not 40 unrelated names; they are families -- SUPPORT2's
  physiology panel, CRIME's per-capita block.  Families are more realistic and
  avoid inventing 800 unique names by hand.
"""

def fam(prefix, parts, noise=1.5):
    return {f"{prefix}{p}": noise for p in parts}


Q = ["_q1", "_q2", "_q3", "_q4"]
PCT = ["_p50", "_p90", "_p99"]

TABLES = [
    dict(
        salt=1, name="WAREHOUSE_FULFILMENT", target="order_late",
        prediction_point="when the order is released to the warehouse floor, "
                         "before picking begins",
        reason=["pick_sla_breach_flag", "carrier_cutoff_missed_flag"],
        reason_thresh=[1.15, 1.35],
        consequence={"expedite_fee_usd": (12.0, 240.0, 0.80),
                     "service_credit_usd": (5.0, 90.0, 0.05)},
        timing={"final_transit_hours": (1.6, 1.0),
                "delivery_scan_delta_h": (0.30, 1.0)},
        legit_predictive={
            "order_line_count": 0.30, "pallet_weight_kg": 0.45,
            "origin_dock_backlog": 1.30, "pick_path_metres": 1.60,
            "replen_shortfall_units": 2.10,
            **fam("outbound_volume", Q), **fam("dock_dwell_min", PCT)},
        legit_noise_cols=["customer_region_code", "sku_family_id",
                          "order_channel_code", "packaging_class",
                          "carrier_account_id", "shift_code", "aisle_zone",
                          "label_printer_id", "tote_type", "route_wave_id",
                          "promo_units_q1", "promo_units_q2", "promo_units_q3",
                          "promo_units_q4", "returns_prior_q1",
                          "returns_prior_q2", "returns_prior_q3",
                          "cube_utilisation_p50", "cube_utilisation_p90"],
    ),
    dict(
        salt=2, name="WATER_MAIN_INTEGRITY", target="main_break_1yr",
        prediction_point="at the start of the fiscal year, before any break is "
                         "recorded on the segment",
        reason=["corrosion_index_flag", "pressure_transient_flag"],
        reason_thresh=[1.25, 1.40],
        consequence={"emergency_repair_cost_usd": (800.0, 26000.0, 0.75),
                     "boil_notice_hours": (2.0, 96.0, 0.06)},
        timing={"post_year_flow_anomaly": (1.5, 1.0),
                "valve_exercise_delta": (0.26, 1.0)},
        legit_predictive={
            "pipe_age_years": 0.30, "diameter_mm": 0.45,
            "prior_breaks_5yr": 1.30, "soil_resistivity_ohm_m": 1.60,
            "cover_depth_m": 2.10,
            **fam("night_flow", Q), **fam("pressure_bar", PCT)},
        legit_noise_cols=["zone_id", "material_code", "survey_crew_id",
                          "asset_class", "joint_type", "hydrant_count",
                          "gis_confidence", "lining_code", "district_id",
                          "contract_lot", "rainfall_mm_q1", "rainfall_mm_q2",
                          "rainfall_mm_q3", "rainfall_mm_q4",
                          "traffic_load_index_q1", "traffic_load_index_q2",
                          "traffic_load_index_q3", "temp_c_p50", "temp_c_p90"],
    ),
    dict(
        salt=3, name="COMPONENT_REMOVAL", target="unscheduled_removal",
        prediction_point="at the start of the maintenance interval, before the "
                         "component is pulled from the aircraft",
        reason=["vibration_exceed_flag", "oil_debris_flag"],
        reason_thresh=[1.20, 1.45],
        consequence={"aog_hours": (1.0, 72.0, 0.85),
                     "replacement_part_cost_usd": (900.0, 41000.0, 0.04)},
        timing={"teardown_finding_score": (1.7, 1.0),
                "shop_visit_delta_days": (0.34, 1.0)},
        legit_predictive={
            "cycles_since_overhaul": 0.30, "hours_since_inspection": 0.45,
            "fleet_avg_egt_margin": 1.30, "bleed_valve_cycles": 1.60,
            "start_count_since_shop": 2.10,
            **fam("egt_margin", Q), **fam("n2_vib", PCT)},
        legit_noise_cols=["station_code", "tail_suffix", "vendor_id",
                          "part_series", "config_mod_level", "lease_flag",
                          "ata_chapter", "crew_base", "manual_rev",
                          "storage_class", "oil_consumption_q1",
                          "oil_consumption_q2", "oil_consumption_q3",
                          "oil_consumption_q4", "sector_length_hr_q1",
                          "sector_length_hr_q2", "sector_length_hr_q3",
                          "ambient_temp_p50", "ambient_temp_p90"],
    ),
]

for t in TABLES:
    t["_n_leak"] = len(t["reason"]) + len(t["consequence"]) + len(t["timing"])
    t["_n_cols"] = (t["_n_leak"] + len(t["legit_predictive"])
                    + len(t["legit_noise_cols"]))
