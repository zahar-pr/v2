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
              Балл от 0 до 100 отвечает на один вопрос: <b>кому звонить первым</b>. Вкус продукта
              по открытым данным знать нельзя, а вот санитарную историю, документы и реквизиты —
              можно, и именно из них складывается балл.
            </p>
            <p>
              Санитарная история работает особым образом: это не слагаемое, а потолок. Действующее
              решение надзора обнуляет карточку целиком, истёкшая приостановка держит балл ниже
              тридцати — сколько бы ни было телефонов и деклараций.
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
              о нём мало известно. В карточке для таких есть список «что уточнить в первом звонке»
              и блок «чего не хватает»: это ровно те поля, которых нет, с объяснением, зачем они
              нужны. Запрос КП подставляет их в письмо автоматически.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
