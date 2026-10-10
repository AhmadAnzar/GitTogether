import { useState } from 'react';
import { resumeUrl } from '../api.js';
import { AVAILABILITY, YEAR_LABEL, initials, shortHash } from '../constants.js';
import { CheckIcon, EditIcon, FileIcon, LinkIcon, LockIcon, PlusIcon, TrashIcon } from './Icons.jsx';

/**
 * One student. `actions` handles everything the viewer can do:
 * { onEdit, onDelete, onConnect, onAccept, onDecline, onCancel, onRemove, onSkillClick }
 */
export default function ProfileCard({ profile, actions, activeSkill, busy }) {
  const availability = AVAILABILITY[profile.availability];
  const meta = [profile.department, YEAR_LABEL[profile.year]].filter(Boolean).join(' · ');
  const count = profile.connections_count;

  return (
    <article className="card">
      <header className="card-head">
        <div className={`avatar tone-${profile.id % 4}`} aria-hidden="true">{initials(profile.name)}</div>
        <div className="card-title">
          <h3>{profile.name}</h3>
          <p className="card-meta">
            {meta || 'Campus'}
            {count > 0 && <span> · {count} {count === 1 ? 'connection' : 'connections'}</span>}
          </p>
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
          <span>Skills, LinkedIn and resume are visible to {profile.name.split(' ')[0]}&apos;s connections only.</span>
        </div>
      ) : (
        <ul className="skills" aria-label="Skills">
          {profile.skills.length === 0 && <li className="skill skill-empty">No skills listed yet</li>}
          {profile.skills.map((skill) => (
            <li key={skill}>
              <button
                type="button"
                className={`skill ${activeSkill?.toLowerCase() === skill.toLowerCase() ? 'skill-active' : ''}`}
                onClick={() => actions.onSkillClick?.(skill)}
                title={`Show everyone with ${skill}`}
              >
                {skill}
              </button>
            </li>
          ))}
        </ul>
      )}

      {(profile.linkedin_url || profile.has_resume) && (
        <div className="card-links">
          {profile.linkedin_url && (
            <a className="btn-link" href={profile.linkedin_url} target="_blank" rel="noopener noreferrer">
              LinkedIn <LinkIcon width={14} height={14} />
            </a>
          )}
          {profile.has_resume && (
            <a className="btn-link" href={resumeUrl(profile.id)} target="_blank" rel="noopener noreferrer">
              <FileIcon width={14} height={14} /> Resume
            </a>
          )}
        </div>
      )}

      <footer className="card-foot">
        <code className="hash" title="Profile id">#{shortHash(profile.id)}</code>
        <div className="card-actions">
          <CardActions profile={profile} actions={actions} busy={busy} />
        </div>
      </footer>
    </article>
  );
}

function CardActions({ profile, actions, busy }) {
  const [confirming, setConfirming] = useState(null); // 'delete' | 'remove' | 'cancel'

  if (confirming) {
    const labels = { delete: 'Delete profile?', remove: 'Remove connection?', cancel: 'Cancel request?' };
    const run = {
      delete: () => actions.onDelete(profile),
      remove: () => actions.onRemove(profile),
      cancel: () => actions.onCancel(profile),
    }[confirming];
    return (
      <>
        <span className="confirm-text">{labels[confirming]}</span>
        <button type="button" className="btn-text danger" disabled={busy} onClick={() => { run(); setConfirming(null); }}>Yes</button>
        <button type="button" className="btn-text" onClick={() => setConfirming(null)}>No</button>
      </>
    );
  }

  switch (profile.connection_status) {
    case 'SELF':
      return (
        <>
          <button type="button" className="icon-btn" onClick={() => actions.onEdit(profile)} aria-label="Edit my profile"><EditIcon /></button>
          <button type="button" className="icon-btn" onClick={() => setConfirming('delete')} aria-label="Delete my profile"><TrashIcon /></button>
        </>
      );
    case 'CONNECTED':
      return (
        <button type="button" className="btn-chip connected" onClick={() => setConfirming('remove')} title="Click to remove">
          <CheckIcon width={14} height={14} /> Connected
        </button>
      );
    case 'PENDING_OUTGOING':
      return (
        <button type="button" className="btn-chip pending" onClick={() => setConfirming('cancel')} title="Click to cancel">
          Requested
        </button>
      );
    case 'PENDING_INCOMING':
      return (
        <>
          <button type="button" className="btn-chip accept" disabled={busy} onClick={() => actions.onAccept(profile)}>Accept</button>
          <button type="button" className="btn-text" disabled={busy} onClick={() => actions.onDecline(profile)}>Decline</button>
        </>
      );
    default:
      // Profiles from before accounts existed have no owner, so there's nobody to connect with.
      if (profile.owner_id == null) return null;
      return (
        <button type="button" className="btn-chip" disabled={busy} onClick={() => actions.onConnect(profile)}>
          <PlusIcon width={14} height={14} /> Connect
        </button>
      );
  }
}
