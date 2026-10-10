import { YEAR_LABEL, initials } from '../constants.js';
import ProfileCard from './ProfileCard.jsx';

/** Requests (incoming + sent) and accepted connections for the logged-in user. */
export default function ConnectionsView({ data, loading, busy, cardActions, onAccept, onDecline, onCancel, onBrowse }) {
  if (loading) {
    return <div className="grid">{[0, 1].map((i) => <div key={i} className="card skeleton" />)}</div>;
  }
  const { incoming, outgoing, connections } = data;

  return (
    <div className="connections">
      <section aria-labelledby="incoming-title">
        <h2 className="section-title" id="incoming-title">
          Requests <span className="count">{incoming.length}</span>
        </h2>
        {incoming.length === 0 ? (
          <p className="section-empty">No pending requests.</p>
        ) : (
          <ul className="request-list">
            {incoming.map((r) => (
              <RequestRow key={r.id} request={r}>
                <button type="button" className="btn-chip accept" disabled={busy} onClick={() => onAccept(r.id)}>Accept</button>
                <button type="button" className="btn-text" disabled={busy} onClick={() => onDecline(r.id)}>Decline</button>
              </RequestRow>
            ))}
          </ul>
        )}
      </section>

      {outgoing.length > 0 && (
        <section aria-labelledby="outgoing-title">
          <h2 className="section-title" id="outgoing-title">
            Sent <span className="count">{outgoing.length}</span>
          </h2>
          <ul className="request-list">
            {outgoing.map((r) => (
              <RequestRow key={r.id} request={r} note="Waiting for them to accept">
                <button type="button" className="btn-text" disabled={busy} onClick={() => onCancel(r.id)}>Cancel</button>
              </RequestRow>
            ))}
          </ul>
        </section>
      )}

      <section aria-labelledby="connections-title">
        <h2 className="section-title" id="connections-title">
          My connections <span className="count">{connections.length}</span>
        </h2>
        {connections.length === 0 ? (
          <div className="empty empty-compact">
            <p>No connections yet. Find people on the board and send them a request.</p>
            <button type="button" className="btn-ghost" onClick={onBrowse}>Browse the board</button>
          </div>
        ) : (
          <div className="grid">
            {connections.filter((c) => c.profile).map((c) => (
              <ProfileCard key={c.user_id} profile={c.profile} actions={cardActions} busy={busy} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function RequestRow({ request, note, children }) {
  const p = request.profile;
  const meta = p ? [p.department, YEAR_LABEL[p.year]].filter(Boolean).join(' · ') : '';
  return (
    <li className="request-row">
      <div className={`avatar avatar-sm tone-${(p?.id ?? request.user_id) % 4}`} aria-hidden="true">
        {p ? initials(p.name) : '?'}
      </div>
      <div className="request-who">
        <b>{p ? p.name : 'New member'}</b>
        <small>{p ? meta || 'Campus' : "Hasn't created a profile yet"}{note ? ` · ${note}` : ''}</small>
      </div>
      <div className="request-actions">{children}</div>
    </li>
  );
}
