/**
 * Analysis view (Task 15.3, Requirements 6.1-6.4, 14.2, 14.3, 22.1).
 *
 * Lets the user paste a target job description and run an analysis against the
 * active profile. While the request is in flight a progress indicator is shown
 * and the control is disabled (14.3). On success the returned
 * {@link AnalysisResponse} is handed to {@link ResultsView} for display; on
 * failure a human-readable message is surfaced (14.4).
 *
 * The job description mirrors the backend contract: non-empty after trim and at
 * most {@link MAX_JOB_DESCRIPTION_LENGTH} characters (6.2, 6.3). A live counter
 * shows remaining headroom; the backend remains the authority and its 422
 * message is surfaced if the client guard is bypassed.
 *
 * Accessibility: the textarea has an associated `<label htmlFor>` (22.1); the
 * in-progress state is announced via `role="status"` and `aria-busy`.
 */

import { useState } from 'react';

import { ApiError } from '../api/apiClient';
import * as api from '../api/apiClient';
import type { ActiveProfile } from '../App';
import { MAX_JOB_DESCRIPTION_LENGTH, type AnalysisResponse } from '../types';
import { ResultsView } from './ResultsView';

interface AnalysisViewProps {
  activeProfile: ActiveProfile;
}

export function AnalysisView({ activeProfile }: AnalysisViewProps) {
  const [jobDescription, setJobDescription] = useState('');
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const length = jobDescription.length;
  const overLimit = length > MAX_JOB_DESCRIPTION_LENGTH;

  async function handleRun(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = jobDescription.trim();
    if (!trimmed) {
      setError('Enter a job description to analyze.');
      return;
    }
    if (trimmed.length > MAX_JOB_DESCRIPTION_LENGTH) {
      setError(
        `Job description must be at most ${MAX_JOB_DESCRIPTION_LENGTH} characters.`,
      );
      return;
    }
    setRunning(true);
    setError(null);
    try {
      const analysis = await api.createAnalysis(activeProfile.id, {
        job_description: trimmed,
      });
      setResult(analysis);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : 'Could not run the analysis.',
      );
      setResult(null);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div>
      <section className="panel" aria-label="Run analysis">
        <h2>Target job</h2>
        <p className="field-hint" style={{ marginTop: 0 }}>
          Analyzing for <strong>{activeProfile.name}</strong>
        </p>

        {error && (
          <div className="banner banner-error" role="alert">
            {error}
          </div>
        )}

        <form onSubmit={handleRun} aria-label="Run analysis">
          <div className="field">
            <label htmlFor="job-description">Job description</label>
            <textarea
              id="job-description"
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              aria-describedby="job-description-hint"
              aria-invalid={overLimit}
              style={{ minHeight: 200 }}
            />
            <span id="job-description-hint" className="field-hint">
              Paste the full job description.{' '}
              <span className={overLimit ? 'field-error' : undefined}>
                {length.toLocaleString()} /{' '}
                {MAX_JOB_DESCRIPTION_LENGTH.toLocaleString()} characters
              </span>
            </span>
          </div>

          <div className="form-row" style={{ alignItems: 'center' }}>
            <button
              className="btn"
              type="submit"
              disabled={running || overLimit}
            >
              {running ? 'Analyzing…' : 'Run analysis'}
            </button>
            {running && (
              <span role="status" aria-busy="true">
                <span className="spinner" aria-hidden="true" />
                Running analysis…
              </span>
            )}
          </div>
        </form>
      </section>

      {result && <ResultsView result={result} />}
    </div>
  );
}
