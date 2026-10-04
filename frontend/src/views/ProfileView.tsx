/**
 * Profile view (Task 15.2, Requirements 1.6, 2.8, 3.4, 3.5, 4.5, 5.1, 22).
 *
 * Container for everything tied to a single student profile:
 *   - StudentProfileForm: create a new profile, or rename the active one;
 *   - once a profile is active, the full detail is loaded from the API and the
 *     Skills / Certifications / Projects / Resume panels are shown.
 *
 * The active profile is owned by `App`; this view reports changes upward via
 * `onActiveProfileChange` and reloads detail whenever the active id changes.
 *
 * Panels are introduced one at a time as Task 15 proceeds; until a panel
 * exists an inline placeholder stands in so the app keeps compiling. The
 * detail-reload callback (`reloadDetail`) is passed down so a panel can refresh
 * the shared profile detail after it mutates a collection.
 */

import { useCallback, useEffect, useState } from 'react';

import { ApiError } from '../api/apiClient';
import * as api from '../api/apiClient';
import type { ActiveProfile } from '../App';
import type { ProfileDetailResponse } from '../types';
import { StudentProfileForm } from '../components/StudentProfileForm';

interface ProfileViewProps {
  activeProfile: ActiveProfile | null;
  onActiveProfileChange: (profile: ActiveProfile | null) => void;
}

export function ProfileView({
  activeProfile,
  onActiveProfileChange,
}: ProfileViewProps) {
  const [detail, setDetail] = useState<ProfileDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeId = activeProfile?.id ?? null;

  const reloadDetail = useCallback(async () => {
    if (!activeId) {
      setDetail(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const loaded = await api.getProfile(activeId);
      setDetail(loaded);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : 'Failed to load the profile. Please try again.',
      );
      setDetail(null);
    } finally {
      setLoading(false);
    }
  }, [activeId]);

  // Reload whenever the active profile changes (3.5: panels re-fetch on
  // active-profile change — the shared detail reload covers certs/projects).
  useEffect(() => {
    void reloadDetail();
  }, [reloadDetail]);

  return (
    <div>
      <StudentProfileForm
        activeProfile={activeProfile}
        onActiveProfileChange={onActiveProfileChange}
      />

      {!activeProfile && (
        <section className="panel">
          <p className="empty-note">
            Create a profile above, or load one by id, to begin adding skills,
            certifications, projects, and a resume.
          </p>
        </section>
      )}

      {activeProfile && (
        <>
          {error && (
            <div className="banner banner-error" role="alert">
              {error}
            </div>
          )}
          {loading && (
            <div className="banner banner-info">
              <span className="spinner" aria-hidden="true" />
              Loading profile…
            </div>
          )}

          {detail && (
            <>
              <SkillsPlaceholder />
              <CertsPlaceholder />
              <ProjectsPlaceholder />
              <ResumePlaceholder />
            </>
          )}
        </>
      )}
    </div>
  );
}

/* Temporary stand-ins — each replaced by its real panel as Task 15 proceeds. */

function SkillsPlaceholder() {
  return (
    <section className="panel" aria-label="Skills">
      <h2>Skills</h2>
      <p className="empty-note">Skills panel coming next.</p>
    </section>
  );
}

function CertsPlaceholder() {
  return (
    <section className="panel" aria-label="Certifications">
      <h2>Certifications</h2>
      <p className="empty-note">Certifications panel coming next.</p>
    </section>
  );
}

function ProjectsPlaceholder() {
  return (
    <section className="panel" aria-label="Projects">
      <h2>Projects</h2>
      <p className="empty-note">Projects panel coming next.</p>
    </section>
  );
}

function ResumePlaceholder() {
  return (
    <section className="panel" aria-label="Resume">
      <h2>Resume</h2>
      <p className="empty-note">Resume panel coming next.</p>
    </section>
  );
}
