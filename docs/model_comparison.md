# Model Comparison Report

The goal of this document is to have a ready, honest answer for "why didn't you use X" for every reasonable alternative — not just to justify the model you picked.

## Models Actually Used

| Model | Pros | Cons | Why Selected |
|---|---|---|---|
| Logistic Regression (baseline) | Simple, fast, naturally calibrated probabilities, easy to explain | Can't capture non-linear feature interactions | Used only as an honest floor — establishes the minimum bar any more complex model must clear |
| XGBoost | Handles non-linear interactions, native imbalance support (`scale_pos_weight`), strong track record on tabular fraud data, fast inference | Less naturally calibrated than logistic regression (needs calibration, see `calibration_analysis.md`), more hyperparameters to tune | Primary supervised classifier — best fit for tabular, imbalanced, feature-engineered fraud data |
| Isolation Forest | Unsupervised — catches fraud patterns with zero labeled examples; fast; works well in high dimensions | No probability calibration; harder to explain a single anomaly score to a non-technical stakeholder | Companion model specifically for catching novel fraud that XGBoost hasn't seen labeled examples of yet |

## Models Considered But Not Used

| Model | Why Not Selected |
|---|---|
| Random Forest | Reasonable alternative — bagging instead of boosting. Likely would perform similarly on this dataset size, but boosting typically edges out bagging on tabular fraud benchmarks because sequential error-correction handles the minority class signal better than independent trees averaged together. Document your own experiment result here if you actually test this. |
| Neural Network (MLP / tabular deep learning) | Tabular data with manually engineered features generally doesn't benefit enough from deep learning's representation-learning strength to justify the added training complexity, larger data requirements, and harder-to-calibrate/explain outputs. Gradient boosted trees remain the established strong baseline for tabular fraud data at this scale. |
| Logistic Regression (as the final model, not just baseline) | Too limited — fraud patterns involve non-linear interactions (e.g. high amount AND new device AND odd hour, combined, matters more than any one alone) that a linear model can't capture without extensive manual feature crosses. |
| LightGBM | A legitimate alternative to XGBoost — similar performance class, faster training via histogram-based splitting, particularly advantageous on larger datasets. At this project's data scale, the difference would likely be marginal; XGBoost was chosen for its more mature SHAP integration and broader documentation/community support at the time of building. |
| Support Vector Machine (SVM) | Doesn't scale well computationally to larger datasets, and probability outputs require additional calibration (Platt scaling) similarly to XGBoost — without the non-linear interaction handling or speed advantages of gradient boosting. |
| Rule-based system (no ML) | This is the system being explicitly replaced — see `PRD.md` Problem Statement for why fixed rules fail to adapt to evolving fraud patterns. |

## If You Actually Run the Random Forest Comparison

Fill this in if you have time — it turns a written justification into an experiment with real numbers, which is strictly better in an interview.

| Model | PR-AUC | Precision @ threshold | Recall @ threshold | Training time |
|---|---|---|---|---|
| Random Forest | | | | |
| XGBoost | | | | |

## Interview-ready answers

**Q: Why didn't you use Random Forest?**
> Your answer here, ideally backed by the table above if you ran the experiment.

**Q: Why not a neural network — wouldn't deep learning be more powerful?**
> Your answer here.

**Q: If you had 10x more data, would your model choice change?**
> Your answer here — this is a good one to think through honestly (e.g. at much larger scale, deep learning or LightGBM's speed advantage might tip the balance).
