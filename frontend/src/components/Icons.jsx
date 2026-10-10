// Small inline SVG icon set (stroke icons, inherit currentColor).
const base = { width: 16, height: 16, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true };

export const SearchIcon = (p) => (
  <svg {...base} {...p}><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
);
export const PlusIcon = (p) => (
  <svg {...base} {...p}><path d="M12 5v14M5 12h14" /></svg>
);
export const LockIcon = (p) => (
  <svg {...base} {...p}><rect x="4" y="11" width="16" height="10" rx="2" /><path d="M8 11V7a4 4 0 0 1 8 0v4" /></svg>
);
export const GlobeIcon = (p) => (
  <svg {...base} {...p}><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" /></svg>
);
export const LinkIcon = (p) => (
  <svg {...base} {...p}><path d="M7 17 17 7M8 7h9v9" /></svg>
);
export const EditIcon = (p) => (
  <svg {...base} {...p}><path d="M4 20h4L19 9l-4-4L4 16v4Z" /></svg>
);
export const TrashIcon = (p) => (
  <svg {...base} {...p}><path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3" /></svg>
);
export const CloseIcon = (p) => (
  <svg {...base} {...p}><path d="M6 6l12 12M18 6 6 18" /></svg>
);
export const BranchIcon = (p) => (
  <svg {...base} {...p}><circle cx="6" cy="5" r="2" /><circle cx="6" cy="19" r="2" /><circle cx="18" cy="8" r="2" /><path d="M6 7v10M18 10c0 4-6 3-12 7" /></svg>
);
export const UserIcon = (p) => (
  <svg {...base} {...p}><circle cx="12" cy="8" r="4" /><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" /></svg>
);
export const UsersIcon = (p) => (
  <svg {...base} {...p}><circle cx="9" cy="8" r="3.5" /><path d="M2.5 20c1-3.5 3.5-5 6.5-5s5.5 1.5 6.5 5" /><path d="M16 4.5a3.5 3.5 0 0 1 0 7M18 15c2 .7 3.2 2.4 3.8 5" /></svg>
);
export const FileIcon = (p) => (
  <svg {...base} {...p}><path d="M14 3H6v18h12V7l-4-4Z" /><path d="M14 3v4h4M9 13h6M9 17h6" /></svg>
);
export const CheckIcon = (p) => (
  <svg {...base} {...p}><path d="m5 12 5 5 9-10" /></svg>
);
export const LogoutIcon = (p) => (
  <svg {...base} {...p}><path d="M15 4h4v16h-4M10 8l-4 4 4 4M6 12h10" /></svg>
);
