# 🚢 Autonomous Agentic Logistics IDP Hub (Proof of Concept)

An enterprise-grade, intelligent document processing (IDP) and compliance auditing application built for global supply chain operations. This system transitions processing from rigid textual data extraction into an autonomous reasoning loop capable of structural schema enforcement, text-to-SQL business intelligence querying, and tool-driven discrepancy self-auditing.

---

## 🌟 Core Architectural Features

* **Multimodal Extraction Pipeline:** Leverages `gemini-2.5-flash` with native structured Pydantic response schemas to cleanly parse chaotic logistical documentation (PDFs/Images) into structured data matrices.
* **Autonomous Analytical Auditor:** Employs a tool-calling reasoning agent loop that self-determines tracking lookups across isolated database architectures to surface weight variances, missing documents, and vendor name irregularities.
* **Deterministic Security Guardrails:** Includes a text-to-SQL business layer built with strict runtime string filters to block mutation statements (`DROP`, `INSERT`, etc.), neutralizing prompt injection risks.
* **Self-Healing Telemetry Operations:** Intercepts system execution anomalies and logs structural pipeline failures into a dead-letter registry framework for asynchronous developer review.

---

## 🛠️ Project Architecture & File Directory

```text
├── app.py               # Main Streamlit Web UI application orchestrator
├── db_utils.py          # Database schema layouts, multi-engine connections & transactional storage
├── pdf_utils.py         # Document data extraction pipeline & fallback Vision OCR engine
├── schema.py            # Strict structural Pydantic validation schemas
└── requirements.txt     # Complete runtime package dependency manifest
