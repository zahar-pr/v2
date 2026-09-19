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

export function placeOf(s) {
  return [s.city || s.area, distanceOf(s)].filter(Boolean).join(' · ');
}

export function ratingOf(s) {
  if (!s.reviews || !s.rating) return null;
  return { rating: s.rating.toFixed(1), reviews: s.reviews };
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
  { label: 'Тип поставщика', get: (s) => dash(s.typeTitle) },
  { label: 'Город', get: (s) => placeOf(s) || '—' },
  {
    label: 'Оценка команды',
    get: (s) => (s.commentsRating ? `${s.commentsRating} из 5 по ${s.commentsCount} комм.` : 'нет комментариев'),
  },
  { label: 'Отзывы', get: (s) => (ratingOf(s) ? `${s.rating} из 5 по ${s.reviews} отзывам` : 'нет в подключённых источниках') },
  { label: 'Статус в ФНС', get: (s) => dash(s.legalStatus) },
  { label: 'ОКВЭД', get: (s) => dash([s.okved, s.okvedName].filter(Boolean).join(' ')) },
  { label: 'Регион работы', get: (s) => dash(s.geo || s.region) },
  { label: 'Минимальный заказ', get: (s) => dash(s.moq) },
  { label: 'Цена', get: (s) => dash(s.priceList ? 'прайс-лист на сайте' : s.price) },
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
