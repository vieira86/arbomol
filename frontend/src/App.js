import React, { useState } from 'react';
import { Upload, TestTube, Download, AlertCircle, CheckCircle, Loader2, FileText, Atom } from 'lucide-react';
import axios from 'axios';
import './App.css';

// Backend URL: in development this points to localhost:8000, but in
// production/deployment it can (and should) be configured via the
// REACT_APP_API_URL environment variable (e.g. set in the frontend's
// docker-compose.yml).
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const MASSA_MINIMA = 200;
const MASSA_MAXIMA = 700;

const CLASS_STYLES = {
  dengue: { bg: 'rgba(220,38,38,0.08)', border: 'rgba(220,38,38,0.3)', text: '#b91c1c', badge: 'tag-dengue' },
  zika: { bg: 'rgba(13,148,136,0.1)', border: 'rgba(13,148,136,0.32)', text: '#0f766e', badge: 'tag-zika' },
  chikungunya: { bg: 'rgba(124,58,237,0.1)', border: 'rgba(124,58,237,0.32)', text: '#6d28d9', badge: 'tag-chik' },
};
const DEFAULT_CLASS_STYLE = { bg: '#f7f7f5', border: 'var(--card-border)', text: 'var(--text)' };

function App() {
  const [smiles, setSmiles] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [file, setFile] = useState(null);
  const [batchResult, setBatchResult] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [batchLoading, setBatchLoading] = useState(false);

  const handleSinglePrediction = async () => {
    if (!smiles.trim()) {
      setError('Please enter a valid SMILES string');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await axios.post(`${API_URL}/predict`, {
        smiles: smiles.trim()
      });

      if (response.data.erro) {
        setError(response.data.erro);
      } else {
        setResult(response.data);
      }
    } catch (err) {
      setError('Error connecting to the server. Check that the backend is running.');
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = (event) => {
    const uploadedFile = event.target.files[0];
    if (!uploadedFile) return;

    if (!uploadedFile.name.match(/\.(csv|xlsx|xls)$/)) {
      setError('Please select a CSV or Excel file');
      return;
    }

    setFile(uploadedFile);
    setError('');
    setBatchResult(null);
  };

  const handleBatchPrediction = async () => {
    if (!file) {
      setError('Please select a file first');
      return;
    }

    setBatchLoading(true);
    setError('');
    setBatchResult(null);
    setUploadProgress(0);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_URL}/predict_batch`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const progress = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          setUploadProgress(progress);
        },
      });

      setBatchResult(response.data);
    } catch (err) {
      if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError('Error processing the file. Check the format and try again.');
      }
      console.error('Error:', err);
    } finally {
      setBatchLoading(false);
      setUploadProgress(0);
    }
  };

  const handleDownload = async () => {
    if (!batchResult?.download_url) return;

    try {
      const response = await axios.get(`${API_URL}${batchResult.download_url}`, {
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'prediction_results.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('Error downloading the results file');
      console.error('Error:', err);
    }
  };

  const getClassStyle = (classe) => CLASS_STYLES[classe?.toLowerCase()] || DEFAULT_CLASS_STYLE;

  return (
    <div className="app-shell">
      <div className="bg-glow"></div>

      <header>
        <div className="logo">
          <Atom className="logo-icon" />
          Arbo<span>Mol</span>
        </div>
        <nav>
          <a href="#individual">Single Molecule</a>
          <a href="#lote">Batch</a>
          <a href="#sobre">About</a>
          <a href={`${API_URL}/docs`} target="_blank" rel="noopener noreferrer">API</a>
        </nav>
      </header>

      <section className="hero">
        <div className="hero-text">
          <span className="eyebrow">Computational Chemistry &amp; Machine Learning</span>
          <h1>ArboMol <span className="grad">Classificator</span></h1>
          <p>
            Enter a molecule's SMILES (or upload a file with several) and discover its
            potential activity against Dengue, Zika, or Chikungunya, using RDKit
            descriptors and a Machine Learning model trained for this classification task.
          </p>
          <div className="cta-row">
            <a className="btn btn-primary" href="#individual">
              <TestTube size={18} />
              Classify Molecule
            </a>
            <a className="btn btn-ghost" href="#lote">
              <Upload size={18} />
              Batch Processing
            </a>
          </div>
        </div>
      </section>

      <main>
        <div className="app-grid">
          {/* Single Prediction Card */}
          <div id="individual" className="app-card">
            <div className="app-card-head">
              <TestTube className="app-card-icon" />
              <h2>Single Molecule Classification</h2>
            </div>

            <div className="field">
              <label htmlFor="smiles-input">Molecule SMILES</label>
              <textarea
                id="smiles-input"
                value={smiles}
                onChange={(e) => setSmiles(e.target.value)}
                placeholder="E.g.: CCO"
                rows={3}
              />
            </div>

            <button
              onClick={handleSinglePrediction}
              disabled={loading}
              className="btn btn-primary btn-block"
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="spin" />
                  Processing...
                </>
              ) : (
                'Classify Molecule'
              )}
            </button>

            {result && (
              <div
                className="result-box fade-in"
                style={{
                  background: getClassStyle(result.classe).bg,
                  borderColor: getClassStyle(result.classe).border,
                  color: getClassStyle(result.classe).text,
                }}
              >
                <div className="result-box-head">
                  <CheckCircle size={18} />
                  <span>Result</span>
                </div>
                <p className="result-class">{result.classe}</p>
                <p className="result-meta">Molecular weight: {result.massa?.toFixed(2)} Da</p>
                <p className="result-smiles">SMILES: {result.smiles}</p>

                {result.probabilidades && (
                  <div className="prob-list">
                    {Object.entries(result.probabilidades)
                      .sort((a, b) => b[1] - a[1])
                      .map(([classe, prob]) => (
                        <div className="prob-row" key={classe}>
                          <span className="prob-label">{classe}</span>
                          <div className="prob-track">
                            <div
                              className="prob-fill"
                              style={{
                                width: `${(prob * 100).toFixed(1)}%`,
                                background: getClassStyle(classe).text,
                              }}
                            />
                          </div>
                          <span className="prob-value">{(prob * 100).toFixed(1)}%</span>
                        </div>
                      ))}
                  </div>
                )}

                {result.explicacao && result.explicacao.length > 0 && (
                  <div className="explain-box">
                    <p className="explain-title">Why this classification?</p>
                    <p className="explain-hint">
                      Molecular descriptors (RDKit) that most influenced the model's decision:
                    </p>
                    <ul className="explain-list">
                      {result.explicacao.map((item, idx) => (
                        <li key={idx} className="explain-item">
                          <span className="explain-name">{item.descritor}</span>
                          <span className="explain-value">= {item.valor}</span>
                          <span className={`explain-dir ${item.direcao === 'increases' ? 'up' : 'down'}`}>
                            {item.direcao === 'increases' ? '▲' : '▼'} {item.direcao}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Batch Prediction Card */}
          <div id="lote" className="app-card">
            <div className="app-card-head">
              <Upload className="app-card-icon" />
              <h2>Batch Classification</h2>
            </div>

            <div className="field">
              <label htmlFor="file-upload">File with Multiple SMILES</label>
              <div className="dropzone">
                <input
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={handleFileUpload}
                  id="file-upload"
                />
                <label htmlFor="file-upload">
                  <FileText size={36} />
                  <span className="dropzone-title">
                    {file ? file.name : 'Click to select a file'}
                  </span>
                  <span className="dropzone-hint">CSV or Excel (with a "Smiles" column)</span>
                </label>
              </div>
            </div>

            {file && (
              <button
                onClick={handleBatchPrediction}
                disabled={batchLoading}
                className="btn btn-primary btn-block"
              >
                {batchLoading ? (
                  <>
                    <Loader2 size={18} className="spin" />
                    Processing...
                  </>
                ) : (
                  'Process File'
                )}
              </button>
            )}

            {uploadProgress > 0 && (
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${uploadProgress}%` }} />
              </div>
            )}

            {batchResult && (
              <div className="result-box success fade-in">
                <div className="result-box-head">
                  <CheckCircle size={18} />
                  <span>Processing Complete!</span>
                </div>
                <p className="result-meta"><strong>Valid:</strong> {batchResult.validas} molecules</p>
                <p className="result-meta warn"><strong>Invalid:</strong> {batchResult.invalidas} molecules</p>

                {batchResult.validas > 0 && (
                  <button onClick={handleDownload} className="btn btn-ghost btn-block download-btn">
                    <Download size={16} />
                    Download Results
                  </button>
                )}

                {batchResult.erros && batchResult.erros.length > 0 && (
                  <div className="error-list">
                    <p className="error-list-title">Errors found:</p>
                    <ul>
                      {batchResult.erros.slice(0, 3).map((erro, idx) => (
                        <li key={idx}>{erro}</li>
                      ))}
                      {batchResult.erros.length > 3 && (
                        <li>... and {batchResult.erros.length - 3} more errors</li>
                      )}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {error && (
          <div className="result-box danger fade-in banner">
            <div className="result-box-head">
              <AlertCircle size={18} />
              <span>Error</span>
            </div>
            <p className="result-meta">{error}</p>
          </div>
        )}

        {/* Info Section */}
        <section id="sobre">
          <div className="section-head">
            <span className="eyebrow">About</span>
            <h2>About the Classification</h2>
            <p>How molecule screening works on this platform.</p>
          </div>

          <div className="about-grid">
            <div className="about-card">
              <div className="icon">🦟</div>
              <span className="tag tag-dengue">Dengue</span>
              <p>Molecules with potential activity against the Dengue virus.</p>
            </div>
            <div className="about-card">
              <div className="icon">🧬</div>
              <span className="tag tag-zika">Zika</span>
              <p>Molecules with potential activity against the Zika virus.</p>
            </div>
            <div className="about-card">
              <div className="icon">🔬</div>
              <span className="tag tag-chik">Chikungunya</span>
              <p>Molecules with potential activity against the Chikungunya virus.</p>
            </div>
          </div>

          <div className="note-box">
            <strong>Validation:</strong> every molecule is validated for molecular
            weight (between {MASSA_MINIMA} and {MASSA_MAXIMA} Da) before classification.
          </div>
        </section>
      </main>

      <footer>
        © {new Date().getFullYear()} ArboMol Classificator — a research project by{' '}
        <a href="https://rafaelvieira.org" target="_blank" rel="noopener noreferrer">
          Prof. Dr. Rafael Vieira
        </a>
        .
      </footer>
    </div>
  );
}

export default App;
