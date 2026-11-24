'use strict';
const printButton = document.getElementById('print-checklist');
if (printButton) printButton.addEventListener('click', () => window.print());
