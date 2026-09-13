import React, { useEffect, useState } from 'react';
import { COMPARE_ROWS, score } from '../data/suppliers.js';
import { recommend } from '../api/client.js';

function noteRow(notes, s) {
  return notes[s.id] !== undefined ? notes[s.id] : s.note;
}

export default function CompareModal({ items, notes, narrow, onClear, onClose }) {
  const [advice, setAdvice] = useState('');

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [onClose]);

  const ids = items.map((s) => s.id).join('|');

  useEffect(() => {
    if (!items.length) { setAdvice(''); return undefined; }
    let alive = true;
    setAdvice('Считаем рекомендацию…');
    recommend(items.map((s) => s.id))
      .then((answer) => { if (alive) setAdvice(answer.text); })
      .catch(() => { if (alive) setAdvice(''); });
    return () => { alive = false; };
  }, [ids]);

  const rows = [
    ...COMPARE_ROWS,
    { label: 'Заметка', get: (s) => noteRow(notes, s) || '—', muted: true },
  ];

  return (
    <div className="modal" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal__in">
        <div className="modal__sheet">
          <div className="modal__head">
            <h2>Сравнение поставщиков</h2>
            <button type="button" className="btn btn--onDeep" onClick={onClear}>Очистить</button>
            <button type="button" className="btn btn--cyan" onClick={onClose}>Закрыть</button>
          </div>

          {items.length === 0 && (
            <div className="modal__hint">
              Добавьте в сравнение до трех поставщиков кнопкой «Сравнить» в карточке.
            </div>
          )}

          {items.length > 0 && !narrow && (
            <div className="tablewrap">
              <table className="compare">
                <thead>
                  <tr>
                    <th>Параметр</th>
                    {items.map((s) => (
                      <th key={s.id}>
                        <strong>{s.name}</strong>
                        <small>{s.city} · готовность {score(s)}%</small>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.label}>
                      <td>{r.label}</td>
                      {items.map((s) => (
                        <td key={s.id} className={r.mint ? 'cell--mint' : r.muted ? 'cell--muted' : undefined}>
                          {r.get(s)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {items.length > 0 && narrow && (
            <div className="cmpcards">
              {items.map((s, i) => (
                <div className="cmpcard" key={s.id} style={{ animationDelay: `${i * 0.06}s` }}>
                  <div className="cmpcard__head">
                    <strong>{s.name}</strong>
                    <small>{s.city} · готовность {score(s)}%</small>
                  </div>
                  {rows.map((r) => (
                    <div className="cmpcard__row" key={r.label}>
                      <div className="cmpcard__k">{r.label}</div>
                      <div className={`cmpcard__v ${r.mint ? 'cell--mint' : ''}`}>{r.get(s)}</div>
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}

          {items.length > 0 && advice && <div className="recommend">{advice}</div>}
        </div>
      </div>
    </div>
  );
}
