/**
 * Projects panel (Task 15.2, Requirements 4.1-4.4, 4.5, 22.1, 22.3).
 *
 * Lists the active profile's academic projects (title plus optional
 * description) and provides add/remove. Mirrors the backend `ProjectCreate`
 * contract: `title` is required and trimmed; `description` is optional and sent
 * only when non-empty, so an omitted description stays `null` server-side.
 *
 * The list is driven by the shared profile detail reloaded by `ProfileView`;
 * after a local add/remove the panel calls `onChanged` to reload the source of
 * truth.
 *
 * Accessibility: inputs are associated with `<label htmlFor>` (22.1); the add
 * error is linked via `aria-describedby` (22.3).
 */

import { useState } from 'react';

import { ApiError } from '../api/apiClient';
import * as api from '../api/apiClient';
import type { ProjectResponse } from '../types';

interface ProjectsPanelProps {
  profileId: string;
  projects: ProjectResponse[];
  onChanged: () => void | Promise<void>;
}

export function ProjectsPanel({
  profileId,
  projects,
  onChanged,
}: ProjectsPanelProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleAdd(event: React.FormEvent) {
    event.preventDefault();
    const trimmedTitle = title.trim();
    if (!trimmedTitle) {
      setError('Project title must not be empty.');
      return;
    }
    const trimmedDescription = description.trim();
    setBusy(true);
    setError(null);
    try {
      await api.addProject(profileId, {
        title: trimmedTitle,
        // Send the description only when present; omit otherwise so the
        // backend stores null (4.3).
        ...(trimmedDescription ? { description: trimmedDescription } : {}),
      });
      setTitle('');
      setDescription('');
      await onChanged();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : 'Could not add the project.',
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleRemove(projectId: string) {
    setBusy(true);
    setError(null);
    try {
      await api.removeProject(profileId, projectId);
      await onChanged();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : 'Could not remove the project.',
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel" aria-label="Projects">
      <h2>Projects</h2>

      {error && (
        <div className="banner banner-error" role="alert">
          {error}
        </div>
      )}

      <form
        onSubmit={handleAdd}
        aria-label="Add project"
        aria-describedby="add-project-error"
      >
        <div className="field">
          <label htmlFor="project-title">Project title</label>
          <input
            id="project-title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            autoComplete="off"
          />
        </div>
        <div className="field">
          <label htmlFor="project-description">
            Description <span className="field-hint">(optional)</span>
          </label>
          <textarea
            id="project-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            aria-describedby="project-description-hint"
          />
          <span id="project-description-hint" className="field-hint">
            What you built and the technologies used.
          </span>
        </div>
        <button className="btn" type="submit" disabled={busy}>
          Add project
        </button>
      </form>

      {projects.length === 0 ? (
        <p className="empty-note" style={{ marginTop: 12 }}>
          No projects yet.
        </p>
      ) : (
        <ul className="item-list" style={{ marginTop: 12 }}>
          {projects.map((project) => (
            <li
              key={project.id}
              className="item-row"
              style={{ alignItems: 'flex-start' }}
            >
              <div>
                <strong>{project.title}</strong>
                {project.description && (
                  <p style={{ margin: '4px 0 0', color: 'var(--muted)' }}>
                    {project.description}
                  </p>
                )}
              </div>
              <button
                type="button"
                className="btn-danger"
                onClick={() => handleRemove(project.id)}
                disabled={busy}
                aria-label={`Remove ${project.title}`}
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
