# 🛡️ Adaptive Fraud & Risk Scoring Engine

> A production-inspired Machine Learning & MLOps system for real-time fraud detection, explainability, drift monitoring, and automated retraining.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green)
![XGBoost](https://img.shields.io/badge/XGBoost-ML_Model-orange)
![SHAP](https://img.shields.io/badge/SHAP-Explainable_AI-red)
![Docker](https://img.shields.io/badge/Docker-Containerized-blue)
![MLOps](https://img.shields.io/badge/MLOps-Production-purple)

---

# 📌 Overview

Adaptive Fraud & Risk Scoring Engine is a production-inspired machine learning system designed to detect fraudulent financial transactions in real time.

Unlike traditional fraud detection projects that stop at model training, this project covers the complete ML lifecycle:

* Real-time transaction scoring
* Streaming feature engineering
* Imbalanced learning
* Explainable AI using SHAP
* Drift detection
* Automated retraining pipelines
* Load testing and scalability
* Monitoring dashboards
* Production deployment practices

The objective is to learn how modern fraud detection systems are designed, deployed, monitored, and continuously improved in real-world financial organizations.

---

# 🚨 Problem Statement

Fraud detection is one of the most challenging machine learning domains because:

* Fraud is extremely rare (<1% of transactions)
* Fraud patterns evolve continuously
* False positives impact customer experience
* Models must respond within milliseconds
* Regulatory requirements often demand explainable decisions

This project addresses these challenges through a combination of supervised learning, anomaly detection, explainability, and MLOps principles.

---

# 🎯 Project Goals

* Detect fraudulent transactions in real time
* Minimize false positives
* Generate explainable risk scores
* Monitor model performance in production
* Detect data and concept drift
* Automate retraining workflows
* Build a scalable and production-ready architecture

---

# 🏗️ System Architecture

```text
Transaction Stream
        │
        ▼
Feature Engineering
        │
        ▼
XGBoost + Isolation Forest
        │
        ▼
Risk Scoring Engine
        │
        ▼
SHAP Explainability
        │
        ▼
Decision Engine
        │
        ▼
Allow / Challenge / Block
        │
        ▼
Feedback Collection
        │
        ▼
Drift Detection (PSI)
        │
        ▼
Retraining Pipeline
```

---

# ⚙️ Core Features

## Real-Time Risk Scoring

* FastAPI-based prediction service
* Fraud probability scoring
* Risk score (0–100)
* Low-latency inference

## Advanced Feature Engineering

### Velocity Features

* Transactions per minute
* Transactions per hour
* Transactions per day

### Geo-Velocity Features

* Impossible travel detection
* Location change analysis

### Behavioral Features

* Spending deviation
* Time-of-day deviation
* Merchant novelty

### Device Intelligence

* New device detection
* IP/location changes

---

# 🤖 Machine Learning Models

| Model               | Purpose                  |
| ------------------- | ------------------------ |
| Logistic Regression | Baseline Model           |
| XGBoost             | Primary Fraud Classifier |
| Isolation Forest    | Novel Fraud Detection    |

---

# 🧠 Explainable AI

The system uses SHAP (SHapley Additive exPlanations) to explain predictions.

### Global Explanations

Understand which features influence fraud detection overall.

### Local Explanations

Understand why a specific transaction was flagged.

Example:

| Feature          | Contribution |
| ---------------- | ------------ |
| New Device       | +35%         |
| High Velocity    | +25%         |
| Unusual Location | +20%         |
| High Amount      | +12%         |

---

# 📊 Machine Learning Concepts Covered

This project is intentionally designed to cover real-world ML concepts:

* Feature Engineering
* Imbalanced Learning
* Logistic Regression
* XGBoost
* Isolation Forest
* SHAP Explainability
* Calibration
* Threshold Optimization
* Cost-Sensitive Learning
* Data Leakage Prevention
* Error Analysis
* Drift Detection
* Model Monitoring

---

# 🔄 MLOps Components

## Drift Detection

* Population Stability Index (PSI)
* Feature distribution monitoring
* Drift alerts

## Retraining Pipeline

* Feedback ingestion
* Scheduled retraining
* Model validation
* Safe model promotion

## Monitoring

* Latency
* Throughput
* Prediction distribution
* Fraud detection metrics

---

# 🚀 Production Engineering Concepts

* Stateless API Architecture
* Horizontal Scaling
* Async FastAPI
* Connection Pooling
* Caching Layer
* Docker Containerization
* CI/CD Pipelines
* Load Testing
* Monitoring & Alerting

---

# 🛠️ Technology Stack

## Backend

* Python
* FastAPI
* Scikit-Learn
* XGBoost
* SHAP

## Database

* PostgreSQL
* Supabase

## Dashboard

* Streamlit

## Infrastructure

* Docker
* GitHub Actions

## Testing

* Locust
* k6

---

# 📂 Project Structure

```text
adaptive-fraud-risk-scoring-engine/

├── api/
├── dashboard/
├── pipeline/
├── data/
├── docs/
│
├── research/
│   ├── 01_fraud_domain.md
│   ├── 02_feature_engineering.md
│   ├── 03_imbalance_learning.md
│   ├── 04_xgboost_notes.md
│   ├── 05_shap_notes.md
│   ├── 06_drift_detection.md
│   ├── 07_system_design.md
│   ├── calibration_analysis.md
│   ├── data_leakage.md
│   ├── error_analysis.md
│   ├── feature_dictionary.md
│   └── model_comparison.md
│
├── tests/
├── load-tests/
├── docker/
│
├── README.md
├── requirements.txt
├── Tracker.md
└── .gitignore
```

---

# 📚 Research & Learning Notes

The repository includes dedicated learning notes covering:

* Fraud Domain Knowledge
* Feature Engineering
* Imbalanced Learning
* XGBoost
* SHAP
* Drift Detection
* Data Leakage
* Calibration
* Error Analysis
* System Design

The goal is not only to build a working project but also to deeply understand every concept involved.

---

# 🗺️ Development Roadmap

### Phase 1

* Research & Planning
* Fraud Domain Study

### Phase 2

* Synthetic Transaction Generator
* Feature Engineering

### Phase 3

* Baseline Models
* Logistic Regression

### Phase 4

* XGBoost Risk Scoring

### Phase 5

* SHAP Explainability

### Phase 6

* FastAPI Deployment

### Phase 7

* Drift Detection

### Phase 8

* Load Testing & Optimization

---

# 🔮 Future Enhancements

* Kafka-based transaction streaming
* Redis Feature Store
* Kubernetes Deployment
* Real-time Drift Monitoring
* Ensemble Risk Models
* LLM-powered Fraud Investigation Assistant

---

# 🎓 Learning Outcomes

By completing this project, you will gain hands-on experience in:

* Machine Learning Engineering
* Feature Engineering
* Fraud Analytics
* Explainable AI
* MLOps
* Model Monitoring
* Drift Detection
* FastAPI
* Docker
* System Design
* Production ML Workflows

---

# 👨‍💻 Author

**Shubham Gupta**

Machine Learning • AI Engineering • MLOps

---

⭐ If you found this project interesting, consider giving it a star and following the development journey.
