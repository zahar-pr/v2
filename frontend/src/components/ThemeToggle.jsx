import React from 'react';

const SUN = (
  <svg viewBox="0 0 20 20" width="18" height="18" fill="none" aria-hidden="true">
    <circle cx="10" cy="10" r="3.6" stroke="currentColor" strokeWidth="1.6" />
    {[0, 45, 90, 135, 180, 225, 270, 315].map((angle) => (
      <path
        key={angle}
        d="M10 1.6V3.4"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        transform={`rotate(${angle} 10 10)`}
      />
    ))}
  </svg>
);

const MOON = (
  <svg viewBox="0 0 20 20" width="18" height="18" fill="none" aria-hidden="true">
    <path
      d="M16.2 12.4A6.8 6.8 0 017.6 3.8a6.8 6.8 0 108.6 8.6z"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinejoin="round"
    />
  </svg>
);

export default function ThemeToggle({ theme, onToggle }) {
  const dark = theme === 'dark';
  return (
    <button
      type="button"
      className="theme"
      onClick={onToggle}
      title={dark ? 'Включить светлую тему' : 'Включить тёмную тему'}
      aria-label={dark ? 'Включить светлую тему' : 'Включить тёмную тему'}
      aria-pressed={dark}
    >
      {dark ? SUN : MOON}
    </button>
  );
}
