import { useCallback, useEffect, useRef, useState } from 'react';
import * as api from './api.js';
import { FILTERS } from './constants.js';
import ProfileCard from './components/ProfileCard.jsx';
import ProfileForm from './components/ProfileForm.jsx';
import { BranchIcon, CloseIcon, PlusIcon, SearchIcon } from './components/Icons.jsx';

const EMPTY_STATS = { total: 0, openToTeam: 0, busy: 0, notLooking: 0, limited: 0, topSkills: [] };

function useDebounced(value, delay = 250) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

export default function App() {
  const [profiles, setProfiles] = useState([]);
  const [stats, setStats] = useState(EMPTY_STATS);
  const [query, setQuery] = useState('');
  const [skill, setSkill] = useState('');
  const [availability, setAvailability] = useState('ALL');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [form, setForm] = useState(null); // null = closed, {} = new, {profile} = edit
  const [toast, setToast] = useState('');
  const toastTimer = useRef();

  const q = useDebounced(query);
  const s = useDebounced(skill);

  const load = useCallback(async () => {
    try {
      setError('');
      const [list, st] = await Promise.all([api.listProfiles({ q, skill: s, availability }), api.getStats()]);
      setProfiles(list);
      setStats(st);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [q, s, availability]);

  useEffect(() => { load(); }, [load]);

  const notify = (message) => {
    setToast(message);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(''), 2600);
  };

  const closeForm = useCallback(() => setForm(null), []);

  const save = async (payload) => {
    if (form?.profile) {
      await api.updateProfile(form.profile.id, payload);
      notify('Profile updated');
    } else {
      await api.createProfile(payload);
      notify('You’re listed. Teams can find you now.');
    }
    setForm(null);
    load();
  };

  const remove = async (profile) => {
    try {
      await api.deleteProfile(profile.id);
      notify(`Removed ${profile.name}`);
      load();
    } catch (e) {
      notify(e.message);
    }
  };

  const filtering = q || s || availability !== 'ALL';
  const clearFilters = () => { setQuery(''); setSkill(''); setAvailability('ALL'); };

  return (
    <div className="page">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true"><i /><i /></span>
          <span className="brand-name">git<span>together</span></span>
        </div>
        <span className="crumb"><BranchIcon /> main / campus</span>
        <button className="btn-primary" onClick={() => setForm({})}>
          <PlusIcon /> <span>Add my profile</span>
        </button>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">campus skill marketplace</p>
          <h1>Find your people for the <mark>next hackathon</mark>.</h1>
          <p className="lede">
            Students list what they can build. Teams find them by skill. If you’re shy, keep your skills private
            and show only your name and availability.
          </p>
        </div>

        <dl className="stats">
          <div className="stat stat-lead"><dt>On the board</dt><dd>{stats.total}</dd></div>
          <div className="stat"><dt>Open to team</dt><dd>{stats.openToTeam}</dd></div>
          <div className="stat"><dt>Busy</dt><dd>{stats.busy}</dd></div>
          <div className="stat"><dt>Limited profiles</dt><dd>{stats.limited}</dd></div>
        </dl>
      </section>

      <section className="toolbar" aria-label="Search and filters">
        <div className="search">
          <label className="search-box">
            <SearchIcon />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search name or department" aria-label="Search name or department" />
          </label>
          <label className="search-box search-skill">
            <span className="prompt">skill:</span>
            <input value={skill} onChange={(e) => setSkill(e.target.value)} placeholder="react" aria-label="Filter by skill" />
            {skill && <button className="icon-btn small" onClick={() => setSkill('')} aria-label="Clear skill"><CloseIcon /></button>}
          </label>
        </div>

        <div className="tabs" role="tablist">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              role="tab"
              aria-selected={availability === f.value}
              className={availability === f.value ? 'tab on' : 'tab'}
              onClick={() => setAvailability(f.value)}
            >
              {f.label}
            </button>
          ))}
        </div>

        {stats.topSkills.length > 0 && (
          <div className="trending">
            <span className="trending-label">trending</span>
            {stats.topSkills.map((t) => (
              <button
                key={t.skill}
                className={`chip ${s.toLowerCase() === t.skill ? 'on' : ''}`}
                onClick={() => setSkill(s.toLowerCase() === t.skill ? '' : t.skill)}
              >
                {t.skill}<b>{t.count}</b>
              </button>
            ))}
          </div>
        )}
      </section>

      <main>
        {error && (
          <div className="banner" role="alert">
            <b>Can’t reach the API.</b> {error}. Check that the backend and Postgres are running, then
            <button className="btn-text" onClick={load}>retry</button>
          </div>
        )}

        {loading ? (
          <div className="grid">{[0, 1, 2].map((i) => <div key={i} className="card skeleton" />)}</div>
        ) : profiles.length ? (
          <>
            <p className="result-count">
              {profiles.length} {profiles.length === 1 ? 'student' : 'students'}
              {filtering && <button className="btn-text" onClick={clearFilters}>clear filters</button>}
            </p>
            <div className="grid">
              {profiles.map((p) => (
                <ProfileCard
                  key={p.id}
                  profile={p}
                  activeSkill={s}
                  onEdit={(profile) => setForm({ profile })}
                  onDelete={remove}
                  onSkillClick={setSkill}
                />
              ))}
            </div>
          </>
        ) : !error && (
          <div className="empty">
            <pre aria-hidden="true">{'$ git log --students\n  nothing to show'}</pre>
            {filtering ? (
              <>
                <p>Nobody matches those filters yet.</p>
                <button className="btn-ghost" onClick={clearFilters}>Clear filters</button>
              </>
            ) : (
              <>
                <p>The board is empty. Be the first to list your skills.</p>
                <button className="btn-primary" onClick={() => setForm({})}><PlusIcon /> Add my profile</button>
              </>
            )}
          </div>
        )}
      </main>

      <footer className="site-foot">
        <span>GitTogether · DevOps capstone</span>
        <span className="mono">FastAPI · Postgres · React · K8s</span>
      </footer>

      {form && <ProfileForm profile={form.profile} onSubmit={save} onClose={closeForm} />}
      {toast && <div className="toast" role="status">{toast}</div>}
    </div>
  );
}
