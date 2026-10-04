/**
 * Certifications panel (Task 15.2, Requirements 3.1-3.3, 3.4, 3.5, 22.1, 22.3).
 *
 * Lists the active profile's certifications and provides add/remove. The list
 * is driven by the shared profile detail that `ProfileView` reloads whenever
 * the active profile changes, satisfying the "re-fetch on active-profile
 * change" requirement (3.5): a profile switch reloads detail in the parent and
 * this panel re-renders from the new `certifications`. After a local add/remove
 * the panel calls `onChanged` so the parent reloads the source of truth.
 *
 * Accessibility: the name input is associated with a `<label htmlFor>` (22.1)
 * and the add error is linked via `aria-describedby` (22.3).
 */

import { useState } from 'react';

import { ApiError } from '../api/apiClient';
import * as api from '../api/apiClient';
import type { CertificationResponse } from '../types';

interface CertsPanelProps {
  profileId: string;
  certifications: CertificationResponse[];
  onChanged: () => void | Promise<void>;
}

export function CertsPanel({
  profileId,
  certifications,
  onChanged,
}: CertsPanelProps) {
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleAdd(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      setError('Certification name must not be empty.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.addCertification(profileId, { name: trimmed });
      setName('');
      await onChanged();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : 'Could not add the certification.',
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleRemove(certId: string) {
    setBusy(true);
    setError(null);
    try {
      await api.removeCertification(profileId, certId);
      await onChanged();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : 'Could not remove the certification.',
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel" aria-label="Certifications">
      <h2>Certifications</h2>

      {error && (
        <div className="banner banner-error" role="alert">
          {error}
        </div>
      )}

      <form
        onSubmit={handleAdd}
        aria-label="Add certification"
        aria-describedby="add-cert-error"
      >
        <div className="form-row">
          <div className="field">
            <label htmlFor="cert-name">Certification name</label>
            <input
              id="cert-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoComplete="off"
            />
          </div>
          <button className="btn" type="submit" disabled={busy}>
            Add certification
          </button>
        </div>
      </form>

      {certifications.length === 0 ? (
        <p className="empty-note" style={{ marginTop: 12 }}>
          No certifications yet.
        </p>
      ) : (
        <ul className="item-list" style={{ marginTop: 12 }}>
          {certifications.map((cert) => (
            <li key={cert.id} className="item-row">
              <span>{cert.name}</span>
              <button
                type="button"
                className="btn-danger"
                onClick={() => handleRemove(cert.id)}
                disabled={busy}
                aria-label={`Remove ${cert.name}`}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
