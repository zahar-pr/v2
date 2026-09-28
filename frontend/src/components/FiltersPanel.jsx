import React, { useState } from 'react';

const SHORT_LIST = 6;

function Group({ title, action, onAction, children }) {
  return (
    <section className="fgroup">
      <div className="fgroup__head">
        <h3 className="fgroup__title">{title}</h3>
        {action && (
          <button type="button" className="fgroup__link" onClick={onAction}>{action}</button>
        )}
      </div>
      {children}
    </section>
  );
}

function Option({ type, checked, disabled, label, hint, count, onChange }) {
  return (
    <label className={`option${disabled ? ' option--off' : ''}`}>
      <input type={type} checked={checked} disabled={disabled} onChange={onChange} />
      <span className="option__body">
        <span className="option__label">{label}</span>
        {hint && <span className="option__hint">{hint}</span>}
      </span>
      {count !== undefined && <span className="option__count">{count}</span>}
    </label>
  );
}

export default function FiltersPanel({
  meta, preset, cats, kinds, onlyDocs, onlyVerified, onlyContacts,
  facets, onPreset, onExplain, onCat, onAllCats, onKind,
  onDocs, onVerified, onContacts, onReset, anyFilter, total, loading, onApply,
}) {
  const [allCats, setAllCats] = useState(false);
  if (!meta) return null;

  const categories = meta.categories.filter((c) => c.id !== 'all');
  const tail = categories.slice(SHORT_LIST);
  const pinned = tail.some((c) => cats.includes(c.id));
  const shown = allCats || pinned ? categories : categories.slice(0, SHORT_LIST);
  const more = tail.length > 0 && !pinned;

  return (
    <>
      <div className="filters__in">
        <div className="filters__bar">
          <span className="filters__label">Фильтры</span>
          {anyFilter && (
            <button type="button" className="filters__clear" onClick={onReset}>Сбросить</button>
          )}
        </div>

        <Group title="Что важнее" action="Как считается" onAction={onExplain}>
          <div className="options">
            {meta.presets.map((item) => (
              <Option
                key={item.id}
                type="radio"
                checked={preset === item.id}
                label={item.title}
                hint={preset === item.id ? item.hint : ''}
                onChange={() => onPreset(item.id)}
              />
            ))}
          </div>
        </Group>

        <Group title="Тип поставщика">
          <div className="options">
            {meta.kinds.map((k) => (
              <Option
                key={k.id}
                type="checkbox"
                checked={kinds.includes(k.id)}
                label={k.title}
                count={facets ? facets.types[k.id] || 0 : undefined}
                onChange={() => onKind(k.id)}
              />
            ))}
          </div>
        </Group>

        <Group
          title="Категория"
          action={more ? (allCats ? 'Свернуть' : `Ещё ${tail.length}`) : ''}
          onAction={() => setAllCats((v) => !v)}
        >
          <div className="options">
            <Option
              type="checkbox"
              checked={cats.length === 0}
              label="Все категории"
              onChange={onAllCats}
            />
            {shown.map((c) => {
              const count = facets ? facets.cats[c.id] || 0 : undefined;
              const on = cats.includes(c.id);
              return (
                <Option
                  key={c.id}
                  type="checkbox"
                  checked={on}
                  disabled={!on && count === 0}
                  label={c.title}
                  count={count}
                  onChange={() => onCat(c.id)}
                />
              );
            })}
          </div>
        </Group>

        <Group title="Показывать только">
          <div className="options">
            <Option
              type="checkbox" checked={onlyContacts} label="С контактами"
              count={facets ? facets.withContacts : undefined} onChange={onContacts}
            />
            <Option
              type="checkbox" checked={onlyDocs} label="С документами"
              count={facets ? facets.withDocs : undefined} onChange={onDocs}
            />
            <Option
              type="checkbox" checked={onlyVerified} label="Данные подтверждены"
              count={facets ? facets.verified : undefined} onChange={onVerified}
            />
          </div>
        </Group>
      </div>

      <div className="filters__foot">
        <button type="button" className="btn btn--ghost" onClick={onReset} disabled={!anyFilter}>
          Сбросить
        </button>
        <button type="button" className="btn btn--cyan" onClick={onApply}>
          {loading ? 'Считаем…' : `Показать ${total}`}
        </button>
      </div>
    </>
  );
}
