import { useEffect, useRef, useState } from 'react';
import { AVAILABILITY } from '../constants.js';
import { resumeUrl } from '../api.js';
import { CloseIcon, FileIcon, GlobeIcon, LockIcon } from './Icons.jsx';

const MAX_RESUME_BYTES = 5 * 1024 * 1024;

const EMPTY = {
  name: '',
  department: '',
  year: '',
  bio: '',
  skills: [],
  linkedin_url: '',
  availability: 'OPEN_TO_TEAM',
  visibility: 'PUBLIC',
};

export default function ProfileForm({ profile, onSubmit, onClose }) {
  const editing = Boolean(profile);
  // Skills/LinkedIn of a LIMITED profile are never sent to the browser, so they can't be prefilled.
  const secretsHidden = editing && profile.hidden;
  const [form, setForm] = useState(() => (editing ? { ...EMPTY, ...profile, year: profile.year ?? '' } : EMPTY));
  const [skillDraft, setSkillDraft] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [resumeFile, setResumeFile] = useState(null);
  const [removeResume, setRemoveResume] = useState(false);
  const firstField = useRef(null);

  useEffect(() => {
    firstField.current?.focus();
    const onKey = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const addSkill = (raw) => {
    const parts = raw.split(',').map((s) => s.trim()).filter(Boolean);
    if (!parts.length) return;
    setForm((f) => {
      const existing = new Set(f.skills.map((s) => s.toLowerCase()));
      const next = [...f.skills];
      parts.forEach((p) => {
        if (!existing.has(p.toLowerCase()) && next.length < 15) {
          existing.add(p.toLowerCase());
          next.push(p);
        }
      });
      return { ...f, skills: next };
    });
    setSkillDraft('');
  };

  const onSkillKey = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      addSkill(skillDraft);
    } else if (e.key === 'Backspace' && !skillDraft && form.skills.length) {
      setForm((f) => ({ ...f, skills: f.skills.slice(0, -1) }));
    }
  };

  const removeSkill = (skill) => setForm((f) => ({ ...f, skills: f.skills.filter((s) => s !== skill) }));

  const pickResume = (e) => {
    const file = e.target.files?.[0] ?? null;
    setError('');
    if (file && file.size > MAX_RESUME_BYTES) {
      setError('Resume must be 5 MB or smaller');
      e.target.value = '';
      return;
    }
    setResumeFile(file);
    if (file) setRemoveResume(false);
  };

  const submit = async (e) => {
    e.preventDefault();
    const pending = skillDraft.trim() ? [...form.skills, ...skillDraft.split(',').map((s) => s.trim()).filter(Boolean)] : form.skills;
    const payload = {
      name: form.name.trim(),
      department: form.department.trim(),
      year: form.year === '' ? null : Number(form.year),
      bio: form.bio.trim(),
      availability: form.availability,
      visibility: form.visibility,
    };
    // For hidden profiles, blank fields mean "keep what's stored".
    if (!secretsHidden || pending.length) payload.skills = pending;
    if (!secretsHidden || form.linkedin_url.trim()) payload.linkedin_url = form.linkedin_url.trim();

    setSaving(true);
    setError('');
    try {
      await onSubmit(payload, { resumeFile, removeResume });
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  };

  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <form className="sheet" onSubmit={submit} aria-labelledby="form-title">
        <div className="sheet-head">
          <div>
            <p className="eyebrow">{editing ? 'git commit --amend' : 'git add me'}</p>
            <h2 id="form-title">{editing ? 'Edit profile' : 'List your skills'}</h2>
          </div>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close"><CloseIcon /></button>
        </div>

        <div className="sheet-body">
          <label className="field">
            <span>Name</span>
            <input ref={firstField} required maxLength={120} value={form.name} onChange={set('name')} placeholder="Ayesha Khan" />
          </label>

          <div className="field-row">
            <label className="field">
              <span>Department</span>
              <input maxLength={80} value={form.department} onChange={set('department')} placeholder="CSE" />
            </label>
            <label className="field field-narrow">
              <span>Year</span>
              <select value={form.year} onChange={set('year')}>
                <option value="">-</option>
                {[1, 2, 3, 4, 5, 6].map((y) => <option key={y} value={y}>{y}</option>)}
              </select>
            </label>
          </div>

          <label className="field">
            <span>Bio <em>{form.bio.length}/500</em></span>
            <textarea rows={3} maxLength={500} value={form.bio} onChange={set('bio')} placeholder="What you're building, what kind of team you want" />
          </label>

          <div className="field">
            <span>Skills <em>Enter or comma to add</em></span>
            <div className="tag-input" onClick={(e) => e.currentTarget.querySelector('input')?.focus()}>
              {form.skills.map((skill) => (
                <span className="skill skill-removable" key={skill}>
                  {skill}
                  <button type="button" onClick={() => removeSkill(skill)} aria-label={`Remove ${skill}`}>×</button>
                </span>
              ))}
              <input
                value={skillDraft}
                onChange={(e) => setSkillDraft(e.target.value)}
                onKeyDown={onSkillKey}
                onBlur={() => addSkill(skillDraft)}
                placeholder={secretsHidden ? 'Hidden: leave empty to keep current skills' : form.skills.length ? '' : 'Python, React, Figma…'}
              />
            </div>
          </div>

          <label className="field">
            <span>LinkedIn</span>
            <input
              type="url"
              value={form.linkedin_url}
              onChange={set('linkedin_url')}
              placeholder={secretsHidden ? 'Hidden: leave empty to keep current link' : 'https://www.linkedin.com/in/your-name'}
            />
          </label>

          <div className="field">
            <span>Resume <em>PDF, max 5 MB</em></span>
            {editing && profile.has_resume && !resumeFile && (
              <div className="resume-current">
                <FileIcon width={14} height={14} />
                <a href={resumeUrl(profile.id)} target="_blank" rel="noopener noreferrer">Current resume</a>
                <label className="resume-remove">
                  <input type="checkbox" checked={removeResume} onChange={(e) => setRemoveResume(e.target.checked)} />
                  Remove it
                </label>
              </div>
            )}
            <input
              className="file-input"
              type="file"
              accept="application/pdf,.pdf"
              onChange={pickResume}
              aria-label={editing && profile.has_resume ? 'Replace resume' : 'Upload resume'}
            />
          </div>

          <fieldset className="field">
            <legend>Availability</legend>
            <div className="segmented">
              {Object.entries(AVAILABILITY).map(([value, { label, tone }]) => (
                <label key={value} className={form.availability === value ? 'on' : ''}>
                  <input type="radio" name="availability" value={value} checked={form.availability === value} onChange={set('availability')} />
                  <span className={`dot dot-${tone}`} />
                  {label}
                </label>
              ))}
            </div>
          </fieldset>

          <fieldset className="field">
            <legend>Who can see your skills?</legend>
            <div className="visibility">
              <label className={form.visibility === 'PUBLIC' ? 'on' : ''}>
                <input type="radio" name="visibility" value="PUBLIC" checked={form.visibility === 'PUBLIC'} onChange={set('visibility')} />
                <GlobeIcon />
                <span><b>Public</b><small>Everyone sees your skills, LinkedIn and resume.</small></span>
              </label>
              <label className={form.visibility === 'LIMITED' ? 'on' : ''}>
                <input type="radio" name="visibility" value="LIMITED" checked={form.visibility === 'LIMITED'} onChange={set('visibility')} />
                <LockIcon />
                <span><b>Limited</b><small>Only your connections see skills, LinkedIn and resume. Everyone else sees your name, department and availability.</small></span>
              </label>
            </div>
          </fieldset>

          {error && <p className="form-error" role="alert">{error}</p>}
        </div>

        <div className="sheet-foot">
          <button type="button" className="btn-ghost" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? 'Saving…' : editing ? 'Save changes' : 'Publish profile'}
          </button>
        </div>
      </form>
    </div>
  );
}
