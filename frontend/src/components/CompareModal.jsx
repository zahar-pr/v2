import React, { useEffect, useState } from 'react';
import FactorStrip from './FactorStrip.jsx';
import { COMPARE_ROWS, placeOf, weightsToString } from '../data/suppliers.js';
import { recommend } from '../api/client.js';

function noteRow(notes, s) {
  return notes[s.id] !== undefined ? notes[s.id] : s.note;
}

export default function CompareModal({
  items, notes, narrow, preset, weights, showcase, onShowcase, onClear, onClose,
}) {
  const [advice, setAdvice] = useState(null);
  const [loading, setLoading] = useState(false);

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
    if (!items.length) { setAdvice(null); return undefined; }
    let alive = true;
    setLoading(true);
    recommend(items.map((s) => s.id), preset, weightsToString(weights))
      .then((answer) => { if (alive) { setAdvice(answer); setLoading(false); } })
      .catch(() => { if (alive) { setAdvice(null); setLoading(false); } });
    return () => { alive = false; };
  }, [ids, preset]);

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
              <p>Добавьте в сравнение до трёх поставщиков кнопкой «Сравнить» в карточке.</p>
              {showcase.length > 0 && (
                <button type="button" className="btn btn--cyan" onClick={onShowcase}>
                  Показать пример: {showcase.map((s) => s.name).join(' и ')}
                </button>
              )}
            </div>
          )}

          {items.length > 0 && (
            <div className="cmpheads">
              {items.map((s) => (
                <div className="cmphead" key={s.id}>
                  <div className={`prio prio--${s.level}`}>{s.score}</div>
                  <div>
                    <strong>{s.name}</strong>
                    <small>{[s.typeTitle, placeOf(s)].filter(Boolean).join(' · ')}</small>
                  </div>
                  <FactorStrip factors={s.factors} onOpen={() => {}} />
                </div>
              ))}
            </div>
          )}

          {loading && <div className="modal__hint">Считаем, кто впереди…</div>}

          {advice && advice.diff.length > 0 && (
            <div className="diff">
              <div className="diff__title">Почему впереди «{(items.find((s) => s.id === advice.bestId) || {}).name}»</div>
              {advice.diff.map((row) => (
                <div className="diff__row" key={row.factor}>
                  <span className="diff__factor">{row.factor}</span>
                  <span className="diff__gap">+{row.gap}</span>
                  <span className="diff__text">
                    <b>{row.leader}</b>: {row.reason || 'данные полнее'}
                    {row.lack ? <> · у второго {row.lack}</> : null}
                  </span>
                </div>
              ))}
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
                        <small>{placeOf(s) || s.region}</small>
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
                    <small>{[placeOf(s) || s.region, `приоритет ${s.score}`].filter(Boolean).join(' · ')}</small>
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

          {advice && advice.text && <div className="recommend">{advice.text}</div>}
        </div>
      </div>
    </div>
  );
}
