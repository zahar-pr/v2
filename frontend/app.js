'use strict';

const $ = (id) => document.getElementById(id);

fetch('/api/options')
  .then((response) => response.json())
  .then((options) => {
    $('category').innerHTML = options.categories
      .map((item) => `<option value="${item.id}">${item.title}</option>`)
      .join('');
    $('place').innerHTML = options.places
      .map((city) => `<option>${city}</option>`)
      .join('');
    $('category').value = options.defaults.category;
    $('place').value = options.defaults.place;
  });

$('search').onsubmit = async (event) => {
  event.preventDefault();
  $('status').textContent = 'Загрузка данных о поставщиках, ...';
  $('results').innerHTML = '';

  try {
    const query = new URLSearchParams({
      place: $('place').value,
      category: $('category').value,
    });
    const response = await fetch('/api/search?' + query);
    const answer = await response.json();

    if (!response.ok) {
      throw new Error(answer.detail);
    }

    $('status').textContent = '';
    $('results').innerHTML = answer.html;
  } catch (error) {
    $('status').textContent = error.message || 'К сожалению ничего не нашлось, выберите другой город/поставщика';
  }
};
