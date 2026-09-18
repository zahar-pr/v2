import React, { useEffect } from 'react';

export default function ScoreExplainer({ factors, presets, onClose }) {
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
            <h2>Как считается приоритет звонка</h2>
            <button type="button" className="btn btn--cyan" onClick={onClose}>Понятно</button>
          </div>

          <div className="explain">
            <p>
              Балл от 0 до 100 отвечает на один вопрос: <b>кому звонить первым</b>. Это не оценка
              качества продукции — её по открытым данным знать нельзя. Это оценка того, насколько
              поставщик готов к разговору о закупке и насколько мы в нём уверены.
            </p>

            <div className="explain__grid">
              {factors.map((f) => (
                <div className="explain__item" key={f.id}>
                  <div className="explain__title">{f.title}</div>
                  <div className="explain__text">{f.hint}</div>
                </div>
              ))}
            </div>

            <p>
              Каждый фактор считается отдельно от 0 до 100, затем складывается с весом. Веса
              переключаются пресетами:
            </p>

            <div className="explain__presets">
              {presets.map((p) => (
                <div className="explain__preset" key={p.id}>
                  <b>{p.title}</b> — {p.hint}
                  <div className="explain__weights">
                    {factors.map((f) => `${f.title} ${p.weights[f.id]}%`).join(' · ')}
                  </div>
                </div>
              ))}
            </div>

            <p>
              Низкий балл не значит плохой поставщик — чаще это значит, что в открытых источниках
              о нём мало известно. В карточке для таких есть список «что уточнить в первом звонке»:
              это ровно те поля, которых не хватает.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
