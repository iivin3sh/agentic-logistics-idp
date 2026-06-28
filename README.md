# Intelligent Logistics IDP Hub

https://agentic-logistics-idp-ubyq4ginjx9rotpknkajf2.streamlit.app/

An enterprise-grade Intelligent Document Processing (IDP) framework engineered to ingest, parse, validate, and audit complex supply chain and logistics documentation. The system utilizes the Gemini 2.5 platform for multimodal data extraction, enforces runtime structural integrity via Pydantic, coordinates relational storage logs in SQLite/PostgreSQL, and integrates localized vector embeddings for Retrieval-Augmented Generation (RAG).

## Core Architecture

The system consists of five decoupled operational components:
* **Orchestration and UI Engine (`app.py`):** A multi-tab Streamlit terminal managing real-time document ingestion pipelines, data visualizations, and interactive conversational agent states[cite: 1].
* **Pipeline Logic (`process_doc.py`):** Controls recursive self-correction processing streams, multimodal fallback mechanics, and fallback incident diagnostics[cite: 4].
* **Storage and Vector Analytics (`db_utils.py`):** Manages relational database operations, custom agent database tools, and vector embeddings within ChromaDB[cite: 2].
* **Data Validation Profiles (`schema.py`):** Structural Pydantic blueprints defining nested transaction item parameters across eight distinct logistics frameworks[cite: 5].
* **Document Processing Layer (`pdf_utils.py`):** Manages text-layer extraction and binary conversion into standalone page images for multimodal input fallback[cite: 3].

---

## Technical Features

### 1. Structured Output Enforcement & Self-Correction
The ingestion mechanism restricts model output to structured JSON matching predefined Pydantic frameworks[cite: 1, 4]. If parsing violations occur, runtime exceptions are caught recursively and routed back into an automated validation loop for self-correction[cite: 4]. Persistent structural validation failures initiate an exception reliability agent that analyzes tail-end logs to diagnose why schema alignment broke down[cite: 4].

### 2. Autonomous Agentic Workflows
The platform implements multiple agentic loops utilizing function-calling patterns:
* **Cross-Document Auditor:** Leverages specialized read tools to compare standalone data entries, identifying compliance issues and metrics variances across disparate files[cite: 1, 2].
* **Logistics Copilot:** Evaluates natural language input, formulates precise read-only SQL parameters, executes them against underlying tables, and renders structural insights[cite: 1, 2].

### 3. Grounded Retrieval-Augmented Generation (RAG)
An independent vector loop ingests local compliance manuals and operational standard operating procedures (SOPs)[cite: 1]. Document text is broken into window segments, converted to coordinate spaces using `text-embedding-004`, and committed to a local persistent ChromaDB collection to provide verifiable context for regulatory queries[cite: 1, 2].

### 4. Multimodal Fallback Capability
When processed PDF files contain unmapped text coordinates or raw scanned imagery, the pipeline routes the stream to an image processing block[cite: 1, 4]. Pages are rendered as individual byte streams and fed into the model's vision processing engine to preserve data capture[cite: 1, 4].

---

## Supported Document Types

The system establishes individual parent and nested child relationship tables for the following logistics artifacts:
* Bills of Lading and Shipping Containers[cite: 2, 5]
* Commercial Invoices and Line Items[cite: 2, 5]
* Packing Lists and Item Package Metrics[cite: 2, 5]
* Supplier Quotations and Part Records[cite: 2, 5]
* Certificates of Origin[cite: 2, 5]
* Warehouse Delivery Notes and Received Conditions[cite: 2, 5]
* Air and Sea Waybills[cite: 2, 5]
* Government Customs Declarations[cite: 2, 5]

---

## Environmental Configuration

The application checks configuration paths via environmental contexts to shift from local testing footprints to production cloud structures:

```bash
# Relational Database Target Configuration (Defaults to local shipments.db if absent)
export DATABASE_URL="postgresql://user:password@host:port/dbname"

# Google GenAI Authentication Token
export GEMINI_API_KEY="your_api_key_here"
