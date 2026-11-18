'use strict';
// Choice-based learning suggestions; no scoring, profiling, storage, or network requests.
(function () {
  const form = document.getElementById('leader-form');
  const result = document.getElementById('leader-result');
  const error = document.getElementById('leader-error');
  if (!form || !result || !error) return;
  const roles = Object.freeze({
    specialist: 'Предложите данные и проведите отдельный этап кейса вместе с наставником; согласуйте полномочия с руководителем.',
    team: 'Организуйте совместный разбор функций, распределите действия и согласуйте решение с владельцем процесса.',
    sponsor: 'Уточните цель, ресурсы, границы полномочий и правила эскалации; помогите команде получить обратную связь.'
  });
  const skills = Object.freeze({
    systems: { title: 'Системное мышление', task: 'Нарисуйте поток одного заказа и обсудите, как изменение запаса повлияет на склад, продажи и финансы.', anchor: '#systems' },
    data: { title: 'Решения на основе данных', task: 'Проверьте источник, период и качество данных для одного показателя; отдельно запишите неизвестные.', anchor: '#data-skills' },
    people: { title: 'Взаимодействие и переговоры', task: 'Проведите короткий разбор с двумя функциями, зафиксируйте их интересы и согласуйте следующее действие.', anchor: '#people-skills' },
    change: { title: 'Изменения и ответственность', task: 'Подготовьте ограниченный пилот с владельцем решения, защитными показателями и условием остановки.', anchor: '#change-skills' }
  });
  function clear() { result.hidden = true; error.textContent = ''; document.getElementById('leader-role-advice').textContent = ''; document.getElementById('leader-skill-advice').textContent = ''; document.getElementById('leader-next').removeAttribute('href'); }
  form.addEventListener('change', clear);
  form.addEventListener('submit', event => {
    event.preventDefault(); clear();
    const roleKey = form.elements.namedItem('role').value;
    const skillKey = form.elements.namedItem('skill').value;
    const role = Object.hasOwn(roles, roleKey) ? roles[roleKey] : null;
    const skill = Object.hasOwn(skills, skillKey) ? skills[skillKey] : null;
    if (!role || !skill) { error.textContent = 'Выберите роль и направление развития из списка.'; return; }
    document.getElementById('leader-role-advice').textContent = role;
    document.getElementById('leader-skill-advice').textContent = `${skill.title}: ${skill.task}`;
    const next = document.getElementById('leader-next');
    next.href = skill.anchor;
    next.textContent = `Открыть материалы: ${skill.title}`;
    result.hidden = false;
  });
  form.querySelector('button[type="submit"]').disabled = false;
})();
