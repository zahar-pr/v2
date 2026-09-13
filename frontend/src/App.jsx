import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Logo from './components/Logo.jsx';
import Dropdown from './components/Dropdown.jsx';
import SupplierCard from './components/SupplierCard.jsx';
import SupplierPanel from './components/SupplierPanel.jsx';
import CompareModal from './components/CompareModal.jsx';
import useNarrow from './hooks/useNarrow.js';
import useDebounced from './hooks/useDebounced.js';
import { getMeta, getNotes, getStatus, getSuppliers, saveNote } from './api/client.js';
import { plural } from './data/suppliers.js';

const MAX_COMPARE = 3;
const SKELETONS = [0, 1, 2, 3, 4, 5];
const PER_PAGE = 12;

const STEPS = [
  { n: 1, color: '#00E1E1', title: 'Фильтр по категории и региону', text: 'Поиск идёт по индексу: категория, регион, город, документы, опт и производство.' },
  { n: 2, color: '#2BE2A0', title: 'Единая карточка данных', text: 'Контакты, реквизиты, документы, минимальный заказ и ссылки на все источники.' },
  { n: 3, color: '#FFFFFF', title: 'Сравнение и решение', text: 'До трёх компаний рядом, оценка готовности к контакту и заметки по переговорам.' },
];

export default function App() {
  const [meta, setMeta] = useState(null);
  const [query, setQuery] = useState('');
  const [cat, setCat] = useState('all');
  const [region, setRegion] = useState('');
  const [city, setCity] = useState('');
  const [sort, setSort] = useState('');
  const [onlyDocs, setOnlyDocs] = useState(false);
  const [onlyVerified, setOnlyVerified] = useState(false);
  const [onlyWholesale, setOnlyWholesale] = useState(false);

  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState('');
  const [stats, setStats] = useState(null);
  const [status, setStatus] = useState(null);

  const [menu, setMenu] = useState(null);
  const [selId, setSelId] = useState(null);
  const [compare, setCompare] = useState([]);
  const [compareOpen, setCompareOpen] = useState(false);
  const [notes, setNotes] = useState({});

  const narrow = useNarrow();
  const settledQuery = useDebounced(query, 350);
  const timers = useRef({});
  const ready = Boolean(meta);

  useEffect(() => {
    let alive = true;

    getMeta()
      .then((answer) => {
        if (!alive) return;
        setMeta(answer);
        setRegion(answer.defaults.region);
        setCity(answer.defaults.city);
        setSort(answer.defaults.sort);
        setStats(answer.stats);
        setStatus(answer.status);
      })
      .catch((e) => {
        if (!alive) return;
        setError(e.message);
        setLoading(false);
      });

    getNotes()
      .then((saved) => {
        if (!alive) return;
        const map = {};
        saved.forEach((note) => { map[note.supplierId] = note.text; });
        setNotes(map);
      })
      .catch(() => {});

    return () => { alive = false; };
  }, []);

  const load = useCallback(
    (nextPage, append) => {
      if (!meta) return undefined;
      let alive = true;

      if (append) setLoadingMore(true);
      else setLoading(true);
      setError('');

      getSuppliers({
        q: settledQuery.trim(),
        category: cat,
        region,
        city,
        sort,
        onlyDocs,
        onlyVerified,
        onlyWholesale,
        page: nextPage,
        perPage: PER_PAGE,
      })
        .then((answer) => {
          if (!alive) return;
          setItems((prev) => (append ? [...prev, ...answer.items] : answer.items));
          setTotal(answer.total);
          setPages(answer.pages);
          setPage(answer.page);
          setStats(answer.stats);
          setStatus(answer.status);
          setLoading(false);
          setLoadingMore(false);
        })
        .catch((e) => {
          if (!alive) return;
          if (!append) setItems([]);
          setError(e.message);
          setLoading(false);
          setLoadingMore(false);
        });

      return () => { alive = false; };
    },
    [meta, settledQuery, cat, region, city, sort, onlyDocs, onlyVerified, onlyWholesale]
  );

  useEffect(() => {
    setSelId(null);
    return load(1, false);
  }, [load]);

  useEffect(() => {
    if (!status || !status.indexing) return undefined;
    const timer = setInterval(() => {
      getStatus()
        .then((answer) => {
          setStats(answer.stats);
          setStatus(answer.status);
          if (!answer.status.indexing) load(1, false);
        })
        .catch(() => {});
    }, 6000);
    return () => clearInterval(timer);
  }, [status, load]);

  const cities = useMemo(() => {
    if (!meta) return [];
    const list = meta.cities[region] || meta.cities[meta.labels.anyRegion] || [];
    return [meta.labels.anyCity, ...list];
  }, [meta, region]);

  const selected = items.find((s) => s.id === selId) || null;
  const compareItems = compare.map((id) => items.find((s) => s.id === id)).filter(Boolean);
  const anyFilter = Boolean(query) || onlyDocs || onlyVerified || onlyWholesale
    || (meta && (cat !== meta.defaults.category || region !== meta.defaults.region
      || city !== meta.defaults.city || sort !== meta.defaults.sort));

  const toggleCompare = (id) => setCompare((prev) => (
    prev.includes(id)
      ? prev.filter((x) => x !== id)
      : prev.length >= MAX_COMPARE ? prev : [...prev, id]
  ));

  const resetAll = () => {
    if (!meta) return;
    setQuery('');
    setCat(meta.defaults.category);
    setRegion(meta.defaults.region);
    setCity(meta.defaults.city);
    setSort(meta.defaults.sort);
    setOnlyDocs(false); setOnlyVerified(false); setOnlyWholesale(false);
  };

  const changeRegion = (value) => {
    setRegion(value);
    if (meta) setCity(meta.defaults.city);
  };

  const changeNote = (supplierId, text) => {
    setNotes((prev) => ({ ...prev, [supplierId]: text }));
    clearTimeout(timers.current[supplierId]);
    timers.current[supplierId] = setTimeout(() => {
      saveNote(supplierId, text).catch(() => {});
    }, 600);
  };

  const indexing = Boolean(status && status.indexing);
  const badge = () => {
    if (loading) return 'Ищем поставщиков';
    if (indexing) {
      return `Индекс наполняется: ${status.citiesDone} из ${status.citiesTotal} городов`;
    }
    const n = (stats && stats.total) || 0;
    return `${n} ${plural(n, 'поставщик', 'поставщика', 'поставщиков')} в индексе`;
  };

  return (
    <>
      <header className="header">
        <div className="wrap header__in">
          <div className="brand">
            <Logo />
            <span className="brand__name">Провизия</span>
          </div>
          <div className="header__found">Найдено: <b>{loading ? '…' : total}</b></div>
          <button
            type="button"
            className={`btn-compare${compare.length ? ' btn-compare--on' : ''}`}
            onClick={() => { setCompareOpen(true); setSelId(null); setMenu(null); }}
          >
            Сравнить
            <span className="btn-compare__count">{compare.length}</span>
          </button>
        </div>
      </header>

      <div className="hero">
        <section className="wrap hero__in">
          <div className="hero__badge">
            <i />
            <span style={{ whiteSpace: 'nowrap' }}>{badge()}</span>
          </div>
          <h1>Поставщики продуктов, ингредиентов и упаковки в одном каталоге</h1>

          <div className="steps">
            {STEPS.map((s, i) => (
              <div className="step" key={s.n} style={{ animationDelay: `${0.06 * (i + 1) + 0.04}s` }}>
                <div className="step__head">
                  <span className="step__n" style={{ background: s.color }}>{s.n}</span>
                  <span className="step__title">{s.title}</span>
                </div>
                <p>{s.text}</p>
              </div>
            ))}
          </div>

          <div className="search">
            <div className="search__row">
              <div className="search__field">
                <svg viewBox="0 0 20 20" width="18" height="18" fill="none" style={{ flex: 'none' }}>
                  <circle cx="8.5" cy="8.5" r="6" stroke="#0F2229" strokeWidth="1.8" />
                  <path d="M13.2 13.2L18 18" stroke="#0F2229" strokeWidth="1.8" strokeLinecap="round" />
                </svg>
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Название, вид продукции, город, документы…"
                  aria-label="Поиск поставщиков"
                />
                {query && (
                  <button type="button" className="search__clear" onClick={() => setQuery('')}>Сбросить</button>
                )}
              </div>

              <Dropdown
                label="Регион"
                value={region || '—'}
                options={(meta && meta.regions) || []}
                open={menu === 'region'}
                onToggle={(v) => setMenu(v ? 'region' : null)}
                onSelect={changeRegion}
              />
              <Dropdown
                label="Город"
                value={city || '—'}
                options={cities}
                open={menu === 'city'}
                onToggle={(v) => setMenu(v ? 'city' : null)}
                onSelect={setCity}
              />
              <Dropdown
                label="Сортировка"
                value={sort || '—'}
                options={(meta && meta.sorts) || []}
                open={menu === 'sort'}
                onToggle={(v) => setMenu(v ? 'sort' : null)}
                onSelect={setSort}
              />
            </div>

            <div className="chips">
              {((meta && meta.categories) || []).map((c) => (
                <button
                  type="button"
                  key={c.id}
                  className={`chip${cat === c.id ? ' chip--on' : ''}`}
                  onClick={() => setCat(c.id)}
                >
                  {c.title}
                </button>
              ))}
            </div>
          </div>
        </section>
      </div>

      <section className="wrap catalog">
        <div className="filterbar">
          <label>
            <input type="checkbox" checked={onlyDocs} onChange={() => setOnlyDocs((v) => !v)} />
            Только с документами
          </label>
          <label>
            <input type="checkbox" checked={onlyVerified} onChange={() => setOnlyVerified((v) => !v)} />
            Данные подтверждены
          </label>
          <label>
            <input type="checkbox" checked={onlyWholesale} onChange={() => setOnlyWholesale((v) => !v)} />
            Опт и производство
          </label>
          {anyFilter && (
            <button type="button" className="filterbar__reset" onClick={resetAll}>Сбросить все фильтры</button>
          )}
        </div>

        {indexing && !loading && (
          <div className="notice">
            Индекс наполняется в фоне: {status.citiesDone} из {status.citiesTotal} городов
            {status.city ? `, сейчас ${status.city}` : ''}. Выдача пополняется автоматически.
          </div>
        )}

        {loading && (
          <div className="grid">
            {SKELETONS.map((i) => (
              <article className="card card--skel" key={i} style={{ animationDelay: `${i * 0.04}s` }}>
                <div className="skel skel--title" />
                <div className="skel skel--sub" />
                <div className="skel skel--tags" />
                <div className="skel skel--specs" />
                <div className="skel skel--bar" />
              </article>
            ))}
          </div>
        )}

        {!loading && error && (
          <div className="empty">
            <h3>Не получилось загрузить поставщиков</h3>
            <p>{error}</p>
            <button type="button" className="btn btn--cyan" onClick={() => load(1, false)}>Повторить</button>
          </div>
        )}

        {!loading && !error && items.length > 0 && (
          <>
            <div className="grid">
              {items.map((s, i) => (
                <SupplierCard
                  key={s.id}
                  supplier={s}
                  index={i % PER_PAGE}
                  inCompare={compare.includes(s.id)}
                  compareFull={compare.length >= MAX_COMPARE && !compare.includes(s.id)}
                  onOpen={() => { setSelId(s.id); setMenu(null); }}
                  onCompare={() => toggleCompare(s.id)}
                />
              ))}
            </div>

            <div className="more">
              <span className="more__count">Показано {items.length} из {total}</span>
              {page < pages && (
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => load(page + 1, true)}
                  disabled={loadingMore}
                >
                  {loadingMore ? 'Загружаем…' : 'Показать ещё'}
                </button>
              )}
            </div>
          </>
        )}

        {!loading && !error && items.length === 0 && (
          <div className="empty">
            <h3>{indexing ? 'Индекс ещё наполняется' : 'Под эти фильтры поставщиков нет'}</h3>
            <p>
              {indexing
                ? 'Города добавляются по очереди, это занимает несколько минут. Выберите город — он проиндексируется сразу.'
                : 'Снимите часть условий, очистите строку поиска или выберите другой регион.'}
            </p>
            <button type="button" className="btn btn--cyan" onClick={resetAll}>Сбросить фильтры</button>
          </div>
        )}
      </section>

      <footer className="footer">
        <div className="wrap footer__in">
          <div>Провизия — поиск поставщиков food-направления</div>
          <div>
            Источники: {((meta && meta.sources) || []).filter((s) => s.active).map((s) => s.title).join(', ')}
          </div>
        </div>
      </footer>

      {selected && (
        <SupplierPanel
          supplier={selected}
          note={notes[selected.id] !== undefined ? notes[selected.id] : selected.note}
          onNote={(v) => changeNote(selected.id, v)}
          inCompare={compare.includes(selected.id)}
          compareFull={compare.length >= MAX_COMPARE && !compare.includes(selected.id)}
          onCompare={() => toggleCompare(selected.id)}
          onClose={() => setSelId(null)}
        />
      )}

      {compareOpen && (
        <CompareModal
          items={compareItems}
          notes={notes}
          narrow={narrow}
          onClear={() => setCompare([])}
          onClose={() => setCompareOpen(false)}
        />
      )}
    </>
  );
}
