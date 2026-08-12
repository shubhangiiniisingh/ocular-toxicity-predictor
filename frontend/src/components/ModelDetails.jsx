import React from 'react';
import { FileText, Cpu, Database, CheckCircle, List } from 'lucide-react';

export default function ModelDetails({ modelInfo }) {
  return (
    <div>
      <div className="header-banner">
        <div className="page-title">
          <FileText style={{ color: 'var(--accent-purple)' }} size={32} />
          Model Specifications & Technical Details
        </div>
        <div className="page-description">
          Technical specifications for the pre-trained ExtraTrees Classifier, RDKit descriptor filtering methodology, and research performance validation.
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: '32px' }}>
        {/* Model Specs Card */}
        <div className="glass-card">
          <div className="card-title">
            <Cpu size={20} style={{ color: 'var(--accent-cyan)' }} />
            Machine Learning Classifier
          </div>

          <table className="data-table" style={{ marginTop: '12px' }}>
            <tbody>
              <tr>
                <td style={{ color: 'var(--text-dim)', fontWeight: 600 }}>Algorithm</td>
                <td style={{ fontWeight: 700, color: 'var(--accent-cyan)' }}>{modelInfo?.algorithm || 'ExtraTreesClassifier'}</td>
              </tr>
              <tr>
                <td style={{ color: 'var(--text-dim)', fontWeight: 600 }}>Feature Representation</td>
                <td>RDKit 2D Molecular Descriptors</td>
              </tr>
              <tr>
                <td style={{ color: 'var(--text-dim)', fontWeight: 600 }}>Final Feature Count</td>
                <td><strong>165 Filtered Descriptors</strong> (from ~208 raw)</td>
              </tr>
              <tr>
                <td style={{ color: 'var(--text-dim)', fontWeight: 600 }}>Decision Boundary</td>
                <td>Optimized Threshold <strong>{modelInfo?.threshold || '0.45'}</strong></td>
              </tr>
              <tr>
                <td style={{ color: 'var(--text-dim)', fontWeight: 600 }}>Resampling Strategy</td>
                <td>SMOTE (Synthetic Minority Over-sampling Technique)</td>
              </tr>
              <tr>
                <td style={{ color: 'var(--text-dim)', fontWeight: 600 }}>Training Date</td>
                <td>{modelInfo?.created_on || '2026-08-07'}</td>
              </tr>
            </tbody>
          </table>
        </div>

        {/* Dataset Breakdown */}
        <div className="glass-card">
          <div className="card-title">
            <Database size={20} style={{ color: 'var(--accent-emerald)' }} />
            Training & Validation Datasets
          </div>

          <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)', lineHeight: '1.6' }}>
            <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--border-color)', marginBottom: '12px' }}>
              <div style={{ fontWeight: 700, color: '#ffffff' }}>Internal Dataset (4,901 Compounds)</div>
              <div style={{ fontSize: '0.82rem', marginTop: '4px' }}>
                Split into 3,920 Training compounds (1,765 Toxic / 2,155 Non-Toxic) and 981 Test compounds (445 Toxic / 536 Non-Toxic).
              </div>
            </div>

            <div style={{ padding: '12px', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
              <div style={{ fontWeight: 700, color: '#ffffff' }}>External Validation Dataset (266 Compounds)</div>
              <div style={{ fontSize: '0.82rem', marginTop: '4px' }}>
                Completely independent external validation dataset evaluated to verify out-of-sample generalization (External AUC: 0.7514).
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Terminal Performance Console Card */}
      <div className="glass-card terminal-card" style={{ marginBottom: '32px' }}>
        <div className="terminal-header">
          <div className="terminal-dots">
            <span className="dot red"></span>
            <span className="dot yellow"></span>
            <span className="dot green"></span>
          </div>
          <span className="terminal-title">Performance Metrics Console</span>
        </div>
        <div className="terminal-body">
          <div className="terminal-row">Dataset size:     <span className="term-val">4,901</span></div>
          <div className="terminal-row">Toxic:            <span className="term-val">2,210</span></div>
          <div className="terminal-row">Non-toxic:        <span className="term-val">2,691</span></div>
          <br />
          <div className="terminal-row">Test samples:     <span className="term-val">981</span></div>
          <br />
          <div className="terminal-row">Accuracy:         <span className="term-val">79.71%</span></div>
          <div className="terminal-row">Precision:        <span className="term-val">78.47%</span></div>
          <div className="terminal-row">Recall:           <span className="term-val">76.18%</span></div>
          <div className="terminal-row">F1 Score:         <span className="term-val">77.31%</span></div>
          <br />
          <div className="terminal-row" style={{ fontWeight: 'bold', color: 'var(--lime)' }}>Confusion Matrix</div>
          <br />
          <div className="terminal-matrix">
            <pre>{`                Predicted
               0        1
Actual 0      443       93   (TN / FP)
Actual 1      106      339   (FN / TP)`}</pre>
          </div>
        </div>
      </div>

      {/* Feature Selection Pipeline */}
      <div className="glass-card">
        <div className="card-title">
          <List size={20} style={{ color: 'var(--accent-amber)' }} />
          4-Step Descriptor Selection Pipeline
        </div>

        <div className="grid-4" style={{ marginTop: '16px' }}>
          <div style={{ padding: '16px', background: 'rgba(10,15,26,0.6)', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '0.8rem', color: 'var(--accent-cyan)', fontWeight: 700 }}>STEP 1</div>
            <div style={{ fontWeight: 700, color: '#ffffff', marginTop: '4px' }}>NaN Filtering</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '6px' }}>
              Extracted 208 descriptors using RDKit. Dropped descriptors with &gt;20% missing values across compounds.
            </div>
          </div>

          <div style={{ padding: '16px', background: 'rgba(10,15,26,0.6)', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '0.8rem', color: 'var(--accent-teal)', fontWeight: 700 }}>STEP 2</div>
            <div style={{ fontWeight: 700, color: '#ffffff', marginTop: '4px' }}>Median Imputation</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '6px' }}>
              Imputed remaining missing values and infinite values using column medians from the training set.
            </div>
          </div>

          <div style={{ padding: '16px', background: 'rgba(10,15,26,0.6)', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '0.8rem', color: 'var(--accent-purple)', fontWeight: 700 }}>STEP 3</div>
            <div style={{ fontWeight: 700, color: '#ffffff', marginTop: '4px' }}>Variance Threshold</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '6px' }}>
              Applied VarianceThreshold filter (threshold = 0.01) to eliminate non-informative constant features.
            </div>
          </div>

          <div style={{ padding: '16px', background: 'rgba(10,15,26,0.6)', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
            <div style={{ fontSize: '0.8rem', color: 'var(--accent-emerald)', fontWeight: 700 }}>STEP 4</div>
            <div style={{ fontWeight: 700, color: '#ffffff', marginTop: '4px' }}>Correlation Filter</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '6px' }}>
              Calculated pairwise Pearson correlations and removed redundant features with r &gt; 0.95, yielding 165 features.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
