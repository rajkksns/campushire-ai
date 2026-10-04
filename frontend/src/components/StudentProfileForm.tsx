/**
 * Student profile form (Task 15.2, Requirements 1.1, 1.5, 1.6, 22.1, 22.3).
 *
 * Two responsibilities tied to profile identity:
 *   - create a new profile from a name;
 *   - load an existing profile by id, and rename the active profile.
 *
 * There is no "list all profiles" endpoint in the backend contract, so a
 * profile is selected either by creating it (the response carries the new id)
 * or by entering a known id to load. Both set the active profile on `App`.
 *
 * Accessibility: every input is associated with a `<label htmlFor>` (22.1) and
 * validation messages are rendered adjacent to their input and linked via
 * `aria-describedby` (22.3).
 */

import { useEffect, useState } from 'react';

import { ApiError } from '../api/apiClient';
import * as api from '../api/apiClient';
import type { ActiveProfile } from '../App';

interface StudentProfileFormProps {
  activeProfile: ActiveProfile | null;
  onActiveProfileChange: (profile: ActiveProfile | null) => void;
}

export function StudentProfileForm({
  activeProfile,
  onActiveProfileChange,
}: StudentProfileFormProps) {
  const [newName, setNewName] = useState('');
  const [loadId, setLoadId] = useState('');
  const [renameValue, setRenameValue] = useState(activeProfile?.name ?? '');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Keep the rename field in sync when the active profile changes elsewhere.
  useEffect(() => {
    setRenameValue(activeProfile?.name ?? '');
  }, [activeProfile?.id, activeProfile?.name]);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    const name = newName.trim();
    if (!name) {
      setError('Profile name must not be empty.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const created = await api.createProfile({ name });
      onActiveProfileChange({ id: created.id, name: created.name });
      setNewName('');
    } catch (err) {
      setError(messageFor(err, 'Could not create the profile.'));
    } finally {
      setBusy(false);
    }
  }

  async function handleLoad(event: React.FormEvent) {
    event.preventDefault();
    const id = loadId.trim();
    if (!id) {
      setError('Enter a profile id to load.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const detail = await api.getProfile(id);
      onActiveProfileChange({ id: detail.id, name: detail.name });
      setLoadId('');
    } catch (err) {
      setError(messageFor(err, 'Could not load that profile.'));
    } finally {
      setBusy(false);
    }
  }

  async function handleRename(event: React.FormEvent) {
    event.preventDefault();
    if (!activeProfile) return;
    const name = renameValue.trim();
    if (!name) {
      setError('Profile name must not be empty.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const updated = await api.updateProfile(activeProfile.id, { name });
      onActiveProfileChange({ id: updated.id, name: updated.name });
    } catch (err) {
      setError(messageFor(err, 'Could not rename the profile.'));
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    if (!activeProfile) return;
    setBusy(true);
    setError(null);
    try {
      await api.deleteProfile(activeProfile.id);
      onActiveProfileChange(null);
    } catch (err) {
      setError(messageFor(err, 'Could not delete the profile.'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel" aria-label="Student profile">
      <h2>Student profile</h2>

      {error && (
        <div className="banner banner-error" role="alert">
          {error}
        </div>
      )}

      {!activeProfile ? (
        <div className="form-row" style={{ alignItems: 'flex-start' }}>
          <form onSubmit={handleCreate} aria-label="Create profile">
            <div className="field">
              <label htmlFor="new-profile-name">New profile name</label>
              <input
                id="new-profile-name"
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                aria-describedby="new-profile-name-hint"
                autoComplete="off"
              />
              <span id="new-profile-name-hint" className="field-hint">
                e.g. your full name
              </span>
            </div>
            <button className="btn" type="submit" disabled={busy}>
              Create profile
            </button>
          </form>

          <form onSubmit={handleLoad} aria-label="Load profile by id">
            <div className="field">
              <label htmlFor="load-profile-id">Load existing by id</label>
              <input
                id="load-profile-id"
                type="text"
                value={loadId}
                onChange={(e) => setLoadId(e.target.value)}
                aria-describedby="load-profile-id-hint"
                autoComplete="off"
              />
              <span id="load-profile-id-hint" className="field-hint">
                paste a profile id to resume
              </span>
            </div>
            <button className="btn btn-secondary" type="submit" disabled={busy}>
              Load profile
            </button>
          </form>
        </div>
      ) : (
        <form onSubmit={handleRename} aria-label="Rename profile">
          <div className="field">
            <label htmlFor="rename-profile">Profile name</label>
            <input
              id="rename-profile"
              type="text"
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              aria-describedby="rename-profile-hint"
              autoComplete="off"
            />
            <span id="rename-profile-hint" className="field-hint">
              id: {activeProfile.id}
            </span>
          </div>
          <div className="form-row">
            <button className="btn" type="submit" disabled={busy}>
              Save name
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => onActiveProfileChange(null)}
              disabled={busy}
            >
              Switch profile
            </button>
            <button
              type="button"
              className="btn-danger"
              onClick={handleDelete}
              disabled={busy}
            >
              Delete profile
            </button>
          </div>
        </form>
      )}
    </section>
  );
}

/** Reduce any thrown value to a human-readable message for display (14.4). */
function messageFor(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}
