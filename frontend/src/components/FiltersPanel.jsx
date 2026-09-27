import React from 'react';

export default function FiltersPanel({
  meta, preset, cat, kinds, onlyDocs, onlyVerified, onlyContacts,
  facets, onPreset, onExplain,
  onCat, onKind, onDocs, onVerified, onContacts, onReset, anyFilter,
  total, loading, onApply,
}) {
  if (!meta) return null;

  return (
    <div className="filters__in">
      <div className="fgroup">
        <div className="fgroup__head">
          <span className="fgroup__title">Что важнее</span>
          <button type="button" className="fgroup__link" onClick={onExplain}>Как считается</button>
        </div>
        <div className="fgroup__body">
          {meta.presets.map((item) => (
            <button
              type="button"
              key={item.id}
              className={`preset${preset === item.id ? ' preset--on' : ''}`}
              onClick={() => onPreset(item.id)}
            >
              <span className="preset__title">{item.title}</span>
              <span className="preset__hint">{item.hint}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="fgroup">
        <div className="fgroup__head"><span className="fgroup__title">Тип поставщика</span></div>
        <div className="fgroup__body fgroup__body--row">
          {meta.kinds.map((k) => (
            <button
              type="button" key={k.id}
              className={`pill${kinds.includes(k.id) ? ' pill--on' : ''}`}
              onClick={() => onKind(k.id)}
            >
              {k.title}
              {facets && <span className="pill__count">{facets.types[k.id] || 0}</span>}
            </button>
          ))}
        </div>
      </div>

      <div className="fgroup">
        <div className="fgroup__head"><span className="fgroup__title">Категория</span></div>
        <div className="fgroup__body fgroup__body--grid">
          {meta.categories.map((c) => (
            <button
              type="button" key={c.id}
              className={`chip chip--wide${cat === c.id ? ' chip--on' : ''}`}
              onClick={() => onCat(c.id)}
            >
              {c.title}
            </button>
          ))}
        </div>
      </div>

      <div className="fgroup">
        <div className="fgroup__head"><span className="fgroup__title">Показывать только</span></div>
        <div className="fgroup__body">
          <label className="check">
            <input type="checkbox" checked={onlyContacts} onChange={onContacts} />
            С контактами
            {facets && <span className="check__count">{facets.withContacts}</span>}
          </label>
          <label className="check">
            <input type="checkbox" checked={onlyDocs} onChange={onDocs} />
            С документами
            {facets && <span className="check__count">{facets.withDocs}</span>}
          </label>
          <label className="check">
            <input type="checkbox" checked={onlyVerified} onChange={onVerified} />
            С подтверждёнными данными
            {facets && <span className="check__count">{facets.verified}</span>}
          </label>
        </div>
      </div>

      <div className="filters__foot">
        {anyFilter && (
          <button type="button" className="btn btn--ghost" onClick={onReset}>Сбросить</button>
        )}
        <button type="button" className="btn btn--cyan" onClick={onApply}>
          {loading ? 'Считаем…' : `Показать ${total}`}
        </button>
      </div>
    </div>
  );
}
