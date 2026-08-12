import React, { useState } from 'react';
import { Upload, Download, Search, FileSpreadsheet, CheckCircle2, ShieldAlert, AlertCircle } from 'lucide-react';
import { DisclaimerAlert } from './SinglePredictor';

export default function BatchPredictor() {
  const API_BASE = import.meta.env.VITE_API_URL || '';
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setErrorMsg(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setErrorMsg('Please select an Excel (.xlsx) or CSV (.csv) file to upload.');
      return;
    }

    setLoading(true);
    setErrorMsg(null);

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await fetch(API_BASE + '/api/predict/batch', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Batch processing failed.');
      }

      setResults(data);
      setCurrentPage(1);
    } catch (err) {
      setErrorMsg(err.message);
      setResults(null);
    } finally {
      setLoading(false);
    }
  };

  const handleExportCSV = () => {
    if (!results || !results.results) return;

    const headers = ['Index', 'Compound Name', 'Input SMILES', 'Canonical SMILES', 'Prediction', 'Probability Toxic', 'MW', 'LogP', 'TPSA', 'AD Status'];
    const rows = results.results.map((r) => [
      r.index,
      `"${(r.compound_name || '-').replace(/"/g, '""')}"`,
      `"${r.input_smiles.replace(/"/g, '""')}"`,
      `"${r.canonical_smiles.replace(/"/g, '""')}"`,
      r.prediction,
      r.probability_toxic,
      r.mw,
      r.logp,
      r.tpsa,
      `"${r.ad_status}"`
    ]);

    const csvContent = [headers.join(','), ...rows.map((row) => row.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `OcularTox_Batch_Predictions.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const filteredResults = results?.results ? results.results.filter((r) =>
    (r.compound_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    r.input_smiles.toLowerCase().includes(searchTerm.toLowerCase()) ||
    r.canonical_smiles.toLowerCase().includes(searchTerm.toLowerCase()) ||
    r.prediction.toLowerCase().includes(searchTerm.toLowerCase())
  ) : [];

  const totalPages = Math.ceil(filteredResults.length / itemsPerPage);
  const currentResults = filteredResults.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  return (
    <div>
      <div className="header-banner">
        <div className="page-title">
          <FileSpreadsheet style={{ color: 'var(--accent-teal)' }} size={32} />
          Batch Compound Predictor
        </div>
        <div className="page-description">
          Upload an Excel (`.xlsx`) or CSV (`.csv`) file containing SMILES strings to calculate predictions and RDKit molecular descriptors in batch.
        </div>
      </div>

      <div className="glass-card" style={{ marginBottom: '32px' }}>
        <div className="card-title">Upload File for Batch Processing</div>
        
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          <input
            type="file"
            accept=".xlsx, .xls, .csv"
            onChange={handleFileChange}
            id="file-upload"
            style={{ display: 'none' }}
          />
          
          <label htmlFor="file-upload" className="btn-secondary" style={{ flex: 1, justifyContent: 'center', cursor: 'pointer', padding: '16px' }}>
            <Upload size={20} />
            {selectedFile ? selectedFile.name : 'Choose Excel (.xlsx) or CSV (.csv) file'}
          </label>

          <button className="btn-primary" onClick={handleUpload} disabled={loading || !selectedFile} style={{ padding: '16px 32px' }}>
            {loading ? <div className="spinner" /> : <FileSpreadsheet size={20} />}
            Process Batch
          </button>
        </div>

        {errorMsg && (
          <div style={{ marginTop: '16px', padding: '12px 16px', background: 'rgba(244, 63, 94, 0.1)', border: '1px solid var(--accent-crimson)', borderRadius: '8px', color: 'var(--accent-crimson)', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertCircle size={18} />
            {errorMsg}
          </div>
        )}
      </div>

      {/* Results Table */}
      {results && (
        <div className="glass-card" style={{ marginBottom: '32px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div>
              <div className="card-title" style={{ marginBottom: 0 }}>Batch Prediction Results</div>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                Processed {results.total_processed} compounds using column '{results.smiles_column_used}'.
              </div>
            </div>

            <div style={{ display: 'flex', gap: '12px' }}>
              <div style={{ position: 'relative', width: '220px' }}>
                <input
                  type="text"
                  className="input-text"
                  placeholder="Filter results..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  style={{ paddingLeft: '36px', fontSize: '0.85rem' }}
                />
                <Search size={16} style={{ position: 'absolute', left: '12px', top: '12px', color: 'var(--text-dim)' }} />
              </div>

              <button className="btn-secondary" onClick={handleExportCSV}>
                <Download size={16} />
                Export CSV
              </button>
            </div>
          </div>

          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Compound Name</th>
                  <th>Input SMILES</th>
                  <th>Canonical SMILES</th>
                  <th>Prediction</th>
                  <th>Prob. Toxic</th>
                  <th>MW</th>
                  <th>LogP</th>
                  <th>TPSA</th>
                  <th>Domain Status</th>
                </tr>
              </thead>
              <tbody>
                {currentResults.map((r, idx) => (
                  <tr key={idx}>
                    <td style={{ color: 'var(--text-dim)' }}>{r.index}</td>
                    <td style={{ fontWeight: 600, color: 'var(--lime)', fontSize: '0.85rem' }}>{r.compound_name || '-'}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem' }}>{r.input_smiles}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--text-muted)' }}>{r.canonical_smiles}</td>
                    <td>
                      {r.prediction === 'Toxic' ? (
                        <span className="badge badge-toxic"><ShieldAlert size={12} /> Toxic</span>
                      ) : r.prediction === 'Non-Toxic' ? (
                        <span className="badge badge-safe"><CheckCircle2 size={12} /> Non-Toxic</span>
                      ) : (
                        <span className="badge" style={{ background: 'rgba(255,255,255,0.05)', color: 'var(--text-dim)' }}>Invalid</span>
                      )}
                    </td>
                    <td style={{ fontWeight: 600 }}>{(r.probability_toxic * 100).toFixed(1)}%</td>
                    <td>{r.mw}</td>
                    <td>{r.logp}</td>
                    <td>{r.tpsa}</td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{r.ad_status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '20px', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
              <div>Showing Page {currentPage} of {totalPages}</div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button className="btn-secondary" onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))} disabled={currentPage === 1}>
                  Previous
                </button>
                <button className="btn-secondary" onClick={() => setCurrentPage((p) => Math.min(p + 1, totalPages))} disabled={currentPage === totalPages}>
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      <DisclaimerAlert />
    </div>
  );
}
