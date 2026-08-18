"""Independently constructed tables. No shared template.

WHY NOT ONE PARAMETERISED GENERATOR

  The first attempt built every table from one `build(spec)` with different
  names bolted on.  It showed: B3 came out at exactly 0.667 on all three,
  because they were the same table three times.  Twenty of those is one
  finding replicated twenty times, not twenty findings, and the cluster
  bootstrap over "tables" would badly overstate its own precision.

  So each function below is its own data-generating process -- its own row
  semantics, its own labelling story, its own leak mechanics, its own width and
  prevalence.  They share only two things: the primitives in `generate.py`, and
  the CONTRACT that every injected column must be re-derivable from the frame.

THE CONTRACT

  Each builder returns a dict with:
    name, target, prediction_point   what the prompt will say
    df                               the table
    truth                            column -> "REASON"|"CONSEQUENCE"|"TIMING"|None
    checks                           [callable(df) -> list of problem strings]

  `checks` is per-table because the mechanics are per-table.  A CONSEQUENCE
  column in the adjudication table is an appeal record; in the cold-chain table
  it is a disposal ticket.  One generic assertion could not test either
  properly, and a check that cannot fail is not a check.
"""
import numpy as np
import pandas as pd

BASE_SEED = 20260818


def _rng(salt):
    return np.random.default_rng(BASE_SEED + salt)


def _shuffle_cols(df, target, rng):
    """Leak position must not encode the answer."""
    others = [c for c in df.columns if c != target]
    return df[list(rng.permutation(others)) + [target]]



# Real wide tables carry long tails of administrative columns that predict
# nothing.  Six leaks in 34 columns is 18%; the real Stratum A is 40 in 306,
# which is 13%.  The precision denominator is the legitimate columns, so a
# leak-dense table makes precision easy and the comparison soft.
def _filler(cols, truth, rng, n, names):
    for nm in names:
        cols[nm] = rng.integers(0, 8, n)
        truth[nm] = None

# ==========================================================================
# 1. WAREHOUSE_FULFILMENT -- label assigned by an explicit business rule
#    The AI4I shape: a rule fires on indicator columns, so those indicators
#    are REASON by construction.
# ==========================================================================
def warehouse():
    rng = _rng(1)
    n = 5200
    congestion = rng.normal(0, 1, n)          # latent, never observed
    truth, cols = {}, {}

    # rule inputs -> REASON
    sla = ((congestion + rng.normal(0, .4, n)) > 1.05).astype(int)
    cut = ((congestion + rng.normal(0, .6, n)) > 1.45).astype(int)
    cols["pick_sla_breach_flag"] = sla; truth["pick_sla_breach_flag"] = "REASON"
    cols["carrier_cutoff_missed_flag"] = cut; truth["carrier_cutoff_missed_flag"] = "REASON"
    y = ((sla + cut) > 0).astype(int)

    # exists because the order was late
    fee = np.where((y == 1) & (rng.random(n) < .80),
                   rng.uniform(12, 240, n), 0.0)
    cred = np.where((y == 1) & (rng.random(n) < .05),
                    rng.uniform(5, 90, n), 0.0)
    cols["expedite_fee_usd"] = np.round(fee, 2); truth["expedite_fee_usd"] = "CONSEQUENCE"
    cols["service_credit_usd"] = np.round(cred, 2); truth["service_credit_usd"] = "CONSEQUENCE"

    # measured after the order shipped
    cols["final_transit_hours"] = np.round(rng.normal(28 + y * 9, 6, n), 2)
    truth["final_transit_hours"] = "TIMING"
    cols["delivery_scan_delta_h"] = np.round(rng.normal(y * .30, 1, n), 3)
    truth["delivery_scan_delta_h"] = "TIMING"

    for nm, sd in [("order_line_count", .30), ("pallet_weight_kg", .45),
                   ("origin_dock_backlog", 1.3), ("pick_path_metres", 1.6),
                   ("replen_shortfall_units", 2.1)]:
        cols[nm] = np.round(congestion + rng.normal(0, sd, n), 3); truth[nm] = None
    for q in ["_q1", "_q2", "_q3", "_q4"]:
        cols["outbound_volume" + q] = np.round(congestion + rng.normal(0, 1.5, n), 3)
        truth["outbound_volume" + q] = None
    for nm in ["customer_region_code", "sku_family_id", "order_channel_code",
               "packaging_class", "carrier_account_id", "shift_code",
               "aisle_zone", "label_printer_id", "tote_type", "route_wave_id",
               "promo_units_q1", "promo_units_q2", "returns_prior_q1",
               "returns_prior_q2", "cube_utilisation_p50", "dock_dwell_p90",
               "pallet_pattern_id", "hazmat_class", "insert_leaflet_code"]:
        cols[nm] = rng.integers(0, 6, n); truth[nm] = None

    _filler(cols, truth, rng, n,
            ["bill_to_account", "ship_complete_flag", "pack_station_id",
             "wave_priority_code", "conveyor_lane", "audit_sample_flag",
             "pallet_licence_plate", "trailer_door_id", "load_sequence",
             "freight_class_code", "edi_partner_id", "sort_zone_code"])
    df = pd.DataFrame(cols); df["order_late"] = y
    def check(d):
        p = []
        if not np.array_equal(((d.pick_sla_breach_flag + d.carrier_cutoff_missed_flag) > 0)
                              .astype(int).to_numpy(), d.order_late.to_numpy()):
            p.append("rule does not reproduce order_late")
        for c in ["expedite_fee_usd", "service_credit_usd"]:
            if (d.loc[d.order_late == 0, c] != 0).any():
                p.append(f"{c}: populated on an on-time order")
        return p
    return dict(name="WAREHOUSE_FULFILMENT", target="order_late",
                prediction_point="when the order is released to the warehouse "
                                 "floor, before picking begins",
                df=_shuffle_cols(df, "order_late", rng), truth=truth,
                checks=[check])


# ==========================================================================
# 2. COMPONENT_REMOVAL -- time-to-event, label is "event within the interval"
#    Different story: no rule fires.  A latent hazard produces an event time;
#    REASON is what the maintenance controller ACTED ON, which is a noisy read
#    of the hazard, not the label's arithmetic parent.
# ==========================================================================
def component():
    rng = _rng(2)
    n = 3600
    hazard = rng.gamma(2.0, 1.0, n)
    # rate calibrated so the interval catches ~12% of units.  The first value
    # (0.05) put mean time-to-event at ~10 against a 120-unit interval and
    # produced a 97.5% positive rate -- a table where almost every row is an
    # event teaches nothing about precision.
    t_event = rng.exponential(1 / (0.0005 * hazard))
    interval = 120.0
    y = (t_event <= interval).astype(int)
    truth, cols = {}, {}

    # the findings the controller used to raise the removal order
    for nm, k in [("vibration_exceed_flag", .82), ("oil_debris_flag", .55)]:
        v = ((rng.random(n) < np.where(y == 1, k, .05))).astype(int)
        cols[nm] = v; truth[nm] = "REASON"

    aog = np.where((y == 1) & (rng.random(n) < .85), rng.uniform(1, 72, n), 0.0)
    part = np.where((y == 1) & (rng.random(n) < .04), rng.uniform(900, 41000, n), 0.0)
    cols["aog_hours"] = np.round(aog, 2); truth["aog_hours"] = "CONSEQUENCE"
    cols["replacement_part_cost_usd"] = np.round(part, 2)
    truth["replacement_part_cost_usd"] = "CONSEQUENCE"

    cols["teardown_finding_score"] = np.round(rng.normal(y * 1.7, 1, n), 3)
    truth["teardown_finding_score"] = "TIMING"
    cols["shop_visit_delta_days"] = np.round(rng.normal(y * .34, 1, n), 3)
    truth["shop_visit_delta_days"] = "TIMING"

    # a legitimate column MORE predictive than the faint leaks: this is the
    # TITANIC.sex case, and it is what stops a correlation threshold separating
    # the two classes cleanly.  Without it B3 sat on the band's 0.800 edge.
    cols["condition_monitor_index"] = np.round(hazard + rng.normal(0, .25, n), 3)
    truth["condition_monitor_index"] = None
    for nm, sd in [("cycles_since_overhaul", .30), ("hours_since_inspection", .45),
                   ("fleet_avg_egt_margin", 1.3), ("bleed_valve_cycles", 1.6),
                   ("start_count_since_shop", 2.1)]:
        cols[nm] = np.round(hazard + rng.normal(0, sd * 2, n), 3); truth[nm] = None
    for q in ["_q1", "_q2", "_q3", "_q4"]:
        cols["egt_margin" + q] = np.round(hazard + rng.normal(0, 3, n), 3)
        truth["egt_margin" + q] = None
    for nm in ["station_code", "tail_suffix", "vendor_id", "part_series",
               "config_mod_level", "lease_flag", "ata_chapter", "crew_base",
               "manual_rev", "storage_class", "oil_consumption_q1",
               "oil_consumption_q2", "sector_length_hr_q1", "ambient_temp_p50",
               "n2_vib_p90", "shelf_life_code"]:
        cols[nm] = rng.integers(0, 6, n); truth[nm] = None

    _filler(cols, truth, rng, n,
            ["engine_position", "line_station", "task_card_rev", "zone_code",
             "kit_number", "tool_calibration_id", "hangar_bay", "shift_team",
             "log_page_prefix", "eng_order_class", "consumable_lot",
             "torque_spec_rev", "access_panel_code", "inspection_method",
             "planner_group"])
    df = pd.DataFrame(cols); df["unscheduled_removal"] = y
    def check(d):
        p = []
        for c in ["aog_hours", "replacement_part_cost_usd"]:
            if (d.loc[d.unscheduled_removal == 0, c] != 0).any():
                p.append(f"{c}: populated with no removal")
        # REASON here is probabilistic, not arithmetic: assert it is strongly
        # associated but NOT a deterministic parent, which is the honest claim
        for c in ["vibration_exceed_flag", "oil_debris_flag"]:
            if d.loc[d.unscheduled_removal == 0, c].mean() > 0.20:
                p.append(f"{c}: fires too often without the event")
        return p
    return dict(name="COMPONENT_REMOVAL", target="unscheduled_removal",
                prediction_point="at the start of the maintenance interval, "
                                 "before the component is pulled",
                df=_shuffle_cols(df, "unscheduled_removal", rng), truth=truth,
                checks=[check])


# ==========================================================================
# 3. PERMIT_ADJUDICATION -- the label is a HUMAN DECISION
#    REASON here is not a sensor flag: it is the reviewer's own scored
#    criteria, the things the decision was made out of.  Closest real analogue
#    is KOI's false-positive flags.
# ==========================================================================
def permit():
    rng = _rng(3)
    n = 2800
    quality = rng.normal(0, 1, n)
    truth, cols = {}, {}

    setback = np.clip(np.round(3 - quality + rng.normal(0, .5, n)), 0, 5)
    egress = np.clip(np.round(3 - quality + rng.normal(0, .7, n)), 0, 5)
    cols["reviewer_setback_deficiency"] = setback
    truth["reviewer_setback_deficiency"] = "REASON"
    cols["reviewer_egress_deficiency"] = egress
    truth["reviewer_egress_deficiency"] = "REASON"
    # >= 6 is the median of two clipped ~3s, i.e. a coin flip: it gave a 59%
    # rejection rate.  >= 8 puts it near a fifth, which is a plausible
    # rejection rate and leaves a real negative class.
    y = ((setback + egress) >= 8).astype(int)

    appeal = np.where((y == 1) & (rng.random(n) < .62), rng.integers(1, 4, n), 0)
    resub = np.where((y == 1) & (rng.random(n) < .07), rng.integers(1, 3, n), 0)
    cols["appeal_hearings_scheduled"] = appeal
    truth["appeal_hearings_scheduled"] = "CONSEQUENCE"
    cols["resubmission_count"] = resub; truth["resubmission_count"] = "CONSEQUENCE"

    cols["days_to_final_disposition"] = np.round(rng.normal(40 + y * 26, 14, n), 1)
    truth["days_to_final_disposition"] = "TIMING"
    cols["post_decision_correspondence"] = np.round(rng.normal(y * .28, 1, n), 3)
    truth["post_decision_correspondence"] = "TIMING"

    for nm, sd in [("plan_sheet_count", .30), ("prior_approvals_5yr", .5),
                   ("designer_experience_yrs", 1.4), ("parcel_area_m2", 1.9)]:
        cols[nm] = np.round(quality + rng.normal(0, sd, n), 3); truth[nm] = None
    for nm in ["zoning_district", "applicant_type", "intake_clerk_id",
               "fee_schedule_ver", "submission_channel", "ward_id",
               "flood_zone_code", "historic_overlay", "parcel_shape_code",
               "sewer_district", "school_district", "council_district"]:
        cols[nm] = rng.integers(0, 7, n); truth[nm] = None

    _filler(cols, truth, rng, n,
            ["assessor_roll_class", "frontage_class", "utility_provider",
             "curb_cut_code", "tree_ordinance_zone", "survey_vendor",
             "plan_format", "notary_office", "e_filing_ver", "fee_waiver_code",
             "site_access_code", "grading_permit_class", "stormwater_tier",
             "septic_class", "easement_code", "lot_orientation",
             "corner_lot_flag", "alley_access_flag", "sidewalk_class",
             "streetlight_zone", "refuse_route", "recycling_route",
             "snow_route_class", "leaf_collection_zone"])
    df = pd.DataFrame(cols); df["permit_rejected"] = y
    def check(d):
        p = []
        if not np.array_equal(((d.reviewer_setback_deficiency
                                + d.reviewer_egress_deficiency) >= 8)
                              .astype(int).to_numpy(), d.permit_rejected.to_numpy()):
            p.append("scored criteria do not reproduce permit_rejected")
        for c in ["appeal_hearings_scheduled", "resubmission_count"]:
            if (d.loc[d.permit_rejected == 0, c] != 0).any():
                p.append(f"{c}: populated on an approved permit")
        return p
    return dict(name="PERMIT_ADJUDICATION", target="permit_rejected",
                prediction_point="when the application is accepted for review, "
                                 "before any reviewer has scored it",
                df=_shuffle_cols(df, "permit_rejected", rng), truth=truth,
                checks=[check])


BUILDERS = [warehouse, component, permit]


# ==========================================================================
# 4. COLD_CHAIN_SPOILAGE -- sensor panel, and the leak mix is TIMING-heavy
#    A fixed 2/2/2 split across every table would be a template artefact in
#    its own right: a model could learn the shape of the answer rather than
#    read the columns.  Real tables carry whatever mix their process produces,
#    so from here the mix varies and only the CORPUS totals are controlled.
# ==========================================================================
def coldchain():
    rng = _rng(4)
    n = 6400
    stress = rng.gamma(1.6, 1.0, n)                 # cumulative thermal stress
    y = (rng.random(n) < 1 / (1 + np.exp(4.2 - 1.15 * stress))).astype(int)
    truth, cols = {}, {}

    # QA disposition criteria -- what the inspector scored to condemn the load
    dev = np.clip(np.round(stress * .6 + rng.normal(0, .5, n)), 0, 6)
    cols["qa_excursion_severity_score"] = np.where(y == 1, dev, np.minimum(dev, 2))
    truth["qa_excursion_severity_score"] = "REASON"

    cols["qa_hold_code_applied"] = ((stress + rng.normal(0, .5, n)) > 2.4).astype(int)
    truth["qa_hold_code_applied"] = "REASON"

    # three TIMING columns: this table's process generates most of its leakage
    # after the fact, because the loggers are only read on arrival
    cols["logger_download_max_c"] = np.round(rng.normal(4 + y * 3.1, 1.6, n), 2)
    truth["logger_download_max_c"] = "TIMING"
    cols["arrival_pulp_temp_c"] = np.round(rng.normal(3 + y * 1.2, 1.4, n), 2)
    truth["arrival_pulp_temp_c"] = "TIMING"
    cols["post_arrival_hold_hours"] = np.round(rng.normal(y * .33, 1, n), 3)
    truth["post_arrival_hold_hours"] = "TIMING"

    disp = np.where((y == 1) & (rng.random(n) < .72), rng.uniform(50, 900, n), 0.0)
    cols["disposal_ticket_usd"] = np.round(disp, 2)
    truth["disposal_ticket_usd"] = "CONSEQUENCE"

    for nm, sd in [("route_distance_km", .35), ("reefer_setpoint_c", .6),
                   ("door_open_events", 1.4), ("pallet_height_cm", 2.0),
                   ("precool_hours", 1.1)]:
        cols[nm] = np.round(stress + rng.normal(0, sd, n), 3); truth[nm] = None
    for q in ["_q1", "_q2", "_q3", "_q4"]:
        cols["ambient_route_temp" + q] = np.round(stress + rng.normal(0, 2.2, n), 3)
        truth["ambient_route_temp" + q] = None
    _filler(cols, truth, rng, n,
            ["carrier_scac", "reefer_unit_id", "trailer_class", "origin_dc",
             "dest_dc", "commodity_code", "pack_size", "grower_lot",
             "pallet_wrap_type", "seal_number_prefix", "customs_regime",
             "booking_channel", "driver_team_flag", "fuel_card_zone",
             "gate_in_shift", "yard_slot", "appointment_band",
             "load_plan_ver", "temp_probe_model", "calibration_lot",
             "inspection_desk", "claims_office", "insurer_code",
             "invoice_terms", "palletiser_line", "label_stock",
             "case_gtin_prefix", "route_variant", "toll_zone", "depot_region",
             "handling_unit_type", "stack_limit_code"])

    df = pd.DataFrame(cols); df["shipment_spoiled"] = y
    def check(d):
        p = []
        if (d.loc[d.shipment_spoiled == 0, "disposal_ticket_usd"] != 0).any():
            p.append("disposal_ticket_usd: raised on an unspoiled shipment")
        if d.loc[d.shipment_spoiled == 0, "qa_excursion_severity_score"].max() > 2:
            p.append("qa_excursion_severity_score: condemning score without condemnation")
        return p
    return dict(name="COLD_CHAIN_SPOILAGE", target="shipment_spoiled",
                prediction_point="when the load is sealed at the origin dock, "
                                 "before the trailer departs",
                df=_shuffle_cols(df, "shipment_spoiled", rng), truth=truth,
                checks=[check])


# ==========================================================================
# 5. CARD_CHARGEBACK -- heavily imbalanced, and REASON-heavy
#    Low prevalence is its own regime: at 3% a model that flags freely is
#    destroyed on precision, which the ~15% tables do not test.
# ==========================================================================
def chargeback():
    rng = _rng(5)
    n = 9000
    risk = rng.normal(0, 1, n)
    truth, cols = {}, {}

    # three REASON columns: the issuer's own rule scores, which the dispute
    # decision was made out of
    for nm, thr in [("issuer_rule_velocity_score", 2.30),
                    ("issuer_rule_geo_mismatch", 2.55),
                    ("issuer_rule_device_novel", 2.75)]:
        cols[nm] = ((risk + rng.normal(0, .5, n)) > thr).astype(int)
        truth[nm] = "REASON"
    y = ((cols["issuer_rule_velocity_score"] + cols["issuer_rule_geo_mismatch"]
          + cols["issuer_rule_device_novel"]) >= 2).astype(int)

    fee = np.where((y == 1) & (rng.random(n) < .88), rng.uniform(15, 45, n), 0.0)
    cols["chargeback_fee_usd"] = np.round(fee, 2)
    truth["chargeback_fee_usd"] = "CONSEQUENCE"
    rep = np.where((y == 1) & (rng.random(n) < .06), rng.integers(1, 3, n), 0)
    cols["representment_rounds"] = rep; truth["representment_rounds"] = "CONSEQUENCE"

    cols["days_to_dispute_close"] = np.round(rng.normal(y * .29, 1, n), 3)
    truth["days_to_dispute_close"] = "TIMING"

    cols["merchant_fraud_rate_90d"] = np.round(risk + rng.normal(0, .22, n), 3)
    truth["merchant_fraud_rate_90d"] = None
    for nm, sd in [("auth_amount_usd", .32), ("account_tenure_days", .5),
                   ("prior_disputes_12mo", 1.5), ("avg_ticket_usd", 2.0)]:
        cols[nm] = np.round(risk + rng.normal(0, sd, n), 3); truth[nm] = None
    _filler(cols, truth, rng, n,
            ["mcc_code", "acquirer_bin", "entry_mode", "terminal_class",
             "currency_code", "network_token_flag", "issuer_country",
             "merchant_region", "settlement_batch", "processor_id",
             "card_product", "reward_tier", "statement_cycle", "channel_code",
             "risk_model_ver", "decline_reason_prior", "cvv_result_code",
             "avs_result_code", "three_ds_version", "wallet_provider",
             "installment_flag", "recurring_flag", "cross_border_flag",
             "fx_markup_band", "chargeback_office", "case_queue",
             "merchant_tier", "onboarding_vintage", "mid_group", "tid_group",
             "batch_close_hour", "funding_delay_band", "reserve_class"])

    df = pd.DataFrame(cols); df["chargeback_filed"] = y
    def check(d):
        p = []
        r = (d.issuer_rule_velocity_score + d.issuer_rule_geo_mismatch
             + d.issuer_rule_device_novel) >= 2
        if not np.array_equal(r.astype(int).to_numpy(), d.chargeback_filed.to_numpy()):
            p.append("issuer rules do not reproduce chargeback_filed")
        for c in ["chargeback_fee_usd", "representment_rounds"]:
            if (d.loc[d.chargeback_filed == 0, c] != 0).any():
                p.append(f"{c}: populated with no chargeback")
        return p
    return dict(name="CARD_CHARGEBACK", target="chargeback_filed",
                prediction_point="at authorisation, before the transaction "
                                 "settles and before any dispute is raised",
                df=_shuffle_cols(df, "chargeback_filed", rng), truth=truth,
                checks=[check])


BUILDERS = [warehouse, component, permit, coldchain, chargeback]


# ==========================================================================
# 6. DRIVE_RMA -- the label is an APPROVAL DECISION, not a physical event.
#    Chosen deliberately: REASON means "an input used to ASSIGN the label",
#    so a target that is a raw physical failure has no honest REASON column.
#    Here the vendor's triage assigns the approval, and its codes are REASON.
# ==========================================================================
def drive_rma():
    rng = _rng(6)
    n = 12000
    wear = rng.gamma(2.4, 1.0, n)
    truth, cols = {}, {}
    tri = np.clip(np.round(wear * .5 + rng.normal(0, .6, n)), 0, 6)
    cols["vendor_triage_code"] = tri; truth["vendor_triage_code"] = "REASON"
    y = (tri >= 4).astype(int)

    rec = np.where((y == 1) & (rng.random(n) < .55), rng.uniform(2, 40, n), 0.0)
    cols["data_recovery_hours"] = np.round(rec, 2)
    truth["data_recovery_hours"] = "CONSEQUENCE"
    shp = np.where((y == 1) & (rng.random(n) < .04), rng.uniform(20, 90, n), 0.0)
    cols["return_freight_usd"] = np.round(shp, 2)
    truth["return_freight_usd"] = "CONSEQUENCE"

    cols["postmortem_reallocated_sectors"] = np.round(rng.normal(y * 1.4, 1, n), 3)
    truth["postmortem_reallocated_sectors"] = "TIMING"
    cols["days_to_disposition"] = np.round(rng.normal(y * .27, 1, n), 3)
    truth["days_to_disposition"] = "TIMING"

    cols["smart_health_index"] = np.round(wear + rng.normal(0, .28, n), 3)
    truth["smart_health_index"] = None
    for nm, sd in [("power_on_hours", .4), ("load_cycle_count", .7),
                   ("temp_max_c", 1.5), ("spin_retry_count", 2.0)]:
        cols[nm] = np.round(wear + rng.normal(0, sd, n), 3); truth[nm] = None
    _filler(cols, truth, rng, n,
            ["model_family", "firmware_rev", "rack_row", "chassis_slot",
             "purchase_lot", "warranty_tier", "site_code", "fleet_group",
             "controller_type", "raid_level", "capacity_class", "interface_type",
             "vendor_region", "shipment_batch", "asset_tag_prefix",
             "depot_code", "rma_queue", "carrier_account", "packaging_spec",
             "test_bench_id", "operator_shift", "label_printer", "pallet_id",
             "inbound_dock", "qa_sample_flag", "disposition_office",
             "recycler_code", "erase_method", "cert_template", "audit_batch"])
    df = pd.DataFrame(cols); df["rma_approved"] = y
    def check(d):
        p = []
        if not np.array_equal((d.vendor_triage_code >= 4).astype(int).to_numpy(),
                              d.rma_approved.to_numpy()):
            p.append("triage code does not reproduce rma_approved")
        for c in ["data_recovery_hours", "return_freight_usd"]:
            if (d.loc[d.rma_approved == 0, c] != 0).any():
                p.append(f"{c}: populated on a rejected RMA")
        return p
    return dict(name="DRIVE_RMA", target="rma_approved",
                prediction_point="when the drive is pulled and shipped to the "
                                 "vendor, before triage has looked at it",
                df=_shuffle_cols(df, "rma_approved", rng), truth=truth,
                checks=[check])


# ==========================================================================
# 7. TRIAL_WITHDRAWAL -- survival with censoring, and NO consequence column.
#    Not every process leaves a downstream record.  A corpus in which every
#    table carries all three mechanisms teaches the shape of the answer.
# ==========================================================================
def trial_withdrawal():
    rng = _rng(7)
    n = 2100
    burden = rng.normal(0, 1, n)
    # 0.004 put the median exit inside the 180-day window and gave a 52.6%
    # withdrawal rate -- and with the classes balanced every leak correlates
    # maximally, which pushed B3 to 0.889, outside the band.
    t_exit = rng.exponential(1 / (0.0011 * np.exp(0.8 * burden)))
    y = (t_exit <= 180).astype(int)
    truth, cols = {}, {}

    for nm, k in [("coordinator_deviation_code", .70),
                  ("site_retention_concern_flag", .48)]:
        cols[nm] = (rng.random(n) < np.where(y == 1, k, .06)).astype(int)
        truth[nm] = "REASON"

    cols["last_visit_albumin"] = np.round(rng.normal(4.0 - y * .30, .55, n), 2)
    truth["last_visit_albumin"] = "TIMING"
    cols["final_diary_compliance"] = np.round(rng.normal(y * .31, 1, n), 3)
    truth["final_diary_compliance"] = "TIMING"
    cols["unreturned_kit_count"] = np.round(rng.normal(y * 1.05, 1, n), 3)
    truth["unreturned_kit_count"] = "TIMING"

    cols["final_visit_window_slip"] = np.round(rng.normal(y * .22, 1, n), 3)
    truth["final_visit_window_slip"] = "TIMING"

    cols["baseline_symptom_burden"] = np.round(burden + rng.normal(0, .26, n), 3)
    truth["baseline_symptom_burden"] = None
    for nm, sd in [("travel_distance_km", .5), ("prior_trial_count", 1.2),
                   ("comorbidity_index", 1.7), ("age_years", 2.2)]:
        cols[nm] = np.round(burden + rng.normal(0, sd, n), 3); truth[nm] = None
    _filler(cols, truth, rng, n,
            ["site_id", "country_code", "arm_code", "stratum_code",
             "consent_version", "irb_office", "monitor_id", "kit_lot",
             "shipper_code", "lab_vendor", "ecrf_version", "visit_window_code",
             "randomisation_block", "sponsor_region", "protocol_amendment",
             "language_code", "referral_source", "insurance_class",
             "transport_support", "caregiver_flag", "device_model",
             "reminder_channel", "pharmacy_code", "storage_class",
             "temperature_logger", "courier_zone", "scan_centre",
             "imaging_protocol", "read_vendor", "query_queue"])
    df = pd.DataFrame(cols); df["participant_withdrew"] = y
    def check(d):
        p = []
        for c in ["coordinator_deviation_code", "site_retention_concern_flag"]:
            if d.loc[d.participant_withdrew == 0, c].mean() > 0.20:
                p.append(f"{c}: fires too often without a withdrawal")
            if d.loc[d.participant_withdrew == 1, c].mean() < 0.30:
                p.append(f"{c}: barely fires on withdrawals")
        return p
    return dict(name="TRIAL_WITHDRAWAL", target="participant_withdrew",
                prediction_point="at randomisation, before the participant has "
                                 "attended a single study visit",
                df=_shuffle_cols(df, "participant_withdrew", rng), truth=truth,
                checks=[check])


# ==========================================================================
# 8. RESTAURANT_CLOSURE -- ordinal violation points crossing a statutory cut.
# ==========================================================================
def restaurant():
    rng = _rng(8)
    n = 4400
    hygiene = rng.normal(0, 1, n)
    truth, cols = {}, {}
    crit = np.clip(np.round(3.2 - hygiene * 1.4 + rng.normal(0, .8, n)), 0, 12)
    cols["critical_violation_points"] = crit
    truth["critical_violation_points"] = "REASON"
    y = (crit >= 7).astype(int)

    fee = np.where((y == 1) & (rng.random(n) < .78), rng.uniform(150, 600, n), 0.0)
    cols["reinspection_fee_usd"] = np.round(fee, 2)
    truth["reinspection_fee_usd"] = "CONSEQUENCE"
    hrs = np.where((y == 1) & (rng.random(n) < .05), rng.uniform(4, 96, n), 0.0)
    cols["closure_duration_hours"] = np.round(hrs, 2)
    truth["closure_duration_hours"] = "CONSEQUENCE"

    cols["followup_inspection_score"] = np.round(rng.normal(y * 1.3, 1, n), 3)
    truth["followup_inspection_score"] = "TIMING"

    cols["days_to_reinspection"] = np.round(rng.normal(y * .21, 1, n), 3)
    truth["days_to_reinspection"] = "TIMING"

    cols["prior_grade_index"] = np.round(hygiene + rng.normal(0, .24, n), 3)
    truth["prior_grade_index"] = None
    for nm, sd in [("seats_licensed", .55), ("staff_turnover_rate", 1.1),
                   ("years_in_operation", 1.6), ("menu_item_count", 2.3)]:
        cols[nm] = np.round(hygiene + rng.normal(0, sd, n), 3); truth[nm] = None
    _filler(cols, truth, rng, n,
            ["cuisine_code", "ward", "inspector_route", "licence_class",
             "owner_entity_type", "grease_hauler", "pest_contract",
             "water_district", "permit_month", "sanitarian_id", "block_group",
             "frontage_type", "delivery_platform_flag", "alcohol_licence",
             "outdoor_seating", "hood_type", "dishwasher_class",
             "walkin_count", "supplier_group", "pos_vendor", "payroll_vendor",
             "training_provider", "signage_class", "grease_trap_size",
             "recycling_tier", "noise_zone", "parking_class"])
    df = pd.DataFrame(cols); df["closure_ordered"] = y
    def check(d):
        p = []
        if not np.array_equal((d.critical_violation_points >= 7).astype(int).to_numpy(),
                              d.closure_ordered.to_numpy()):
            p.append("violation points do not reproduce closure_ordered")
        for c in ["reinspection_fee_usd", "closure_duration_hours"]:
            if (d.loc[d.closure_ordered == 0, c] != 0).any():
                p.append(f"{c}: charged without a closure")
        return p
    return dict(name="RESTAURANT_CLOSURE", target="closure_ordered",
                prediction_point="when the inspection is scheduled, before the "
                                 "inspector arrives on site",
                df=_shuffle_cols(df, "closure_ordered", rng), truth=truth,
                checks=[check])


# ==========================================================================
# 9. TOWER_OUTAGE -- NO reason column.  The outage is a physical event with no
#    adjudication step, so nothing was "used to assign" it.  Inventing a
#    REASON column here would be inventing the mechanism.
# ==========================================================================
def tower_outage():
    rng = _rng(9)
    n = 5600
    fragility = rng.normal(0, 1, n)
    y = (rng.random(n) < 1 / (1 + np.exp(2.4 - 1.2 * fragility))).astype(int)
    truth, cols = {}, {}

    cred = np.where((y == 1) & (rng.random(n) < .66), rng.uniform(200, 5000, n), 0.0)
    cols["sla_credit_usd"] = np.round(cred, 2); truth["sla_credit_usd"] = "CONSEQUENCE"
    roll = np.where((y == 1) & (rng.random(n) < .07), rng.integers(1, 4, n), 0)
    cols["truck_rolls_dispatched"] = roll
    truth["truck_rolls_dispatched"] = "CONSEQUENCE"

    cols["restoration_minutes"] = np.round(rng.normal(y * 1.6, 1, n), 3)
    truth["restoration_minutes"] = "TIMING"
    cols["postevent_alarm_count"] = np.round(rng.normal(y * .30, 1, n), 3)
    truth["postevent_alarm_count"] = "TIMING"

    cols["generator_runtime_index"] = np.round(fragility + rng.normal(0, .25, n), 3)
    truth["generator_runtime_index"] = None
    for nm, sd in [("battery_age_months", .5), ("feeder_reliability", 1.0),
                   ("lightning_density", 1.6), ("site_elevation_m", 2.2)]:
        cols[nm] = np.round(fragility + rng.normal(0, sd, n), 3); truth[nm] = None
    _filler(cols, truth, rng, n,
            ["market_code", "tower_class", "landlord_type", "backhaul_vendor",
             "power_utility", "access_road_class", "fence_type", "shelter_model",
             "hvac_model", "antenna_vendor", "band_plan", "sector_count",
             "lease_expiry_band", "security_tier", "climb_permit_class",
             "grounding_spec", "cabinet_model", "rectifier_model",
             "fuel_contract", "spares_depot", "noc_queue", "escalation_tier",
             "region_group", "district_code", "crew_base", "permit_zone",
             "zoning_class", "tower_height_band", "guy_wire_flag"])
    df = pd.DataFrame(cols); df["outage_over_4h"] = y
    def check(d):
        p = []
        for c in ["sla_credit_usd", "truck_rolls_dispatched"]:
            if (d.loc[d.outage_over_4h == 0, c] != 0).any():
                p.append(f"{c}: raised with no qualifying outage")
        return p
    return dict(name="TOWER_OUTAGE", target="outage_over_4h",
                prediction_point="at the start of the reporting month, before "
                                 "any outage has occurred at the site",
                df=_shuffle_cols(df, "outage_over_4h", rng), truth=truth,
                checks=[check])


# ==========================================================================
# 10. GEARBOX_REPLACEMENT -- wide table, low prevalence, oil-analysis REASON.
# ==========================================================================
def gearbox():
    rng = _rng(10)
    n = 3000
    degradation = rng.gamma(1.8, 1.0, n)
    truth, cols = {}, {}
    fe = np.clip(np.round(degradation * .8 + rng.normal(0, .7, n)), 0, 10)
    cols["oil_iron_ppm_band"] = fe; truth["oil_iron_ppm_band"] = "REASON"
    cols["endoscopy_pitting_grade"] = np.clip(
        np.round(degradation * .5 + rng.normal(0, .8, n)), 0, 6)
    truth["endoscopy_pitting_grade"] = "REASON"
    y = ((fe >= 5) & (cols["endoscopy_pitting_grade"] >= 2)).astype(int)

    crane = np.where((y == 1) & (rng.random(n) < .90), rng.uniform(18000, 90000, n), 0.0)
    cols["crane_mobilisation_usd"] = np.round(crane, 2)
    truth["crane_mobilisation_usd"] = "CONSEQUENCE"

    cols["post_swap_vibration_rms"] = np.round(rng.normal(y * 1.5, 1, n), 3)
    truth["post_swap_vibration_rms"] = "TIMING"
    cols["downtime_days"] = np.round(rng.normal(y * .28, 1, n), 3)
    truth["downtime_days"] = "TIMING"

    cols["scada_temp_trend"] = np.round(degradation + rng.normal(0, .26, n), 3)
    truth["scada_temp_trend"] = None
    for nm, sd in [("operating_hours", .5), ("capacity_factor", 1.0),
                   ("turbulence_index", 1.5), ("yaw_error_mean", 2.1)]:
        cols[nm] = np.round(degradation + rng.normal(0, sd, n), 3); truth[nm] = None
    _filler(cols, truth, rng, n,
            ["site_id", "turbine_model", "gearbox_vendor", "bearing_lot",
             "lube_brand", "filter_spec", "controller_ver", "park_zone",
             "grid_node", "warranty_class", "service_contract", "crew_region",
             "port_of_entry", "vessel_class", "tower_type", "foundation_type",
             "blade_vendor", "pitch_system", "converter_model",
             "transformer_class", "met_mast_id", "sector_management",
             "curtailment_regime", "noise_mode", "icing_package",
             "lightning_zone", "access_class", "spare_depot", "insurer",
             "commission_quarter", "oem_campaign"])
    df = pd.DataFrame(cols); df["gearbox_replaced"] = y
    def check(d):
        p = []
        r = (d.oil_iron_ppm_band >= 5) & (d.endoscopy_pitting_grade >= 2)
        if not np.array_equal(r.astype(int).to_numpy(), d.gearbox_replaced.to_numpy()):
            p.append("oil/endoscopy rule does not reproduce gearbox_replaced")
        if (d.loc[d.gearbox_replaced == 0, "crane_mobilisation_usd"] != 0).any():
            p.append("crane_mobilisation_usd: billed with no replacement")
        return p
    return dict(name="GEARBOX_REPLACEMENT", target="gearbox_replaced",
                prediction_point="at the annual service planning review, before "
                                 "any borescope or oil sample is taken",
                df=_shuffle_cols(df, "gearbox_replaced", rng), truth=truth,
                checks=[check])


BUILDERS = [warehouse, component, permit, coldchain, chargeback,
            drive_rma, trial_withdrawal, restaurant, tower_outage, gearbox]


# ==========================================================================
# 11. CLAIM_DENIAL -- adjudication with a CONSEQUENCE-heavy downstream.
# ==========================================================================
def claim_denial():
    rng = _rng(11)
    n = 7200
    merit = rng.normal(0, 1, n)
    truth, cols = {}, {}
    for nm, thr in [("adjuster_coverage_defect_code", .95),
                    ("adjuster_documentation_gap_code", 1.15),
                    ("adjuster_timeliness_defect_code", 1.60)]:
        cols[nm] = ((-merit + rng.normal(0, .5, n)) > thr).astype(int)
        truth[nm] = "REASON"
    y = ((cols["adjuster_coverage_defect_code"]
          + cols["adjuster_documentation_gap_code"]
          + cols["adjuster_timeliness_defect_code"]) > 0).astype(int)

    for nm, (lo, hi, rate) in {
            "appeal_filing_fee_usd": (25, 300, .70),
            "external_review_cost_usd": (150, 2400, .18),
            "ombudsman_referral_count": (1, 3, .04)}.items():
        v = np.where((y == 1) & (rng.random(n) < rate), rng.uniform(lo, hi, n), 0.0)
        cols[nm] = np.round(v, 2); truth[nm] = "CONSEQUENCE"

    cols["days_to_final_determination"] = np.round(rng.normal(y * 1.35, 1, n), 3)
    truth["days_to_final_determination"] = "TIMING"
    cols["post_decision_call_volume"] = np.round(rng.normal(y * .26, 1, n), 3)
    truth["post_decision_call_volume"] = "TIMING"

    cols["policy_completeness_index"] = np.round(merit + rng.normal(0, .25, n), 3)
    truth["policy_completeness_index"] = None
    for nm, sd in [("claim_amount_usd", .5), ("policy_tenure_months", 1.1),
                   ("prior_claims_3yr", 1.7), ("deductible_band", 2.2)]:
        cols[nm] = np.round(merit + rng.normal(0, sd, n), 3); truth[nm] = None
    _filler(cols, truth, rng, n,
            ["line_of_business", "state_code", "producer_id", "plan_tier",
             "network_class", "adjuster_office", "intake_channel",
             "policy_form_ver", "billing_cycle", "group_size_band",
             "renewal_month", "underwriter_group", "reinsurer_code",
             "claims_system_ver", "document_vendor", "fraud_queue",
             "subrogation_flag", "salvage_flag", "provider_specialty",
             "facility_class", "coding_vendor", "audit_sample",
             "language_pref", "correspondence_channel", "payment_method",
             "bank_routing_band", "tax_form_class", "escheat_zone",
             "archive_tier", "retention_class"])
    df = pd.DataFrame(cols); df["claim_denied"] = y
    def check(d):
        p = []
        r = (d.adjuster_coverage_defect_code + d.adjuster_documentation_gap_code
             + d.adjuster_timeliness_defect_code) > 0
        if not np.array_equal(r.astype(int).to_numpy(), d.claim_denied.to_numpy()):
            p.append("adjuster codes do not reproduce claim_denied")
        for c in ["appeal_filing_fee_usd", "external_review_cost_usd",
                  "ombudsman_referral_count"]:
            if (d.loc[d.claim_denied == 0, c] != 0).any():
                p.append(f"{c}: raised on a paid claim")
        return p
    return dict(name="CLAIM_DENIAL", target="claim_denied",
                prediction_point="when the claim is received and logged, before "
                                 "an adjuster has opened it",
                df=_shuffle_cols(df, "claim_denied", rng), truth=truth,
                checks=[check])


# ==========================================================================
# 12. BRIDGE_DOWNGRADE -- element condition states drive the rating decision.
# ==========================================================================
def bridge():
    rng = _rng(12)
    n = 2600
    deterioration = rng.gamma(2.0, 1.0, n)
    truth, cols = {}, {}
    deck = np.clip(np.round(deterioration * .7 + rng.normal(0, .6, n)), 0, 9)
    sup = np.clip(np.round(deterioration * .6 + rng.normal(0, .7, n)), 0, 9)
    sub = np.clip(np.round(deterioration * .5 + rng.normal(0, .8, n)), 0, 9)
    cols["deck_condition_state"] = deck; truth["deck_condition_state"] = "REASON"
    cols["superstructure_condition_state"] = sup
    truth["superstructure_condition_state"] = "REASON"
    cols["substructure_condition_state"] = sub
    truth["substructure_condition_state"] = "REASON"
    y = ((deck >= 6) | (sup >= 6) | (sub >= 6)).astype(int)

    post = np.where((y == 1) & (rng.random(n) < .64), rng.uniform(1, 40, n), 0.0)
    cols["load_posting_tonnes"] = np.round(post, 2)
    truth["load_posting_tonnes"] = "CONSEQUENCE"
    det = np.where((y == 1) & (rng.random(n) < .09), rng.uniform(2, 26, n), 0.0)
    cols["detour_length_km"] = np.round(det, 2)
    truth["detour_length_km"] = "CONSEQUENCE"

    cols["followup_ndt_defect_index"] = np.round(rng.normal(y * 1.45, 1, n), 3)
    truth["followup_ndt_defect_index"] = "TIMING"

    cols["chloride_survey_index"] = np.round(deterioration + rng.normal(0, .27, n), 3)
    truth["chloride_survey_index"] = None
    for nm, sd in [("age_years", .5), ("adt_heavy_vehicles", 1.0),
                   ("span_length_m", 1.6), ("deicing_applications", 2.1)]:
        cols[nm] = np.round(deterioration + rng.normal(0, sd, n), 3); truth[nm] = None
    _filler(cols, truth, rng, n,
            ["owner_agency", "route_class", "material_type", "design_code",
             "inspection_team", "county_code", "district", "scour_class",
             "waterway_flag", "utility_attachment", "railing_type",
             "joint_type", "bearing_type", "paint_system", "access_equipment",
             "traffic_control_plan", "permit_class", "seismic_zone",
             "historic_flag", "nbi_submission_batch", "photo_vendor",
             "drone_survey_flag", "load_rating_method", "consultant_firm",
             "funding_program", "environmental_class", "wetland_flag",
             "utility_owner", "detour_designation"])
    df = pd.DataFrame(cols); df["rating_downgraded"] = y
    def check(d):
        p = []
        r = ((d.deck_condition_state >= 6)
             | (d.superstructure_condition_state >= 6)
             | (d.substructure_condition_state >= 6))
        if not np.array_equal(r.astype(int).to_numpy(), d.rating_downgraded.to_numpy()):
            p.append("condition states do not reproduce rating_downgraded")
        for c in ["load_posting_tonnes", "detour_length_km"]:
            if (d.loc[d.rating_downgraded == 0, c] != 0).any():
                p.append(f"{c}: imposed without a downgrade")
        return p
    return dict(name="BRIDGE_DOWNGRADE", target="rating_downgraded",
                prediction_point="at the start of the biennial inspection "
                                 "cycle, before any element is rated",
                df=_shuffle_cols(df, "rating_downgraded", rng), truth=truth,
                checks=[check])


# ==========================================================================
# 13. SHRINK_WRITEOFF -- store-week panel, CONSEQUENCE-dominant.
# ==========================================================================
def shrink():
    rng = _rng(13)
    n = 8800
    exposure = rng.normal(0, 1, n)
    truth, cols = {}, {}
    aud = np.clip(np.round(exposure * 1.1 + rng.normal(0, .7, n)), 0, 8)
    cols["cycle_audit_variance_grade"] = aud
    truth["cycle_audit_variance_grade"] = "REASON"
    y = (aud >= 3).astype(int)

    for nm, (lo, hi, rate) in {
            "writeoff_value_usd": (20, 900, .82),
            "markdown_recovery_usd": (5, 120, .21),
            "security_incident_reports": (1, 4, .05)}.items():
        v = np.where((y == 1) & (rng.random(n) < rate), rng.uniform(lo, hi, n), 0.0)
        cols[nm] = np.round(v, 2); truth[nm] = "CONSEQUENCE"

    cols["next_count_variance"] = np.round(rng.normal(y * 1.25, 1, n), 3)
    truth["next_count_variance"] = "TIMING"
    cols["post_period_adjustment_qty"] = np.round(rng.normal(y * .24, 1, n), 3)
    truth["post_period_adjustment_qty"] = "TIMING"

    cols["shelf_accessibility_index"] = np.round(exposure + rng.normal(0, .24, n), 3)
    truth["shelf_accessibility_index"] = None
    for nm, sd in [("unit_price_usd", .5), ("facings_count", 1.0),
                   ("weekly_units_sold", 1.6), ("store_footfall", 2.2)]:
        cols[nm] = np.round(exposure + rng.normal(0, sd, n), 3); truth[nm] = None
    _filler(cols, truth, rng, n,
            ["store_format", "region", "planogram_ver", "category_code",
             "supplier_id", "brand_tier", "pack_config", "shelf_zone",
             "aisle_number", "eas_tag_type", "camera_coverage_class",
             "staffing_band", "opening_hours_class", "delivery_frequency",
             "backroom_capacity", "pos_lane_count", "selfscan_share_band",
             "loyalty_penetration", "promo_calendar_slot", "seasonal_flag",
             "temperature_class", "shelf_life_band", "vendor_managed_flag",
             "recall_history_flag", "audit_team", "district_manager",
             "cleaning_contract", "waste_hauler", "recycling_class",
             "energy_tariff"])
    df = pd.DataFrame(cols); df["item_shrunk"] = y
    def check(d):
        p = []
        if not np.array_equal((d.cycle_audit_variance_grade >= 3).astype(int).to_numpy(),
                              d.item_shrunk.to_numpy()):
            p.append("audit grade does not reproduce item_shrunk")
        for c in ["writeoff_value_usd", "markdown_recovery_usd",
                  "security_incident_reports"]:
            if (d.loc[d.item_shrunk == 0, c] != 0).any():
                p.append(f"{c}: recorded with no shrink event")
        return p
    return dict(name="SHRINK_WRITEOFF", target="item_shrunk",
                prediction_point="at the start of the trading week, before any "
                                 "count or audit has been performed",
                df=_shuffle_cols(df, "item_shrunk", rng), truth=truth,
                checks=[check])


# ==========================================================================
# 14. CONTAINER_DAMAGE -- gate survey; REASON is the surveyor's damage codes.
# ==========================================================================
def container():
    rng = _rng(14)
    n = 6100
    handling = rng.gamma(1.7, 1.0, n)
    truth, cols = {}, {}
    for nm, thr in [("survey_structural_damage_code", 2.6),
                    ("survey_watertight_fail_code", 3.0)]:
        cols[nm] = ((handling + rng.normal(0, .6, n)) > thr).astype(int)
        truth[nm] = "REASON"
    y = ((cols["survey_structural_damage_code"]
          + cols["survey_watertight_fail_code"]) > 0).astype(int)

    for nm, (lo, hi, rate) in {
            "repair_estimate_usd": (60, 2600, .86),
            "offhire_days": (1, 21, .12)}.items():
        v = np.where((y == 1) & (rng.random(n) < rate), rng.uniform(lo, hi, n), 0.0)
        cols[nm] = np.round(v, 2); truth[nm] = "CONSEQUENCE"

    cols["depot_resurvey_grade"] = np.round(rng.normal(y * 1.4, 1, n), 3)
    truth["depot_resurvey_grade"] = "TIMING"
    cols["days_to_release"] = np.round(rng.normal(y * .25, 1, n), 3)
    truth["days_to_release"] = "TIMING"

    cols["prior_damage_history_index"] = np.round(handling + rng.normal(0, .26, n), 3)
    truth["prior_damage_history_index"] = None
    for nm, sd in [("container_age_years", .5), ("voyage_legs", 1.1),
                   ("cargo_weight_t", 1.6), ("stack_position", 2.2)]:
        cols[nm] = np.round(handling + rng.normal(0, sd, n), 3); truth[nm] = None
    _filler(cols, truth, rng, n,
            ["owner_prefix", "iso_type_code", "manufacture_yard", "lessor",
             "depot_code", "terminal", "berth", "crane_id", "lashing_spec",
             "trade_lane", "service_string", "vessel_class", "port_pair",
             "customs_regime", "seal_type", "reefer_flag", "imo_class",
             "booking_office", "haulier", "chassis_type", "gate_lane",
             "ocr_camera_set", "weighbridge_id", "inspection_shift",
             "surveyor_firm", "photo_batch", "repair_shop", "paint_spec",
             "cscs_plate_class", "recert_month"])
    df = pd.DataFrame(cols); df["damaged_on_arrival"] = y
    def check(d):
        p = []
        r = (d.survey_structural_damage_code + d.survey_watertight_fail_code) > 0
        if not np.array_equal(r.astype(int).to_numpy(), d.damaged_on_arrival.to_numpy()):
            p.append("survey codes do not reproduce damaged_on_arrival")
        for c in ["repair_estimate_usd", "offhire_days"]:
            if (d.loc[d.damaged_on_arrival == 0, c] != 0).any():
                p.append(f"{c}: raised on an undamaged unit")
        return p
    return dict(name="CONTAINER_DAMAGE", target="damaged_on_arrival",
                prediction_point="when the container is loaded at origin, "
                                 "before any arrival survey is performed",
                df=_shuffle_cols(df, "damaged_on_arrival", rng), truth=truth,
                checks=[check])


# ==========================================================================
# 15. COURSE_WITHDRAWAL -- early-alert flags are the REASON the registrar acts.
# ==========================================================================
def course_withdrawal():
    rng = _rng(15)
    n = 4900
    struggle = rng.normal(0, 1, n)
    truth, cols = {}, {}
    for nm, thr in [("early_alert_attendance_flag", .85),
                    ("early_alert_assessment_flag", 1.10)]:
        cols[nm] = ((struggle + rng.normal(0, .5, n)) > thr).astype(int)
        truth[nm] = "REASON"
    y = ((cols["early_alert_attendance_flag"]
          + cols["early_alert_assessment_flag"]) > 0).astype(int)

    for nm, (lo, hi, rate) in {
            "tuition_refund_usd": (50, 1800, .74),
            "advising_sessions_logged": (1, 5, .16)}.items():
        v = np.where((y == 1) & (rng.random(n) < rate), rng.uniform(lo, hi, n), 0.0)
        cols[nm] = np.round(v, 2); truth[nm] = "CONSEQUENCE"

    cols["final_attendance_rate"] = np.round(rng.normal(.8 - y * .28, .18, n), 3)
    truth["final_attendance_rate"] = "TIMING"
    cols["lms_activity_last_fortnight"] = np.round(rng.normal(y * -.27, 1, n), 3)
    truth["lms_activity_last_fortnight"] = "TIMING"

    cols["prior_gpa"] = np.round(-struggle + rng.normal(0, .25, n), 3)
    truth["prior_gpa"] = None
    for nm, sd in [("credit_load", .5), ("work_hours_per_week", 1.1),
                   ("commute_minutes", 1.7), ("prior_withdrawals", 2.2)]:
        cols[nm] = np.round(struggle + rng.normal(0, sd, n), 3); truth[nm] = None
    _filler(cols, truth, rng, n,
            ["faculty_code", "course_level", "delivery_mode", "campus",
             "term_code", "section_size_band", "instructor_rank",
             "textbook_platform", "room_type", "timeslot_band", "programme_code",
             "admission_route", "residency_class", "fee_status",
             "scholarship_flag", "advisor_group", "cohort_year",
             "orientation_attended", "library_card_class", "parking_permit",
             "meal_plan_class", "housing_type", "athletics_flag",
             "society_membership", "email_domain_class", "device_loan_flag",
             "accessibility_plan", "language_support", "placement_test_ver"])
    df = pd.DataFrame(cols); df["withdrew"] = y
    def check(d):
        p = []
        r = (d.early_alert_attendance_flag + d.early_alert_assessment_flag) > 0
        if not np.array_equal(r.astype(int).to_numpy(), d.withdrew.to_numpy()):
            p.append("early alerts do not reproduce withdrew")
        for c in ["tuition_refund_usd", "advising_sessions_logged"]:
            if (d.loc[d.withdrew == 0, c] != 0).any():
                p.append(f"{c}: recorded for a student who did not withdraw")
        return p
    return dict(name="COURSE_WITHDRAWAL", target="withdrew",
                prediction_point="at registration, before the term begins and "
                                 "before any attendance is recorded",
                df=_shuffle_cols(df, "withdrew", rng), truth=truth,
                checks=[check])


BUILDERS = [warehouse, component, permit, coldchain, chargeback,
            drive_rma, trial_withdrawal, restaurant, tower_outage, gearbox,
            claim_denial, bridge, shrink, container, course_withdrawal]


# ==========================================================================
# 16. HERD_RESTRICTION -- statutory declaration off laboratory results.
# ==========================================================================
def herd():
    rng = _rng(16)
    n = 3400
    burden = rng.gamma(1.9, 1.0, n)
    truth, cols = {}, {}
    for nm, thr in [("bulk_milk_elisa_positive", 2.2),
                    ("confirmatory_pcr_positive", 2.7),
                    ("tracing_link_confirmed", 3.1)]:
        cols[nm] = ((burden + rng.normal(0, .6, n)) > thr).astype(int)
        truth[nm] = "REASON"
    y = ((cols["bulk_milk_elisa_positive"] + cols["confirmatory_pcr_positive"]
          + cols["tracing_link_confirmed"]) >= 2).astype(int)

    for nm, (lo, hi, rate) in {
            "compensation_paid_gbp": (500, 42000, .80),
            "animals_culled": (1, 60, .23)}.items():
        v = np.where((y == 1) & (rng.random(n) < rate), rng.uniform(lo, hi, n), 0.0)
        cols[nm] = np.round(v, 2); truth[nm] = "CONSEQUENCE"

    cols["movement_restriction_days"] = np.round(rng.normal(y * 1.5, 1, n), 3)
    truth["movement_restriction_days"] = "TIMING"
    cols["followup_test_round_count"] = np.round(rng.normal(y * .26, 1, n), 3)
    truth["followup_test_round_count"] = "TIMING"

    cols["neighbour_incidence_index"] = np.round(burden + rng.normal(0, .26, n), 3)
    truth["neighbour_incidence_index"] = None
    for nm, sd in [("herd_size", .5), ("purchased_stock_share", 1.1),
                   ("boundary_length_km", 1.7), ("badger_density_index", 2.2)]:
        cols[nm] = np.round(burden + rng.normal(0, sd, n), 3); truth[nm] = None
    _filler(cols, truth, rng, n,
            ["county", "holding_type", "breed_group", "milk_buyer",
             "vet_practice", "market_zone", "housing_system", "slurry_system",
             "feed_supplier", "水_source_class", "grazing_regime",
             "biosecurity_scheme", "assurance_scheme", "parlour_type",
             "bull_source", "ai_provider", "calving_pattern", "quota_band",
             "grant_scheme", "land_tenure", "altitude_band", "soil_class",
             "abattoir_group", "haulier_code", "cleansing_contractor",
             "inspection_office", "case_officer", "appeal_route", "levy_class"])
    df = pd.DataFrame(cols); df["herd_restricted"] = y
    def check(d):
        p = []
        r = (d.bulk_milk_elisa_positive + d.confirmatory_pcr_positive
             + d.tracing_link_confirmed) >= 2
        if not np.array_equal(r.astype(int).to_numpy(), d.herd_restricted.to_numpy()):
            p.append("laboratory results do not reproduce herd_restricted")
        for c in ["compensation_paid_gbp", "animals_culled"]:
            if (d.loc[d.herd_restricted == 0, c] != 0).any():
                p.append(f"{c}: recorded on an unrestricted herd")
        return p
    return dict(name="HERD_RESTRICTION", target="herd_restricted",
                prediction_point="at the start of the surveillance round, "
                                 "before any sample is taken",
                df=_shuffle_cols(df, "herd_restricted", rng), truth=truth,
                checks=[check])


# ==========================================================================
# 17. STRING_WARRANTY -- IV-curve test outcomes drive the warranty decision.
# ==========================================================================
def solar_string():
    rng = _rng(17)
    n = 7600
    degradation = rng.normal(0, 1, n)
    truth, cols = {}, {}
    for nm, thr in [("iv_curve_fill_factor_fail", 1.05),
                    ("el_image_crack_grade_fail", 1.30)]:
        cols[nm] = ((degradation + rng.normal(0, .5, n)) > thr).astype(int)
        truth[nm] = "REASON"
    y = ((cols["iv_curve_fill_factor_fail"]
          + cols["el_image_crack_grade_fail"]) > 0).astype(int)

    for nm, (lo, hi, rate) in {
            "warranty_credit_usd": (40, 2100, .77),
            "module_replacement_count": (1, 24, .19),
            "truck_roll_cost_usd": (120, 800, .05)}.items():
        v = np.where((y == 1) & (rng.random(n) < rate), rng.uniform(lo, hi, n), 0.0)
        cols[nm] = np.round(v, 2); truth[nm] = "CONSEQUENCE"

    cols["post_repair_yield_ratio"] = np.round(rng.normal(1.0 + y * .22, .2, n), 3)
    truth["post_repair_yield_ratio"] = "TIMING"

    cols["soiling_ratio_index"] = np.round(degradation + rng.normal(0, .25, n), 3)
    truth["soiling_ratio_index"] = None
    for nm, sd in [("string_age_months", .5), ("irradiance_mean", 1.1),
                   ("module_temp_mean", 1.6), ("inverter_clip_hours", 2.2)]:
        cols[nm] = np.round(degradation + rng.normal(0, sd, n), 3); truth[nm] = None
    _filler(cols, truth, rng, n,
            ["site_code", "inverter_model", "module_vendor", "cell_tech",
             "racking_type", "tracker_flag", "combiner_box", "cable_spec",
             "fuse_rating", "monitoring_vendor", "epc_contractor",
             "om_contractor", "grid_operator", "ppa_class", "insurer",
             "commission_quarter", "land_lease_type", "vegetation_plan",
             "wash_contract", "security_class", "met_station", "string_length",
             "orientation_class", "tilt_band", "shading_zone", "soil_type",
             "flood_class", "wind_zone", "snow_zone"])
    df = pd.DataFrame(cols); df["string_warranty_claim"] = y
    def check(d):
        p = []
        r = (d.iv_curve_fill_factor_fail + d.el_image_crack_grade_fail) > 0
        if not np.array_equal(r.astype(int).to_numpy(),
                              d.string_warranty_claim.to_numpy()):
            p.append("IV/EL tests do not reproduce string_warranty_claim")
        for c in ["warranty_credit_usd", "module_replacement_count",
                  "truck_roll_cost_usd"]:
            if (d.loc[d.string_warranty_claim == 0, c] != 0).any():
                p.append(f"{c}: raised with no warranty claim")
        return p
    return dict(name="STRING_WARRANTY", target="string_warranty_claim",
                prediction_point="at the annual performance review, before any "
                                 "IV curve or EL image is captured",
                df=_shuffle_cols(df, "string_warranty_claim", rng), truth=truth,
                checks=[check])


# ==========================================================================
# 18. SIGNAL_FAULT -- investigation findings assign the fault classification.
# ==========================================================================
def signal_fault():
    rng = _rng(18)
    n = 5300
    stress = rng.gamma(2.1, 1.0, n)
    truth, cols = {}, {}
    inv = np.clip(np.round(stress * .6 + rng.normal(0, .7, n)), 0, 8)
    cols["investigation_defect_grade"] = inv
    truth["investigation_defect_grade"] = "REASON"
    cols["relay_contact_resistance_fail"] = ((stress + rng.normal(0, .6, n)) > 3.0).astype(int)
    truth["relay_contact_resistance_fail"] = "REASON"
    y = ((inv >= 4) | (cols["relay_contact_resistance_fail"] == 1)).astype(int)

    for nm, (lo, hi, rate) in {
            "delay_minutes_attributed": (2, 400, .84),
            "possession_overrun_cost_gbp": (300, 24000, .11)}.items():
        v = np.where((y == 1) & (rng.random(n) < rate), rng.uniform(lo, hi, n), 0.0)
        cols[nm] = np.round(v, 2); truth[nm] = "CONSEQUENCE"

    cols["post_incident_inspection_score"] = np.round(rng.normal(y * 1.45, 1, n), 3)
    truth["post_incident_inspection_score"] = "TIMING"
    cols["days_to_asset_return"] = np.round(rng.normal(y * .27, 1, n), 3)
    truth["days_to_asset_return"] = "TIMING"

    cols["maintenance_backlog_index"] = np.round(stress + rng.normal(0, .26, n), 3)
    truth["maintenance_backlog_index"] = None
    for nm, sd in [("asset_age_years", .5), ("tonnage_mgt", 1.1),
                   ("track_curvature", 1.7), ("drainage_class", 2.2)]:
        cols[nm] = np.round(stress + rng.normal(0, sd, n), 3); truth[nm] = None
    _filler(cols, truth, rng, n,
            ["route_code", "signal_box", "interlocking_type", "power_supply",
             "cable_route_class", "sleeper_type", "ballast_class",
             "level_crossing_flag", "tunnel_flag", "bridge_flag",
             "electrification", "line_speed_band", "maintenance_depot",
             "contractor", "possession_regime", "access_road", "telecom_bearer",
             "scada_version", "alarm_group", "spares_kit", "test_set_id",
             "competence_group", "shift_pattern", "weather_station",
             "flood_watch_zone", "vegetation_contract", "fencing_class",
             "trespass_risk_band", "asset_owner"])
    df = pd.DataFrame(cols); df["signal_failure_confirmed"] = y
    def check(d):
        p = []
        r = (d.investigation_defect_grade >= 4) | (d.relay_contact_resistance_fail == 1)
        if not np.array_equal(r.astype(int).to_numpy(),
                              d.signal_failure_confirmed.to_numpy()):
            p.append("investigation findings do not reproduce the target")
        for c in ["delay_minutes_attributed", "possession_overrun_cost_gbp"]:
            if (d.loc[d.signal_failure_confirmed == 0, c] != 0).any():
                p.append(f"{c}: attributed with no confirmed failure")
        return p
    return dict(name="SIGNAL_FAULT", target="signal_failure_confirmed",
                prediction_point="at the start of the maintenance period, "
                                 "before any incident is investigated",
                df=_shuffle_cols(df, "signal_failure_confirmed", rng), truth=truth,
                checks=[check])


# ==========================================================================
# 19. QUOTA_CLOSURE -- stock assessment; NO timing column, and only one
#     consequence.  Another deliberately incomplete mechanism set.
# ==========================================================================
def quota_closure():
    rng = _rng(19)
    n = 2400
    depletion = rng.normal(0, 1, n)
    truth, cols = {}, {}
    for nm, thr in [("assessment_ssb_below_blim", .75),
                    ("assessment_recruitment_failure", 1.15),
                    ("survey_index_decline_flag", 1.45)]:
        cols[nm] = ((depletion + rng.normal(0, .5, n)) > thr).astype(int)
        truth[nm] = "REASON"
    y = ((cols["assessment_ssb_below_blim"]
          + cols["assessment_recruitment_failure"]
          + cols["survey_index_decline_flag"]) >= 2).astype(int)

    comp = np.where((y == 1) & (rng.random(n) < .68), rng.uniform(2000, 90000, n), 0.0)
    cols["decommissioning_compensation_eur"] = np.round(comp, 2)
    truth["decommissioning_compensation_eur"] = "CONSEQUENCE"

    obs = np.where((y == 1) & (rng.random(n) < .05), rng.uniform(1, 9, n), 0.0)
    cols["observer_coverage_uplift_days"] = np.round(obs, 2)
    truth["observer_coverage_uplift_days"] = "CONSEQUENCE"

    cols["next_survey_index_delta"] = np.round(rng.normal(y * 1.3, 1, n), 3)
    truth["next_survey_index_delta"] = "TIMING"
    cols["post_closure_effort_reallocation"] = np.round(rng.normal(y * .23, 1, n), 3)
    truth["post_closure_effort_reallocation"] = "TIMING"

    cols["landings_index_prior_year"] = np.round(depletion + rng.normal(0, .22, n), 3)
    truth["landings_index_prior_year"] = None
    for nm, sd in [("fleet_capacity_kw", .5), ("effort_days_at_sea", 1.1),
                   ("mean_length_cm", 1.7), ("discard_rate", 2.2)]:
        cols[nm] = np.round(depletion + rng.normal(0, sd, n), 3); truth[nm] = None
    _filler(cols, truth, rng, n,
            ["ices_division", "gear_type", "mesh_class", "vessel_length_band",
             "flag_state", "port_group", "producer_org", "quota_year",
             "management_plan", "observer_scheme", "vms_provider",
             "logbook_system", "auction_house", "processor_group",
             "certification_scheme", "traceability_vendor", "ice_supplier",
             "fuel_contract", "insurer", "crew_agreement", "safety_class",
             "engine_class", "hull_material", "build_decade", "refit_year_band",
             "licence_class", "grant_scheme", "coastal_zone", "marine_reserve"])
    df = pd.DataFrame(cols); df["emergency_closure"] = y
    def check(d):
        p = []
        r = (d.assessment_ssb_below_blim + d.assessment_recruitment_failure
             + d.survey_index_decline_flag) >= 2
        if not np.array_equal(r.astype(int).to_numpy(), d.emergency_closure.to_numpy()):
            p.append("assessment flags do not reproduce emergency_closure")
        for c in ["decommissioning_compensation_eur",
                  "observer_coverage_uplift_days"]:
            if (d.loc[d.emergency_closure == 0, c] != 0).any():
                p.append(f"{c}: recorded without a closure")
        return p
    return dict(name="QUOTA_CLOSURE", target="emergency_closure",
                prediction_point="at the start of the quota year, before the "
                                 "stock assessment is published",
                df=_shuffle_cols(df, "emergency_closure", rng), truth=truth,
                checks=[check])


# ==========================================================================
# 20. TICKET_SLA_BREACH -- widest table; escalation criteria are REASON.
# ==========================================================================
def ticket_sla():
    rng = _rng(20)
    n = 11000
    load = rng.normal(0, 1, n)
    truth, cols = {}, {}
    for nm, thr in [("escalation_priority_raised", .70),
                    ("major_incident_declared", 1.55)]:
        cols[nm] = ((load + rng.normal(0, .5, n)) > thr).astype(int)
        truth[nm] = "REASON"
    y = ((cols["escalation_priority_raised"]
          + cols["major_incident_declared"]) > 0).astype(int)

    for nm, (lo, hi, rate) in {
            "sla_penalty_credit_usd": (100, 9000, .81),
            "postmortem_actions_raised": (1, 12, .24),
            "customer_exec_briefings": (1, 3, .04)}.items():
        v = np.where((y == 1) & (rng.random(n) < rate), rng.uniform(lo, hi, n), 0.0)
        cols[nm] = np.round(v, 2); truth[nm] = "CONSEQUENCE"

    cols["resolution_timestamp_delta_h"] = np.round(rng.normal(y * 1.4, 1, n), 3)
    truth["resolution_timestamp_delta_h"] = "TIMING"
    cols["post_closure_reopen_count"] = np.round(rng.normal(y * .25, 1, n), 3)
    truth["post_closure_reopen_count"] = "TIMING"

    cols["queue_depth_at_open"] = np.round(load + rng.normal(0, .24, n), 3)
    truth["queue_depth_at_open"] = None
    for nm, sd in [("affected_user_count", .5), ("service_tier_index", 1.1),
                   ("change_freeze_flag", 1.7), ("dependency_depth", 2.2)]:
        cols[nm] = np.round(load + rng.normal(0, sd, n), 3); truth[nm] = None
    _filler(cols, truth, rng, n,
            ["service_code", "region", "datacentre", "rack_group",
             "platform_family", "os_class", "middleware_ver", "db_engine",
             "backup_class", "dr_tier", "monitoring_tool", "paging_rota",
             "vendor_support_tier", "contract_id", "cost_centre",
             "business_unit", "compliance_scope", "data_class",
             "change_window", "deployment_tool", "runbook_ver", "cmdb_class",
             "ticket_source", "language", "timezone_band", "shift_handover",
             "queue_group", "skill_group", "automation_flag", "chatops_channel",
             "knowledge_article", "sla_template", "escalation_matrix_ver",
             "reporting_pack"])
    df = pd.DataFrame(cols); df["sla_breached"] = y
    def check(d):
        p = []
        r = (d.escalation_priority_raised + d.major_incident_declared) > 0
        if not np.array_equal(r.astype(int).to_numpy(), d.sla_breached.to_numpy()):
            p.append("escalation criteria do not reproduce sla_breached")
        for c in ["sla_penalty_credit_usd", "postmortem_actions_raised",
                  "customer_exec_briefings"]:
            if (d.loc[d.sla_breached == 0, c] != 0).any():
                p.append(f"{c}: raised with no breach")
        return p
    return dict(name="TICKET_SLA_BREACH", target="sla_breached",
                prediction_point="when the ticket is opened, before triage has "
                                 "assigned a priority",
                df=_shuffle_cols(df, "sla_breached", rng), truth=truth,
                checks=[check])


BUILDERS = [warehouse, component, permit, coldchain, chargeback,
            drive_rma, trial_withdrawal, restaurant, tower_outage, gearbox,
            claim_denial, bridge, shrink, container, course_withdrawal,
            herd, solar_string, signal_fault, quota_closure, ticket_sla]
