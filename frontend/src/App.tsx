/**
 * App shell and navigation (Task 15.1, Requirement 14.1).
 *
 * Owns the top-level application state:
 *   - the active profile (id + name), lifted here so both the Profile view and
 *     the Analysis view operate against the same selected profile;
 *   - which view is currently shown (profile vs. analysis).
 *
 * Navigation is a simple two-tab switch. The Analysis tab is disabled until a
 * profile is active, because an analysis is always run against a profile.
 *
 * The real view components are introduced one at a time as Task 15 proceeds.
 * Until a given view exists, a small inline placeholder stands in so the app
 * always compiles and runs. `ProfileView` is wired in first.
 */

import { useState } from 'react';

import { ProfileView } from './views/ProfileView';

/** The identity of the currently selected profile, shared across views. */
export interface ActiveProfile {
  id: string;
  name: string;
}

type ViewKey = 'profile' | 'analysis';

export default function App() {
  const [activeProfile, setActiveProfile] = useState<ActiveProfile | null>(
    null,
  );
  const [view, setView] = useState<ViewKey>('profile');

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <h1 className="app-title">CampusHire AI</h1>
          <p className="app-subtitle">
            Placement-readiness and skill-gap analysis
          </p>
        </div>
        {activeProfile && (
          <div aria-live="polite">
            <span className="field-hint">Active profile</span>
            <br />
            <strong>{activeProfile.name}</strong>{' '}
            <span className="field-hint">({activeProfile.id})</span>
          </div>
        )}
      </header>

      <nav className="app-nav" aria-label="Primary">
        <button
          type="button"
          className="nav-tab"
          aria-current={view === 'profile'}
          onClick={() => setView('profile')}
        >
          Profile
        </button>
        <button
          type="button"
          className="nav-tab"
          aria-current={view === 'analysis'}
          onClick={() => setView('analysis')}
          disabled={!activeProfile}
          title={
            activeProfile ? undefined : 'Select or create a profile first'
          }
        >
          Analysis
        </button>
      </nav>

      <main>
        {view === 'profile' ? (
          <ProfileView
            activeProfile={activeProfile}
            onActiveProfileChange={setActiveProfile}
          />
        ) : (
          <AnalysisPlaceholder />
        )}
      </main>
    </div>
  );
}

/**
 * Temporary stand-in for the Analysis view (built in Task 15.3). Keeps the
 * app runnable while the real view is pending.
 */
function AnalysisPlaceholder() {
  return (
    <section className="panel" aria-label="Analysis">
      <h2>Analysis</h2>
      <p className="empty-note">
        The analysis view is coming next. Add skills and a resume on the
        Profile tab in the meantime.
      </p>
    </section>
  );
}
