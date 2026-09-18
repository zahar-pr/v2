import React from 'react';

export default function FactorStrip({ factors, onOpen }) {
  const total = factors.reduce((sum, f) => sum + Math.max(f.weight, 1), 0);

  return (
    <button type="button" className="fstrip" onClick={onOpen} title="Показать раскладку балла">
      {factors.map((f) => (
        <span
          key={f.id}
          className="fseg"
          style={{ flexGrow: Math.max(f.weight, 1) / total }}
          title={`${f.title}: ${f.score} из 100, вес ${f.weight}%`}
        >
          <span className="fseg__track">
            <span className={`fseg__fill fseg__fill--${level(f.score)}`} style={{ width: `${f.score}%` }} />
          </span>
          <span className="fseg__name">{f.title}</span>
        </span>
      ))}
    </button>
  );
}

function level(score) {
  if (score >= 60) return 'high';
  if (score >= 30) return 'mid';
  return 'low';
}
