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

export function score(s) {
  return typeof s.score === 'number' ? s.score : 0;
}

export function contactsOf(s) {
  const found = [
    s.phone && 'телефон',
    s.email && 'почта',
    s.site && s.site !== '—' && 'сайт',
  ].filter(Boolean);
  return found.length ? `есть ${found.join(', ')}` : 'контактов в источниках нет';
}

export function checkedAt(s) {
  if (!s.checkedAt) return '';
  return new Date(s.checkedAt * 1000).toLocaleDateString('ru-RU');
}

export const COMPARE_ROWS = [
  { label: 'Готовность к контакту', get: (s) => `${score(s)}% · ${dash(s.verdict)}`, mint: true },
  { label: 'Рейтинг данных', get: (s) => (s.rating ? `${s.rating.toFixed(1)} / 5` : '—') },
  { label: 'Город', get: (s) => dash(s.city) },
  { label: 'Регион работы', get: (s) => dash(s.geo || s.region) },
  { label: 'Минимальный заказ', get: (s) => dash(s.moq) },
  { label: 'Цена', get: (s) => dash(s.price) },
  { label: 'Документы', get: (s) => (s.certs.length ? s.certs.join(', ') : 'нет данных') },
  { label: 'Доставка', get: (s) => dash(s.delivery) },
  { label: 'Опт или производство', get: (s) => (s.wholesale ? 'да' : 'нет данных') },
  { label: 'Реквизиты', get: (s) => dash([s.inn && `ИНН ${s.inn}`, s.ogrn && `ОГРН ${s.ogrn}`].filter(Boolean).join(' · ')) },
  {
    label: 'Статус данных',
    get: (s) => (s.verified ? s.verifiedBy || 'подтверждено' : 'требует проверки'),
  },
  { label: 'Контакт', get: (s) => [s.phone, s.email].filter(Boolean).join(' · ') || '—' },
];
