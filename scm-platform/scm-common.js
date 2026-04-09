// Общие функции для SCM-платформы

window.SCMData = (function() {
    // --- Работа с реестром аудитов ---
    function getAuditRegistry() {
        const reg = localStorage.getItem('audit_registry');
        return reg ? JSON.parse(reg) : [];
    }

    function saveAuditRegistry(registry) {
        localStorage.setItem('audit_registry', JSON.stringify(registry));
    }

    function addAudit(auditData) {
        const registry = getAuditRegistry();
        auditData.id = Date.now().toString();
        auditData.createdAt = new Date().toISOString();
        registry.push(auditData);
        saveAuditRegistry(registry);
        return auditData.id;
    }

    function getAuditById(id) {
        const registry = getAuditRegistry();
        return registry.find(a => a.id === id);
    }

    function updateAudit(id, newData) {
        let registry = getAuditRegistry();
        const index = registry.findIndex(a => a.id === id);
        if (index !== -1) {
            registry[index] = { ...registry[index], ...newData, updatedAt: new Date().toISOString() };
            saveAuditRegistry(registry);
        }
    }

    function deleteAudit(id) {
        let registry = getAuditRegistry();
        registry = registry.filter(a => a.id !== id);
        saveAuditRegistry(registry);
    }

    // --- Работа с KPI (сохранение/загрузка) ---
    function saveKPI(kpiId, data) {
        localStorage.setItem(`kpi_${kpiId}`, JSON.stringify({ ...data, timestamp: new Date().toISOString() }));
    }

    function loadKPI(kpiId) {
        const raw = localStorage.getItem(`kpi_${kpiId}`);
        return raw ? JSON.parse(raw) : null;
    }

    function getAllKPIs() {
        const kpis = ['otif', 'turnover', 'forecast', 'scm_cost', 'c2c'];
        const result = {};
        kpis.forEach(k => { result[k] = loadKPI(k); });
        return result;
    }

    // --- Работа с чек-листами (прогресс) ---
    function saveChecklist(category, itemsState) {
        localStorage.setItem(`checklist_${category}`, JSON.stringify(itemsState));
    }

    function loadChecklist(category) {
        const raw = localStorage.getItem(`checklist_${category}`);
        return raw ? JSON.parse(raw) : {};
    }

    // --- Прогресс дорожной карты ---
    function saveRoadmapProgress(phaseId, progress) {
        const all = JSON.parse(localStorage.getItem('roadmap_progress') || '{}');
        all[phaseId] = progress;
        localStorage.setItem('roadmap_progress', JSON.stringify(all));
    }

    function loadRoadmapProgress() {
        return JSON.parse(localStorage.getItem('roadmap_progress') || '{}');
    }

    // --- Результаты аудита (последний) ---
    function saveAuditResult(result) {
        localStorage.setItem('last_audit_result', JSON.stringify(result));
    }

    function getLastAuditResult() {
        const raw = localStorage.getItem('last_audit_result');
        return raw ? JSON.parse(raw) : null;
    }

    // --- Экспорт всех данных (для отладки/бэкапа) ---
    function exportAllData() {
        const keys = Object.keys(localStorage).filter(k => k.startsWith('kpi_') || k.startsWith('checklist_') || k === 'audit_registry' || k === 'roadmap_progress');
        const data = {};
        keys.forEach(k => { data[k] = localStorage.getItem(k); });
        return JSON.stringify(data, null, 2);
    }

    function importAllData(jsonStr) {
        try {
            const data = JSON.parse(jsonStr);
            for (const [key, value] of Object.entries(data)) {
                localStorage.setItem(key, value);
            }
            return true;
        } catch(e) { return false; }
    }

    return {
        // аудит
        getAuditRegistry,
        saveAuditRegistry,
        addAudit,
        getAuditById,
        updateAudit,
        deleteAudit,
        // KPI
        saveKPI,
        loadKPI,
        getAllKPIs,
        // чек-листы
        saveChecklist,
        loadChecklist,
        // дорожная карта
        saveRoadmapProgress,
        loadRoadmapProgress,
        // аудит результат
        saveAuditResult,
        getLastAuditResult,
        // экспорт/импорт
        exportAllData,
        importAllData
    };
})();

// Вспомогательная функция для инициализации навигации (подсветка активного пункта)
document.addEventListener('DOMContentLoaded', () => {
    const currentPage = window.location.pathname.split('/').pop();
    const links = document.querySelectorAll('.sidebar nav a');
    links.forEach(link => {
        const href = link.getAttribute('href');
        if (href === currentPage) link.classList.add('active');
        else if (currentPage === '' && href === 'dashboard.html') link.classList.add('active');
    });

    // Бургер-меню для мобильных (если есть кнопка)
    const toggleBtn = document.querySelector('.menu-toggle');
    if (toggleBtn) {
        const sidebar = document.querySelector('.sidebar');
        toggleBtn.addEventListener('click', () => sidebar.classList.toggle('open'));
    }
});
