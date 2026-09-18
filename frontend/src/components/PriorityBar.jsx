import React, { useState } from 'react';

export default function PriorityBar({ presets, factors, preset, weights, onPreset, onWeights, onExplain }) {
  const [open, setOpen] = useState(false);
  const current = presets.find((p) => p.id === preset);

  return (
    <div className="priority">
      <div className="priority__row">
        <span className="priority__label">Что важнее</span>
        {presets.map((item) => (
          <button
            type="button"
            key={item.id}
            className={`chip${preset === item.id ? ' chip--on' : ''}`}
            onClick={() => onPreset(item.id)}
            title={item.hint}
          >
            {item.title}
          </button>
        ))}
        <button type="button" className="priority__link" onClick={() => setOpen((v) => !v)}>
          {open ? 'Скрыть веса' : 'Настроить веса'}
        </button>
        <button type="button" className="priority__link" onClick={onExplain}>
          Как считается
        </button>
      </div>

      <div className="priority__hint">
        {current ? current.hint : 'Свои веса факторов'} — выдача пересортируется сразу.
      </div>

      {open && (
        <div className="weights">
          {factors.map((f) => (
            <label className="weight" key={f.id}>
              <span className="weight__title" title={f.hint}>{f.title}</span>
              <input
                type="range"
                min="0"
                max="60"
                step="5"
                value={weights[f.id] || 0}
                onChange={(e) => onWeights({ ...weights, [f.id]: Number(e.target.value) })}
              />
              <span className="weight__value">{weights[f.id] || 0}%</span>
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
