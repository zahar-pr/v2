import React from 'react';

/** Санитарный вывод одной плашкой: с этого закупщик начинает читать карточку. */
export default function SafetyBadge({ safety, compact }) {
  if (!safety) return null;
  const { state, tone, title, incident } = safety;
  const mark = tone === 'ok' ? '✓' : tone === 'danger' ? '!' : '?';
  const when = incident && incident.date ? ` · ${incident.date}` : '';

  return (
    <span
      className={`safety safety--${tone} safety--${state}${compact ? ' safety--compact' : ''}`}
      title={safety.text}
    >
      <i aria-hidden="true">{mark}</i>
      <span>{title}{compact ? '' : when}</span>
    </span>
  );
}
