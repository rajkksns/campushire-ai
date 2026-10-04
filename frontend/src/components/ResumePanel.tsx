/**
 * Resume panel (Task 15.2, Requirements 5.1-5.6, 22.1, 22.3).
 *
 * Two ways to submit a resume for the active profile:
 *   - paste raw text (JSON body `{ content }`);
 *   - upload a file (`text/plain` or `application/pdf`), sent as multipart.
 *
 * Submitting replaces any prior resume (5.6). The backend applies ordered
 * guards and may respond 415 (unsupported media type), 413 (too large), or 422
 * (empty); those messages are surfaced inline (14.4). The profile detail does
 * not echo stored resume text, so success is confirmed via the returned
 * `updated_at` timestamp.
 *
 * Accessibility: both the textarea and the file input have associated
 * `<label htmlFor>` elements (22.1); errors/status are linked via
 * `aria-describedby` and announced with `role` (22.3).
 */

import { useState } from 'react';

import { ApiError } from '../api/apiClient';
import * as api from '../api/apiClient';
import { RESUME_MEDIA_TYPES } from '../types';

interface ResumePanelProps {
  profileId: string;
}

type Mode = 'paste' | 'upload';

export function ResumePanel({ profileId }: ResumePanelProps) {
  const [mode, setMode] = useState<Mode>('paste');
  const [text, setText] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handlePaste(event: React.FormEvent) {
    event.preventDefault();
    if (!text.trim()) {
      setError('Resume text must not be empty.');
      setStatus(null);
      return;
    }
    await submit(() => api.saveResumeText(profileId, text));
  }

  async function handleUpload(event: React.FormEvent) {
    event.preventDefault();
    if (!file) {
      setError('Choose a resume file to upload.');
      setStatus(null);
      return;
    }
    await submit(() => api.uploadResumeFile(profileId, file));
  }

  async function submit(action: () => Promise<{ updated_at: string }>) {
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      const result = await action();
      setStatus(`Resume saved (updated ${result.updated_at}).`);
      setText('');
      setFile(null);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : 'Could not save the resume.',
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel" aria-label="Resume">
      <h2>Resume</h2>

      {error && (
        <div className="banner banner-error" role="alert">
          {error}
        </div>
      )}
      {status && (
        <div className="banner banner-info" role="status">
          {status}
        </div>
      )}

      <div
        className="app-nav"
        role="tablist"
        aria-label="Resume input method"
        style={{ margin: '0 0 16px' }}
      >
        <button
          type="button"
          role="tab"
          className="nav-tab"
          aria-selected={mode === 'paste'}
          aria-current={mode === 'paste'}
          onClick={() => setMode('paste')}
        >
          Paste text
        </button>
        <button
          type="button"
          role="tab"
          className="nav-tab"
          aria-selected={mode === 'upload'}
          aria-current={mode === 'upload'}
          onClick={() => setMode('upload')}
        >
          Upload file
        </button>
      </div>

      {mode === 'paste' ? (
        <form onSubmit={handlePaste} aria-label="Paste resume text">
          <div className="field">
            <label htmlFor="resume-text">Resume text</label>
            <textarea
              id="resume-text"
              value={text}
              onChange={(e) => setText(e.target.value)}
              aria-describedby="resume-text-hint"
              style={{ minHeight: 180 }}
            />
            <span id="resume-text-hint" className="field-hint">
              Paste the full text of your resume.
            </span>
          </div>
          <button className="btn" type="submit" disabled={busy}>
            Save resume
          </button>
        </form>
      ) : (
        <form onSubmit={handleUpload} aria-label="Upload resume file">
          <div className="field">
            <label htmlFor="resume-file">Resume file</label>
            <input
              id="resume-file"
              type="file"
              accept={RESUME_MEDIA_TYPES.join(',')}
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              aria-describedby="resume-file-hint"
            />
            <span id="resume-file-hint" className="field-hint">
              Accepted: plain text (.txt) or PDF (.pdf), up to 5 MB.
            </span>
          </div>
          <button className="btn" type="submit" disabled={busy}>
            Upload resume
          </button>
        </form>
      )}
    </section>
  );
}
