export function dash(value) {
  return value === null || value === undefined || value === '' ? '—' : value;
}

export function plural(n, one, few, many) {
  const m10 = n % 10;
  const m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 10 || m100 >= 20)) return few;
  return many;
}

export function statusTitle(status, statuses) {
  const found = (statuses || []).find((item) => item.id === status);
  return found ? found.title : status;
}

export function placeOf(s) {
  return [s.city || s.area, distanceOf(s)].filter(Boolean).join(' · ');
}

export function ratingOf(s) {
  if (!s.rating || !s.reviewsSource) return null;
  return { rating: s.rating.toFixed(1), reviews: s.reviews || 0, source: s.reviewsSource };
}

export function distanceOf(s) {
  if (s.distanceKm === null || s.distanceKm === undefined) return '';
  return `${Math.round(s.distanceKm)} км от центра`;
}

export function strongest(s) {
  const ranked = [...s.factors].sort((a, b) => b.score * b.weight - a.score * a.weight);
  const found = ranked.find((f) => f.plus.length);
  return found ? { title: found.title, text: found.plus[0] } : null;
}

export function weakest(s) {
  const ranked = [...s.factors].sort(
    (a, b) => (100 - b.score) * b.weight - (100 - a.score) * a.weight
  );
  const found = ranked.find((f) => f.minus.length);
  return found ? { title: found.title, text: found.minus[0] } : null;
}

export function checkedAt(s) {
  if (!s.checkedAt) return '';
  return new Date(s.checkedAt * 1000).toLocaleDateString('ru-RU');
}

export function weightsToString(weights) {
  return Object.entries(weights)
    .map(([key, value]) => `${key}:${value}`)
    .join(',');
}

export const COMPARE_ROWS = [
  { label: 'Приоритет звонка', get: (s) => `${s.score} из 100 · ${dash(s.verdict)}`, mint: true },
  { label: 'Санитарная история', get: (s) => s.safety.title, mint: true },
  {
    label: 'Ограничение сейчас',
    get: (s) => {
      if (!s.safety.incident) return 'решений надзора не найдено';
      return s.safety.incident.active ? 'действует' : `снято ${s.safety.incident.until}`;
    },
  },
  {
    label: 'Уровень цен',
    get: (s) => s.priceLevel.title + (s.priceLevel.estimate ? ' (оценка)' : ''),
    mint: true,
  },
  { label: 'Почему такой уровень', get: (s) => s.priceLevel.why[0] || '—' },
  {
    label: 'Куда возит',
    get: (s) => s.coverage.reason
      || (s.coverage.all ? 'по всей России' : s.coverage.regions.join(', ') || '—'),
  },
  { label: 'Профиль заполнен', get: (s) => `${s.profile.percent}% · ${s.profile.filled} из ${s.profile.total} полей` },
  {
    label: 'Проверка поставщика',
    get: (s) => {
      if (s.trustTier === 'trusted') return `поставщик сетей: ${s.clients.join(', ') || 'HoReCa'}`;
      if (s.trustTier === 'blocked') return 'в списке санитарных решений';
      return 'в кураторских списках нет';
    },
  },
  { label: 'Тип поставщика', get: (s) => dash(s.typeTitle) },
  { label: 'Город', get: (s) => placeOf(s) || '—' },
  {
    label: 'Оценка команды',
    get: (s) => (s.commentsRating ? `${s.commentsRating} из 5 по ${s.commentsCount} комм.` : 'нет комментариев'),
  },
  {
    label: 'Внешние отзывы',
    get: (s) => {
      const box = s.reviewsSummary || {};
      if (box.externalAverage === null || box.externalAverage === undefined) {
        return 'нет в подключённых источниках';
      }
      const count = box.externalCount
        ? ` по ${box.externalCount} ${plural(box.externalCount, 'отзыву', 'отзывам', 'отзывам')}`
        : '';
      return `${box.externalAverage} из 5${count}`;
    },
  },
  { label: 'Статус в ФНС', get: (s) => dash(s.legalStatus) },
  { label: 'ОКВЭД', get: (s) => dash([s.okved, s.okvedName].filter(Boolean).join(' ')) },
  { label: 'Регион работы', get: (s) => dash(s.geo || s.region) },
  { label: 'Минимальный заказ', get: (s) => dash(s.moq) },
  { label: 'Цена из источников', get: (s) => dash(s.priceList ? 'прайс-лист на сайте' : s.price) },
  { label: 'Документы', get: (s) => (s.certs.length ? s.certs.join(', ') : 'не найдены') },
  { label: 'Доставка', get: (s) => dash(s.delivery) },
  { label: 'Юрлицо', get: (s) => dash(s.legalName) },
  { label: 'Руководитель', get: (s) => dash(s.legalHead) },
  {
    label: 'Реквизиты',
    get: (s) => dash([s.inn && `ИНН ${s.inn}`, s.ogrn && `ОГРН ${s.ogrn}`].filter(Boolean).join(' · ')),
  },
  { label: 'На рынке', get: (s) => dash(s.years) },
  {
    label: 'Статус данных',
    get: (s) => (s.verified ? s.verifiedBy || 'подтверждено' : 'требует проверки'),
  },
  { label: 'Контакт', get: (s) => [s.phone, s.email].filter(Boolean).join(' · ') || '—' },
];

export function ageText(days) {
  if (days === null || days === undefined) return '';
  if (days === 0) return 'сегодня';
  if (days === 1) return 'вчера';
  return `${days} ${plural(days, 'день', 'дня', 'дней')} назад`;
}

export function quoteLetter(s) {
  const subject = `Запрос коммерческого предложения — ${s.name}`;
  const gaps = (s.profile ? s.profile.missing : []).map((item) => item.title);
  const need = (title, line) => (gaps.includes(title) ? [line] : []);

  const body = [
    'Здравствуйте!',
    '',
    `Мы закупаем продукты для сети общепита, направление «${s.cats[0] || 'продукты'}».`,
    'Просим прислать коммерческое предложение и документы:',
    '',
    ...need('Цена', '— актуальный прайс-лист;'),
    ...need('Минимальный заказ', '— минимальный заказ и шаг отгрузки;'),
    ...need('Доставка', `— сроки и стоимость доставки${s.city ? ` в ${s.city}` : ''};`),
    ...need('Документы', '— декларации ТР ТС и протоколы лабораторных испытаний;'),
    ...need('ИНН', '— ИНН и реквизиты для проверки юрлица;'),
    ...need('География поставок', '— в какие города возите своим транспортом;'),
    '— условия оплаты и возможность отсрочки;',
    '— контакт менеджера, который ведёт сетевых клиентов.',
    '',
    'Если по части пунктов есть готовая презентация — пришлите её, сэкономим время.',
    '',
    'Спасибо, ждём ответа.',
  ].join('\n');
  return `mailto:${s.email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}
