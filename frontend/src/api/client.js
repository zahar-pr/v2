const BASE = import.meta.env.VITE_API_URL || '';

async function call(path, options) {
  let response;
  try {
    response = await fetch(BASE + path, options);
  } catch (error) {
    throw new Error('Сервис недоступен. Проверьте, запущен ли бэкенд.');
  }

  const answer = await response.json().catch(() => null);

  if (!response.ok) {
    throw new Error((answer && answer.detail) || `Ошибка ${response.status}`);
  }

  return answer;
}

function json(path, body, method = 'POST') {
  return call(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

export function getMeta() {
  return call('/api/meta');
}

export function getStatus() {
  return call('/api/status');
}

export function getSuppliers(filters) {
  const query = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== '' && value !== undefined && value !== null && value !== false) {
      query.set(key, String(value));
    }
  });
  return call('/api/suppliers?' + query);
}

export function getNotes() {
  return call('/api/notes');
}

export function saveNote(supplierId, text) {
  return json('/api/notes', { supplierId, text });
}

export function recommend(ids) {
  return json('/api/compare/recommend', { ids });
}
