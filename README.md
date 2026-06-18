# Fraud-Detection-mlops

## Overview

Adaptive Fraud & Risk Scoring Engine is a production-inspired machine learning system designed to detect fraudulent financial transactions in real time.

Unlike traditional fraud detection projects that focus only on model training, this project covers the complete ML lifecycle:

* Real-time transaction scoring
* Feature engineering on streaming transaction data
* Imbalanced learning
* Explainable AI using SHAP
* Drift detection
* Automated retraining pipelines
* Load testing and horizontal scaling
* Dashboard-driven monitoring

The goal is to learn how real-world fraud detection systems are built and maintained in production environments.

---

## Problem Statement

Fraud detection is one of the most challenging machine learning domains because:

* Fraud is extremely rare (<1% of transactions)
* Fraud patterns constantly evolve
* False positives directly impact customer experience
* Models must make decisions within milliseconds
* Decisions often require explanations for compliance and auditing

This project addresses these challenges through a combination of supervised learning, anomaly detection, explainability, and MLOps practices.

---

## Key Features

### Real-Time Risk Scoring

* FastAPI-based scoring API
* Risk score (0–100)
* Allow / Challenge / Block decisions
* Low-latency inference

### Feature Engineering

* Velocity features
* Geo-velocity features
* Behavioral deviation features
* Device intelligence features

### Machine Learning Models

* Logistic Regression (Baseline)
* XGBoost (Primary Model)
* Isolation Forest (Novel Fraud Detection)

### Explainability

* SHAP-based local explanations
* Global feature importance analysis
* Per-transaction explanation reports

### Drift Monitoring

* Population Stability Index (PSI)
* Feature distribution monitoring
* Drift alerts

### Retraining Pipeline

* Feedback ingestion
* Scheduled retraining
* Validation and promotion workflow

### Scalability

* Stateless API architecture
* Horizontal scaling
* Connection pooling
* Caching layer
* Load-tested architecture

---

## Technology Stack

### Backend

* FastAPI
* Python
* XGBoost
* Scikit-learn
* SHAP

### Database

* PostgreSQL (Supabase)

### Dashboard

* Streamlit

### Infrastructure

* Docker
* GitHub Actions
* Locust / k6

---

## Project Architecture

Transaction Stream
↓
Feature Engineering
↓
Risk Scoring
↓
SHAP Explainability
↓
Decision Engine
↓
Feedback Collection
↓
Drift Detection
↓
Retraining Pipeline

---

## Learning Objectives

This project is designed to develop expertise in:

* Feature Engineering
* Imbalanced Learning
* Fraud Analytics
* Explainable AI
* MLOps
* Model Monitoring
* Drift Detection
* System Design
* Load Testing
* Production ML

---

## Research Notes

The repository contains dedicated learning notes covering:

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

These notes are maintained alongside the implementation to ensure deep understanding rather than tutorial-based development.

---

## Current Status

Project Status: Planning & Research Phase

Next Milestone:

* Data Foundations
* Synthetic Transaction Generator
* Fraud Dataset Analysis

---

## Author

Shubham Gupta

Machine Learning | AI Engineering | MLOps
