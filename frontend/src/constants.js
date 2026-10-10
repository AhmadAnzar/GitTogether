export const AVAILABILITY = {
  OPEN_TO_TEAM: { label: 'Open to team', tone: 'open' },
  BUSY: { label: 'Busy', tone: 'busy' },
  NOT_LOOKING: { label: 'Not looking', tone: 'idle' },
};

export const FILTERS = [
  { value: 'ALL', label: 'Everyone' },
  { value: 'OPEN_TO_TEAM', label: 'Open to team' },
  { value: 'BUSY', label: 'Busy' },
  { value: 'NOT_LOOKING', label: 'Not looking' },
];

export const YEAR_LABEL = { 1: '1st yr', 2: '2nd yr', 3: '3rd yr', 4: '4th yr', 5: '5th yr', 6: '6th yr' };

// A short, stable commit-style hash for each profile id (purely decorative).
export function shortHash(id) {
  return ((id * 2654435761) >>> 0).toString(16).padStart(8, '0').slice(0, 7);
}

export function initials(name) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join('');
}
