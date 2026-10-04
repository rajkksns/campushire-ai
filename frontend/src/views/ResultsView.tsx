/**
 * Results view (Task 15.3, Requirements 11.3, 12.7, 22.2).
 *
 * Presents a persisted/returned analysis result:
 *   - the 0-100 placement-readiness score, shown prominently with its numeric
 *     value (22.2);
 *   - the itemized score breakdown (name, weight, category, points) (10.10);
 *   - the matched / weak / missing skill groups, clearly labeled (11.3);
 *   - the prioritized learning roadmap in order (12.7).
 *
 * When the backend identifies no required skills, the result is a valid
 * score-0 analysis with empty groups (7.6, 10.12); this view renders that case
 * with an explanatory note rather than an error.
 */

import type { AnalysisResponse } from '../types';

interface ResultsViewProps {
  result: AnalysisResponse;
}

export function ResultsView({ result }: ResultsViewProps) {
  const {
    readiness_score,
    breakdown,
    matched,
    weak,
    missing,
    roadmap,
  } = result;

  const noRequiredSkills =
    breakdown.length === 0 &&
    matched.length === 0 &&
    weak.length === 0 &&
    missing.length === 0;

  return (
    <section className="panel" aria-label="Analysis results">
      <h2>Results</h2>

      <div className="score-hero">
        <div
          className="score-dial"
          style={{ ['--score' as string]: String(readiness_score) }}
          role="img"
          aria-label={`Placement readiness score: ${readiness_score} out of 100`}
        >
          <div className="score-dial-inner">{readiness_score}</div>
        </div>
        <div>
          <h3 style={{ margin: '0 0 4px' }}>Placement readiness</h3>
          <p style={{ margin: 0 }}>
            <strong>{readiness_score}</strong>
            <span className="field-hint"> / 100</span>
          </p>
        </div>
      </div>

      {noRequiredSkills && (
        <div className="banner banner-info" style={{ marginTop: 16 }}>
          No required skills were identified in the job description, so the
          score is 0. Try a more detailed description.
        </div>
      )}

      <h3>Score breakdown</h3>
      {breakdown.length === 0 ? (
        <p className="empty-note">No breakdown items.</p>
      ) : (
        <table className="breakdown">
          <thead>
            <tr>
              <th scope="col">Skill</th>
              <th scope="col">Category</th>
              <th scope="col" className="num">
                Weight
              </th>
              <th scope="col" className="num">
                Points
              </th>
            </tr>
          </thead>
          <tbody>
            {breakdown.map((item) => (
              <tr key={`${item.name}-${item.category}`}>
                <td>{item.name}</td>
                <td className={`cat-${item.category}`}>{item.category}</td>
                <td className="num">{item.weight}</td>
                <td className="num">{item.points}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h3>Skill gaps</h3>
      <div className="gap-groups">
        <GapGroup
          heading="Matched"
          className="cat-matched"
          items={matched.map((m) => ({
            key: m.name,
            label: m.name,
            detail: `weight ${m.weight} · proficiency ${m.proficiency}`,
          }))}
        />
        <GapGroup
          heading="Weak"
          className="cat-weak"
          items={weak.map((w) => ({
            key: w.name,
            label: w.name,
            detail: `weight ${w.weight} · proficiency ${w.proficiency}`,
          }))}
        />
        <GapGroup
          heading="Missing"
          className="cat-missing"
          items={missing.map((m) => ({
            key: m.name,
            label: m.name,
            detail: `weight ${m.weight}`,
          }))}
        />
      </div>

      <h3>Prioritized learning roadmap</h3>
      {roadmap.length === 0 ? (
        <p className="empty-note">
          No roadmap items — nothing to close for this role.
        </p>
      ) : (
        <ol className="roadmap">
          {roadmap.map((item) => (
            <li key={item.name}>
              <strong>{item.name}</strong>{' '}
              <span className={`cat-${item.category}`}>({item.category})</span>{' '}
              <span className="field-hint">
                priority #{item.priority_rank} · weight {item.weight}
              </span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

interface GapItem {
  key: string;
  label: string;
  detail: string;
}

function GapGroup({
  heading,
  className,
  items,
}: {
  heading: string;
  className: string;
  items: GapItem[];
}) {
  return (
    <div>
      <h4 className={className} style={{ margin: '0 0 8px' }}>
        {heading} ({items.length})
      </h4>
      {items.length === 0 ? (
        <p className="empty-note">None.</p>
      ) : (
        <ul className="item-list">
          {items.map((item) => (
            <li key={item.key} className="item-row">
              <span>{item.label}</span>
              <span className="field-hint">{item.detail}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
