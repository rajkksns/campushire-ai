/**
 * Skills panel (Task 15.2, Requirements 2.1-2.7, 2.8, 22.1, 22.3).
 *
 * Lists the active profile's skills split into two separate labeled groups —
 * Technical and Soft (2.8) — and provides an add form plus per-skill removal.
 *
 * Add form fields mirror the backend `SkillCreate` contract: `name` (required,
 * trimmed), `skill_type` (technical | soft), and `proficiency` (integer 1..5,
 * defaulting to 1 when the input is left at its default). A case-insensitive
 * duplicate is rejected by the backend with 409; that message is surfaced
 * inline (14.4).
 *
 * After any mutation the panel calls `onChanged` so the parent reloads the
 * shared profile detail and the groups re-render from the source of truth.
 *
 * Accessibility: inputs use `<label htmlFor>` (22.1); the add error is linked
 * to the form via `aria-describedby` (22.3).
 */

import { useState } from 'react';

import { ApiError } from '../api/apiClient';
import * as api from '../api/apiClient';
import {
  MAX_PROFICIENCY,
  MIN_PROFICIENCY,
  type SkillResponse,
  type SkillType,
} from '../types';

interface SkillsPanelProps {
  profileId: string;
  skills: SkillResponse[];
  onChanged: () => void | Promise<void>;
}

export function SkillsPanel({ profileId, skills, onChanged }: SkillsPanelProps) {
  const [name, setName] = useState('');
  const [skillType, setSkillType] = useState<SkillType>('technical');
  const [proficiency, setProficiency] = useState<number>(MIN_PROFICIENCY);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const technical = skills.filter((s) => s.skill_type === 'technical');
  const soft = skills.filter((s) => s.skill_type === 'soft');

  async function handleAdd(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      setError('Skill name must not be empty.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.addSkill(profileId, {
        name: trimmed,
        skill_type: skillType,
        proficiency,
      });
      setName('');
      setProficiency(MIN_PROFICIENCY);
      await onChanged();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : 'Could not add the skill.',
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleRemove(skillId: string) {
    setBusy(true);
    setError(null);
    try {
      await api.removeSkill(profileId, skillId);
      await onChanged();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : 'Could not remove the skill.',
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel" aria-label="Skills">
      <h2>Skills</h2>

      {error && (
        <div className="banner banner-error" role="alert">
          {error}
        </div>
      )}

      <form
        onSubmit={handleAdd}
        aria-label="Add skill"
        aria-describedby="add-skill-error"
      >
        <div className="form-row">
          <div className="field">
            <label htmlFor="skill-name">Skill name</label>
            <input
              id="skill-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoComplete="off"
            />
          </div>
          <div className="field">
            <label htmlFor="skill-type">Type</label>
            <select
              id="skill-type"
              value={skillType}
              onChange={(e) => setSkillType(e.target.value as SkillType)}
            >
              <option value="technical">Technical</option>
              <option value="soft">Soft</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="skill-proficiency">Proficiency (1–5)</label>
            <input
              id="skill-proficiency"
              type="number"
              min={MIN_PROFICIENCY}
              max={MAX_PROFICIENCY}
              step={1}
              value={proficiency}
              onChange={(e) =>
                setProficiency(clampProficiency(e.target.valueAsNumber))
              }
            />
          </div>
          <button className="btn" type="submit" disabled={busy}>
            Add skill
          </button>
        </div>
      </form>

      <div className="gap-groups" style={{ marginTop: 16 }}>
        <SkillGroup
          heading="Technical skills"
          skills={technical}
          onRemove={handleRemove}
          busy={busy}
        />
        <SkillGroup
          heading="Soft skills"
          skills={soft}
          onRemove={handleRemove}
          busy={busy}
        />
      </div>
    </section>
  );
}

interface SkillGroupProps {
  heading: string;
  skills: SkillResponse[];
  onRemove: (skillId: string) => void;
  busy: boolean;
}

function SkillGroup({ heading, skills, onRemove, busy }: SkillGroupProps) {
  return (
    <div>
      <h3>{heading}</h3>
      {skills.length === 0 ? (
        <p className="empty-note">None yet.</p>
      ) : (
        <ul className="item-list">
          {skills.map((skill) => (
            <li key={skill.id} className="item-row">
              <span>
                {skill.name}{' '}
                <span className="field-hint">
                  · proficiency {skill.proficiency}
                </span>
              </span>
              <button
                type="button"
                className="btn-danger"
                onClick={() => onRemove(skill.id)}
                disabled={busy}
                aria-label={`Remove ${skill.name}`}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Keep the proficiency input within the inclusive 1..5 bound (NaN -> min). */
function clampProficiency(value: number): number {
  if (Number.isNaN(value)) return MIN_PROFICIENCY;
  return Math.min(MAX_PROFICIENCY, Math.max(MIN_PROFICIENCY, Math.round(value)));
}
