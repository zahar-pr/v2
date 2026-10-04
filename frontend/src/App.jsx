import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Logo from './components/Logo.jsx';
import ClientLogos from './components/ClientLogos.jsx';
import Dropdown from './components/Dropdown.jsx';
import FiltersPanel from './components/FiltersPanel.jsx';
import ThemeToggle from './components/ThemeToggle.jsx';
import SupplierCard from './components/SupplierCard.jsx';
import SupplierPanel from './components/SupplierPanel.jsx';
import CompareModal from './components/CompareModal.jsx';
import CallList from './components/CallList.jsx';
import ScoreExplainer from './components/ScoreExplainer.jsx';
import Intro from './components/Intro.jsx';
import HelpButton from './components/HelpButton.jsx';
import Workspace from './components/Workspace.jsx';
import useNarrow from './hooks/useNarrow.js';
import useTheme from './hooks/useTheme.js';
import useDebounced from './hooks/useDebounced.js';
import {
  getCallList, getMeta, getNotes, getStatus, getSupplier, getSuppliers, getWorkspace,
  saveNote, setStatus,
} from './api/client.js';
import { plural, weightsToString } from './data/suppliers.js';

const MAX_COMPARE = 3;
const SKELETONS = [0, 1, 2, 3, 4, 5];
const PER_PAGE = 12;

export default function App() {
  const [meta, setMeta] = useState(null);
  const [query, setQuery] = useState('');
  const [cats, setCats] = useState([]);
  const [region, setRegion] = useState('');
  const [city, setCity] = useState('');
  const [sort, setSort] = useState('');
  const [preset, setPreset] = useState('balanced');
  const [weights, setWeights] = useState({});
  const [kinds, setKinds] = useState([]);
  const [onlyDocs, setOnlyDocs] = useState(false);
  const [onlyVerified, setOnlyVerified] = useState(false);
  const [onlyContacts, setOnlyContacts] = useState(false);
  const [onlySafe, setOnlySafe] = useState(false);
  const [price, setPrice] = useState('');
  const [delivers, setDelivers] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');

  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState('');
  const [stats, setStats] = useState(null);
  const [status, setStatusState] = useState(null);
  const [counts, setCounts] = useState({});
  const [facets, setFacets] = useState(null);
  const [relax, setRelax] = useState([]);

  const [menu, setMenu] = useState(null);
  const [selId, setSelId] = useState(null);
  const [compare, setCompare] = useState([]);
  const [compareOpen, setCompareOpen] = useState(false);
  const [callsOpen, setCallsOpen] = useState(false);
  const [calls, setCalls] = useState({ working: [], suggest: [] });
  const [callsLoading, setCallsLoading] = useState(false);
  const [explainOpen, setExplainOpen] = useState(false);
  const [introOpen, setIntroOpen] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [deskOpen, setDeskOpen] = useState(false);
  const [desk, setDesk] = useState(null);
  const [deskLoading, setDeskLoading] = useState(false);
  const [project, setProject] = useState(null);
  const [notes, setNotes] = useState({});
  const [showcase, setShowcase] = useState([]);
  const [shared, setShared] = useState(null);

  const narrow = useNarrow();
  const [theme, toggleTheme] = useTheme();
  const settledQuery = useDebounced(query, 350);
  const timers = useRef({});

  useEffect(() => {
    let alive = true;

    getMeta()
      .then((answer) => {
        if (!alive) return;
        setMeta(answer);
        setCats(answer.defaults.category && answer.defaults.category !== 'all'
          ? [answer.defaults.category] : []);
        setRegion(answer.defaults.region);
        setCity(answer.defaults.city);
        setSort(answer.defaults.sort);
        setPreset(answer.defaults.preset);
        setKinds(answer.defaults.kinds);
        const found = answer.presets.find((p) => p.id === answer.defaults.preset);
        setWeights(found ? found.weights : {});
        setStats(answer.stats);
        setStatusState(answer.status);
        setShowcase(answer.showcase || []);
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

  const filters = useMemo(() => ({
    q: settledQuery.trim(),
    category: cats.join(','),
    region,
    city,
    kinds: kinds.join(','),
    onlyDocs,
    onlyVerified,
    onlyContacts,
    onlySafe,
    price,
    delivers,
    status: statusFilter,
    preset,
    weights: weightsToString(weights),
    sort,
  }), [settledQuery, cats, region, city, kinds, onlyDocs, onlyVerified, onlyContacts, onlySafe,
    price, delivers, statusFilter, preset, weights, sort]);

  // памятка встречает на каждом заходе и обновлении страницы
  useEffect(() => {
    if (meta) setIntroOpen(true);
  }, [meta]);

  const closeIntro = () => setIntroOpen(false);

  // первый заход открывается с готовым примером сравнения — парой поставщиков одного продукта
  useEffect(() => {
    if (!showcase.length) return;
    try {
      if (localStorage.getItem('provizia_seen_v2')) return;
      localStorage.setItem('provizia_seen_v2', '1');
    } catch (error) {
      // приватный режим: пример всё равно показываем
    }
    setCompare(showcase.slice(0, 2).map((s) => s.id));
  }, [showcase]);

  // Досье можно переслать коллеге: адрес вида #/s/<id> открывает ту же карточку.
  const openId = () => {
    const found = /^#\/s\/(.+)$/.exec(window.location.hash || '');
    return found ? decodeURIComponent(found[1]) : '';
  };

  const wanted = useRef(openId());

  // Карточки из ссылки может не быть в текущей выдаче — тогда тянем её отдельно.
  useEffect(() => {
    if (!selId || !meta) return;
    if (items.some((s) => s.id === selId)) return;
    if (shared && shared.id === selId) return;
    getSupplier(selId, filters)
      .then(setShared)
      .catch(() => setShared(null));
  }, [selId, meta, items]);

  useEffect(() => {
    // Пока входящая ссылка не прочитана, адрес не трогаем — иначе сами её и затрём.
    if (wanted.current) return;
    const target = selId ? `#/s/${encodeURIComponent(selId)}` : '';
    if ((window.location.hash || '') === target) return;
    window.history.replaceState(null, '', target || window.location.pathname);
  }, [selId]);

  const load = useCallback(
    (nextPage, append) => {
      if (!meta) return undefined;
      let alive = true;

      if (append) setLoadingMore(true);
      else setLoading(true);
      setError('');

      getSuppliers({ ...filters, page: nextPage, perPage: PER_PAGE })
        .then((answer) => {
          if (!alive) return;
          setItems((prev) => (append ? [...prev, ...answer.items] : answer.items));
          setTotal(answer.total);
          setPages(answer.pages);
          setPage(answer.page);
          setStats(answer.stats);
          setStatusState(answer.status);
          setCounts(answer.pipeline || {});
          setFacets(answer.facets || null);
          setRelax(answer.relax || []);
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
    [meta, filters]
  );

  // Открытую карточку закрывает смена фильтров, а не каждый перезапуск загрузки:
  // пока условия те же, пришедшее по ссылке досье остаётся на экране.
  const filtersKey = JSON.stringify(filters);
  const lastFilters = useRef('');

  useEffect(() => {
    if (!meta) return undefined;
    const changed = lastFilters.current !== '' && lastFilters.current !== filtersKey;
    lastFilters.current = filtersKey;
    if (changed) {
      setSelId(null);
    } else if (wanted.current) {
      setSelId(wanted.current);
      wanted.current = '';
    }
    return load(1, false);
  }, [load, meta]);

  useEffect(() => {
    if (!filtersOpen) return undefined;
    const onKey = (e) => { if (e.key === 'Escape') setFiltersOpen(false); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [filtersOpen]);

  useEffect(() => {
    if (!status || !status.indexing) return undefined;
    const timer = setInterval(() => {
      getStatus()
        .then((answer) => {
          setStats(answer.stats);
          setStatusState(answer.status);
          if (!answer.status.indexing) load(1, false);
        })
        .catch(() => {});
    }, 6000);
    return () => clearInterval(timer);
  }, [status, load]);

  const exportUrl = () => {
    const search = new URLSearchParams();
    Object.entries({ ...filters, delivers: String(delivers), limit: 300 }).forEach(([key, value]) => {
      if (value !== '' && value !== undefined && value !== null && value !== false) {
        search.set(key, String(value));
      }
    });
    return '/api/export.csv?' + search;
  };

  const openDesk = () => {
    setDeskOpen(true);
    setMenu(null);
    if (desk) return;
    setDeskLoading(true);
    getWorkspace()
      .then((answer) => { setDesk(answer); setDeskLoading(false); })
      .catch(() => { setDesk(null); setDeskLoading(false); });
  };

  // Проект сети — это готовый срез: город сети и набор её продуктов.
  const pickProject = (item) => {
    if (!meta) return;
    setProject(item);
    setCats(item.cats);
    setCity(item.city || meta.labels.anyCity);
    setRegion(item.city ? (meta.regions.find((r) => (meta.cities[r] || []).includes(item.city)) || meta.labels.anyRegion) : meta.labels.anyRegion);
    setKinds(meta.defaults.kinds);
    setOnlySafe(true);
    setStatusFilter('');
    setQuery('');
    setDeskOpen(false);
  };

  const openCalls = () => {
    setCallsOpen(true);
    setCallsLoading(true);
    setMenu(null);
    getCallList({ ...filters, limit: 20 })
      .then((answer) => {
        setCalls({ working: answer.working || [], suggest: answer.suggest || [] });
        setCallsLoading(false);
      })
      .catch(() => { setCalls({ working: [], suggest: [] }); setCallsLoading(false); });
  };

  const cities = useMemo(() => {
    if (!meta) return [];
    const list = meta.cities[region] || meta.cities[meta.labels.anyRegion] || [];
    return [meta.labels.anyCity, ...list];
  }, [meta, region]);

  const inCalls = (id) => calls.working.find((s) => s.id === id)
    || calls.suggest.find((s) => s.id === id);
  const selected = items.find((s) => s.id === selId)
    || inCalls(selId)
    || (shared && shared.id === selId ? shared : null);
  const compareItems = compare
    .map((id) => items.find((s) => s.id === id)
      || inCalls(id)
      || (shared && shared.id === id ? shared : null)
      || showcase.find((s) => s.id === id))
    .filter(Boolean);
  const anyFilter = Boolean(query) || onlyDocs || onlyVerified || onlyContacts || onlySafe
    || price || !delivers || statusFilter
    || cats.length > 0
    || (meta && (region !== meta.defaults.region || city !== meta.defaults.city
      || sort !== meta.defaults.sort || kinds.join(',') !== meta.defaults.kinds.join(',')));

  const toggleCompare = (id) => setCompare((prev) => (
    prev.includes(id)
      ? prev.filter((x) => x !== id)
      : prev.length >= MAX_COMPARE ? prev : [...prev, id]
  ));

  const toggleCat = (id) => setCats((prev) => (
    prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
  ));

  const toggleKind = (id) => setKinds((prev) => (
    prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
  ));

  const resetAll = () => {
    if (!meta) return;
    setQuery('');
    setCats([]);
    setRegion(meta.defaults.region);
    setCity(meta.defaults.city);
    setSort(meta.defaults.sort);
    setKinds(meta.defaults.kinds);
    setOnlyDocs(false); setOnlyVerified(false); setOnlyContacts(false); setOnlySafe(false);
    setPrice(''); setDelivers(true);
    setStatusFilter('');
    setProject(null);
  };

  const changeRegion = (value) => {
    setRegion(value);
    if (meta) setCity(meta.defaults.city);
  };

  const changePreset = (id) => {
    setPreset(id);
    const found = meta.presets.find((p) => p.id === id);
    if (found) setWeights(found.weights);
  };

  const applyRelax = (item) => {
    if (!meta) return;
    (item.keys || [item.key]).forEach(relaxOne);
  };

  const relaxOne = (key) => {
    if (!meta) return;
    if (key === 'only_docs') setOnlyDocs(false);
    else if (key === 'only_safe') setOnlySafe(false);
    else if (key === 'price') setPrice('');
    else if (key === 'delivers') setDelivers(true);
    else if (key === 'only_verified') setOnlyVerified(false);
    else if (key === 'only_contacts') setOnlyContacts(false);
    else if (key === 'kinds') setKinds(meta.kinds.map((k) => k.id));
    else if (key === 'query') setQuery('');
    else if (key === 'category') setCats([]);
    else if (key === 'city') setCity(meta.defaults.city);
    else if (key === 'region') setRegion(meta.labels.anyRegion);
    else if (key === 'status') setStatusFilter('');
  };

  const changeNote = (supplierId, text) => {
    setNotes((prev) => ({ ...prev, [supplierId]: text }));
    clearTimeout(timers.current[supplierId]);
    timers.current[supplierId] = setTimeout(() => {
      saveNote(supplierId, text).catch(() => {});
    }, 600);
  };

  const changeStatus = (supplierId, next) => {
    const apply = (list) => list.map((s) => (s.id === supplierId ? { ...s, status: next } : s));
    setItems(apply);
    setCalls(apply);
    setStatus(supplierId, next)
      .then((answer) => setCounts(answer.counts || {}))
      .catch(() => {});
  };

  const activeFilters = [
    query, onlyDocs, onlyVerified, onlyContacts, onlySafe, price, !delivers, statusFilter,
    cats.length > 0,
    meta && kinds.join(',') !== meta.defaults.kinds.join(','),
  ].filter(Boolean).length;
  const presetTitle = ((meta && meta.presets) || []).find((p) => p.id === preset)?.title || '';

  const indexing = Boolean(status && status.indexing);
  const badge = () => {
    if (loading) return 'Подбираем поставщиков';
    if (indexing) return `Индекс наполняется: ${status.citiesDone} из ${status.citiesTotal} городов`;
    if (!stats) return '';
    const mills = plural(stats.producers, 'производство', 'производства', 'производств');
    const bases = plural(stats.wholesale, 'оптовая база', 'оптовых базы', 'оптовых баз');
    const towns = plural(stats.citiesIndexed, 'городе', 'городах', 'городах');
    return `${stats.producers} ${mills} и ${stats.wholesale} ${bases} в ${stats.citiesIndexed} ${towns}`
      + ' · все сверены с перечнями Роспотребнадзора';
  };

  return (
    <>
      <header className="header">
        <div className="wrap header__in">
          <div className="brand">
            <Logo />
            <span className="brand__name">Goulash Поставщики</span>
          </div>
          <div className="header__found">Найдено: <b>{loading ? '…' : total}</b></div>
          <ThemeToggle theme={theme} onToggle={toggleTheme} />
          <HelpButton onOpen={() => setIntroOpen(true)} />
          <button type="button" className="btn-compare btn-compare--desk" onClick={openDesk}>
            Кабинет
          </button>
          <button type="button" className="btn-compare" onClick={openCalls}>
            Обзвон
            <span className="btn-compare__count">{counts.calling || 0}</span>
          </button>
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
            <span>{badge()}</span>
          </div>
          <ClientLogos />

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
                label="Регион" value={region || '—'} options={(meta && meta.regions) || []}
                open={menu === 'region'} onToggle={(v) => setMenu(v ? 'region' : null)}
                onSelect={changeRegion}
              />
              <Dropdown
                label="Город" value={city || '—'} options={cities}
                open={menu === 'city'} onToggle={(v) => setMenu(v ? 'city' : null)}
                onSelect={setCity}
              />
            </div>

          </div>
        </section>
      </div>

      <section className="wrap catalog">
        <div className="catalog__in">
          {filtersOpen && (
            <button type="button" className="scrim scrim--filters" aria-label="Закрыть фильтры"
              onClick={() => setFiltersOpen(false)} />
          )}

          <aside className={`filters${filtersOpen ? ' filters--open' : ''}`}>
            <div className="filters__head">
              <span>Фильтры</span>
              <button type="button" className="panel__close" onClick={() => setFiltersOpen(false)}>✕</button>
            </div>
            <FiltersPanel
              meta={meta} preset={preset} cats={cats} kinds={kinds}
              onlyDocs={onlyDocs} onlyVerified={onlyVerified} onlyContacts={onlyContacts}
              onlySafe={onlySafe} price={price} delivers={delivers}
              city={city === (meta && meta.labels.anyCity) ? '' : city}
              facets={facets} anyFilter={anyFilter}
              onPreset={changePreset}
              onExplain={() => { setExplainOpen(true); setFiltersOpen(false); }}
              onCat={toggleCat} onAllCats={() => setCats([])} onKind={toggleKind}
              onDocs={() => setOnlyDocs((v) => !v)}
              onVerified={() => setOnlyVerified((v) => !v)}
              onContacts={() => setOnlyContacts((v) => !v)}
              onSafe={() => setOnlySafe((v) => !v)}
              onPrice={setPrice}
              onDelivers={() => setDelivers((v) => !v)}
              onReset={resetAll}
              total={total} loading={loading}
              onApply={() => setFiltersOpen(false)}
            />
          </aside>

          <div className="results">
           <div className="board">
            <div className="results__bar">
              <button type="button" className="filters__toggle" onClick={() => setFiltersOpen(true)}>
                Фильтры{activeFilters ? ` · ${activeFilters}` : ''}
              </button>
              <div className="results__count">
                {loading ? 'Подбираем…' : `Найдено ${total}`}
                {presetTitle ? <span className="results__preset">{presetTitle}</span> : null}
              </div>
              <div className="results__sort">
                <Dropdown
                  label="Сортировка" value={sort || '—'} options={(meta && meta.sorts) || []}
                  open={menu === 'sort'} onToggle={(v) => setMenu(v ? 'sort' : null)}
                  onSelect={setSort}
                />
              </div>
            </div>

            <div className="tabs">
              <button
                type="button"
                className={`tab${statusFilter === '' ? ' tab--on' : ''}`}
                onClick={() => setStatusFilter('')}
              >
                Все
              </button>
              {((meta && meta.statuses) || []).filter((s) => s.id !== 'new').map((s) => (
                <button
                  type="button" key={s.id}
                  className={`tab${statusFilter === s.id ? ' tab--on' : ''}`}
                  onClick={() => setStatusFilter(statusFilter === s.id ? '' : s.id)}
                  disabled={!counts[s.id]}
                >
                  {s.title}
                  <span className="tab__count">{counts[s.id] || 0}</span>
                </button>
              ))}
            </div>

            {project && (
              <div className="projectbar">
                <span className="projectbar__tag">Проект</span>
                <b>{project.chain}</b>
                <span className="projectbar__need">{project.need}</span>
                <button type="button" onClick={() => { setProject(null); resetAll(); }}>
                  Снять
                </button>
              </div>
            )}

            {!loading && !error && facets && total > 0 && (
              <div className="summary">
                С контактами <b>{facets.withContacts}</b>, с документами <b>{facets.withDocs}</b>,
                профиль заполнен в среднем на <b>{facets.fullness}%</b>.
                {facets.risky ? (
                  <>
                    {' '}С замечаниями: <b>{facets.risky}</b>
                    {onlySafe ? ' — скрыты фильтром.' : ' — они в конце списка.'}
                  </>
                ) : null}
                {counts.calling ? <> В работе: <b>{counts.calling}</b>.</> : null}
                {counts.fit ? <> Подходят: <b>{counts.fit}</b>.</> : null}
              </div>
            )}

            {indexing && !loading && (
              <div className="notice">
                Индекс наполняется: {status.citiesDone} из {status.citiesTotal} городов
                {status.city ? `, сейчас ${status.city}` : ''}.
              </div>
            )}

            {loading && (
              <div className="list">
                {SKELETONS.map((i) => (
                  <article className="row row--skel" key={i} style={{ animationDelay: `${i * 0.04}s` }}>
                    <div className="row__main">
                      <div className="skel skel--title" />
                      <div className="skel skel--sub" />
                      <div className="skel skel--tags" />
                      <div className="skel skel--specs" />
                    </div>
                    <div className="row__side"><div className="skel skel--bar" /></div>
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
                <div className="list">
                  {items.map((s, i) => (
                    <SupplierCard
                      key={s.id} supplier={s} index={i % PER_PAGE}
                      statuses={(meta && meta.statuses) || []}
                      inCompare={compare.includes(s.id)}
                      compareFull={compare.length >= MAX_COMPARE && !compare.includes(s.id)}
                      onOpen={() => { setSelId(s.id); setMenu(null); }}
                      onCompare={() => toggleCompare(s.id)}
                      onStatus={(next) => changeStatus(s.id, next)}
                    />
                  ))}
                </div>

                <div className="more">
                  <span className="more__count">Показано {items.length} из {total}</span>
                  <a className="btn btn--ghost" href={exportUrl()} download>Выгрузить CSV</a>
                  {page < pages && (
                    <button
                      type="button" className="btn btn--ghost"
                      onClick={() => load(page + 1, true)} disabled={loadingMore}
                    >
                      {loadingMore ? 'Загружаем…' : 'Показать ещё'}
                    </button>
                  )}
                </div>
              </>
            )}

            {!loading && !error && items.length === 0 && (
              <div className="empty">
                <h3>{indexing ? 'Индекс ещё наполняется' : 'Под эти условия поставщиков нет'}</h3>
                <p>
                  {indexing
                    ? 'Города добавляются по очереди. Выберите город — он проиндексируется сразу.'
                    : relax.length
                      ? 'Вот что можно ослабить, чтобы поставщики появились:'
                      : 'Снимите часть фильтров или расширьте регион.'}
                </p>
                {relax.length > 0 && (
                  <div className="relax">
                    {relax.map((item) => (
                      <button
                        type="button" key={item.key} className="relax__item"
                        onClick={() => applyRelax(item)}
                      >
                        {item.title}
                        <span className="relax__count">{item.count}</span>
                      </button>
                    ))}
                  </div>
                )}
                <button type="button" className="btn btn--cyan" onClick={resetAll}>Сбросить всё</button>
              </div>
            )}
           </div>
          </div>
        </div>
      </section>

      <footer className="footer">
        <div className="wrap footer__in">
          <div>Goulash Поставщики — поиск поставщиков продуктов для общепита</div>
          <div>
            Источники: {((meta && meta.sources) || []).filter((s) => s.active).map((s) => s.title).join(', ')}
          </div>
        </div>
      </footer>

      {selected && (
        <SupplierPanel
          supplier={selected}
          statuses={(meta && meta.statuses) || []}
          note={notes[selected.id] !== undefined ? notes[selected.id] : selected.note}
          onNote={(v) => changeNote(selected.id, v)}
          onStatus={(next) => changeStatus(selected.id, next)}
          onComment={() => load(1, false)}
          inCompare={compare.includes(selected.id)}
          compareFull={compare.length >= MAX_COMPARE && !compare.includes(selected.id)}
          onCompare={() => toggleCompare(selected.id)}
          onClose={() => setSelId(null)}
        />
      )}

      {compareOpen && (
        <CompareModal
          items={compareItems} notes={notes} narrow={narrow}
          showcase={showcase}
          onShowcase={() => setCompare(showcase.slice(0, MAX_COMPARE).map((x) => x.id))}
          preset={preset} weights={weights}
          onClear={() => setCompare([])} onClose={() => setCompareOpen(false)}
        />
      )}

      {callsOpen && (
        <CallList
          working={calls.working} suggest={calls.suggest}
          statuses={(meta && meta.statuses) || []} loading={callsLoading}
          onStatus={changeStatus}
          onOpen={(id) => { setSelId(id); setCallsOpen(false); }}
          onClose={() => setCallsOpen(false)}
        />
      )}

      {deskOpen && (
        <Workspace
          data={desk} loading={deskLoading}
          statuses={(meta && meta.statuses) || []}
          onPick={pickProject}
          onOpen={(id) => { setSelId(id); setDeskOpen(false); }}
          onClose={() => setDeskOpen(false)}
        />
      )}

      {introOpen && meta && (
        <Intro
          weights={meta.presets.find((p) => p.id === 'balanced').weights}
          onDetails={() => { closeIntro(); setExplainOpen(true); }}
          onClose={closeIntro}
        />
      )}

      {explainOpen && meta && (
        <ScoreExplainer
          factors={meta.factors} presets={meta.presets} onClose={() => setExplainOpen(false)}
        />
      )}
    </>
  );
}
