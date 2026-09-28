import React, { useEffect } from 'react';
import StatusPicker from './StatusPicker.jsx';
import { distanceOf, plural } from '../data/suppliers.js';

function Call({ s, number, statuses, onStatus, onOpen }) {
  return (
    <div className="call" style={{ animationDelay: `${number * 0.03}s` }}>
      <div className="call__num">{number}</div>
      <div className="call__main">
        <button type="button" className="call__name" onClick={() => onOpen(s.id)}>
          {s.name}
        </button>
        <div className="call__sub">
          {[s.typeTitle, s.city || s.area, distanceOf(s)].filter(Boolean).join(' · ')}
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
  );
}

export default function CallList({
  working, suggest, statuses, loading, onStatus, onOpen, onClose,
}) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [onClose]);

  const call = (s, i) => (
    <Call
      key={s.id} s={s} number={i + 1} statuses={statuses}
      onStatus={onStatus} onOpen={onOpen}
    />
  );

  return (
    <div className="modal" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal__in">
        <div className="modal__sheet">
          <div className="modal__head">
            <h2>Список обзвона</h2>
            <button type="button" className="btn btn--cyan" onClick={onClose}>Закрыть</button>
          </div>

          {loading && <div className="modal__hint">Собираем очередь…</div>}

          {!loading && (
            <div className="callbox">
              <div className="callbox__head">
                <h3 className="callbox__title">В работе</h3>
                <span className="callbox__count">
                  {working.length} {plural(working.length, 'поставщик', 'поставщика', 'поставщиков')}
                </span>
              </div>
              <div className="callbox__hint">
                Все, кому команда поставила «Звоним», — независимо от фильтров в выдаче.
              </div>
              {working.length > 0
                ? <div className="calls">{working.map(call)}</div>
                : (
                  <div className="modal__hint">
                    Пока никого. Отметьте «Звоним» у тех, с кем начинаете работать.
                  </div>
                )}

              <div className="callbox__head callbox__head--next">
                <h3 className="callbox__title">Кого добавить</h3>
                <span className="callbox__count">
                  {suggest.length} {plural(suggest.length, 'кандидат', 'кандидата', 'кандидатов')}
                </span>
              </div>
              <div className="callbox__hint">
                Лучшие по вашему приоритету под текущие фильтры: есть контакты, статус ещё не
                проставлен.
              </div>
              {suggest.length > 0
                ? <div className="calls">{suggest.map(call)}</div>
                : (
                  <div className="modal__hint">
                    Под текущие фильтры некому звонить — ослабьте условия.
                  </div>
                )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
