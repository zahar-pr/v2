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

function query(filters) {
  const search = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== '' && value !== undefined && value !== null && value !== false) {
      search.set(key, String(value));
    }
  });
  return search;
}

export function getMeta() {
  return call('/api/meta');
}

export function getWorkspace() {
  return call('/api/workspace');
}

export function getStatus() {
  return call('/api/status');
}

export function getSuppliers(filters) {
  return call('/api/suppliers?' + query(filters));
}

export function getCallList(filters) {
  return call('/api/calllist?' + query(filters));
}

export function getNotes() {
  return call('/api/notes');
}

export function saveNote(supplierId, text) {
  return json('/api/notes', { supplierId, text });
}

export function setStatus(supplierId, status) {
  return json('/api/pipeline', { supplierId, status });
}

export function recommend(ids, preset, weights) {
  return json('/api/compare/recommend', { ids, preset, weights });
}

export function getComments(supplierId) {
  return call('/api/comments/' + supplierId);
}

export function addComment(supplierId, text, rating, author) {
  return json('/api/comments', { supplierId, text, rating, author });
}

export function deleteComment(id) {
  return call('/api/comments/' + id, { method: 'DELETE' });
}

export function saveProfile(name) {
  return json('/api/profile', { name });
}

export function setCheck(supplierId, question, done) {
  return json('/api/checks', { supplierId, question, done });
}
