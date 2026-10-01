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
* **Android Debug Bridge (ADB)**

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


# WhatsApp Forensics

## Overview

**WhatsApp Forensics** is a digital forensics tool developed to analyze WhatsApp SQLite databases and WAL (Write-Ahead Log) files for recovering and examining message-related evidence.

The project extracts active messages from the WhatsApp database, identifies deleted message markers, scans WAL files for recoverable message strings, builds a chronological timeline, and generates forensic reports.

A **Streamlit-based interface** is provided for uploading forensic artifacts and viewing the analysis results.

## Objectives

* Analyze WhatsApp SQLite database files.
* Examine WAL files for recoverable message remnants.
* Identify active and deleted message records.
* Build a chronological forensic timeline.
* Preserve evidence integrity using SHA-256 hashing.
* Export recovered information as CSV.
* Generate structured HTML forensic reports.
* Support analysis of decrypted WhatsApp database files.

## System Architecture

```text
WhatsApp Database / WAL Files
            │
            ▼
     Evidence Acquisition
            │
            ▼
 ┌─────────────────────────┐
 │ SQLite Database Analysis│
 │ Active Messages         │
 │ Deleted Markers         │
 └─────────────────────────┘
            │
            ▼
 ┌─────────────────────────┐
 │ WAL File Analysis       │
 │ Frame & Page Processing │
 │ String Extraction       │
 └─────────────────────────┘
            │
            ▼
      Evidence Correlation
            │
            ▼
     Timeline Construction
            │
            ▼
 ┌─────────────────────────┐
 │ Streamlit Dashboard     │
 │ CSV Export               │
 │ HTML Forensic Report    │
 └─────────────────────────┘
```

## How It Works

The project works with WhatsApp's SQLite database and associated WAL file.

### 1. Database Analysis

The tool connects to the supplied `msgstore.db` database and analyzes the `message` table.

It extracts information such as:

* Message ID
* Sender / chat
* Message text
* Timestamp
* Message status
* Message direction
* Message type

The implementation supports different WhatsApp database schemas by checking whether the message text is stored in `text_data` or `data`.

### 2. Deleted Message Identification

The tool searches for message records where the message text is unavailable and treats them as **deleted markers**.

These records are retained in the forensic timeline even when the original message text cannot be recovered.

### 3. WAL Analysis

The project analyzes the SQLite WAL file by:

* Reading the WAL header.
* Processing WAL frames.
* Reading page data.
* Extracting printable strings.
* Filtering out common SQLite/system strings.
* Identifying strings that may represent message content.

Recovered strings are marked with their corresponding WAL frame and page as the evidence source.

### 4. Timeline Construction

Active messages, deleted markers, and WAL-recovered strings are combined into a single timeline.

Message timestamps are converted from milliseconds into a human-readable date and time.

### 5. Evidence Integrity

SHA-256 hashes are calculated for the database and WAL files to help verify evidence integrity.

An evidence log can record:

* Acquisition time
* Database path
* Database SHA-256 hash
* WAL path
* WAL SHA-256 hash

### 6. Report Generation

The tool can generate:

* **CSV files** containing the analyzed message entries.
* **HTML forensic reports** containing message details, timestamps, sources, and summary statistics.

## Decryption Support

The project also contains a decryption module for processing encrypted WhatsApp database files such as `.crypt14`.

The decryption workflow uses an extracted WhatsApp key and produces a decrypted `msgstore.db` that can then be analyzed by the recovery pipeline.

## Technology Stack

* **Python**
* **SQLite**
* **Pandas**
* **Streamlit**
* **Android Debug Bridge (ADB)**
* **SHA-256**
* **HTML**
* **CSV**
* **WhatsApp SQLite/WAL artifacts**

## Project Structure

```text
whatsapp_forensics/
│
├── app.py                  # Streamlit forensic analysis interface
├── recovery.py             # Core database and WAL recovery functions
├── decrypt_db.py           # WhatsApp encrypted database decryption
│
├── check_msgs.py           # Database message inspection
├── check_wal.py            # WAL printable-string inspection
├── search_wal.py           # Search for specific strings in WAL
├── test.py                 # WAL parsing/testing
│
├── create_test_db.py       # Creates a test database and simulated WAL
├── simulate_wal.py         # Simulates message deletion and WAL creation
│
├── msgstore.db             # WhatsApp SQLite database
├── msgstore_backup.db      # Database backup
├── wal_file.db             # WAL file used for analysis
├── shm_file.db             # SQLite shared-memory artifact
├── shm_backup              # SHM backup
├── key                     # WhatsApp decryption key
│
├── recovered_messages.csv  # Recovered/analyzed messages
├── forensic_report.html    # Generated forensic report
├── evidence_log.txt        # Evidence integrity log
└── commands.txt            # Acquisition and execution commands
```

## Installation

Clone the repository and install the required Python packages:

```bash
git clone <repository-url>
cd whatsapp_forensics

pip install streamlit pandas
```

For encrypted WhatsApp database decryption, install the required WhatsApp cryptographic package used by `decrypt_db.py`.

## Running the Project

Start the Streamlit application:

```bash
streamlit run app.py
```

The application opens a browser interface where you can upload:

```text
msgstore.db
wal_file.db
```

The tool then:

1. Calculates the database hash.
2. Extracts active messages.
3. Identifies deleted markers.
4. Processes the WAL file.
5. Builds the forensic timeline.
6. Displays the recovered/analyzed entries.
7. Provides CSV and HTML report downloads.

## Experimental Testing

The project includes scripts for creating a controlled forensic test environment.

```bash
python create_test_db.py
python recovery.py
streamlit run app.py
```

`simulate_wal.py` can also be used to simulate message deletion and create a WAL containing test message content.

For Android emulator-based acquisition, ADB commands are provided in `commands.txt`.

## Output

The tool produces:

### CSV Report

Contains fields such as:

```text
Message ID
Sender
Message Text
Timestamp
Status
From Me
Source
Datetime
```

### HTML Forensic Report

The generated report provides:

* Active message count
* Deleted marker count
* WAL recovered count
* Total entries
* Date/time
* Contact or group
* Message direction
* Message content
* Evidence source

## Current Limitations

* WAL recovery currently focuses on extracting printable strings from WAL pages rather than fully reconstructing SQLite records.
* Recovery depends on the WAL data still containing recoverable information.
* WAL checkpointing or overwriting can remove previously recoverable data.
* Not every deleted message can be recovered.
* The project is primarily tested using controlled Android emulator data.
* WhatsApp database schemas may change between application versions.

## Future Improvements

* Implement deeper SQLite WAL record reconstruction.
* Improve deleted-message identification and correlation.
* Support additional WhatsApp database versions.
* Automate Android artifact acquisition using ADB.
* Add media and attachment analysis.
* Improve evidence correlation between database, WAL, and backup files.
* Add advanced forensic timeline visualization.
* Generate standardized forensic investigation reports.

## Project Status

**Research / Prototype**

WhatsApp Forensics is a research-oriented digital forensics project focused on analyzing WhatsApp SQLite databases and WAL artifacts, recovering potentially available message remnants, and presenting the findings through a forensic analysis interface.


