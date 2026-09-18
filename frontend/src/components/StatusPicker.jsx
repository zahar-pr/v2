import React from 'react';

export default function StatusPicker({ value, statuses, onChange, compact }) {
  return (
    <select
      className={`status status--${value}${compact ? ' status--compact' : ''}`}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onClick={(e) => e.stopPropagation()}
      aria-label="Статус работы с поставщиком"
    >
      {statuses.map((item) => (
        <option key={item.id} value={item.id}>{item.title}</option>
      ))}
    </select>
  );
}
