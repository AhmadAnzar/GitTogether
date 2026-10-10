import { useState } from 'react';
import { AVAILABILITY, YEAR_LABEL, initials, shortHash } from '../constants.js';
import { EditIcon, LinkIcon, LockIcon, TrashIcon } from './Icons.jsx';

export default function ProfileCard({ profile, onEdit, onDelete, onSkillClick, activeSkill }) {
  const [confirming, setConfirming] = useState(false);
  const availability = AVAILABILITY[profile.availability];
  const meta = [profile.department, YEAR_LABEL[profile.year]].filter(Boolean).join(' · ');

  return (
    <article className="card">
      <header className="card-head">
        <div className={`avatar tone-${profile.id % 4}`} aria-hidden="true">{initials(profile.name)}</div>
        <div className="card-title">
          <h3>{profile.name}</h3>
          <p className="card-meta">{meta || 'Campus'}</p>
        </div>
        <span className={`status status-${availability.tone}`}>
          <span className="dot" />
          {availability.label}
        </span>
      </header>

      {profile.bio && <p className="card-bio">{profile.bio}</p>}

      {profile.hidden ? (
        <div className="hidden-note">
          <LockIcon />
          <span>Skills and LinkedIn are private. This student chose a limited profile.</span>
        </div>
      ) : (
        <ul className="skills" aria-label="Skills">
          {profile.skills.length === 0 && <li className="skill skill-empty">No skills listed yet</li>}
          {profile.skills.map((skill) => (
            <li key={skill}>
              <button
                type="button"
                className={`skill ${activeSkill?.toLowerCase() === skill.toLowerCase() ? 'skill-active' : ''}`}
                onClick={() => onSkillClick(skill)}
                title={`Show everyone with ${skill}`}
              >
                {skill}
              </button>
            </li>
          ))}
        </ul>
      )}

      <footer className="card-foot">
        <code className="hash" title="Profile id">#{shortHash(profile.id)}</code>
        <div className="card-actions">
          {confirming ? (
            <>
              <span className="confirm-text">Delete?</span>
              <button type="button" className="btn-text danger" onClick={() => onDelete(profile)}>Yes</button>
              <button type="button" className="btn-text" onClick={() => setConfirming(false)}>No</button>
            </>
          ) : (
            <>
              <button type="button" className="icon-btn" onClick={() => onEdit(profile)} aria-label={`Edit ${profile.name}`}><EditIcon /></button>
              <button type="button" className="icon-btn" onClick={() => setConfirming(true)} aria-label={`Delete ${profile.name}`}><TrashIcon /></button>
              {profile.linkedin_url && (
                <a className="btn-link" href={profile.linkedin_url} target="_blank" rel="noopener noreferrer">
                  LinkedIn <LinkIcon width={14} height={14} />
                </a>
              )}
            </>
          )}
        </div>
      </footer>
    </article>
  );
}
