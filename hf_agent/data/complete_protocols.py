"""Complete heart failure medication protocols with all dosing and safety information."""

# Vital Sign Parameters
VITAL_SIGN_PARAMETERS = {
    "blood_pressure": {
        "titration_range": {"sbp_min": 80, "sbp_max": 200, "dbp_min": 40, "dbp_max": 110},
        "goal_range": {"sbp_min": 90, "sbp_max": 120, "dbp_min": 50, "dbp_max": 80}
    },
    "heart_rate": {
        "titration_minimum": 50,
        "goal_range": {"min": 55, "max": 90}
    }
}

# ACE Inhibitors
ACE_INHIBITORS = {
    "enalapril": {
        "class": "ACE-I",
        "starting_dose": {"value": 2.5, "unit": "mg", "frequency": "twice daily"},
        "incremental_doses": [2.5, 5, 10, 20],
        "maximum_dose": {"value": 20, "unit": "mg", "frequency": "twice daily"},
        "contraindications": [
            "History of angioedema with ACE-I",
            "Bilateral renal artery stenosis",
            "Pregnancy",
            "Concomitant use with aliskiren in patients with diabetes",
            "Concurrent or recent (<48 hours) use of neprilysin inhibitor"
        ],
        "hold_criteria": {
            "potassium_high": 5.5,
            "creatinine_increase_percent": 30,
            "egfr_low": 30,
            "sbp_low": 90
        }
    },
    "lisinopril": {
        "class": "ACE-I",
        "starting_dose": {"value": 2.5, "unit": "mg", "frequency": "daily"},
        "incremental_doses": [2.5, 5, 10, 20, 40],
        "maximum_dose": {"value": 40, "unit": "mg", "frequency": "daily"},
        "contraindications": [
            "History of angioedema with ACE-I",
            "Bilateral renal artery stenosis",
            "Pregnancy",
            "Concomitant use with aliskiren in patients with diabetes",
            "Concurrent or recent (<48 hours) use of neprilysin inhibitor"
        ],
        "hold_criteria": {
            "potassium_high": 5.5,
            "creatinine_increase_percent": 30,
            "egfr_low": 30,
            "sbp_low": 90
        }
    },
    "ramipril": {
        "class": "ACE-I",
        "starting_dose": {"value": 1.25, "unit": "mg", "frequency": "daily"},
        "incremental_doses": [1.25, 2.5, 5, 10],
        "maximum_dose": {"value": 10, "unit": "mg", "frequency": "daily"},
        "contraindications": [
            "History of angioedema with ACE-I",
            "Bilateral renal artery stenosis",
            "Pregnancy",
            "Concomitant use with aliskiren in patients with diabetes",
            "Concurrent or recent (<48 hours) use of neprilysin inhibitor"
        ],
        "hold_criteria": {
            "potassium_high": 5.5,
            "creatinine_increase_percent": 30,
            "egfr_low": 30,
            "sbp_low": 90
        }
    },
    "captopril": {
        "class": "ACE-I",
        "starting_dose": {"value": 6.25, "unit": "mg", "frequency": "three times daily"},
        "incremental_doses": [6.25, 12.5, 25, 50],
        "maximum_dose": {"value": 50, "unit": "mg", "frequency": "three times daily"},
        "contraindications": [
            "History of angioedema with ACE-I",
            "Bilateral renal artery stenosis",
            "Pregnancy",
            "Concomitant use with aliskiren in patients with diabetes",
            "Concurrent or recent (<48 hours) use of neprilysin inhibitor"
        ],
        "hold_criteria": {
            "potassium_high": 5.5,
            "creatinine_increase_percent": 30,
            "egfr_low": 30,
            "sbp_low": 90
        }
    }
}

# ARBs
ARBS = {
    "losartan": {
        "class": "ARB",
        "starting_dose": {"value": 25, "unit": "mg", "frequency": "daily"},
        "incremental_doses": [25, 50, 100],
        "maximum_dose": {"value": 100, "unit": "mg", "frequency": "daily"},
        "contraindications": [
            "History of angioedema with ARB",
            "Bilateral renal artery stenosis",
            "Pregnancy",
            "Concomitant use with aliskiren in patients with diabetes",
            "Concurrent or recent (<48 hours) use of neprilysin inhibitor"
        ],
        "hold_criteria": {
            "potassium_high": 5.5,
            "creatinine_increase_percent": 30,
            "egfr_low": 30,
            "sbp_low": 90
        }
    },
    "valsartan": {
        "class": "ARB",
        "starting_dose": {"value": 40, "unit": "mg", "frequency": "twice daily"},
        "incremental_doses": [40, 80, 160],
        "maximum_dose": {"value": 160, "unit": "mg", "frequency": "twice daily"},
        "contraindications": [
            "History of angioedema with ARB",
            "Bilateral renal artery stenosis",
            "Pregnancy",
            "Concomitant use with aliskiren in patients with diabetes",
            "Concurrent or recent (<48 hours) use of neprilysin inhibitor"
        ],
        "hold_criteria": {
            "potassium_high": 5.5,
            "creatinine_increase_percent": 30,
            "egfr_low": 30,
            "sbp_low": 90
        }
    },
    "candesartan": {
        "class": "ARB",
        "starting_dose": {"value": 4, "unit": "mg", "frequency": "daily"},
        "incremental_doses": [4, 8, 16, 32],
        "maximum_dose": {"value": 32, "unit": "mg", "frequency": "daily"},
        "contraindications": [
            "History of angioedema with ARB",
            "Bilateral renal artery stenosis",
            "Pregnancy",
            "Concomitant use with aliskiren in patients with diabetes",
            "Concurrent or recent (<48 hours) use of neprilysin inhibitor"
        ],
        "hold_criteria": {
            "potassium_high": 5.5,
            "creatinine_increase_percent": 30,
            "egfr_low": 30,
            "sbp_low": 90
        }
    }
}

# ARNI (Neprilysin Inhibitor/ARB)
ARNI = {
    "sacubitril_valsartan": {
        "class": "ARNI",
        "name": "Sacubitril/Valsartan (Entresto)",
        "starting_dose": {"value": "24/26", "unit": "mg", "frequency": "twice daily"},
        "starting_dose_low": {"value": "24/26", "unit": "mg", "frequency": "twice daily"},
        "starting_dose_high": {"value": "49/51", "unit": "mg", "frequency": "twice daily"},
        "incremental_doses": ["24/26", "49/51", "97/103"],
        "maximum_dose": {"value": "97/103", "unit": "mg", "frequency": "twice daily"},
        "special_requirements": "Initiate 48 hours following cessation of previous ACE-I",
        "contraindications": [
            "History of angioedema with ACE-I, ARB, or neprilysin inhibitor",
            "Concurrent use with ACE-I (must wait 48 hours after last ACE-I dose)",
            "Pregnancy",
            "Severe hepatic impairment (Child-Pugh Class C)"
        ],
        "hold_criteria": {
            "potassium_high": 5.5,
            "creatinine_increase_percent": 30,
            "egfr_low": 20,
            "sbp_low": 90
        },
        "starting_dose_criteria": {
            "low_dose_if": [
                "Patient not currently taking ACE-I/ARB",
                "Currently taking ACE-I/ARB equivalent to ≤10 mg Enalapril daily",
                "eGFR <30 mL/min",
                "Hepatic impairment Child-Pugh Class B"
            ],
            "high_dose_if": [
                "Currently taking ACE-I/ARB equivalent to >10 mg Enalapril daily"
            ]
        }
    }
}

# Aldosterone Antagonists
ALDOSTERONE_ANTAGONISTS = {
    "spironolactone": {
        "class": "Aldosterone Antagonist",
        "starting_dose": {"value": 12.5, "unit": "mg", "frequency": "daily"},
        "incremental_doses": [12.5, 25, 50],
        "maximum_dose": {"value": 50, "unit": "mg", "frequency": "daily"},
        "note": "25 mg daily often sufficient",
        "contraindications": [
            "Baseline potassium >5.0 mEq/L",
            "eGFR <30 mL/min",
            "Addison's disease or hyperkalemia"
        ],
        "hold_criteria": {
            "potassium_high": 5.5,
            "potassium_discontinue": 6.0,
            "creatinine_increase_percent": 30,
            "egfr_low": 30
        },
        "special_considerations": [
            "Severe gynecomastia or breast tenderness (consider switching to eplerenone)"
        ]
    },
    "eplerenone": {
        "class": "Aldosterone Antagonist",
        "starting_dose": {"value": 25, "unit": "mg", "frequency": "daily"},
        "incremental_doses": [25, 50],
        "maximum_dose": {"value": 50, "unit": "mg", "frequency": "daily"},
        "contraindications": [
            "Baseline potassium >5.0 mEq/L",
            "eGFR <30 mL/min",
            "Concurrent use of strong CYP3A4 inhibitors",
            "Addison's disease or hyperkalemia"
        ],
        "hold_criteria": {
            "potassium_high": 5.5,
            "potassium_discontinue": 6.0,
            "creatinine_increase_percent": 30,
            "egfr_low": 30
        }
    }
}

# Beta Blockers
BETA_BLOCKERS = {
    "carvedilol": {
        "class": "Beta Blocker",
        "starting_dose": {"value": 3.125, "unit": "mg", "frequency": "twice daily"},
        "incremental_doses": [3.125, 6.25, 12.5, 25],
        "maximum_dose": {"value": 25, "unit": "mg", "frequency": "twice daily"},
        "maximum_dose_high_weight": {"value": 50, "unit": "mg", "frequency": "twice daily", "weight_threshold": 85},
        "contraindications": [
            "Symptomatic bradycardia or heart rate <50 bpm",
            "Second or third-degree AV block (without pacemaker)",
            "Sick sinus syndrome (without pacemaker)",
            "Severe decompensated heart failure requiring inotropic support",
            "Severe asthma or active bronchospasm",
            "Cardiogenic shock"
        ],
        "hold_criteria": {
            "hr_low": 50,
            "hr_very_low": 45,
            "sbp_low": 85
        }
    },
    "metoprolol_succinate": {
        "class": "Beta Blocker",
        "name": "Metoprolol Succinate (Extended-Release)",
        "starting_dose": {"value": 12.5, "unit": "mg", "frequency": "daily"},
        "incremental_doses": [12.5, 25, 50, 100, 200],
        "maximum_dose": {"value": 200, "unit": "mg", "frequency": "daily"},
        "contraindications": [
            "Symptomatic bradycardia or heart rate <50 bpm",
            "Second or third-degree AV block (without pacemaker)",
            "Sick sinus syndrome (without pacemaker)",
            "Severe decompensated heart failure requiring inotropic support",
            "Severe asthma or active bronchospasm",
            "Cardiogenic shock"
        ],
        "hold_criteria": {
            "hr_low": 50,
            "hr_very_low": 45,
            "sbp_low": 85
        }
    },
    "bisoprolol": {
        "class": "Beta Blocker",
        "starting_dose": {"value": 1.25, "unit": "mg", "frequency": "daily"},
        "incremental_doses": [1.25, 2.5, 5, 10],
        "maximum_dose": {"value": 10, "unit": "mg", "frequency": "daily"},
        "contraindications": [
            "Symptomatic bradycardia or heart rate <50 bpm",
            "Second or third-degree AV block (without pacemaker)",
            "Sick sinus syndrome (without pacemaker)",
            "Severe decompensated heart failure requiring inotropic support",
            "Severe asthma or active bronchospasm",
            "Cardiogenic shock"
        ],
        "hold_criteria": {
            "hr_low": 50,
            "hr_very_low": 45,
            "sbp_low": 85
        }
    }
}

# Hydralazine/Isosorbide Dinitrate
HYDRALAZINE_ISOSORBIDE = {
    "hydralazine": {
        "class": "Vasodilator",
        "starting_dose": {"value": 25, "unit": "mg", "frequency": "three times daily"},
        "incremental_doses": [25, 37.5, 50, 75],
        "maximum_dose": {"value": 75, "unit": "mg", "frequency": "three times daily"},
        "note": "up to 100 mg TID in some protocols",
        "contraindications": [
            "Severe hypotension",
            "Drug-induced lupus syndrome"
        ],
        "hold_criteria": {
            "sbp_low": 90,
            "drug_induced_lupus": True
        },
        "special_monitoring": [
            "Monitor for drug-induced lupus syndrome (positive ANA, arthralgias, fever)"
        ]
    },
    "isosorbide_dinitrate": {
        "class": "Nitrate",
        "starting_dose": {"value": 20, "unit": "mg", "frequency": "three times daily"},
        "incremental_doses": [20, 30, 40],
        "maximum_dose": {"value": 40, "unit": "mg", "frequency": "three times daily"},
        "contraindications": [
            "Severe hypotension",
            "Concurrent use of PDE-5 inhibitors (sildenafil, tadalafil)",
            "Recent MI (within 24-48 hours)"
        ],
        "hold_criteria": {
            "sbp_low": 90,
            "severe_headache": True
        }
    },
    "bidil": {
        "class": "Fixed-Dose Combination",
        "name": "BiDil (Hydralazine 37.5mg + Isosorbide dinitrate 20mg)",
        "starting_dose": {"value": "1 tablet", "unit": "tablet", "frequency": "three times daily"},
        "incremental_doses": ["1 tablet", "2 tablets"],
        "maximum_dose": {"value": "2 tablets", "unit": "tablets", "frequency": "three times daily"},
        "contraindications": [
            "Severe hypotension",
            "Concurrent use of PDE-5 inhibitors with nitrates",
            "Recent MI (within 24-48 hours)",
            "Drug-induced lupus syndrome"
        ],
        "hold_criteria": {
            "sbp_low": 90
        }
    }
}

# SGLT-2 Inhibitors
SGLT2_INHIBITORS = {
    "dapagliflozin": {
        "class": "SGLT-2 Inhibitor",
        "starting_dose": {"value": 10, "unit": "mg", "frequency": "daily"},
        "maximum_dose": {"value": 10, "unit": "mg", "frequency": "daily"},
        "requires_titration": False,
        "contraindications": [
            "eGFR <20 mL/min",
            "Type 1 diabetes (relative contraindication)",
            "History of diabetic ketoacidosis",
            "Dialysis"
        ],
        "hold_criteria": {
            "egfr_low": 20,
            "dka": True,
            "severe_dehydration": True,
            "fournier_gangrene": True,
            "acute_kidney_injury": True
        }
    },
    "empagliflozin": {
        "class": "SGLT-2 Inhibitor",
        "starting_dose": {"value": 10, "unit": "mg", "frequency": "daily"},
        "maximum_dose": {"value": 10, "unit": "mg", "frequency": "daily"},
        "requires_titration": False,
        "contraindications": [
            "eGFR <20 mL/min",
            "Type 1 diabetes (relative contraindication)",
            "History of diabetic ketoacidosis",
            "Dialysis"
        ],
        "hold_criteria": {
            "egfr_low": 20,
            "dka": True,
            "severe_dehydration": True,
            "fournier_gangrene": True,
            "acute_kidney_injury": True
        }
    },
    "sotagliflozin": {
        "class": "SGLT-2 Inhibitor",
        "starting_dose": {"value": 200, "unit": "mg", "frequency": "daily"},
        "incremental_doses": [200, 400],
        "maximum_dose": {"value": 400, "unit": "mg", "frequency": "daily"},
        "requires_titration": True,
        "contraindications": [
            "eGFR <25 mL/min",
            "Type 1 diabetes (relative contraindication)",
            "History of diabetic ketoacidosis",
            "Dialysis"
        ],
        "hold_criteria": {
            "egfr_low": 25,
            "dka": True,
            "severe_dehydration": True,
            "fournier_gangrene": True,
            "acute_kidney_injury": True
        }
    }
}

# sGC Stimulator
SGC_STIMULATOR = {
    "vericiguat": {
        "class": "sGC Stimulator",
        "starting_dose": {"value": 2.5, "unit": "mg", "frequency": "daily"},
        "incremental_doses": [2.5, 5, 10],
        "maximum_dose": {"value": 10, "unit": "mg", "frequency": "daily"},
        "titration_interval": "every 2 weeks",
        "contraindications": [
            "Concomitant use with PDE-5 inhibitors (riociguat, sildenafil, tadalafil)",
            "Pregnancy",
            "Severe hepatic impairment (Child-Pugh Class C)"
        ],
        "hold_criteria": {
            "sbp_low": 90,
            "symptomatic_hypotension": True,
            "concurrent_pde5_inhibitor": True,
            "pregnancy": True,
            "worsening_anemia": True
        }
    }
}

# Lab Monitoring Requirements
LAB_MONITORING = {
    "basic_panel": ["sodium", "potassium", "chloride", "bicarbonate", "glucose"],
    "renal_function": ["creatinine", "bun", "egfr"],
    "additional": ["magnesium", "hemoglobin", "hematocrit"],
    "monitoring_schedule": {
        "aldosterone_antagonist": "1-2 weeks after initiation or dose change",
        "ace_arb_arni": "1-2 weeks after initiation or dose change",
        "ace_arb_arni_plus_aldosterone": "1-2 weeks for combination changes",
        "beta_blocker": "2-4 weeks if renal or electrolyte concerns",
        "sglt2_inhibitor": "2-4 weeks after initiation",
        "sgc_stimulator": "2-4 weeks after initiation (check BMP, hemoglobin)",
        "hydralazine_nitrates": "generally less frequent labs needed unless concerns"
    }
}

# General Hold/Adjust Criteria
GENERAL_HOLD_CRITERIA = {
    "potassium_hold": 5.5,
    "potassium_discontinue": 6.0,
    "creatinine_increase_percent": 30,
    "egfr_critical_low": 20,
    "egfr_caution_low": 30,
    "sodium_low": 130,
    "sbp_symptomatic_low": 80,
    "sbp_general_low": 90,
    "hr_hold": 50,
    "hr_critical": 45
}

# Titration Sequences (Examples)
TITRATION_SEQUENCES = {
    "single_drug": {
        "description": "Titrate one medication to target before adding next",
        "example": [
            "Start beta blocker at low dose → titrate to target over 6-8 weeks",
            "Start ACE-I/ARB/ARNI at low dose → titrate to target over 4-6 weeks",
            "Start aldosterone antagonist at low dose → titrate to target over 2-4 weeks",
            "Add SGLT-2 inhibitor at standard dose",
            "Add sGC stimulator or hydralazine/nitrates if indicated"
        ],
        "timeline": "4-6 months to reach full GDMT"
    },
    "multiple_by_order": {
        "description": "Start multiple drugs at low doses, titrate Drug 1 to target → Drug 2 → Drug 3",
        "timeline": "3-4 months to reach full GDMT"
    },
    "multiple_alternating": {
        "description": "Start multiple drugs at low doses, alternate titrations between drugs",
        "timeline": "3-4 months to reach full GDMT"
    }
}

# All medications combined
ALL_MEDICATIONS = {
    **ACE_INHIBITORS,
    **ARBS,
    **ARNI,
    **ALDOSTERONE_ANTAGONISTS,
    **BETA_BLOCKERS,
    **HYDRALAZINE_ISOSORBIDE,
    **SGLT2_INHIBITORS,
    **SGC_STIMULATOR
}

# Medication class mapping
MEDICATION_CLASSES = {
    "ACE-I": list(ACE_INHIBITORS.keys()),
    "ARB": list(ARBS.keys()),
    "ARNI": list(ARNI.keys()),
    "Aldosterone Antagonist": list(ALDOSTERONE_ANTAGONISTS.keys()),
    "Beta Blocker": list(BETA_BLOCKERS.keys()),
    "Vasodilator": ["hydralazine", "isosorbide_dinitrate", "bidil"],
    "SGLT-2 Inhibitor": list(SGLT2_INHIBITORS.keys()),
    "sGC Stimulator": list(SGC_STIMULATOR.keys())
}

# Endpoint Definitions
PROGRAM_ENDPOINTS = {
    "complete_success": "Patient demonstrates consistent progress throughout the titration program, tolerating medication increases well and achieving all target therapeutic doses.",
    "partial_success": "Patient shows variable responses to medication adjustments, with some drugs reaching their intended targets while others plateau at submaximal doses due to tolerance limitations or mild side effects.",
    "non_adherence_failure": "Patient exhibits a progressive pattern of missed doses and declining medication-taking behavior, preventing safe titration advancement.",
    "side_effect_failure": "Patient experiences increasingly problematic adverse effects from medications that raise safety concerns despite dose adjustments or management attempts.",
    "acute_decompensation_ed": "During the conversation, the patient reports acute worsening heart failure symptoms requiring immediate medical evaluation and emergency department referral.",
    "hospitalization_pause": "Patient experiences significant clinical deterioration requiring hospital admission, with temporary suspension of the titration program.",
    "patient_withdrawal": "Patient expresses unwillingness or refusal to continue with the medication titration process, despite clinical appropriateness."
}