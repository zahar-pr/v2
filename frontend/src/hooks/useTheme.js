import { useEffect, useState } from 'react';

const KEY = 'provizia_theme';

function saved() {
  try {
    const value = localStorage.getItem(KEY);
    return value === 'dark' || value === 'light' ? value : '';
  } catch (error) {
    return '';
  }
}

/**
 * Тема страницы. По умолчанию светлая — тёмную включают кнопкой, и тогда выбор
 * запоминается. Системную настройку не подхватываем: сервис задуман светлым.
 */
export default function useTheme() {
  const [theme, setTheme] = useState(() => saved() || 'light');

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const toggle = () => {
    const next = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    try {
      localStorage.setItem(KEY, next);
    } catch (error) {
      // приватный режим: тема продержится до перезагрузки
    }
  };

  return [theme, toggle];
}
