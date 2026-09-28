import React, { useEffect, useRef } from 'react';

/** Кастомный выпадающий список: закрывается кликом вне и по Escape. */
export default function Dropdown({ label, value, options, open, onToggle, onSelect }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const onDown = (e) => { if (ref.current && !ref.current.contains(e.target)) onToggle(false); };
    const onKey = (e) => { if (e.key === 'Escape') onToggle(false); };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open, onToggle]);

  return (
    <div className={`dd${open ? ' dd--open' : ''}`} ref={ref}>
      <button
        type="button" className="dd__btn" aria-label={label} aria-expanded={open}
        onClick={() => onToggle(!open)}
      >
        <span className="dd__value">
          <span className="dd__label">{label}</span>
          <span className="dd__current">{value}</span>
        </span>
        <svg className="dd__chev" viewBox="0 0 12 8" width="12" height="8" fill="none">
          <path d="M1 1.5L6 6.5L11 1.5" stroke="#0F2229" strokeWidth="1.7" strokeLinecap="round" />
        </svg>
      </button>

      {open && (
        <div className="dd__menu" role="listbox">
          {options.map((o, i) => (
            <button
              key={o}
              style={{ animationDelay: `${(i * 0.022).toFixed(3)}s` }}
              type="button"
              role="option"
              aria-selected={o === value}
              className={`dd__opt${o === value ? ' dd__opt--on' : ''}`}
              onClick={() => { onSelect(o); onToggle(false); }}
            >
              <span>{o}</span>
              <span className="dd__tick">{o === value ? '✓' : ''}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
