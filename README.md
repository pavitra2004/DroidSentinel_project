# DroidSentinel

## Overview

**DroidSentinel** is an Android anti-forensics detection system designed to identify suspicious activities that attempt to remove, modify, or conceal digital evidence from Android devices.

The system analyzes multiple Android forensic artifacts and uses a combination of a **rule-based detection engine** and **Isolation Forest anomaly detection** to identify potential anti-forensic activity.

## Objectives

* Detect common Android anti-forensics techniques.
* Analyze multiple forensic artifacts for suspicious changes.
* Assign weighted risk scores to detected activities.
* Identify abnormal behavior using machine learning.
* Provide investigators with evidence-based indicators of possible anti-forensic activity.

## System Architecture

```text
Android Device / Forensic Data
            ↓
     Artifact Collection
            ↓
   Artifact Preprocessing
            ↓
 ┌───────────────────────────┐
 │ Rule-Based Detection      │
 │ + Weighted Risk Scoring   │
 └───────────────────────────┘
            ↓
 ┌───────────────────────────┐
 │ Isolation Forest          │
 │ Anomaly Detection         │
 └───────────────────────────┘
            ↓
      Risk Assessment
            ↓
    Detection / Report
```

## How It Works

DroidSentinel analyzes Android forensic artifacts such as:

* `packages.xml`
* Usage statistics
* Dropbox/system logs
* Notification database

It focuses on anti-forensic scenarios including:

* File wiping
* Application uninstallation
* Manual clearing of logs
* Factory reset

The system combines multiple indicators and assigns weighted scores to determine whether the observed activity is potentially suspicious.

An **Isolation Forest** model is additionally used to detect anomalous behavior based on patterns learned from normal samples.

## Detection Approach

DroidSentinel uses an **11-rule weighted detection engine** to evaluate different forensic indicators.

The system then combines rule-based evidence with anomaly detection to improve identification of suspicious activity.

The current experimental dataset contains **21 real Android forensic samples extended to 110 by using synthetic data**,  with the Isolation Forest trained on normal samples for anomaly detection.

## Technology Stack

* **Python**
* **Pandas**
* **NumPy**
* **Scikit-learn**
* **Isolation Forest**
* **Rule-based detection**
* **Android Forensic Artifacts**
* **Android Studio Emulator**

## Project Structure

```text
DroidSentinel/
│
├── apks/                  # APK files used for analysis
├── artifacts/             # Collected Android forensic artifacts
├── collector/             # Artifact collection modules
├── engine/                # Detection and analysis engine
├── reports/               # Generated detection reports
├── research/              # Research and supporting resources
├── scans/                 # Scan results and analysis data
│
├── app.py                 # Main application
├── config.py              # Project configuration
├── report_generator.py    # Report generation
│
└── README.md
```

```

## Installation

```bash
git clone <repository-url>
cd DroidSentinel
pip install -r requirements.txt
```

## Running the Project

Run the main application:

```bash
python app.py
```

The application processes the required Android forensic artifacts, applies the detection rules and anomaly detection model, and generates the corresponding detection results and reports.

## Current Limitations

* The experimental dataset is relatively small.
* Detection performance depends on the availability and quality of forensic artifacts.
* Some anti-forensic techniques may require additional artifact sources for reliable detection.
* Further testing on larger and more diverse Android datasets is required.

## Future Improvements

* Expand the dataset with more real-world Android forensic cases.
* Add detection rules for additional anti-forensic techniques.
* Improve cross-artifact correlation.
* Integrate automated forensic artifact extraction.
* Develop a graphical investigation dashboard.
* Evaluate the system against larger and more diverse datasets.

## Project Status

**Research / Prototype**

DroidSentinel is a prototype Android anti-forensics detection system developed for academic and research purposes.
