import React, { useEffect } from 'react';
import StatusPicker from './StatusPicker.jsx';
import { distanceOf } from '../data/suppliers.js';

export default function CallList({ items, statuses, loading, onStatus, onOpen, onClose }) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [onClose]);

  return (
    <div className="modal" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal__in">
        <div className="modal__sheet">
          <div className="modal__head">
            <h2>Список обзвона</h2>
            <button type="button" className="btn btn--cyan" onClick={onClose}>Закрыть</button>
          </div>

          <div className="modal__hint">
            Поставщики с контактами, в порядке вашего приоритета. Отказы и подходящие сюда не попадают.
          </div>

          {loading && <div className="modal__hint">Собираем очередь…</div>}

          {!loading && items.length === 0 && (
            <div className="modal__hint">Под текущие фильтры некому звонить — ослабьте условия.</div>
          )}

          <div className="calls">
            {items.map((s, i) => (
              <div className="call" key={s.id} style={{ animationDelay: `${i * 0.03}s` }}>
                <div className="call__num">{i + 1}</div>
                <div className="call__main">
                  <button type="button" className="call__name" onClick={() => onOpen(s.id)}>
                    {s.name}
                  </button>
                  <div className="call__sub">
                    {[s.typeTitle, s.city, distanceOf(s)].filter(Boolean).join(' · ')}
                  </div>
                  {s.ask.length > 0 && (
                    <div className="call__ask">Спросить: {s.ask.slice(0, 3).join('; ').toLowerCase()}</div>
                  )}
                </div>
                <div className="call__side">
                  <div className={`prio prio--${s.level}`}>{s.score}</div>
                  {s.phone
                    ? <a className="call__phone" href={`tel:${s.phone.replace(/[^+\d]/g, '')}`}>{s.phone}</a>
                    : <a className="call__phone" href={`mailto:${s.email}`}>{s.email}</a>}
                  <StatusPicker value={s.status} statuses={statuses} onChange={(v) => onStatus(s.id, v)} compact />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
