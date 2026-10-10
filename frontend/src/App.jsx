import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import * as api from './api.js';
import { FILTERS } from './constants.js';
import AuthModal from './components/AuthModal.jsx';
import ConnectionsView from './components/ConnectionsView.jsx';
import ProfileCard from './components/ProfileCard.jsx';
import ProfileForm from './components/ProfileForm.jsx';
import { BranchIcon, CloseIcon, LogoutIcon, PlusIcon, SearchIcon, UserIcon, UsersIcon } from './components/Icons.jsx';

const EMPTY_STATS = { total: 0, openToTeam: 0, busy: 0, notLooking: 0, limited: 0, topSkills: [] };
const EMPTY_CONNECTIONS = { incoming: [], outgoing: [], connections: [] };

function useDebounced(value, delay = 250) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

export default function App() {
  const [me, setMe] = useState(undefined); // undefined = still checking, null = logged out
  const [view, setView] = useState('board');
  const [profiles, setProfiles] = useState([]);
  const [stats, setStats] = useState(EMPTY_STATS);
  const [query, setQuery] = useState('');
  const [skill, setSkill] = useState('');
  const [availability, setAvailability] = useState('ALL');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [conn, setConn] = useState(EMPTY_CONNECTIONS);
  const [connLoading, setConnLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState(null); // null = closed, {} = new, {profile} = edit
  const [auth, setAuth] = useState(null); // null = closed, { mode, reason }
  const [toast, setToast] = useState('');
  const toastTimer = useRef();

  const q = useDebounced(query);
  const s = useDebounced(skill);
  const viewerId = me?.id ?? null;

  const notify = (message) => {
    setToast(message);
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(''), 2800);
  };

  // ---------- data loading ----------

  const refreshMe = useCallback(async () => {
    try {
      setMe(await api.me());
    } catch {
      setMe(null);
    }
  }, []);

  useEffect(() => { refreshMe(); }, [refreshMe]);

  const loadBoard = useCallback(async () => {
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
    // viewerId: what a viewer may see depends on who is logged in, so reload when it changes.
  }, [q, s, availability, viewerId]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadConnections = useCallback(async () => {
    if (!viewerId) {
      setConn(EMPTY_CONNECTIONS);
      return;
    }
    setConnLoading(true);
    try {
      const [requests, connections] = await Promise.all([api.listRequests(), api.listConnections()]);
      setConn({ ...requests, connections });
    } catch (e) {
      notify(e.message);
    } finally {
      setConnLoading(false);
    }
  }, [viewerId]);

  useEffect(() => { if (me !== undefined) loadBoard(); }, [loadBoard, me]);
  useEffect(() => { loadConnections(); }, [loadConnections]);

  const refreshAll = () => Promise.all([loadBoard(), loadConnections()]);

  // ---------- auth ----------

  const askToLogin = (reason) => setAuth({ mode: 'register', reason });
  const closeAuth = useCallback(() => setAuth(null), []);

  const onAuthed = (user) => {
    setAuth(null);
    setMe(user);
    notify(`Signed in as ${user.email}`);
  };

  const doLogout = async () => {
    await api.logout().catch(() => {});
    setMe(null);
    setView('board');
    notify('Logged out');
  };

  // ---------- profile ----------

  const closeForm = useCallback(() => setForm(null), []);

  const openMyProfile = async () => {
    if (!me) return askToLogin('Create an account to list your skills.');
    if (!me.profile_id) return setForm({});
    try {
      setForm({ profile: await api.getProfile(me.profile_id) });
    } catch (e) {
      notify(e.message);
    }
  };

  const save = async (payload, { resumeFile, removeResume }) => {
    const saved = form?.profile
      ? await api.updateProfile(form.profile.id, payload)
      : await api.createProfile(payload);
    if (resumeFile) await api.uploadResume(saved.id, resumeFile);
    else if (removeResume) await api.deleteResume(saved.id);
    notify(form?.profile ? 'Profile updated' : 'You’re listed. Teams can find you now.');
    setForm(null);
    await refreshMe();
    loadBoard();
  };

  const removeProfile = async (profile) => {
    try {
      await api.deleteProfile(profile.id);
      notify('Your profile was deleted');
      await refreshMe();
      refreshAll();
    } catch (e) {
      notify(e.message);
    }
  };

  // ---------- connections ----------

  const run = async (action, message) => {
    setBusy(true);
    try {
      await action();
      if (message) notify(message);
      await refreshAll();
    } catch (e) {
      notify(e.message);
    } finally {
      setBusy(false);
    }
  };

  const cardActions = useMemo(() => ({
    onEdit: (profile) => setForm({ profile }),
    onDelete: removeProfile,
    onSkillClick: (value) => { setView('board'); setSkill(value); },
    onConnect: (profile) => {
      if (!me) return askToLogin(`Create an account to connect with ${profile.name.split(' ')[0]}.`);
      run(() => api.sendRequest(profile.owner_id), 'Request sent');
    },
    onAccept: (profile) => run(() => api.acceptRequest(profile.request_id), `You're connected with ${profile.name}`),
    onDecline: (profile) => run(() => api.declineRequest(profile.request_id)),
    onCancel: (profile) => run(() => api.cancelRequest(profile.request_id), 'Request cancelled'),
    onRemove: (profile) => run(() => api.removeConnection(profile.owner_id), 'Connection removed'),
  }), [me]); // eslint-disable-line react-hooks/exhaustive-deps

  // ---------- render ----------

  const filtering = q || s || availability !== 'ALL';
  const clearFilters = () => { setQuery(''); setSkill(''); setAvailability('ALL'); };
  const incomingCount = conn.incoming.length;

  return (
    <div className="page">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true"><i /><i /></span>
          <span className="brand-name">git<span>together</span></span>
        </div>

        {me ? (
          <nav className="nav-tabs" aria-label="Main">
            <button className={view === 'board' ? 'nav-tab on' : 'nav-tab'} onClick={() => setView('board')}>
              Board
            </button>
            <button className={view === 'connections' ? 'nav-tab on' : 'nav-tab'} onClick={() => setView('connections')}>
              <UsersIcon /> Connections
              {incomingCount > 0 && <span className="badge" aria-label={`${incomingCount} pending requests`}>{incomingCount}</span>}
            </button>
          </nav>
        ) : (
          <span className="crumb"><BranchIcon /> main / campus</span>
        )}

        <div className="topbar-actions">
          {me === undefined ? null : me ? (
            <>
              <button className="btn-primary" onClick={openMyProfile}>
                {me.profile_id ? <UserIcon /> : <PlusIcon />}
                <span>{me.profile_id ? 'My profile' : 'Add my profile'}</span>
              </button>
              <span className="user-chip" title={me.email}>{me.email}</span>
              <button className="icon-btn" onClick={doLogout} aria-label="Log out" title="Log out"><LogoutIcon /></button>
            </>
          ) : (
            <>
              <button className="btn-ghost" onClick={() => setAuth({ mode: 'login' })}>Log in</button>
              <button className="btn-primary" onClick={() => setAuth({ mode: 'register' })}>Sign up</button>
            </>
          )}
        </div>
      </header>

      {view === 'connections' && me ? (
        <main className="view-connections">
          <div className="view-head">
            <p className="eyebrow">your network</p>
            <h1 className="view-title">Connections</h1>
            <p className="lede">Connections can see each other’s skills, LinkedIn and resume, even on limited profiles.</p>
          </div>
          <ConnectionsView
            data={conn}
            loading={connLoading && conn === EMPTY_CONNECTIONS}
            busy={busy}
            cardActions={cardActions}
            onAccept={(id) => run(() => api.acceptRequest(id), 'Connected')}
            onDecline={(id) => run(() => api.declineRequest(id))}
            onCancel={(id) => run(() => api.cancelRequest(id), 'Request cancelled')}
            onBrowse={() => setView('board')}
          />
        </main>
      ) : (
        <>
          <section className="hero">
            <div className="hero-copy">
              <p className="eyebrow">campus skill marketplace</p>
              <h1>Find your people for the <mark>next hackathon</mark>.</h1>
              <p className="lede">
                Students list what they can build. Teams find them by skill and send a connection request. Keep your
                profile limited and only your connections see your skills, LinkedIn and resume.
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
                <button className="btn-text" onClick={loadBoard}>retry</button>
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
                    <ProfileCard key={p.id} profile={p} actions={cardActions} activeSkill={s} busy={busy} />
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
                    <button className="btn-primary" onClick={openMyProfile}><PlusIcon /> Add my profile</button>
                  </>
                )}
              </div>
            )}
          </main>
        </>
      )}

      <footer className="site-foot">
        <span>GitTogether · DevOps capstone</span>
        <span className="mono">FastAPI · Postgres · React · K8s</span>
      </footer>

      {form && <ProfileForm profile={form.profile} onSubmit={save} onClose={closeForm} />}
      {auth && <AuthModal mode={auth.mode} reason={auth.reason} onAuthed={onAuthed} onClose={closeAuth} />}
      {toast && <div className="toast" role="status">{toast}</div>}
    </div>
  );
}
